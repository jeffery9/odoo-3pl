from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Add 3PL-specific fields to stock moves
    owner_id = fields.Many2one(
        'wms.owner',
        string='3PL Owner',
        help='Owner of the goods for multi-owner scenarios'
    )
    cargo_type_id = fields.Many2one(
        'wms.cargo.type',
        string='Cargo Type',
        help='Cargo type for this move'
    )
    workzone_id = fields.Many2one(
        'wms.workzone',
        string='Work Zone',
        help='Work zone this move belongs to'
    )
    storage_category_id = fields.Many2one(
        'stock.storage.category',
        string='Storage Category',
        help='Storage category for this move'
    )
    abc_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')
    ], 'ABC Category', help='ABC classification for the move')

    # Additional lot integration fields
    lot_ids = fields.Many2many('stock.lot', string='Lot/Serial Numbers',
                               compute='_compute_lot_ids', help='All lot/serial numbers associated with this move')
    def _compute_lot_ids(self):
        """Compute lot_ids for this move based on move lines"""
        for move in self:
            move.lot_ids = move.move_line_ids.mapped('lot_id')