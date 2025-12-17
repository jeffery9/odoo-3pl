from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WmsReturnAuthorization(models.Model):
    _name = 'wms.return.authorization'
    _description = 'Return Merchandise Authorization (RMA)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char('RMA Number', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True,
                               default=lambda self: self.env['wms.owner'].get_default_owner())
    sale_order_id = fields.Many2one('sale.order', 'Original Sale Order')
    purchase_order_id = fields.Many2one('purchase.order', 'Original Purchase Order')
    customer_id = fields.Many2one('res.partner', 'Customer', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    origin = fields.Char('Source Document')
    date_issued = fields.Datetime('Date Issued', default=fields.Datetime.now, required=True)
    date_deadline = fields.Datetime('Return Deadline')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('received', 'Received'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    return_reason = fields.Selection([
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item Sent'),
        ('no_longer_needed', 'No Longer Needed'),
        ('damaged', 'Damaged in Transit'),
        ('not_as_described', 'Not as Described'),
        ('change_of_mind', 'Change of Mind'),
        ('other', 'Other'),
    ], string='Return Reason', required=True)
    return_reason_description = fields.Text('Return Reason Details')
    return_method = fields.Selection([
        ('pick_up', 'Pick Up'),
        ('ship_back', 'Ship Back'),
        ('drop_off', 'Drop Off'),
    ], string='Return Method', default='ship_back')
    return_cost = fields.Float('Return Shipping Cost', digits='Product Price')

    # Product Lines
    return_line_ids = fields.One2many('wms.return.line', 'rma_id', 'Return Lines')
    product_qty = fields.Float('Total Quantity', compute='_compute_product_qty', store=True)

    # Financial Information
    refund_amount = fields.Float('Refund Amount', digits='Product Price')
    refund_reference = fields.Char('Refund Reference')
    refund_date = fields.Datetime('Refund Date')

    # Quality Control
    qc_required = fields.Boolean('Quality Control Required', default=True)
    qc_completed = fields.Boolean('Quality Control Completed', default=False)
    qc_notes = fields.Text('Quality Control Notes')

    # Disposition
    disposition = fields.Selection([
        ('refund', 'Full Refund'),
        ('exchange', 'Exchange'),
        ('credit', 'Store Credit'),
        ('repair', 'Repair and Return'),
        ('scrap', 'Scrap'),
        ('restock', 'Restock as-is'),
    ], string='Disposition')

    # Tracking
    carrier_id = fields.Many2one('delivery.carrier', 'Return Carrier')
    tracking_number = fields.Char('Return Tracking Number')
    received_date = fields.Datetime('Date Received')

    # Additional Notes
    notes = fields.Text('Additional Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.return.authorization') or _('New')
        return super().create(vals)

    @api.depends('return_line_ids.quantity')
    def _compute_product_qty(self):
        for rma in self:
            rma.product_qty = sum(line.quantity for line in rma.return_line_ids)

    def action_confirm(self):
        """Confirm the RMA"""
        for rma in self:
            rma.state = 'confirmed'

    def action_send_for_return(self):
        """Send RMA for return processing"""
        for rma in self:
            if rma.state == 'confirmed':
                rma.state = 'in_transit'

    def action_receive_return(self):
        """Receive returned items"""
        for rma in self:
            if rma.state in ['in_transit', 'confirmed']:
                rma.state = 'received'
                rma.received_date = fields.Datetime.now()

    def action_approve(self):
        """Approve the return"""
        for rma in self:
            if rma.state == 'received':
                rma.state = 'approved'

    def action_reject(self):
        """Reject the return"""
        for rma in self:
            if rma.state in ['received', 'approved']:
                rma.state = 'rejected'

    def action_complete(self):
        """Complete the return process"""
        for rma in self:
            if rma.state in ['approved', 'rejected']:
                rma.state = 'completed'
                if rma.refund_amount > 0:
                    rma.refund_date = fields.Datetime.now()

    def action_cancel(self):
        """Cancel the RMA"""
        for rma in self:
            if rma.state in ['draft', 'confirmed']:
                rma.state = 'cancelled'


class WmsReturnLine(models.Model):
    _name = 'wms.return.line'
    _description = 'Return Line'

    rma_id = fields.Many2one('wms.return.authorization', 'RMA', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    quantity = fields.Float('Quantity', default=1.0, required=True)
    unit_price = fields.Float('Unit Price', digits='Product Price')
    subtotal = fields.Float('Subtotal', compute='_compute_subtotal', store=True)
    reason = fields.Char('Reason for Return')
    condition = fields.Selection([
        ('new', 'New'),
        ('used_good', 'Used - Good'),
        ('used_fair', 'Used - Fair'),
        ('damaged', 'Damaged'),
        ('defective', 'Defective'),
    ], string='Item Condition', default='new')
    notes = fields.Text('Notes')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')
    location_id = fields.Many2one('stock.location', 'Return Location')

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.unit_price = self.product_id.list_price


class WmsReturnReason(models.Model):
    _name = 'wms.return.reason'
    _description = 'Return Reason'
    _order = 'name'

    name = fields.Char('Reason', required=True)
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)
    category = fields.Selection([
        ('quality', 'Quality Issue'),
        ('logistics', 'Logistics Issue'),
        ('customer', 'Customer Request'),
        ('other', 'Other'),
    ], string='Category', default='quality')


class WmsReturnDisposition(models.Model):
    _name = 'wms.return.disposition'
    _description = 'Return Disposition'
    _order = 'name'

    name = fields.Char('Disposition', required=True)
    description = fields.Text('Description')
    action_type = fields.Selection([
        ('refund', 'Refund'),
        ('exchange', 'Exchange'),
        ('credit', 'Credit'),
        ('repair', 'Repair'),
        ('scrap', 'Scrap'),
        ('restock', 'Restock'),
    ], string='Action Type', required=True)
    active = fields.Boolean('Active', default=True)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    rma_ids = fields.One2many('wms.return.authorization', 'sale_order_id',
                              string='RMAs',
                              domain=['|', ('sale_order_id', '!=', False),
                                     ('origin', '=', 'return')])
    rma_count = fields.Integer('RMA Count', compute='_compute_rma_count')

    @api.depends('rma_ids')
    def _compute_rma_count(self):
        for picking in self:
            picking.rma_count = len(picking.rma_ids)

    def action_create_rma(self):
        """Create a new RMA for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.return.authorization',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.sale_order_id.id if hasattr(self, 'sale_order_id') and self.sale_order_id else False,
                'default_origin': self.name,
                'default_customer_id': self.partner_id.id,
                'default_warehouse_id': self.picking_type_id.warehouse_id.id,
            }
        }

    def action_view_rmas(self):
        """View RMAs for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'RMAs',
            'res_model': 'wms.return.authorization',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
            'context': {'default_origin': self.name}
        }