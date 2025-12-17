from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    blind_receive_ids = fields.One2many('wms.blind.receive', 'picking_id', 'Blind Receive Sessions')
    blind_receive_count = fields.Integer('Blind Receive Count', compute='_compute_blind_receive_count')

    @api.depends('blind_receive_ids')
    def _compute_blind_receive_count(self):
        for picking in self:
            picking.blind_receive_count = len(picking.blind_receive_ids)

    def action_start_blind_receive(self):
        """Start a blind receive session for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.blind.receive.create.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id, 'default_owner_id': self.owner_id.id if hasattr(self, 'owner_id') and self.owner_id else False}
        }

    def action_view_blind_receive(self):
        """View blind receive sessions for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Blind Receive Sessions',
            'res_model': 'wms.blind.receive',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id}
        }