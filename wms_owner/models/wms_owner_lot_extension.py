from odoo import models, fields, api


class WmsOwnerLotExtension(models.Model):
    _inherit = 'wms.owner'

    # Add lot-related fields to owner
    lot_ids = fields.One2many('stock.lot', compute='_compute_lots', string='Owner Lots/Serials')
    lot_count = fields.Integer('Lot Count', compute='_compute_lot_count')

    def _compute_lots(self):
        """Compute all lots associated with this owner"""
        for owner in self:
            # Find all lots related to moves/pickings for this owner
            lots = self.env['stock.lot'].search([
                ('quant_ids.owner_id', '=', owner.id)
            ])
            owner.lot_ids = lots

    def _compute_lot_count(self):
        """Compute count of lots for this owner"""
        for owner in self:
            owner.lot_count = len(owner.lot_ids)

    def action_view_lots(self):
        """View all lots associated with this owner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Owner Lots/Serial Numbers',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('quant_ids.owner_id', '=', self.id)],
            'context': {'default_company_id': self.company_id.id if self.company_id else False}
        }