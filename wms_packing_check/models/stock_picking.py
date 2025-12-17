from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    packing_check_ids = fields.One2many('wms.packing.check', 'picking_id', 'Packing Checks')
    packing_check_count = fields.Integer('Packing Check Count', compute='_compute_packing_check_count')

    @api.depends('packing_check_ids')
    def _compute_packing_check_count(self):
        for picking in self:
            picking.packing_check_count = len(picking.packing_check_ids)

    def action_start_packing_check(self):
        """Start a packing check session for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.start.packing.check.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id, 'default_owner_id': self.owner_id.id if hasattr(self, 'owner_id') and self.owner_id else False}
        }

    def action_view_packing_checks(self):
        """View packing checks for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Packing Checks',
            'res_model': 'wms.packing.check',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id}
        }