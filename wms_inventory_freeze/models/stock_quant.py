from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    is_frozen = fields.Boolean('Is Frozen', compute='_compute_is_frozen', store=True, compute_sudo=True)
    freeze_ids = fields.One2many('wms.inventory.freeze', compute='_compute_freeze_ids')

    @api.depends('location_id', 'product_id', 'lot_id', 'quantity')
    def _compute_is_frozen(self):
        """Compute if this quant is frozen"""
        for quant in self:
            freeze_records = self.env['wms.inventory.freeze'].search([
                ('location_id', '=', quant.location_id.id),
                ('product_id', '=', quant.product_id.id),
                ('lot_id', '=', quant.lot_id.id),
                ('status', '=', 'frozen'),
                ('quantity', '<=', quant.quantity),  # Ensure freeze quantity doesn't exceed available
            ])
            quant.is_frozen = bool(freeze_records)
    def _compute_freeze_ids(self):
        """Compute related freeze records"""
        for quant in self:
            freeze_records = self.env['wms.inventory.freeze'].search([
                ('location_id', '=', quant.location_id.id),
                ('product_id', '=', quant.product_id.id),
                ('lot_id', '=', quant.lot_id.id),
                ('status', 'in', ['frozen', 'unfrozen']),
            ])
            quant.freeze_ids = freeze_records

    def action_freeze_inventory(self):
        """Action to freeze inventory for this quant"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.inventory.freeze.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_location_id': self.location_id.id,
                'default_product_id': self.product_id.id,
                'default_lot_id': self.lot_id.id,
                'default_quantity': self.quantity,
                'default_owner_id': self.owner_id.id if hasattr(self, 'owner_id') and self.owner_id else False
            }
        }