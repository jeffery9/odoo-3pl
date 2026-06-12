from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    # Add 3PL-specific fields to stock location
    wms_storage_area_id = fields.Many2one(
        'wms.storage.area',
        string='3PL Storage Area',
        help='Link to 3PL-specific storage area for grouping locations'
    )
    cargo_type_id = fields.Many2one(
        'wms.cargo.type',
        string='Cargo Type',
        help='Define cargo type restrictions for this location'
    )
    workzone_id = fields.Many2one(
        'wms.workzone',
        string='Work Zone',
        help='Physical work zone this location belongs to'
    )
    owner_id = fields.Many2one(
        'wms.owner',
        string='Owner',
        help='Specific owner this location is reserved for (in multi-owner scenarios)'
    )

    # Lot tracking enhancements for locations
    lot_ids = fields.Many2many('stock.lot', compute='_compute_lot_ids', string='Lots in Location')
    def _compute_lot_ids(self):
        """Compute all lots currently in this location"""
        for location in self:
            quants = self.env['stock.quant'].search([('location_id', '=', location.id), ('lot_id', '!=', False)])
            location.lot_ids = quants.mapped('lot_id')