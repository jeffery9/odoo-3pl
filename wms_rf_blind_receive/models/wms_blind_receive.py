from odoo import models, fields, api


class WmsBlindReceive(models.Model):
    _name = 'wms.blind.receive'
    _description = 'WMS Blind Receive'
    _order = 'name desc'

    name = fields.Char('Blind Receive Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], 'Status', default='draft', required=True)
    expected_products = fields.One2many('wms.blind.receive.expected', 'blind_receive_id', 'Expected Products')
    received_products = fields.One2many('wms.blind.receive.received', 'blind_receive_id', 'Received Products')
    discrepancy_count = fields.Integer('Discrepancies', compute='_compute_discrepancies', store=True)
    notes = fields.Text('Notes')
    start_date = fields.Datetime('Start Date')
    completion_date = fields.Datetime('Completion Date')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.blind.receive') or '/'
        return super().create(vals)

    @api.depends('expected_products', 'received_products')
    def _compute_discrepancies(self):
        for record in self:
            # Count discrepancies between expected and received products
            discrepancies = 0
            for expected in record.expected_products:
                received_matches = record.received_products.filtered(
                    lambda r: r.product_id == expected.product_id
                )
                if received_matches:
                    for received in received_matches:
                        if received.quantity != expected.quantity:
                            discrepancies += 1
                else:
                    discrepancies += 1  # Expected product not received
            record.discrepancy_count = discrepancies

    def action_start_blind_receive(self):
        """Start the blind receive process"""
        self.write({
            'status': 'in_progress',
            'start_date': fields.Datetime.now()
        })

    def action_complete_blind_receive(self):
        """Complete the blind receive process"""
        self.write({
            'status': 'completed',
            'completion_date': fields.Datetime.now()
        })

    def action_cancel_blind_receive(self):
        """Cancel the blind receive process"""
        self.write({'status': 'cancelled'})

    def action_generate_report(self):
        """Generate discrepancy report"""
        self.ensure_one()
        # Check if the report action exists, if not show a notification
        try:
            report_action = self.env.ref('wms_rf_blind_receive.action_report_blind_receive')
            return report_action.report_action(self)
        except ValueError:
            # If the report action doesn't exist, show a notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Report Not Available',
                    'message': 'The discrepancy report is not yet configured for this module.',
                    'type': 'warning',
                    'sticky': True
                }
            }


class WmsBlindReceiveExpected(models.Model):
    _name = 'wms.blind.receive.expected'
    _description = 'WMS Blind Receive Expected Product'

    blind_receive_id = fields.Many2one('wms.blind.receive', 'Blind Receive', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    expected_quantity = fields.Float('Expected Quantity', required=True)
    lot_id = fields.Many2one('stock.lot', 'Expected Lot/Serial')
    uom_id = fields.Many2one('uom.uom', 'UOM', required=True)
    notes = fields.Text('Notes')
    owner_id = fields.Many2one('wms.owner', 'Owner', related='blind_receive_id.owner_id', store=True)


class WmsBlindReceiveReceived(models.Model):
    _name = 'wms.blind.receive.received'
    _description = 'WMS Blind Receive Received Product'

    blind_receive_id = fields.Many2one('wms.blind.receive', 'Blind Receive', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    received_quantity = fields.Float('Received Quantity', required=True)
    lot_id = fields.Many2one('stock.lot', 'Received Lot/Serial')
    uom_id = fields.Many2one('uom.uom', 'UOM', required=True)
    notes = fields.Text('Notes')
    received_by = fields.Many2one('res.users', 'Received By', default=lambda self: self.env.user)
    receive_date = fields.Datetime('Receive Date', default=fields.Datetime.now)
    is_matched = fields.Boolean('Matched', compute='_compute_is_matched', store=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', related='blind_receive_id.owner_id', store=True)

    @api.depends('product_id', 'received_quantity', 'blind_receive_id.expected_products')
    def _compute_is_matched(self):
        for record in self:
            if record.blind_receive_id and record.product_id:
                expected_matches = record.blind_receive_id.expected_products.filtered(
                    lambda e: e.product_id == record.product_id
                )
                record.is_matched = bool(expected_matches)
            else:
                record.is_matched = False

    def action_confirm_received(self):
        """Confirm received product"""
        self.ensure_one()
        # This could trigger additional validation or processing
        return True


class WmsBlindReceiveWizard(models.TransientModel):
    _name = 'wms.blind.receive.wizard'
    _description = 'WMS Blind Receive Wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    received_quantity = fields.Float('Received Quantity', required=True, default=1.0)
    blind_receive_id = fields.Many2one('wms.blind.receive', 'Blind Receive Session', required=True)

    def action_add_received_product(self):
        """Add received product to the blind receive session"""
        self.ensure_one()
        self.env['wms.blind.receive.received'].create({
            'blind_receive_id': self.blind_receive_id.id,
            'product_id': self.product_id.id,
            'received_quantity': self.received_quantity,
            'lot_id': self.lot_id.id,
            'uom_id': self.product_id.uom_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}


class WmsBlindReceiveCreateWizard(models.TransientModel):
    _name = 'wms.blind.receive.create.wizard'
    _description = 'WMS Blind Receive Create Wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)

    def action_create_blind_receive(self):
        """Create a new blind receive session from picking"""
        self.ensure_one()

        # Create the blind receive record
        blind_receive = self.env['wms.blind.receive'].create({
            'picking_id': self.picking_id.id,
            'owner_id': self.owner_id.id,
        })

        # Copy expected products from picking moves
        for move in self.picking_id.move_ids_without_package:
            self.env['wms.blind.receive.expected'].create({
                'blind_receive_id': blind_receive.id,
                'product_id': move.product_id.id,
                'expected_quantity': move.product_uom_qty,
                'uom_id': move.product_uom.id,
            })

        # Start the blind receive process
        blind_receive.action_start_blind_receive()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.blind.receive',
            'res_id': blind_receive.id,
            'view_mode': 'form',
            'target': 'current',
        }