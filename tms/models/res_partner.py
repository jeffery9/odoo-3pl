# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    route_area_id = fields.Many2one(
        'route.area',
        string='Route Coverage Area',
        help='The route coverage area that this customer belongs to'
    )
    route_area_code = fields.Char(
        related='route_area_id.code',
        string='Area Code',
        readonly=True,
        store=True
    )
    estimated_service_time = fields.Float(
        string='Estimated Service Time (minutes)',
        help='Estimated time required to service this customer'
    )
    special_delivery_instructions = fields.Text(
        string='Special Delivery Instructions',
        help='Specific delivery instructions for this customer'
    )
    preferred_delivery_time = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ('anytime', 'Any Time'),
    ], string='Preferred Delivery Time', default='anytime')
    delivery_priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Delivery Priority', default='normal')