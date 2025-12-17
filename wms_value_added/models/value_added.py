from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


class WmsValueAddedService(models.Model):
    """
    Value Added Service - Services performed on products in warehouse
    """
    _name = 'wms.value.added.service'
    _description = 'WMS Value Added Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Service Name', required=True)
    code = fields.Char('Service Code', required=True, copy=False)
    description = fields.Text('Description')

    # Service type and category
    service_type = fields.Selection([
        ('assembly', 'Assembly'),
        ('packaging', 'Packaging'),
        ('labeling', 'Labeling'),
        ('kitting', 'Kitting'),
        ('customization', 'Customization'),
        ('inspection', 'Inspection'),
        ('repackaging', 'Repackaging'),
        ('sample_prep', 'Sample Preparation'),
        ('other', 'Other'),
    ], string='Service Type', required=True)

    service_category = fields.Selection([
        ('product', 'Product Enhancement'),
        ('order', 'Order Enhancement'),
        ('compliance', 'Compliance'),
        ('logistics', 'Logistics'),
        ('quality', 'Quality Control'),
    ], string='Service Category')

    # Service configuration
    active = fields.Boolean('Active', default=True)
    standard_time = fields.Float('Standard Time (minutes)')
    cost_per_unit = fields.Float('Cost Per Unit', digits='Product Price')
    price_per_unit = fields.Float('Price Per Unit', digits='Product Price')

    # Resource requirements
    required_skills = fields.Many2many('hr.skill', string='Required Skills')
    required_equipment = fields.Many2many('maintenance.equipment', string='Required Equipment')

    # Service workflow
    has_quality_check = fields.Boolean('Requires Quality Check', default=False)
    requires_approval = fields.Boolean('Requires Approval', default=False)
    creates_lot = fields.Boolean('Creates New Lot/SN', default=False)

    # Integration
    integrated_with_erp = fields.Boolean('Integrated with ERP', default=True)
    automatic_billing = fields.Boolean('Automatic Billing', default=True)

    notes = fields.Text('Notes')


class WmsValueAddedOperation(models.Model):
    """
    Value Added Operation - Specific instance of value added service
    """
    _name = 'wms.value.added.operation'
    _description = 'WMS Value Added Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_scheduled, priority desc'

    name = fields.Char('Operation Reference', required=True, copy=False,
                       default=lambda self: _('New'))
    service_id = fields.Many2one('wms.value.added.service', 'Service', required=True)

    # Operation details
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)

    # Source and destination
    source_document = fields.Reference([
        ('stock.picking', 'Stock Picking'),
        ('stock.move', 'Stock Move'),
        ('stock.quant', 'Stock Quant'),
        ('sale.order', 'Sale Order'),
    ], string='Source Document')

    # Priority and scheduling
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1')

    date_scheduled = fields.Datetime('Scheduled Date', required=True)
    date_started = fields.Datetime('Started Date')
    date_completed = fields.Datetime('Completed Date')

    # Personnel
    assigned_to = fields.Many2one('hr.employee', 'Assigned To')
    completed_by = fields.Many2one('hr.employee', 'Completed By')

    # Materials and BOM
    bom_id = fields.Many2one('mrp.bom', 'Bill of Materials')
    material_ids = fields.One2many('wms.value.added.material', 'operation_id', 'Materials Required')

    # Products involved
    product_line_ids = fields.One2many('wms.value.added.product.line', 'operation_id', 'Product Lines')
    result_product_line_ids = fields.One2many('wms.value.added.product.line', 'operation_id',
                                             domain=[('line_type', '=', 'result')],
                                             string='Result Products')

    # Standards and compliance
    # quality_check_ids = fields.One2many('wms.quality.check', 'value_added_operation_id', 'Quality Checks')  # Removed due to wms_quality_control dependency
    # compliance_check_ids = fields.One2many('wms.compliance.check', 'value_added_operation_id', 'Compliance Checks')  # Removed due to wms_quality_control dependency

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('quality_check', 'Quality Check'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True)

    # Tracking
    progress = fields.Float('Progress (%)', compute='_compute_progress', store=True)
    duration_minutes = fields.Float('Duration (minutes)', compute='_compute_duration', store=True)
    efficiency_rate = fields.Float('Efficiency Rate (%)', compute='_compute_efficiency', store=True)

    # Billing and costs
    cost = fields.Float('Total Cost', compute='_compute_cost', store=True)
    revenue = fields.Float('Revenue', compute='_compute_revenue', store=True)
    margin = fields.Float('Margin', compute='_compute_margin', store=True)

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.value.added.operation') or _('New')
        return super().create(vals)

    @api.depends('state')
    def _compute_progress(self):
        """Calculate operation progress based on state"""
        for operation in self:
            if operation.state == 'completed':
                operation.progress = 100.0
            elif operation.state == 'in_progress':
                # Simplified: assume 50% when in progress
                operation.progress = 50.0
            elif operation.state in ['scheduled', 'quality_check', 'approved']:
                operation.progress = 75.0
            else:
                operation.progress = 0.0

    @api.depends('date_started', 'date_completed')
    def _compute_duration(self):
        """Calculate actual duration of operation"""
        for operation in self:
            if operation.date_started and operation.date_completed:
                duration = (operation.date_completed - operation.date_started).total_seconds() / 60  # in minutes
                operation.duration_minutes = duration
            elif operation.date_started and operation.state == 'in_progress':
                duration = (fields.Datetime.now() - operation.date_started).total_seconds() / 60  # in minutes
                operation.duration_minutes = duration
            else:
                operation.duration_minutes = 0.0

    def _compute_efficiency(self):
        """Calculate efficiency compared to standard time"""
        for operation in self:
            if operation.service_id.standard_time > 0 and operation.duration_minutes > 0:
                operation.efficiency_rate = (operation.service_id.standard_time / operation.duration_minutes) * 100
            else:
                operation.efficiency_rate = 100.0 if operation.service_id.standard_time == 0 and operation.duration_minutes == 0 else 0.0

    def _compute_cost(self):
        """Calculate total operation cost"""
        for operation in self:
            # Simplified cost calculation
            labor_cost = 0.0
            material_cost = 0.0

            # Add labor cost if employee is assigned and has an hourly rate
            if operation.assigned_to:
                # Using a default hourly rate calculation
                hourly_rate = operation.assigned_to.contract_id.wage / 2080 if operation.assigned_to.contract_id.wage else 100
                hourly_rate *= 1.3 # Include benefits
                labor_cost = (operation.duration_minutes / 60) * (hourly_rate / 24)  # Simplified calculation

            # Add material costs
            for material_line in operation.material_ids:
                material_cost += material_line.total_cost

            operation.cost = labor_cost + material_cost

    def _compute_revenue(self):
        """Calculate expected revenue"""
        for operation in self:
            if operation.service_id.price_per_unit and operation.product_line_ids:
                total_qty = sum(line.quantity for line in operation.product_line_ids)
                operation.revenue = operation.service_id.price_per_unit * total_qty
            else:
                operation.revenue = 0.0

    def _compute_margin(self):
        """Calculate profit margin"""
        for operation in self:
            operation.margin = operation.revenue - operation.cost

    def action_start_operation(self):
        """Start the value added operation"""
        for operation in self:
            if operation.state == 'scheduled':
                operation.write({
                    'state': 'in_progress',
                    'date_started': fields.Datetime.now(),
                })

    def action_complete_operation(self):
        """Complete the value added operation"""
        for operation in self:
            if operation.state == 'in_progress':
                operation.write({
                    'state': 'quality_check' if operation.service_id.has_quality_check else 'completed',
                    'date_completed': fields.Datetime.now(),
                })

    def action_approve_operation(self):
        """Approve the operation after quality check"""
        for operation in self:
            if operation.state == 'quality_check':
                operation.write({
                    'state': 'approved' if operation.service_id.requires_approval else 'completed',
                })

    def action_cancel_operation(self):
        """Cancel the operation"""
        for operation in self:
            if operation.state in ['draft', 'scheduled', 'in_progress']:
                operation.write({'state': 'cancelled'})


class WmsValueAddedProductLine(models.Model):
    """
    Value Added Product Line - Products involved in value added operations
    """
    _name = 'wms.value.added.product.line'
    _description = 'WMS Value Added Product Line'

    operation_id = fields.Many2one('wms.value.added.operation', 'Operation', required=True, ondelete='cascade')

    # Product information
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    quantity = fields.Float('Quantity', required=True, default=1.0)

    # Line type
    line_type = fields.Selection([
        ('input', 'Input Product'),
        ('output', 'Output Product'),
        ('consumable', 'Consumable Material'),
        ('result', 'Result Product'),
    ], string='Line Type', default='input', required=True)

    # Lot/Serial tracking
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')
    # expiry_date = fields.Date('Expiry Date', related='lot_id.expiry_date', store=True)  # Removed due to field not existing in Odoo 18

    # Location
    location_id = fields.Many2one('stock.location', 'Location')

    # Cost information
    unit_cost = fields.Float('Unit Cost', digits='Product Price')
    total_cost = fields.Float('Total Cost', digits='Product Price', compute='_compute_total_cost', store=True)

    notes = fields.Text('Notes')

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price


class WmsValueAddedMaterial(models.Model):
    """
    Value Added Material - Materials required for value added operations
    """
    _name = 'wms.value.added.material'
    _description = 'WMS Value Added Material'

    operation_id = fields.Many2one('wms.value.added.operation', 'Operation', required=True, ondelete='cascade')

    # Material information
    product_id = fields.Many2one('product.product', 'Material', required=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    planned_quantity = fields.Float('Planned Quantity', default=1.0)
    used_quantity = fields.Float('Used Quantity', default=0.0)
    unit_cost = fields.Float('Unit Cost', digits='Product Price')
    total_cost = fields.Float('Total Cost', digits='Product Price', compute='_compute_total_cost', store=True)

    # Material usage
    is_consumed = fields.Boolean('Is Consumed', default=True)
    is_returnable = fields.Boolean('Is Returnable', default=False)

    notes = fields.Text('Notes')

    @api.depends('used_quantity', 'unit_cost')
    def _compute_total_cost(self):
        for material in self:
            material.total_cost = material.used_quantity * material.unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price


class WmsValueAddedReport(models.TransientModel):
    """
    Value Added Service Report Wizard
    """
    _name = 'wms.value.added.report'
    _description = 'WMS Value Added Service Report Wizard'

    date_from = fields.Date('Date From', required=True, default=lambda self: fields.Date.to_string(fields.Date.today().replace(day=1)))
    date_to = fields.Date('Date To', required=True, default=fields.Date.today)
    owner_id = fields.Many2one('wms.owner', 'Owner')
    service_type = fields.Selection([
        ('assembly', 'Assembly'),
        ('packaging', 'Packaging'),
        ('labeling', 'Labeling'),
        ('kitting', 'Kitting'),
        ('customization', 'Customization'),
        ('inspection', 'Inspection'),
        ('repackaging', 'Repackaging'),
        ('sample_prep', 'Sample Preparation'),
        ('other', 'Other'),
    ], string='Service Type')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')

    def action_generate_report(self):
        """Generate value added service report"""
        domain = [
            ('date_scheduled', '>=', self.date_from),
            ('date_scheduled', '<=', self.date_to),
            ('state', 'in', ['completed', 'approved']),
        ]

        if self.owner_id:
            domain.append(('owner_id', '=', self.owner_id.id))
        if self.service_type:
            domain.append(('service_id.service_type', '=', self.service_type))
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))

        operations = self.env['wms.value.added.operation'].search(domain)

        # Create a report record or return a tree view of operations
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.value.added.operation',
            'view_mode': 'list,form',
            'domain': [('id', 'in', operations.ids)],
            'context': {
                'search_default_date_from': self.date_from,
                'search_default_date_to': self.date_to,
                'search_default_state_completed': 1,
            },
            'target': 'current',
            'name': f'Value Added Operations Report: {self.date_from} to {self.date_to}'
        }

        return action