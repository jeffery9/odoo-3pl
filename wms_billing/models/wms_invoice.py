from odoo import models, fields, api


class WmsInvoice(models.Model):
    _name = 'wms.invoice'
    _description = 'WMS Invoice'

    # Instead of inheriting from account.move (which can cause field conflicts),
    # create a relationship to account.move
    account_move_id = fields.Many2one('account.move', string='Account Move', ondelete='cascade')

    # Copy relevant fields from account.move that are needed for WMS billing
    name = fields.Char(related='account_move_id.name', string='Invoice Number', store=True)
    partner_id = fields.Many2one('res.partner', related='account_move_id.partner_id', string='Customer', store=True)
    date = fields.Date(related='account_move_id.date', string='Invoice Date', store=True)
    state = fields.Selection(related='account_move_id.state', string='Status', store=True)
    amount_total = fields.Monetary(related='account_move_id.amount_total', string='Total', store=True)
    currency_id = fields.Many2one('res.currency', related='account_move_id.currency_id', string='Currency', store=True)

    billing_records_ids = fields.Many2many(
        'wms.billing.record',
        'wms_invoice_billing_record_rel',
        'invoice_id',
        'billing_record_id',
        string='Billing Records'
    )
    owner_id = fields.Many2one('wms.owner', 'Owner', compute='_compute_owner', store=True)
    billing_period_start = fields.Date('Billing Period Start')
    billing_period_end = fields.Date('Billing Period End')

    @api.depends('partner_id')
    def _compute_owner(self):
        for invoice in self:
            # Try to find the owner based on the partner
            owner = self.env['wms.owner'].search([('partner_id', '=', invoice.partner_id.id)], limit=1)
            invoice.owner_id = owner

    def action_post_invoice(self):
        """Post the related account move when this WMS invoice is processed"""
        # Update billing records state when invoice is processed
        for invoice in self:
            if invoice.billing_records_ids:
                invoice.billing_records_ids.write({'state': 'invoiced'})

        # If there's an associated account move, post it
        if self.account_move_id:
            return self.account_move_id._post()
        return True

    def mark_as_paid_invoice(self):
        """Mark the related account move as paid when this WMS invoice is paid"""
        # Update related billing records
        for invoice in self:
            if invoice.billing_records_ids:
                invoice.billing_records_ids.write({'state': 'paid'})

        # If there's an associated account move, mark it as paid
        if self.account_move_id:
            # Create a wizard to register payment
            return {
                'name': 'Register Payment',
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'context': {
                    'active_id': self.account_move_id.id,
                    'active_ids': [self.account_move_id.id],
                    'active_model': 'account.move',
                },
                'target': 'new',
            }
        return True