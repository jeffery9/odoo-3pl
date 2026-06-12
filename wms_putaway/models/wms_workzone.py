from odoo import models, fields


class WmsWorkzone(models.Model):
    _name = 'wms.workzone'
    _description = 'Work Zone'

    name = fields.Char('Work Zone Name', required=True)
    code = fields.Char('Code', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    zone_type = fields.Selection([
        ('receiving', 'Receiving'),
        ('storage', 'Storage'),
        ('picking', 'Picking'),
        ('packing', 'Packing'),
        ('shipping', 'Shipping'),
        ('quality', 'Quality Control'),
        ('returns', 'Returns'),
    ], 'Zone Type', required=True)
    location_ids = fields.Many2many('stock.location', 'workzone_location_rel',
                                    'workzone_id', 'location_id', 'Locations')
    responsible_user_ids = fields.Many2many('res.users', 'workzone_user_rel',
                                            'workzone_id', 'user_id', 'Responsible Users')
    capacity = fields.Float('Capacity (CBM)')
    current_utilization = fields.Float('Current Utilization (CBM)')
    utilization_rate = fields.Float('Utilization Rate (%)', compute='_compute_utilization_rate')
    active = fields.Boolean('Active', default=True)
    def _compute_utilization_rate(self):
        for zone in self:
            if zone.capacity > 0:
                zone.utilization_rate = (zone.current_utilization / zone.capacity) * 100
            else:
                zone.utilization_rate = 0.0

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Work zone code must be unique!')
    ]