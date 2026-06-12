from odoo import models, fields


class WmsStorageArea(models.Model):
    _name = 'wms.storage.area'
    _description = 'Storage Area'

    name = fields.Char('Area Name', required=True)
    code = fields.Char('Area Code', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    area_type = fields.Selection([
        ('high_rack', 'High Rack'),
        ('floor_stack', 'Floor Stack'),
        ('cold_storage', 'Cold Storage'),
        ('hazmat', 'Hazardous Materials'),
        ('fast_moving', 'Fast Moving'),
        ('slow_moving', 'Slow Moving'),
        ('reserved', 'Reserved Area'),
        ('transit', 'Transit Area'),
    ], 'Area Type')
    location_ids = fields.Many2many('stock.location', 'area_location_rel',
                                    'area_id', 'location_id', 'Locations')
    # Link to native storage category for advanced capacity and restriction management
    storage_category_id = fields.Many2one(
        'stock.storage.category', string='Storage Category',
        help='Native Odoo 18 storage category for enhanced capacity and restriction management'
    )
    capacity = fields.Float('Capacity (CBM)')
    used_capacity = fields.Float('Used Capacity (CBM)', compute='_compute_used_capacity')
    utilization_rate = fields.Float('Utilization Rate (%)', compute='_compute_utilization_rate')
    active = fields.Boolean('Active', default=True)
    def _compute_used_capacity(self):
        for area in self:
            area.used_capacity = 0.0  # This would be computed based on actual inventory

    def _compute_utilization_rate(self):
        for area in self:
            if area.capacity > 0:
                area.utilization_rate = (area.used_capacity / area.capacity) * 100
            else:
                area.utilization_rate = 0.0

    def assign_storage_category_to_locations(self):
        """Assign the storage category to all locations in this area"""
        for area in self:
            if area.storage_category_id:
                area.location_ids.write({'storage_category_id': area.storage_category_id.id})