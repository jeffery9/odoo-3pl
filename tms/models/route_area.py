# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class RouteArea(models.Model):
    _name = 'route.area'
    _description = 'Route Coverage Area'
    _order = 'name'

    name = fields.Char(
        string='Area Name',
        required=True,
        help='Name of the route coverage area'
    )
    code = fields.Char(
        string='Area Code',
        required=True,
        help='Short code for the route area'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of the route area'
    )
    active = fields.Boolean(
        default=True,
        help='Set to false to hide this area'
    )
    partner_ids = fields.One2many(
        'res.partner',
        'route_area_id',
        string='Customers in this Area',
        help='Customers assigned to this route area'
    )
    route_ids = fields.One2many(
        'tms.route',
        'area_id',
        string='Routes in this Area',
        help='Routes that operate in this area'
    )
    sequence = fields.Integer(
        default=10,
        help='Sequence for ordering'
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Area Manager',
        help='User responsible for managing this area'
    )
    delivery_instructions = fields.Text(
        string='Delivery Instructions',
        help='Default delivery instructions for this area'
    )
    geographic_coordinates = fields.Text(
        string='Geographic Coordinates',
        help='Geographic boundaries of the area (JSON format with coordinates)'
    )
    estimated_delivery_time = fields.Float(
        string='Estimated Delivery Time (hours)',
        help='Average estimated delivery time for this area'
    )
    service_level = fields.Selection([
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('premium', 'Premium'),
    ], string='Service Level', default='standard')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Area code must be unique!'),
        ('name_uniq', 'unique(name)', 'Area name must be unique!'),
    ]

    @api.model
    def create(self, vals):
        # Generate code from name if not provided
        if 'code' not in vals or not vals['code']:
            vals['code'] = self._generate_code_from_name(vals.get('name', ''))
        return super().create(vals)

    def _generate_code_from_name(self, name):
        """Generate code from area name"""
        if name:
            # Convert to uppercase and replace spaces with underscores
            return name.upper().replace(' ', '_').replace('-', '_')
        return 'UNNAMED_AREA'

    def name_get(self):
        result = []
        for area in self:
            name = f"{area.code} - {area.name}"
            result.append((area.id, name))
        return result