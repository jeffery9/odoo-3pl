from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


class WmsCourierService(models.Model):
    """
    Courier Service - Integration with courier companies for shipping
    """
    _name = 'wms.courier.service'
    _description = 'WMS Courier Service'
    _order = 'name'

    name = fields.Char('Service Name', required=True)
    code = fields.Char('Service Code', required=True, copy=False)
    description = fields.Text('Description')

    # Courier company information
    courier_company_id = fields.Many2one('wms.courier.company', 'Courier Company', required=True)
    service_type = fields.Selection([
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('overnight', 'Overnight'),
        ('same_day', 'Same Day'),
        ('international', 'International'),
        ('freight', 'Freight'),
    ], string='Service Type', required=True)

    # Pricing and configuration
    active = fields.Boolean('Active', default=True)
    base_cost = fields.Float('Base Cost', digits='Product Price')
    cost_per_kg = fields.Float('Cost Per KG', digits='Product Price')
    cost_per_km = fields.Float('Cost Per KM', digits='Product Price')
    delivery_time_days = fields.Integer('Delivery Time (Days)')
    tracking_url = fields.Char('Tracking URL Template')

    # Service configuration
    is_integrated = fields.Boolean('Integrated with API', default=False)
    api_config = fields.Text('API Configuration', help='Courier API configuration in JSON format')
    requires_label_print = fields.Boolean('Requires Label Print', default=True)
    requires_pickup = fields.Boolean('Requires Pickup Schedule', default=False)

    notes = fields.Text('Notes')


class WmsCourierCompany(models.Model):
    """
    Courier Company - Courier service providers
    """
    _name = 'wms.courier.company'
    _description = 'WMS Courier Company'
    _order = 'name'

    name = fields.Char('Company Name', required=True)
    code = fields.Char('Company Code', required=True, copy=False)
    description = fields.Text('Description')

    # Company details
    active = fields.Boolean('Active', default=True)
    is_integrated = fields.Boolean('API Integrated', default=False)
    contact_email = fields.Char('Contact Email')
    contact_phone = fields.Char('Contact Phone')
    website = fields.Char('Website')

    # API Configuration
    api_url = fields.Char('API URL')
    api_key = fields.Char('API Key')
    api_secret = fields.Char('API Secret')
    username = fields.Char('Username')
    password = fields.Char('Password')

    # Integration settings
    tracking_prefix = fields.Char('Tracking Number Prefix')
    supports_cod = fields.Boolean('Supports Cash on Delivery', default=False)
    supports_insurance = fields.Boolean('Supports Insurance', default=False)
    supports_signature = fields.Boolean('Requires Signature', default=False)

    # Courier services
    service_ids = fields.One2many('wms.courier.service', 'courier_company_id', 'Services')

    notes = fields.Text('Notes')


class WmsShipmentOrder(models.Model):
    """
    Shipment Order - Individual shipping orders to courier companies
    """
    _name = 'wms.shipment.order'
    _description = 'WMS Shipment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_created desc'

    name = fields.Char('Shipment Reference', required=True, copy=False,
                       default=lambda self: _('New'))
    tracking_number = fields.Char('Tracking Number', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True)

    # Order information
    source_document = fields.Reference([
        ('stock.picking', 'Stock Picking'),
        ('sale.order', 'Sale Order'),
    ], string='Source Document')

    # Courier and service
    courier_company_id = fields.Many2one('wms.courier.company', 'Courier Company', required=True)
    courier_service_id = fields.Many2one('wms.courier.service', 'Service', required=True)

    # Shipping details
    date_created = fields.Datetime('Date Created', default=fields.Datetime.now)
    date_confirmed = fields.Datetime('Date Confirmed')
    date_shipped = fields.Datetime('Date Shipped')
    date_delivered = fields.Datetime('Date Delivered')
    date_expected = fields.Datetime('Expected Delivery Date')

    # Addresses
    sender_address = fields.Text('Sender Address', required=True)
    recipient_address = fields.Text('Recipient Address', required=True)
    sender_city = fields.Char('Sender City')
    sender_state = fields.Char('Sender State/Province')
    sender_zip = fields.Char('Sender ZIP/Postal Code')
    sender_country = fields.Char('Sender Country')
    recipient_city = fields.Char('Recipient City')
    recipient_state = fields.Char('Recipient State/Province')
    recipient_zip = fields.Char('Recipient ZIP/Postal Code')
    recipient_country = fields.Char('Recipient Country')

    # Package details
    package_weight = fields.Float('Package Weight (KG)', required=True)
    package_length = fields.Float('Package Length (CM)')
    package_width = fields.Float('Package Width (CM)')
    package_height = fields.Float('Package Height (CM)')
    package_volume = fields.Float('Package Volume (L)', compute='_compute_package_volume')

    # Product details
    product_line_ids = fields.One2many('wms.shipment.product.line', 'shipment_id', 'Products')
    total_value = fields.Float('Total Value', compute='_compute_total_value', store=True)
    declared_value = fields.Float('Declared Value', help='Value declared for insurance purposes')

    # Costs and charges
    base_cost = fields.Float('Base Cost', digits='Product Price')
    weight_cost = fields.Float('Weight Cost', digits='Product Price')
    distance_cost = fields.Float('Distance Cost', digits='Product Price')
    other_charges = fields.Float('Other Charges', digits='Product Price')
    total_cost = fields.Float('Total Cost', digits='Product Price', compute='_compute_total_cost', store=True)

    # Insurance and special services
    is_insured = fields.Boolean('Insured', default=False)
    insurance_value = fields.Float('Insurance Value', digits='Product Price')
    requires_signature = fields.Boolean('Requires Signature')
    is_cod = fields.Boolean('Cash on Delivery')
    cod_amount = fields.Float('COD Amount', digits='Product Price')

    # Integration
    api_response = fields.Text('API Response')
    label_data = fields.Binary('Shipping Label')
    label_name = fields.Char('Label Name')

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.shipment.order') or _('New')
        return super().create(vals)

    @api.depends('package_length', 'package_width', 'package_height')
    def _compute_package_volume(self):
        for shipment in self:
            if shipment.package_length and shipment.package_width and shipment.package_height:
                shipment.package_volume = (shipment.package_length * shipment.package_width * shipment.package_height) / 1000000  # cm³ to liters
            else:
                shipment.package_volume = 0.0

    @api.depends('product_line_ids', 'product_line_ids.total_value')
    def _compute_total_value(self):
        for shipment in self:
            shipment.total_value = sum(line.total_value for line in shipment.product_line_ids)

    @api.depends('base_cost', 'weight_cost', 'distance_cost', 'other_charges')
    def _compute_total_cost(self):
        for shipment in self:
            shipment.total_cost = sum([
                self.base_cost or 0,
                self.weight_cost or 0,
                self.distance_cost or 0,
                self.other_charges or 0
            ])

    @api.onchange('courier_company_id')
    def _onchange_courier_company(self):
        if self.courier_company_id:
            return {'domain': {'courier_service_id': [('courier_company_id', '=', self.courier_company_id.id)]}}

    def action_confirm_shipment(self):
        """Confirm the shipment with the courier company"""
        for shipment in self:
            if shipment.state == 'draft':
                shipment.write({
                    'state': 'confirmed',
                    'date_confirmed': fields.Datetime.now(),
                })

    def action_ship_shipment(self):
        """Mark shipment as shipped and send to courier"""
        for shipment in self:
            if shipment.state == 'confirmed':
                # Here we would integrate with the courier's API
                # For now, we'll just update the state
                shipment.write({
                    'state': 'in_transit',
                    'date_shipped': fields.Datetime.now(),
                })

    def action_deliver_shipment(self):
        """Mark shipment as delivered"""
        for shipment in self:
            if shipment.state == 'in_transit':
                shipment.write({
                    'state': 'delivered',
                    'date_delivered': fields.Datetime.now(),
                })

    def action_track_shipment(self):
        """Track the shipment using the courier's API"""
        for shipment in self:
            if shipment.tracking_number and shipment.courier_company_id:
                # This would make an API call to the courier
                # For now, just return a dummy action
                tracking_url = shipment.courier_company_id.tracking_prefix + shipment.tracking_number
                return {
                    'type': 'ir.actions.act_url',
                    'url': tracking_url,
                    'target': 'new',
                }


class WmsShipmentProductLine(models.Model):
    """
    Shipment Product Line - Products included in a shipment
    """
    _name = 'wms.shipment.product.line'
    _description = 'WMS Shipment Product Line'

    shipment_id = fields.Many2one('wms.shipment.order', 'Shipment', required=True, ondelete='cascade')

    # Product information
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    quantity = fields.Float('Quantity', required=True, default=1.0)

    # Value and cost
    unit_value = fields.Float('Unit Value', digits='Product Price')
    total_value = fields.Float('Total Value', digits='Product Price', compute='_compute_total_value', store=True)
    declared_value = fields.Float('Declared Value', digits='Product Price', help='Value for insurance purposes')

    @api.depends('quantity', 'unit_value')
    def _compute_total_value(self):
        for line in self:
            line.total_value = line.quantity * line.unit_value

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.unit_value = self.product_id.list_price