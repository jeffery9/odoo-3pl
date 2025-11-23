from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
import math


class WmsEnergyEquipment(models.Model):
    _name = 'wms.energy.equipment'
    _description = 'WMS Energy Equipment'
    _order = 'name'

    name = fields.Char('Equipment Name', required=True)
    code = fields.Char('Equipment Code', required=True)
    equipment_type = fields.Selection([
        ('lighting', 'Lighting'),
        ('heating', 'Heating'),
        ('cooling', 'Cooling'),
        ('ventilation', 'Ventilation'),
        ('machinery', 'Machinery'),
        ('conveyor', 'Conveyor System'),
        ('refrigeration', 'Refrigeration'),
        ('other', 'Other'),
    ], string='Equipment Type', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    power_rating = fields.Float('Power Rating (kW)', help='Power rating in kilowatts')
    voltage = fields.Float('Voltage (V)', help='Operating voltage')
    current = fields.Float('Current (A)', help='Operating current')
    energy_source = fields.Selection([
        ('electricity', 'Electricity'),
        ('gas', 'Gas'),
        ('solar', 'Solar'),
        ('wind', 'Wind'),
        ('other', 'Other'),
    ], string='Energy Source', default='electricity')
    is_active = fields.Boolean('Active', default=True)
    installation_date = fields.Date('Installation Date')
    last_maintenance_date = fields.Date('Last Maintenance Date')
    next_maintenance_date = fields.Date('Next Maintenance Date')
    efficiency_rating = fields.Float('Efficiency Rating %', help='Energy efficiency rating')
    notes = fields.Text('Notes')


class WmsEnergyReading(models.Model):
    _name = 'wms.energy.reading'
    _description = 'WMS Energy Reading'
    _order = 'reading_date desc'
    _rec_name = 'equipment_id'

    equipment_id = fields.Many2one('wms.energy.equipment', 'Equipment', required=True)
    reading_date = fields.Datetime('Reading Date', required=True, default=fields.Datetime.now)
    energy_consumed = fields.Float('Energy Consumed (kWh)', required=True, help='Energy consumed in kilowatt-hours')
    peak_demand = fields.Float('Peak Demand (kW)', help='Peak demand in kilowatts during the period')
    power_factor = fields.Float('Power Factor', help='Power factor measurement')
    cost = fields.Float('Cost', digits='Product Price', help='Cost of energy consumed')
    carbon_emissions = fields.Float('Carbon Emissions (kg)', help='Carbon emissions in kilograms')
    reading_type = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('estimation', 'Estimation'),
    ], string='Reading Type', default='manual')
    is_validated = fields.Boolean('Validated', default=False)
    validated_by = fields.Many2one('res.users', 'Validated By')
    validation_date = fields.Datetime('Validation Date')

    @api.constrains('energy_consumed', 'peak_demand', 'cost', 'carbon_emissions')
    def _check_positive_values(self):
        for reading in self:
            if reading.energy_consumed < 0:
                raise ValidationError(_('Energy consumed cannot be negative.'))
            if reading.peak_demand and reading.peak_demand < 0:
                raise ValidationError(_('Peak demand cannot be negative.'))
            if reading.cost < 0:
                raise ValidationError(_('Cost cannot be negative.'))
            if reading.carbon_emissions and reading.carbon_emissions < 0:
                raise ValidationError(_('Carbon emissions cannot be negative.'))

    def action_validate_reading(self):
        """Validate the energy reading"""
        for reading in self:
            reading.is_validated = True
            reading.validated_by = self.env.user
            reading.validation_date = fields.Datetime.now()


class WmsEnergyReport(models.Model):
    _name = 'wms.energy.report'
    _description = 'WMS Energy Report'
    _order = 'report_date desc'

    name = fields.Char('Report Name', required=True)
    report_code = fields.Char('Report Code', required=True, copy=False, readonly=True,
                              default=lambda self: _('New'))
    report_date = fields.Date('Report Date', required=True, default=fields.Date.context_today)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True,
                               default=lambda self: self.env['wms.owner'].get_default_owner())
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)
    total_energy_consumed = fields.Float('Total Energy Consumed (kWh)', compute='_compute_totals', store=True)
    total_cost = fields.Float('Total Cost', digits='Product Price', compute='_compute_totals', store=True)
    total_carbon_emissions = fields.Float('Total Carbon Emissions (kg)', compute='_compute_totals', store=True)
    energy_intensity = fields.Float('Energy Intensity (kWh/sq.m)', compute='_compute_totals', store=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('validated', 'Validated'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text('Notes')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')

    # Related readings
    reading_ids = fields.One2many('wms.energy.reading', 'id', string='Readings', compute='_compute_readings')

    @api.model
    def create(self, vals):
        if vals.get('report_code', _('New')) == _('New'):
            vals['report_code'] = self.env['ir.sequence'].next_by_code('wms.energy.report') or _('New')
        return super().create(vals)

    @api.depends('period_start', 'period_end', 'owner_id')
    def _compute_readings(self):
        for report in self:
            if report.period_start and report.period_end:
                readings = self.env['wms.energy.reading'].search([
                    ('reading_date', '>=', fields.Datetime.to_string(fields.Datetime.from_string(report.period_start))),
                    ('reading_date', '<=', fields.Datetime.to_string(fields.Datetime.from_string(report.period_end))),
                ])
                report.reading_ids = readings
            else:
                report.reading_ids = self.env['wms.energy.reading']

    @api.depends('period_start', 'period_end', 'owner_id')
    def _compute_totals(self):
        for report in self:
            if report.period_start and report.period_end:
                readings = self.env['wms.energy.reading'].search([
                    ('reading_date', '>=', fields.Datetime.to_string(fields.Datetime.from_string(report.period_start))),
                    ('reading_date', '<=', fields.Datetime.to_string(fields.Datetime.from_string(report.period_end))),
                ])
                report.total_energy_consumed = sum(r.energy_consumed for r in readings)
                report.total_cost = sum(r.cost for r in readings)
                report.total_carbon_emissions = sum(r.carbon_emissions for r in readings)

                # Calculate energy intensity - assuming warehouse area is available
                if report.warehouse_id and report.warehouse_id.lot_stock_id:
                    area = report.warehouse_id.lot_stock_id.scrap_location_id  # Simplified approach
                    if area and report.total_energy_consumed > 0:
                        report.energy_intensity = report.total_energy_consumed / 1000  # Placeholder calculation
                    else:
                        report.energy_intensity = 0.0
                else:
                    report.energy_intensity = 0.0
            else:
                report.total_energy_consumed = 0.0
                report.total_cost = 0.0
                report.total_carbon_emissions = 0.0
                report.energy_intensity = 0.0

    def action_generate_report(self):
        """Generate the energy report"""
        for report in self:
            report.status = 'generated'

    def action_validate_report(self):
        """Validate the energy report"""
        for report in self:
            report.status = 'validated'


class WmsEnergyTarget(models.Model):
    _name = 'wms.energy.target'
    _description = 'WMS Energy Target'
    _order = 'target_year desc, target_month'

    name = fields.Char('Target Name', required=True)
    equipment_id = fields.Many2one('wms.energy.equipment', 'Equipment')
    target_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Target Month', required=True)
    target_year = fields.Integer('Target Year', required=True,
                                 default=lambda self: fields.Date.context_today(self).year)
    target_energy = fields.Float('Target Energy (kWh)', required=True, help='Target energy consumption in kWh')
    actual_energy = fields.Float('Actual Energy (kWh)', compute='_compute_actual_energy', store=True)
    variance = fields.Float('Variance (kWh)', compute='_compute_variance', store=True)
    variance_percentage = fields.Float('Variance %', compute='_compute_variance_percentage', store=True)
    achieved = fields.Boolean('Target Achieved', compute='_compute_target_achievement', store=True)

    @api.depends('target_month', 'target_year', 'equipment_id')
    def _compute_actual_energy(self):
        for target in self:
            # Get the first and last day of the target month
            from datetime import date
            import calendar

            first_day = date(target.target_year, int(target.target_month), 1)
            last_day = date(target.target_year, int(target.target_month),
                           calendar.monthrange(target.target_year, int(target.target_month))[1])

            domain = [
                ('reading_date', '>=', fields.Datetime.to_string(first_day)),
                ('reading_date', '<=', fields.Datetime.to_string(last_day)),
            ]

            if target.equipment_id:
                domain.append(('equipment_id', '=', target.equipment_id.id))

            readings = self.env['wms.energy.reading'].search(domain)
            target.actual_energy = sum(r.energy_consumed for r in readings)

    @api.depends('target_energy', 'actual_energy')
    def _compute_variance(self):
        for target in self:
            target.variance = target.target_energy - target.actual_energy

    @api.depends('target_energy', 'actual_energy')
    def _compute_variance_percentage(self):
        for target in self:
            if target.target_energy != 0:
                target.variance_percentage = (target.variance / target.target_energy) * 100
            else:
                target.variance_percentage = 0.0

    @api.depends('target_energy', 'actual_energy')
    def _compute_target_achievement(self):
        for target in self:
            target.achieved = target.actual_energy <= target.target_energy


class WmsEnergyAlert(models.Model):
    _name = 'wms.energy.alert'
    _description = 'WMS Energy Alert'
    _order = 'create_date desc'

    name = fields.Char('Alert Name', required=True)
    equipment_id = fields.Many2one('wms.energy.equipment', 'Equipment')
    alert_type = fields.Selection([
        ('high_consumption', 'High Consumption'),
        ('peak_demand', 'Peak Demand Exceeded'),
        ('anomaly', 'Anomaly Detected'),
        ('maintenance', 'Maintenance Required'),
        ('efficiency', 'Low Efficiency'),
    ], string='Alert Type', required=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', default='medium', required=True)
    message = fields.Text('Alert Message', required=True)
    alert_date = fields.Datetime('Alert Date', default=fields.Datetime.now)
    is_resolved = fields.Boolean('Resolved', default=False)
    resolved_by = fields.Many2one('res.users', 'Resolved By')
    resolved_date = fields.Datetime('Resolved Date')
    reading_id = fields.Many2one('wms.energy.reading', 'Related Reading')

    def action_resolve_alert(self):
        """Resolve the energy alert"""
        for alert in self:
            alert.is_resolved = True
            alert.resolved_by = self.env.user
            alert.resolved_date = fields.Datetime.now()


class WmsEnergyDashboard(models.Model):
    _name = 'wms.energy.dashboard'
    _description = 'WMS Energy Dashboard'
    _auto = False  # This is a view, not a real table

    name = fields.Char('Dashboard Name')
    owner_id = fields.Many2one('wms.owner', 'Owner')
    period = fields.Char('Period')
    total_energy = fields.Float('Total Energy (kWh)')
    total_cost = fields.Float('Total Cost')
    total_emissions = fields.Float('Total Emissions (kg)')
    avg_efficiency = fields.Float('Average Efficiency %')

    def init(self):
        """Create the SQL view for energy dashboard"""
        tools.drop_view_if_exists(self.env.cr, 'wms_energy_dashboard')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW wms_energy_dashboard AS (
                SELECT
                    min(er.id) as id,
                    er.owner_id,
                    'Monthly' as period,
                    sum(er.energy_consumed) as total_energy,
                    sum(er.cost) as total_cost,
                    sum(er.carbon_emissions) as total_emissions,
                    avg(e.efficiency_rating) as avg_efficiency
                FROM wms_energy_reading er
                JOIN wms_energy_equipment e ON e.id = er.equipment_id
                GROUP BY er.owner_id, 'Monthly'
            )
        """)