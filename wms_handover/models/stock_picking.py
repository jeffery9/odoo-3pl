from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    handover_ids = fields.One2many('wms.handover', 'picking_id', 'Handovers')
    handover_count = fields.Integer('Handover Count', compute='_compute_handover_count')

    @api.depends('handover_ids')
    def _compute_handover_count(self):
        for picking in self:
            picking.handover_count = len(picking.handover_ids)

    def action_create_handover(self):
        """Create a handover session for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.handover.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id}
        }

    def action_view_handovers(self):
        """View handovers for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Handovers',
            'res_model': 'wms.handover',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id}
        }