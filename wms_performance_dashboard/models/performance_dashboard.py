from odoo import models, fields, api, _, tools
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class WmsDashboardTemplate(models.Model):
    _name = 'wms.dashboard.template'
    _description = 'WMS Dashboard Template'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    code = fields.Char('Template Code', required=True)
    description = fields.Text('Description')

    # Dashboard type
    dashboard_type = fields.Selection([
        ('executive', 'Executive Dashboard'),
        ('operational', 'Operational Dashboard'),
        ('financial', 'Financial Dashboard'),
        ('quality', 'Quality Dashboard'),
        ('safety', 'Safety Dashboard'),
        ('labor', 'Labor Dashboard'),
        ('energy', 'Energy Dashboard'),
        ('custom', 'Custom Dashboard'),
    ], string='Dashboard Type', required=True)

    # Widgets included in template
    widget_ids = fields.Many2many('wms.dashboard.widget', 'wms_dashboard_template_widget_rel', 'template_id', 'widget_id', 'Widgets')

    # Default settings
    default_owner_id = fields.Many2one('wms.owner', 'Default Owner')
    default_period = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
    ], string='Default Period', default='month')

    is_active = fields.Boolean('Active', default=True)
    is_default = fields.Boolean('Default Template', help='Only one template can be default per dashboard type')


class WmsDashboardWidget(models.Model):
    _name = 'wms.dashboard.widget'
    _description = 'WMS Dashboard Widget'
    _order = 'name'

    name = fields.Char('Widget Name', required=True)
    code = fields.Char('Widget Code', required=True)
    description = fields.Text('Description')

    # Widget type
    widget_type = fields.Selection([
        ('kpi', 'KPI Card'),
        ('chart', 'Chart'),
        ('gauge', 'Gauge'),
        ('table', 'Data Table'),
        ('trend', 'Trend Line'),
        ('comparison', 'Comparison'),
        ('alert', 'Alert/Notification'),
        ('text', 'Text/Description'),
    ], string='Widget Type', required=True)

    # Data source
    data_source = fields.Selection([
        ('stock_picking', 'Stock Picking'),
        ('wms_quality_control', 'Quality Control'),
        ('wms_labor_task', 'Labor Task'),
        ('wms_energy_reading', 'Energy Reading'),
        ('wms_safety_incident', 'Safety Incident'),
        ('wms_financial_transaction', 'Financial Transaction'),
        ('wms_return_authorization', 'Return Authorization'),
        ('custom', 'Custom Query'),
    ], string='Data Source', required=True)

    # Configuration
    configuration = fields.Text('Configuration', help='JSON configuration for the widget')
    calculated_field = fields.Char('Calculated Field', help='Field name for calculated values')

    # Display properties
    size_x = fields.Integer('Width', default=4)
    size_y = fields.Integer('Height', default=2)
    col = fields.Integer('Column', default=0)
    row = fields.Integer('Row', default=0)

    is_active = fields.Boolean('Active', default=True)


class WmsPerformanceKpi(models.Model):
    _name = 'wms.performance.kpi'
    _description = 'WMS Performance KPI'
    _order = 'name'

    name = fields.Char('KPI Name', required=True)
    code = fields.Char('KPI Code', required=True)
    description = fields.Text('Description')

    # KPI category
    category = fields.Selection([
        ('throughput', 'Throughput'),
        ('efficiency', 'Efficiency'),
        ('quality', 'Quality'),
        ('cost', 'Cost'),
        ('safety', 'Safety'),
        ('customer', 'Customer Service'),
        ('labor', 'Labor'),
        ('energy', 'Energy'),
    ], string='Category', required=True)

    # Calculation
    calculation_method = fields.Selection([
        ('count', 'Count'),
        ('sum', 'Sum'),
        ('average', 'Average'),
        ('percentage', 'Percentage'),
        ('ratio', 'Ratio'),
    ], string='Calculation Method', required=True)

    # Data source and field
    source_model = fields.Selection([
        ('stock.picking', 'Stock Picking'),
        ('wms.quality.control', 'Quality Control'),
        ('wms.labor.task', 'Labor Task'),
        ('wms.energy.reading', 'Energy Reading'),
        ('wms.safety.incident', 'Safety Incident'),
        ('wms.financial.transaction', 'Financial Transaction'),
        ('wms.return.authorization', 'Return Authorization'),
    ], string='Source Model', required=True)
    source_field = fields.Char('Source Field', help='Field name in the source model')
    condition = fields.Char('Condition', help='Domain condition for filtering')

    # Target and benchmark
    target_value = fields.Float('Target Value')
    benchmark_value = fields.Float('Benchmark Value')
    unit_of_measure = fields.Char('Unit of Measure', default='%')

    # Trend tracking
    current_value = fields.Float('Current Value', compute='_compute_current_value', store=True)
    previous_value = fields.Float('Previous Value', compute='_compute_previous_value', store=True)
    trend = fields.Float('Trend %', compute='_compute_trend', store=True)

    # Alert settings
    alert_threshold = fields.Float('Alert Threshold')
    alert_type = fields.Selection([
        ('above', 'Above Threshold'),
        ('below', 'Below Threshold'),
    ], string='Alert Type', default='above')

    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)

    @api.depends('source_model', 'source_field', 'condition', 'owner_id')
    def _compute_current_value(self):
        for kpi in self:
            try:
                records = self._get_filtered_records(kpi)
                kpi.current_value = self._calculate_kpi_value(kpi, records)
            except Exception as e:
                _logger.error(f"Error computing KPI {kpi.name}: {e}")
                kpi.current_value = 0.0

    @api.depends('source_model', 'source_field', 'condition', 'owner_id')
    def _compute_previous_value(self):
        for kpi in self:
            try:
                # Get records from previous period (same length as current period)
                records = self._get_filtered_records(kpi, previous_period=True)
                kpi.previous_value = self._calculate_kpi_value(kpi, records)
            except Exception as e:
                _logger.error(f"Error computing previous KPI value {kpi.name}: {e}")
                kpi.previous_value = 0.0

    @api.depends('current_value', 'previous_value')
    def _compute_trend(self):
        for kpi in self:
            if kpi.previous_value != 0:
                kpi.trend = ((kpi.current_value - kpi.previous_value) / kpi.previous_value) * 100
            else:
                kpi.trend = 0.0

    def _get_filtered_records(self, kpi, previous_period=False):
        """Get filtered records for KPI calculation"""
        model = self.env[kpi.source_model]

        # Base domain
        domain = []
        if kpi.condition:
            try:
                domain = eval(kpi.condition)
            except:
                domain = []

        # Add owner filter if applicable
        if 'owner_id' in model._fields:
            domain.append(('owner_id', '=', kpi.owner_id.id))

        # Add date range filter
        today = fields.Date.context_today(self)
        if previous_period:
            # Calculate previous period (e.g., same length as current month)
            start_date = today.replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)
            end_date = today.replace(day=1) - timedelta(days=1)
        else:
            # Current period (this month)
            start_date = today.replace(day=1)
            end_date = today

        if 'date' in model._fields:
            domain.append(('date', '>=', start_date))
            domain.append(('date', '<=', end_date))
        elif 'create_date' in model._fields:
            domain.append(('create_date', '>=', start_date))
            domain.append(('create_date', '<=', end_date))
        elif 'write_date' in model._fields:
            domain.append(('write_date', '>=', start_date))
            domain.append(('write_date', '<=', end_date))

        return model.search(domain)

    def _calculate_kpi_value(self, kpi, records):
        """Calculate KPI value based on method and records"""
        if not records:
            return 0.0

        if kpi.calculation_method == 'count':
            return len(records)
        elif kpi.calculation_method == 'sum':
            if kpi.source_field and hasattr(records[:1], kpi.source_field):
                return sum(getattr(record, kpi.source_field, 0) for record in records)
        elif kpi.calculation_method == 'average':
            if kpi.source_field and hasattr(records[:1], kpi.source_field):
                values = [getattr(record, kpi.source_field, 0) for record in records]
                return sum(values) / len(values) if values else 0.0
        elif kpi.calculation_method == 'percentage':
            # Special handling for percentage calculations
            # This would typically require a numerator and denominator
            # For now, we'll use a simple approach
            if kpi.source_field and hasattr(records[:1], kpi.source_field):
                return (sum(getattr(record, kpi.source_field, 0) for record in records) / len(records)) * 100
        elif kpi.calculation_method == 'ratio':
            # Special handling for ratio calculations
            # This would typically require two fields or special logic
            # For now, we'll use a simple approach
            if kpi.source_field and hasattr(records[:1], kpi.source_field):
                values = [getattr(record, kpi.source_field, 0) for record in records if getattr(record, kpi.source_field, 0) != 0]
                if values:
                    return sum(values) / len(values)

        return 0.0


class WmsPerformanceReport(models.Model):
    _name = 'wms.performance.report'
    _description = 'WMS Performance Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'report_date desc'

    name = fields.Char('Report Name', required=True)
    report_code = fields.Char('Report Code', required=True, copy=False, readonly=True,
                              default=lambda self: _('New'))
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    report_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ], string='Report Type', required=True, default='monthly')

    # Period
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)

    # Report date
    report_date = fields.Date('Report Date', default=fields.Date.context_today, required=True)
    generation_date = fields.Datetime('Generation Date', default=fields.Datetime.now)

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('validated', 'Validated'),
        ('published', 'Published'),
    ], string='Status', default='draft', tracking=True)

    # Content
    executive_summary = fields.Html('Executive Summary')
    detailed_analysis = fields.Html('Detailed Analysis')
    recommendations = fields.Html('Recommendations')
    kpi_results = fields.Text('KPI Results', help='JSON formatted KPI results')

    # Generated data
    report_data = fields.Html('Report Data')
    charts_data = fields.Text('Charts Data', help='JSON formatted chart data')
    alert_summary = fields.Html('Alert Summary')

    # Distribution
    recipients = fields.Many2many('res.users', 'wms_performance_report_user_rel', 'report_id', 'user_id', 'Recipients')

    @api.model
    def create(self, vals):
        if vals.get('report_code', _('New')) == _('New'):
            vals['report_code'] = self.env['ir.sequence'].next_by_code('wms.performance.report') or _('New')
        return super().create(vals)

    def action_generate_report(self):
        """Generate the performance report"""
        for report in self:
            # Generate KPI data, charts, and other metrics
            report._generate_kpi_data()
            report._generate_charts_data()
            report._generate_alert_summary()
            report.status = 'generated'

    def action_validate_report(self):
        """Validate the performance report"""
        for report in self:
            report.status = 'validated'

    def action_publish_report(self):
        """Publish the performance report"""
        for report in self:
            report.status = 'published'
            report.generation_date = fields.Datetime.now()

    def _generate_kpi_data(self):
        """Generate KPI data for the report"""
        # This would typically call methods to calculate KPIs for the report period
        # For now, we'll just store an empty JSON object
        self.kpi_results = '{}'

    def _generate_charts_data(self):
        """Generate charts data for the report"""
        # This would typically call methods to calculate chart data
        # For now, we'll just store an empty JSON object
        self.charts_data = '{}'

    def _generate_alert_summary(self):
        """Generate alert summary for the report"""
        # Find any KPIs that are outside their thresholds
        alert_kpis = self.env['wms.performance.kpi'].search([
            ('owner_id', '=', self.owner_id.id),
            ('alert_threshold', '!=', False),
        ])

        alert_html = '<ul>'
        for kpi in alert_kpis:
            if kpi.alert_type == 'above' and kpi.current_value > kpi.alert_threshold:
                alert_html += f'<li>{kpi.name}: {kpi.current_value} (above threshold of {kpi.alert_threshold})</li>'
            elif kpi.alert_type == 'below' and kpi.current_value < kpi.alert_threshold:
                alert_html += f'<li>{kpi.name}: {kpi.current_value} (below threshold of {kpi.alert_threshold})</li>'
        alert_html += '</ul>'

        self.alert_summary = alert_html


class WmsAlert(models.Model):
    _name = 'wms.alert'
    _description = 'WMS Alert'
    _order = 'create_date desc'

    name = fields.Char('Alert Name', required=True)
    alert_type = fields.Selection([
        ('kpi_threshold', 'KPI Threshold'),
        ('performance_degradation', 'Performance Degradation'),
        ('safety_incident', 'Safety Incident'),
        ('quality_issue', 'Quality Issue'),
        ('capacity_exceeded', 'Capacity Exceeded'),
        ('cost_overrun', 'Cost Overrun'),
        ('customer_satisfaction', 'Customer Satisfaction'),
    ], string='Alert Type', required=True)

    # Severity
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='medium')

    # Related to
    related_model = fields.Reference([
        ('wms.performance.kpi', 'Performance KPI'),
        ('wms.safety.incident', 'Safety Incident'),
        ('wms.quality.issue', 'Quality Issue'),
        ('stock.picking', 'Stock Picking'),
    ], string='Related To')

    # Details
    message = fields.Text('Alert Message', required=True)
    description = fields.Text('Description')
    target_value = fields.Float('Target Value')
    actual_value = fields.Float('Actual Value')

    # Status
    status = fields.Selection([
        ('open', 'Open'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)

    # Assignment
    assigned_to = fields.Many2one('res.users', 'Assigned To')
    due_date = fields.Date('Due Date')

    # Resolution
    resolution_date = fields.Date('Resolution Date')
    resolution_notes = fields.Text('Resolution Notes')

    def action_acknowledge(self):
        """Acknowledge the alert"""
        for alert in self:
            alert.status = 'acknowledged'

    def action_start_resolution(self):
        """Start resolution of the alert"""
        for alert in self:
            if alert.status in ['open', 'acknowledged']:
                alert.status = 'in_progress'

    def action_resolve(self):
        """Resolve the alert"""
        for alert in self:
            if alert.status == 'in_progress':
                alert.status = 'resolved'
                alert.resolution_date = fields.Date.context_today(self)

    def action_close(self):
        """Close the alert"""
        for alert in self:
            if alert.status in ['open', 'acknowledged', 'in_progress', 'resolved']:
                alert.status = 'closed'


class WmsBenchmark(models.Model):
    _name = 'wms.benchmark'
    _description = 'WMS Benchmark'
    _order = 'category, name'

    name = fields.Char('Benchmark Name', required=True)
    code = fields.Char('Benchmark Code', required=True)
    description = fields.Text('Description')

    # Category
    category = fields.Selection([
        ('throughput', 'Throughput'),
        ('efficiency', 'Efficiency'),
        ('quality', 'Quality'),
        ('cost', 'Cost'),
        ('safety', 'Safety'),
        ('customer', 'Customer Service'),
        ('labor', 'Labor'),
        ('energy', 'Energy'),
    ], string='Category', required=True)

    # Type
    benchmark_type = fields.Selection([
        ('industry', 'Industry Standard'),
        ('historical', 'Historical Average'),
        ('target', 'Target Value'),
        ('competitor', 'Competitor Average'),
    ], string='Benchmark Type', required=True)

    # Values
    value = fields.Float('Benchmark Value', required=True)
    unit_of_measure = fields.Char('Unit of Measure', default='%')
    year = fields.Integer('Year', default=lambda self: fields.Date.context_today(self).year)

    # Comparison
    is_current = fields.Boolean('Is Current', default=True)
    weight = fields.Float('Weight', default=1.0, help='Weight for composite scoring')

    # Owner
    owner_id = fields.Many2one('wms.owner', 'Owner')