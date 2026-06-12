from odoo import models, fields


class StockTraceabilityReportLine(models.TransientModel):
    _name = 'wms.stock.traceability.report.line'
    _description = '3PL Traceability Report Line'
    _order = 'date desc'

    report_id = fields.Many2one('wms.stock.traceability.report', 'Report', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    move_id = fields.Many2one('stock.move', 'Stock Move')
    picking_id = fields.Many2one('stock.picking', 'Picking')
    location_from = fields.Many2one('stock.location', 'From Location')
    location_to = fields.Many2one('stock.location', 'To Location')
    quantity = fields.Float('Quantity')
    date = fields.Datetime('Date')
    owner_id = fields.Many2one('wms.owner', 'Owner')

    # 3PL-specific fields
    abc_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')
    ], 'ABC Category')

    # Computed fields for easier reporting
    product_name = fields.Char('Product Name', related='product_id.display_name', store=True)
    lot_name = fields.Char('Lot Name', related='lot_id.name', store=True)
    move_reference = fields.Char('Move Reference', related='move_id.reference', store=True)
    picking_name = fields.Char('Picking Name', related='picking_id.name', store=True)
    location_from_name = fields.Char('From Location Name', related='location_from.display_name', store=True)
    location_to_name = fields.Char('To Location Name', related='location_to.display_name', store=True)

    # Lot expiry date for better traceability
    lot_expiry_date = fields.Datetime(
        'Lot Expiry Date',
        compute='_compute_lot_expiry_date',
        readonly=True,
        store=False
    )
    lot_product_qty = fields.Float('Lot Quantity', related='lot_id.product_qty', readonly=True)
    def _compute_lot_expiry_date(self):
        """Safely compute lot expiry date, handling cases where expiry_date field doesn't exist"""
        for line in self:
            if line.lot_id and hasattr(line.lot_id, 'expiry_date'):
                line.lot_expiry_date = line.lot_id.expiry_date
            else:
                line.lot_expiry_date = False