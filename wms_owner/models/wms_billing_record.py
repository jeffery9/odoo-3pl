from odoo import models, fields, api


class WmsBillingRecord(models.Model):
    _name = 'wms.billing.record'
    _description = 'WMS Billing Record'

    name = fields.Char('Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    operation_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('storage', 'Storage'),
        ('value_added', 'Value Added Service'),
        ('special_handling', 'Special Handling'),
    ], 'Operation Type', required=True)
    service_type = fields.Char('Service Type')
    operation_date = fields.Datetime('Operation Date', required=True)
    quantity = fields.Float('Quantity')
    unit_price = fields.Float('Unit Price')
    amount = fields.Float('Amount', compute='_compute_amount', store=True)
    related_move_id = fields.Many2one('stock.move', 'Related Move')
    related_picking_id = fields.Many2one('stock.picking', 'Related Picking')
    billing_rule_id = fields.Many2one('wms.billing.rule', 'Billing Rule')
    invoice_id = fields.Many2one('account.move', 'Invoice')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
    ], 'State', default='draft')
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.billing.record') or '/'
        return super().create(vals)

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for record in self:
            record.amount = record.quantity * record.unit_price

    def action_confirm(self):
        self.write({'state': 'confirmed'})
    def action_create_invoice(self):
        """Create an invoice for the billing records"""
        # This would create an invoice in the accounting module
        for record in self:
            if record.state != 'confirmed':
                continue

            # Create invoice logic here
            invoice_vals = {
                'partner_id': record.owner_id.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': [(0, 0, {
                    'name': f'{record.operation_type} - {record.service_type or ""}',
                    'quantity': record.quantity,
                    'price_unit': record.unit_price,
                    'account_id': self.env['account.account'].search([
                        ('user_type_id.type', '=', 'income')
                    ], limit=1).id
                })]
            }
            invoice = self.env['account.move'].create(invoice_vals)
            record.invoice_id = invoice.id
            record.state = 'invoiced'