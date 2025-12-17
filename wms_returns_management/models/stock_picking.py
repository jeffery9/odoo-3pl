from odoo import models, fields, api


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
                'default_owner_id': self.owner_id.id if hasattr(self, 'owner_id') and self.owner_id else False,
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