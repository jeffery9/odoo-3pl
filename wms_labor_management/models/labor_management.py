from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WmsLaborActivity(models.Model):
    _name = 'wms.labor.activity'
    _description = 'WMS Labor Activity'
    _order = 'name'

    name = fields.Char('Activity Name', required=True)
    code = fields.Char('Activity Code', required=True)
    description = fields.Text('Description')
    activity_type = fields.Selection([
        ('receiving', 'Receiving'),
        ('putaway', 'Putaway'),
        ('picking', 'Picking'),
        ('packing', 'Packing'),
        ('shipping', 'Shipping'),
        ('inventory', 'Inventory'),
        ('quality', 'Quality Control'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ], string='Activity Type', required=True)
    standard_time = fields.Float('Standard Time (minutes)', help='Standard time to complete this activity')
    active = fields.Boolean('Active', default=True)


class WmsLaborTask(models.Model):
    _name = 'wms.labor.task'
    _description = 'WMS Labor Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, planned_start_date'

    name = fields.Char('Task Name', required=True)
    task_code = fields.Char('Task Code', required=True, copy=False, readonly=True,
                            default=lambda self: _('New'))
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True,
                               default=lambda self: self.env['wms.owner'].get_default_owner())
    activity_id = fields.Many2one('wms.labor.activity', 'Activity', required=True)
    assigned_to = fields.Many2one('hr.employee', 'Assigned To', required=True)
    assigned_team = fields.Many2one('hr.department', 'Assigned Team')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1')

    # Task Details
    planned_start_date = fields.Datetime('Planned Start', required=True)
    planned_end_date = fields.Datetime('Planned End')
    actual_start_date = fields.Datetime('Actual Start')
    actual_end_date = fields.Datetime('Actual End')
    duration = fields.Float('Duration (hours)', compute='_compute_duration', store=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Related Work
    picking_id = fields.Many2one('stock.picking', 'Related Picking')
    inventory_id = fields.Many2one('stock.inventory', 'Related Inventory')
    qc_session_id = fields.Many2one('wms.quality.control', 'Related QC Session')
    quantity_processed = fields.Float('Quantity Processed', default=0.0)

    # Performance
    standard_duration = fields.Float('Standard Duration (hours)', compute='_compute_standard_duration', store=True)
    efficiency = fields.Float('Efficiency %', compute='_compute_efficiency', store=True)
    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('task_code', _('New')) == _('New'):
            vals['task_code'] = self.env['ir.sequence'].next_by_code('wms.labor.task') or _('New')
        return super().create(vals)

    @api.depends('actual_start_date', 'actual_end_date')
    def _compute_duration(self):
        for task in self:
            if task.actual_start_date and task.actual_end_date:
                duration = (task.actual_end_date - task.actual_start_date).total_seconds() / 3600
                task.duration = duration
            else:
                task.duration = 0.0

    @api.depends('activity_id.standard_time')
    def _compute_standard_duration(self):
        for task in self:
            if task.activity_id and task.activity_id.standard_time:
                # Convert minutes to hours
                task.standard_duration = task.activity_id.standard_time / 60.0
            else:
                task.standard_duration = 0.0

    @api.depends('duration', 'standard_duration')
    def _compute_efficiency(self):
        for task in self:
            if task.duration > 0 and task.standard_duration > 0:
                # Efficiency = (standard / actual) * 100
                # Higher than 100% means faster than standard
                task.efficiency = (task.standard_duration / task.duration) * 100
            elif task.duration == 0 and task.standard_duration == 0:
                task.efficiency = 0.0
            elif task.duration == 0:
                task.efficiency = 0.0  # Not started
            else:
                task.efficiency = 0.0  # Completed with no standard

    def action_start_task(self):
        """Start the task"""
        for task in self:
            if task.status in ['draft', 'assigned']:
                task.status = 'in_progress'
                task.actual_start_date = fields.Datetime.now()

    def action_complete_task(self):
        """Complete the task"""
        for task in self:
            if task.status == 'in_progress':
                task.status = 'completed'
                task.actual_end_date = fields.Datetime.now()

    def action_cancel_task(self):
        """Cancel the task"""
        for task in self:
            if task.status in ['draft', 'assigned', 'in_progress']:
                task.status = 'cancelled'

    def action_reset_to_assigned(self):
        """Reset task to assigned status"""
        for task in self:
            if task.status == 'in_progress':
                task.status = 'assigned'
                task.actual_start_date = False


class WmsLaborSchedule(models.Model):
    _name = 'wms.labor.schedule'
    _description = 'WMS Labor Schedule'
    _order = 'date_start desc'

    name = fields.Char('Schedule Name', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    date_start = fields.Datetime('Start Date', required=True)
    date_end = fields.Datetime('End Date', required=True)
    schedule_type = fields.Selection([
        ('regular', 'Regular Shift'),
        ('overtime', 'Overtime'),
        ('temporary', 'Temporary Assignment'),
    ], string='Schedule Type', default='regular')
    is_active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for schedule in self:
            if schedule.date_start and schedule.date_end and schedule.date_start >= schedule.date_end:
                raise ValidationError(_('End date must be after start date.'))

    @api.constrains('date_start', 'date_end', 'employee_id')
    def _check_overlapping_schedule(self):
        for schedule in self:
            overlapping = self.search([
                ('id', '!=', schedule.id),
                ('employee_id', '=', schedule.employee_id.id),
                ('is_active', '=', True),
                ('date_start', '<', schedule.date_end),
                ('date_end', '>', schedule.date_start),
            ])
            if overlapping:
                raise ValidationError(_('Employee already has a schedule overlapping this time period.'))


class WmsEmployeeSkill(models.Model):
    _name = 'wms.employee.skill'
    _description = 'WMS Employee Skill'

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    skill_id = fields.Many2one('wms.labor.activity', 'Skill', required=True)
    proficiency_level = fields.Selection([
        ('novice', 'Novice'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ], string='Proficiency Level', default='novice')
    certification_date = fields.Date('Certification Date')
    expires_date = fields.Date('Expiration Date')
    notes = fields.Text('Notes')

    _sql_constraints = [
        ('employee_skill_unique', 'UNIQUE(employee_id, skill_id)', 'An employee can only have one skill level per activity.'),
    ]


class WmsLaborPerformance(models.Model):
    _name = 'wms.labor.performance'
    _description = 'WMS Labor Performance'
    _order = 'date_recorded desc'

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    activity_id = fields.Many2one('wms.labor.activity', 'Activity', required=True)
    date_recorded = fields.Date('Date', default=fields.Date.context_today, required=True)
    tasks_completed = fields.Integer('Tasks Completed', default=0)
    hours_worked = fields.Float('Hours Worked', default=0.0)
    efficiency_rate = fields.Float('Efficiency Rate %', help='Average efficiency rate for the day')
    productivity_score = fields.Float('Productivity Score', help='Overall productivity score')

    @api.model
    def create(self, vals):
        # Calculate productivity score based on efficiency rate and tasks completed
        if 'efficiency_rate' in vals and 'tasks_completed' in vals:
            efficiency = vals.get('efficiency_rate', 0.0)
            tasks = vals.get('tasks_completed', 0)
            # Productivity score = (efficiency_rate * tasks) / 100
            vals['productivity_score'] = (efficiency * tasks) / 100.0
        return super().create(vals)

    @api.onchange('efficiency_rate', 'tasks_completed')
    def _onchange_performance_metrics(self):
        if self.efficiency_rate and self.tasks_completed:
            # Calculate productivity score based on efficiency rate and tasks completed
            self.productivity_score = (self.efficiency_rate * self.tasks_completed) / 100.0


class WmsLaborCost(models.Model):
    _name = 'wms.labor.cost'
    _description = 'WMS Labor Cost'
    _order = 'date desc'

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    activity_id = fields.Many2one('wms.labor.activity', 'Activity', required=True)
    date = fields.Date('Date', default=fields.Date.context_today, required=True)
    hours_worked = fields.Float('Hours Worked', required=True)
    hourly_rate = fields.Float('Hourly Rate', required=True)
    overtime_rate = fields.Float('Overtime Rate Multiplier', default=1.0)
    total_cost = fields.Float('Total Cost', compute='_compute_total_cost', store=True)
    task_id = fields.Many2one('wms.labor.task', 'Related Task')
    work_description = fields.Text('Work Description')

    @api.depends('hours_worked', 'hourly_rate', 'overtime_rate')
    def _compute_total_cost(self):
        for cost in self:
            cost.total_cost = cost.hours_worked * cost.hourly_rate * cost.overtime_rate

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            # Set default hourly rate from employee contract
            contracts = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            if contracts:
                self.hourly_rate = contracts.wage / 2080  # Assume 2080 working hours per year for annual salary