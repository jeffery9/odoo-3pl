from odoo import models, fields, api


class WmsBillingRecord(models.Model):
    _name = 'wms.billing.record'
    _description = 'WMS Billing Record'
    _order = 'operation_date desc'

    name = fields.Char('Reference', required=True, copy=False, readonly=True, index=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    operation_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('storage', 'Storage'),
        ('value_added', 'Value Added Service'),
        ('special_handling', 'Special Handling'),
        ('pick_pack', 'Pick & Pack'),
        ('palletizing', 'Palletizing'),
        ('repackaging', 'Repackaging'),
    ], 'Operation Type', required=True)
    service_type = fields.Char('Service Type')
    operation_date = fields.Datetime('Operation Date', required=True, default=fields.Datetime.now)
    quantity = fields.Float('Quantity')
    unit_price = fields.Float('Unit Price')
    amount = fields.Float('Amount', compute='_compute_amount', store=True)
    related_move_id = fields.Many2one('stock.move', 'Related Move')
    related_picking_id = fields.Many2one('stock.picking', 'Related Picking')
    related_lot_id = fields.Many2one('stock.lot', 'Related Lot')
    billing_rule_id = fields.Many2one('wms.billing.rule', 'Billing Rule')
    invoice_id = fields.Many2one('account.move', 'Invoice')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], 'State', default='draft', required=True)
    notes = fields.Text('Notes')
    calculated_by = fields.Char('Calculated By')
    calculation_method = fields.Char('Calculation Method')

    @api.model_create_multi
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.billing.record') or '/'
        return super().create(vals)

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for record in self:
            if record.quantity and record.unit_price:
                amount = record.quantity * record.unit_price
                # Apply minimum charge if applicable
                if record.billing_rule_id and record.billing_rule_id.min_charge:
                    amount = max(amount, record.billing_rule_id.min_charge)
                # Apply maximum charge if applicable
                if record.billing_rule_id and record.billing_rule_id.max_charge:
                    amount = min(amount, record.billing_rule_id.max_charge)
                record.amount = amount
            else:
                record.amount = 0.0

    def action_confirm(self):
        self.write({'state': 'confirmed'})
    def action_create_invoice(self):
        """Create an invoice for the billing records"""
        for record in self:
            if record.state != 'confirmed':
                continue

            # Check if an invoice already exists
            if record.invoice_id:
                continue

            # Create invoice
            invoice_vals = {
                'partner_id': record.owner_id.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': [(0, 0, {
                    'name': f'{record.operation_type} - {record.service_type or ""}',
                    'quantity': record.quantity or 1,
                    'price_unit': record.unit_price,
                    'account_id': self.env['account.account'].search([
                        ('user_type_id.type', '=', 'income'),
                        ('company_id', '=', self.env.company.id)
                    ], limit=1).id
                })]
            }
            invoice = self.env['account.move'].create(invoice_vals)
            record.invoice_id = invoice.id
            record.state = 'invoiced'

    def action_mark_paid(self):
        self.write({'state': 'paid'})
    def action_cancel(self):
        self.write({'state': 'cancelled'})
    def action_reset_to_draft(self):
        self.write({'state': 'draft'})