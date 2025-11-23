from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WmsSafetyIncident(models.Model):
    _name = 'wms.safety.incident'
    _description = 'WMS Safety Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char('Incident Number', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True,
                               default=lambda self: self.env['wms.owner'].get_default_owner())
    incident_date = fields.Datetime('Incident Date', required=True, default=fields.Datetime.now)
    incident_type = fields.Selection([
        ('accident', 'Accident'),
        ('near_miss', 'Near Miss'),
        ('injury', 'Injury'),
        ('illness', 'Occupational Illness'),
        ('property_damage', 'Property Damage'),
        ('vehicle', 'Vehicle Incident'),
        ('fire', 'Fire/Explosion'),
        ('chemical', 'Chemical Spill'),
        ('other', 'Other'),
    ], string='Incident Type', required=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    reported_by = fields.Many2one('hr.employee', 'Reported By', required=True)
    injured_employee_id = fields.Many2one('hr.employee', 'Injured Employee')

    # People involved
    witness_ids = fields.Many2many('hr.employee', 'wms_safety_incident_witness_rel', 'incident_id', 'employee_id', 'Witnesses')
    involved_employee_ids = fields.Many2many('hr.employee', 'wms_safety_incident_involved_rel', 'incident_id', 'employee_id', 'Involved Employees')

    # Incident details
    description = fields.Text('Description', required=True)
    immediate_action_taken = fields.Text('Immediate Action Taken')
    root_cause = fields.Text('Root Cause Analysis')
    corrective_action = fields.Text('Corrective Action')
    preventive_action = fields.Text('Preventive Action')

    # Status and tracking
    status = fields.Selection([
        ('reported', 'Reported'),
        ('investigating', 'Investigating'),
        ('action_required', 'Action Required'),
        ('action_taken', 'Action Taken'),
        ('closed', 'Closed'),
    ], string='Status', default='reported', tracking=True)

    # Follow-up
    investigation_date = fields.Datetime('Investigation Date')
    investigation_by = fields.Many2one('hr.employee', 'Investigation By')
    closure_date = fields.Datetime('Closure Date')
    closure_notes = fields.Text('Closure Notes')

    # Classification
    category = fields.Selection([
        ('slip_trip', 'Slip/Trip/Fall'),
        ('struck_by', 'Struck By Object'),
        ('caught_in', 'Caught In/Between'),
        ('fall_from_height', 'Fall from Height'),
        ('electrical', 'Electrical'),
        ('chemical', 'Chemical Exposure'),
        ('vehicle', 'Vehicle/Mobile Equipment'),
        ('fire', 'Fire/Burn'),
        ('ergonomic', 'Ergonomic'),
        ('stress', 'Work Stress'),
        ('other', 'Other'),
    ], string='Category', required=True)

    # Additional fields
    lost_time_hours = fields.Float('Lost Time Hours', help='Hours of work lost due to incident')
    medical_treatment = fields.Boolean('Medical Treatment Required')
    first_aid_only = fields.Boolean('First Aid Only')
    restricted_work = fields.Boolean('Restricted Work Activity')
    job_transfer = fields.Boolean('Job Transfer Required')


class WmsSafetyTraining(models.Model):
    _name = 'wms.safety.training'
    _description = 'WMS Safety Training'
    _order = 'training_date desc'

    name = fields.Char('Training Name', required=True)
    training_code = fields.Char('Training Code', required=True, copy=False, readonly=True,
                                default=lambda self: _('New'))
    training_type = fields.Selection([
        ('fire_safety', 'Fire Safety'),
        ('chemical_safety', 'Chemical Safety'),
        ('ppe_training', 'PPE Training'),
        ('machine_safety', 'Machine Safety'),
        ('emergency_procedures', 'Emergency Procedures'),
        ('ergonomics', 'Ergonomics'),
        ('first_aid', 'First Aid/CPR'),
        ('hazard_recognition', 'Hazard Recognition'),
        ('forklift_safety', 'Forklift Safety'),
        ('safety_awareness', 'General Safety Awareness'),
        ('other', 'Other'),
    ], string='Training Type', required=True)
    description = fields.Text('Description')
    duration_hours = fields.Float('Duration (hours)', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    trainer_id = fields.Many2one('hr.employee', 'Trainer', required=True)
    training_date = fields.Date('Training Date', required=True)
    expiry_date = fields.Date('Expiry Date', help='Date when certification expires')
    active = fields.Boolean('Active', default=True)

    # Participants
    participant_ids = fields.Many2many('hr.employee', 'wms_safety_training_participant_rel', 'training_id', 'employee_id', 'Participants')
    completed_participant_ids = fields.Many2many('hr.employee', 'wms_safety_training_completed_rel', 'training_id', 'employee_id', 'Completed Participants')

    # Certification
    certificate_required = fields.Boolean('Certificate Required', default=True)
    certification_body = fields.Char('Certification Body')
    certificate_number = fields.Char('Certificate Number')
    cost = fields.Float('Cost', digits='Product Price')


class WmsSafetyPpe(models.Model):
    _name = 'wms.safety.ppe'
    _description = 'WMS Personal Protective Equipment'
    _order = 'name'

    name = fields.Char('PPE Name', required=True)
    ppe_type = fields.Selection([
        ('head', 'Head Protection'),
        ('eye_face', 'Eye/Face Protection'),
        ('hearing', 'Hearing Protection'),
        ('respiratory', 'Respiratory Protection'),
        ('hand', 'Hand Protection'),
        ('body', 'Body Protection'),
        ('foot', 'Foot Protection'),
        ('fall_protection', 'Fall Protection'),
        ('high_visibility', 'High Visibility'),
        ('chemical', 'Chemical Protection'),
        ('other', 'Other'),
    ], string='PPE Type', required=True)
    description = fields.Text('Description')
    size = fields.Char('Size')
    color = fields.Char('Color')
    brand = fields.Char('Brand')
    model_number = fields.Char('Model Number')
    supplier_id = fields.Many2one('res.partner', 'Supplier')
    unit_cost = fields.Float('Unit Cost', digits='Product Price')
    stock_quantity = fields.Integer('Stock Quantity', default=0)
    min_stock_level = fields.Integer('Minimum Stock Level', default=10)
    is_active = fields.Boolean('Active', default=True)

    # Usage tracking
    required_for_jobs = fields.Many2many('wms.labor.activity', 'wms_safety_ppe_job_rel', 'ppe_id', 'activity_id', 'Required For')


class WmsSafetyInspection(models.Model):
    _name = 'wms.safety.inspection'
    _description = 'WMS Safety Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc'

    name = fields.Char('Inspection Name', required=True)
    inspection_code = fields.Char('Inspection Code', required=True, copy=False, readonly=True,
                                  default=lambda self: _('New'))
    inspection_type = fields.Selection([
        ('daily', 'Daily Walkthrough'),
        ('weekly', 'Weekly Inspection'),
        ('monthly', 'Monthly Inspection'),
        ('quarterly', 'Quarterly Audit'),
        ('annual', 'Annual Audit'),
        ('special', 'Special Inspection'),
    ], string='Inspection Type', required=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    inspector_id = fields.Many2one('hr.employee', 'Inspector', required=True)
    inspection_date = fields.Date('Inspection Date', required=True, default=fields.Date.context_today)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('requires_action', 'Requires Action'),
    ], string='Status', default='draft', tracking=True)

    # Owner
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True,
                               default=lambda self: self.env['wms.owner'].get_default_owner())

    # Results
    overall_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Overall Rating')
    findings_count = fields.Integer('Findings Count', compute='_compute_findings_count', store=True)
    critical_findings_count = fields.Integer('Critical Findings', compute='_compute_critical_findings_count', store=True)

    # Actions
    action_required = fields.Boolean('Action Required', compute='_compute_action_required', store=True)
    corrective_actions = fields.Text('Corrective Actions Required')
    follow_up_date = fields.Date('Follow-up Date')

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('inspection_code', _('New')) == _('New'):
            vals['inspection_code'] = self.env['ir.sequence'].next_by_code('wms.safety.inspection') or _('New')
        return super().create(vals)

    @api.depends('status')
    def _compute_findings_count(self):
        for inspection in self:
            findings = self.env['wms.safety.inspection.finding'].search([('inspection_id', '=', inspection.id)])
            inspection.findings_count = len(findings)

    @api.depends('status')
    def _compute_critical_findings_count(self):
        for inspection in self:
            critical_findings = self.env['wms.safety.inspection.finding'].search([
                ('inspection_id', '=', inspection.id),
                ('severity', '=', 'high')
            ])
            inspection.critical_findings_count = len(critical_findings)

    @api.depends('critical_findings_count')
    def _compute_action_required(self):
        for inspection in self:
            inspection.action_required = inspection.critical_findings_count > 0

    def action_start_inspection(self):
        """Start the inspection"""
        for inspection in self:
            inspection.status = 'in_progress'

    def action_complete_inspection(self):
        """Complete the inspection"""
        for inspection in self:
            inspection.status = 'completed'

    def action_require_action(self):
        """Mark as requiring action"""
        for inspection in self:
            if inspection.critical_findings_count > 0:
                inspection.status = 'requires_action'


class WmsSafetyInspectionFinding(models.Model):
    _name = 'wms.safety.inspection.finding'
    _description = 'WMS Safety Inspection Finding'
    _order = 'create_date desc'

    inspection_id = fields.Many2one('wms.safety.inspection', 'Inspection', required=True, ondelete='cascade')
    name = fields.Char('Finding', required=True)
    description = fields.Text('Description')
    location = fields.Char('Specific Location')
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='medium')
    status = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('not_applicable', 'Not Applicable'),
    ], string='Status', default='open')

    # Tracking
    assigned_to = fields.Many2one('hr.employee', 'Assigned To')
    due_date = fields.Date('Due Date')
    resolution_date = fields.Date('Resolution Date')
    resolution_notes = fields.Text('Resolution Notes')

    # Corrective action
    corrective_action = fields.Text('Corrective Action Required')
    preventive_action = fields.Text('Preventive Action')


class WmsSafetyCompliance(models.Model):
    _name = 'wms.safety.compliance'
    _description = 'WMS Safety Compliance'
    _order = 'compliance_date desc'

    name = fields.Char('Compliance Requirement', required=True)
    regulation = fields.Char('Regulation/Standard', required=True)
    description = fields.Text('Description')
    compliance_type = fields.Selection([
        ('regulatory', 'Regulatory'),
        ('internal', 'Internal Policy'),
        ('industry', 'Industry Standard'),
        ('customer', 'Customer Requirement'),
    ], string='Compliance Type', required=True)

    # Requirements
    requirement_details = fields.Text('Requirement Details')
    frequency = fields.Selection([
        ('one_time', 'One Time'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Compliance Frequency', default='annual')

    # Tracking
    compliance_date = fields.Date('Last Compliance Date')
    next_compliance_date = fields.Date('Next Compliance Date')
    compliant = fields.Boolean('Compliant', default=False)
    compliant_until = fields.Date('Compliant Until')

    # Verification
    verified_by = fields.Many2one('hr.employee', 'Verified By')
    verification_date = fields.Date('Verification Date')
    notes = fields.Text('Notes')

    @api.onchange('compliance_date', 'frequency')
    def _onchange_compliance_schedule(self):
        """Auto calculate next compliance date based on frequency"""
        if self.compliance_date and self.frequency and self.frequency != 'one_time':
            import datetime
            if self.frequency == 'monthly':
                next_date = self.compliance_date + datetime.timedelta(days=30)
            elif self.frequency == 'quarterly':
                next_date = self.compliance_date + datetime.timedelta(days=90)
            elif self.frequency == 'annual':
                next_date = self.compliance_date.replace(year=self.compliance_date.year + 1)
            else:
                next_date = self.compliance_date
            self.next_compliance_date = next_date


class WmsSafetyRisk(models.Model):
    _name = 'wms.safety.risk'
    _description = 'WMS Safety Risk Assessment'
    _order = 'risk_score desc'

    name = fields.Char('Risk Name', required=True)
    risk_type = fields.Selection([
        ('physical', 'Physical'),
        ('chemical', 'Chemical'),
        ('biological', 'Biological'),
        ('ergonomic', 'Ergonomic'),
        ('psychosocial', 'Psychosocial'),
        ('environmental', 'Environmental'),
        ('other', 'Other'),
    ], string='Risk Type', required=True)

    # Assessment
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    affected_employees = fields.Many2many('hr.employee', 'wms_safety_risk_employee_rel', 'risk_id', 'employee_id', 'Affected Employees')
    probability = fields.Selection([
        ('very_low', 'Very Low (1)'),
        ('low', 'Low (2)'),
        ('medium', 'Medium (3)'),
        ('high', 'High (4)'),
        ('very_high', 'Very High (5)'),
    ], string='Probability', required=True, help='Likelihood of occurrence (1-5)')

    severity = fields.Selection([
        ('very_low', 'Very Low (1)'),
        ('low', 'Low (2)'),
        ('medium', 'Medium (3)'),
        ('high', 'High (4)'),
        ('very_high', 'Very High (5)'),
    ], string='Severity', required=True, help='Potential impact (1-5)')

    risk_score = fields.Integer('Risk Score', compute='_compute_risk_score', store=True, help='Probability x Severity')

    # Controls
    existing_controls = fields.Text('Existing Controls')
    additional_controls = fields.Text('Additional Controls Needed')
    residual_risk = fields.Integer('Residual Risk', compute='_compute_residual_risk', store=True)

    # Status
    status = fields.Selection([
        ('identified', 'Identified'),
        ('assessed', 'Assessed'),
        ('mitigated', 'Mitigated'),
        ('accepted', 'Accepted'),
        ('eliminated', 'Eliminated'),
    ], string='Status', default='identified')

    owner_id = fields.Many2one('wms.owner', 'Owner', required=True,
                               default=lambda self: self.env['wms.owner'].get_default_owner())
    notes = fields.Text('Notes')

    @api.depends('probability', 'severity')
    def _compute_risk_score(self):
        prob_map = {'very_low': 1, 'low': 2, 'medium': 3, 'high': 4, 'very_high': 5}
        sev_map = {'very_low': 1, 'low': 2, 'medium': 3, 'high': 4, 'very_high': 5}
        for risk in self:
            if risk.probability and risk.severity:
                risk.risk_score = prob_map[risk.probability] * sev_map[risk.severity]
            else:
                risk.risk_score = 0

    @api.depends('risk_score', 'additional_controls')
    def _compute_residual_risk(self):
        for risk in self:
            # Simplified calculation - in real implementation this would be more complex
            # For now, assume residual risk is based on risk_score and control effectiveness
            risk.residual_risk = risk.risk_score  # Placeholder - would be reduced by controls in real system