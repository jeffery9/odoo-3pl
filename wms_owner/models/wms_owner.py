from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WmsOwner(models.Model):
    _name = 'wms.owner'
    _description = 'Warehouse Owner'
    _inherits = {'res.partner': 'partner_id'}

    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        required=True,
        ondelete='cascade'
    )
    owner_code = fields.Char('Owner Code', required=True, copy=False)
    storage_fee_rate = fields.Float('Storage Fee Rate (per day per unit)')
    inbound_fee = fields.Float('Inbound Handling Fee')
    outbound_fee = fields.Float('Outbound Handling Fee')
    min_charge = fields.Float('Minimum Charge')
    billing_cycle = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], 'Billing Cycle', default='monthly')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('owner_code_unique', 'UNIQUE(owner_code)', 'Owner code must be unique!')
    ]
    @api.model_create_multi
    def create(self, vals):
        if not vals.get('owner_code'):
            vals['owner_code'] = self.env['ir.sequence'].next_by_code('wms.owner.code') or '/'

        # Create the related partner
        partner_vals = {
            'name': vals.get('name'),
            'is_company': True,
            'is_warehouse_owner': True,
            'owner_code': vals.get('owner_code'),
        }
        partner = self.env['res.partner'].create(partner_vals)
        vals['partner_id'] = partner.id

        return super().create(vals)
    def write(self, vals):
        # Update the related partner
        if 'name' in vals or 'owner_code' in vals:
            partner_vals = {}
            if 'name' in vals:
                partner_vals['name'] = vals['name']
            if 'owner_code' in vals:
                partner_vals['owner_code'] = vals['owner_code']
                partner_vals['is_warehouse_owner'] = True
            if partner_vals:
                self.partner_id.write(partner_vals)

        return super().write(vals)
    def unlink(self):
        # Delete the related partner
        partners = self.mapped('partner_id')
        result = super().unlink()
        partners.unlink()
        return result