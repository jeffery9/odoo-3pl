from odoo import models, fields, api


class WmsQualityControl(models.Model):
    _name = 'wms.quality.control'
    _description = 'WMS Quality Control'
    _order = 'name desc'

    name = fields.Char('Quality Control Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    picking_id = fields.Many2one('stock.picking', 'Picking')
    # Traceability fields
    lot_ids = fields.Many2many('stock.lot', string='Lots/Serials Under QC')
    product_ids = fields.Many2many('product.product', string='Products Under QC')
    # End traceability fields
    qc_type = fields.Selection([
        ('incoming', 'Incoming Inspection'),
        ('outgoing', 'Outgoing Inspection'),
        ('storage', 'Storage Inspection'),
        ('random', 'Random Sampling'),
        ('complaint', 'Complaint Driven'),
    ], 'QC Type', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('reworked', 'Reworked'),
        ('cancelled', 'Cancelled'),
    ], 'Status', default='draft', required=True)
    qc_date = fields.Datetime('QC Date', required=True, default=fields.Datetime.now)
    completion_date = fields.Datetime('Completion Date')
    performed_by = fields.Many2one('res.users', 'Performed By', default=lambda self: self.env.user)
    supervisor_id = fields.Many2one('res.users', 'Supervisor')
    total_points = fields.Integer('Total QC Points', compute='_compute_totals', store=True)
    passed_points = fields.Integer('Passed QC Points', compute='_compute_totals', store=True)
    failed_points = fields.Integer('Failed QC Points', compute='_compute_totals', store=True)
    pass_rate = fields.Float('Pass Rate %', compute='_compute_pass_rate', store=True)
    critical_issues = fields.Integer('Critical Issues', compute='_compute_issues', store=True)
    major_issues = fields.Integer('Major Issues', compute='_compute_issues', store=True)
    minor_issues = fields.Integer('Minor Issues', compute='_compute_issues', store=True)
    notes = fields.Text('Notes')
    qc_checklist_ids = fields.One2many('wms.quality.checklist', 'qc_id', 'QC Checklist')
    qc_issues_ids = fields.One2many('wms.quality.issue', 'qc_id', 'QC Issues')
    corrective_actions_ids = fields.One2many('wms.quality.corrective.action', 'qc_id', 'Corrective Actions')
    # Traceability enhanced fields
    traced_moves_count = fields.Integer('Traced Moves', compute='_compute_traced_moves')
    traced_quantities = fields.Float('Traced Quantities', compute='_compute_traced_quantities')

    @api.model
    def create(self, vals):
        # Auto-populate traceability fields if picking is provided
        if vals.get('picking_id'):
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking:
                # Extract lots from picking move lines
                all_lots = self.env['stock.lot']
                all_products = self.env['product.product']
                for line in picking.move_line_ids:
                    if line.lot_id:
                        all_lots |= line.lot_id
                    if line.lot_ids:
                        all_lots |= line.lot_ids
                    all_products |= line.product_id
                vals['lot_ids'] = [(6, 0, all_lots.ids)]
                vals['product_ids'] = [(6, 0, all_products.ids)]

        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.quality.control') or '/'
        return super().create(vals)

    def write(self, vals):
        # Auto-populate traceability fields if picking is updated
        if vals.get('picking_id') and not vals.get('lot_ids') and not vals.get('product_ids'):
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking:
                # Extract lots from picking move lines
                all_lots = self.env['stock.lot']
                all_products = self.env['product.product']
                for line in picking.move_line_ids:
                    if line.lot_id:
                        all_lots |= line.lot_id
                    if line.lot_ids:
                        all_lots |= line.lot_ids
                    all_products |= line.product_id
                vals['lot_ids'] = [(6, 0, all_lots.ids)]
                vals['product_ids'] = [(6, 0, all_products.ids)]

        return super().write(vals)

    @api.depends('qc_checklist_ids', 'qc_checklist_ids.result')
    def _compute_totals(self):
        for record in self:
            record.total_points = len(record.qc_checklist_ids)
            record.passed_points = len(record.qc_checklist_ids.filtered(lambda c: c.result == 'pass'))
            record.failed_points = len(record.qc_checklist_ids.filtered(lambda c: c.result == 'fail'))

    @api.depends('total_points', 'passed_points')
    def _compute_pass_rate(self):
        for record in self:
            if record.total_points > 0:
                record.pass_rate = (record.passed_points / record.total_points) * 100
            else:
                record.pass_rate = 100.0

    @api.depends('qc_issues_ids', 'qc_issues_ids.severity')
    def _compute_issues(self):
        for record in self:
            record.critical_issues = len(record.qc_issues_ids.filtered(lambda i: i.severity == 'critical'))
            record.major_issues = len(record.qc_issues_ids.filtered(lambda i: i.severity == 'major'))
            record.minor_issues = len(record.qc_issues_ids.filtered(lambda i: i.severity == 'minor'))

    @api.depends('picking_id', 'picking_id.move_ids')
    def _compute_traced_moves(self):
        """Compute number of traced moves for this QC"""
        for record in self:
            if record.picking_id:
                record.traced_moves_count = len(record.picking_id.move_ids)
            else:
                record.traced_moves_count = 0

    @api.depends('picking_id', 'picking_id.move_line_ids.quantity')
    def _compute_traced_quantities(self):
        """Compute total traced quantities for this QC"""
        for record in self:
            if record.picking_id:
                record.traced_quantities = sum(record.picking_id.move_line_ids.mapped('quantity'))
            else:
                record.traced_quantities = 0.0

    def action_view_lots(self):
        """View lots/serials associated with this QC"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lots/Serials under QC',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.lot_ids.ids)],
            'context': {'default_company_id': self.company_id.id if hasattr(self, 'company_id') else False}
        }

    def action_view_products(self):
        """View products associated with this QC"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products under QC',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }

    def action_view_related_moves(self):
        """View related stock moves"""
        self.ensure_one()
        if self.picking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Related Stock Moves',
                'res_model': 'stock.move',
                'view_mode': 'list,form',
                'domain': [('picking_id', '=', self.picking_id.id)],
            }
        else:
            # If no picking, try to find moves related to the lots/products
            domain = []
            if self.lot_ids:
                domain.append(('move_line_ids.lot_id', 'in', self.lot_ids.ids))
            elif self.product_ids:
                domain.append(('product_id', 'in', self.product_ids.ids))

            return {
                'type': 'ir.actions.act_window',
                'name': 'Related Stock Moves',
                'res_model': 'stock.move',
                'view_mode': 'list,form',
                'domain': domain,
            }

    def action_start_qc(self):
        """Start the quality control process"""
        self.write({
            'status': 'in_progress',
            'qc_date': fields.Datetime.now()
        })

    def action_pass_qc(self):
        """Pass the quality control check"""
        self.write({
            'status': 'passed',
            'completion_date': fields.Datetime.now()
        })

    def action_fail_qc(self):
        """Fail the quality control check"""
        self.write({
            'status': 'failed',
            'completion_date': fields.Datetime.now()
        })

    def action_rework_qc(self):
        """Mark quality control as reworked"""
        self.write({'status': 'reworked'})

    def action_cancel_qc(self):
        """Cancel quality control"""
        self.write({'status': 'cancelled'})

    def action_generate_report(self):
        """Generate quality control report"""
        self.ensure_one()
        return self.env.ref('wms_quality_control.action_report_quality_control').report_action(self)


class WmsQualityChecklist(models.Model):
    _name = 'wms.quality.checklist'
    _description = 'WMS Quality Control Checklist'
    _order = 'sequence'

    qc_id = fields.Many2one('wms.quality.control', 'Quality Control', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Check Item', required=True)
    description = fields.Text('Description')
    inspection_method = fields.Selection([
        ('visual', 'Visual Inspection'),
        ('measurement', 'Measurement'),
        ('functional', 'Functional Test'),
        ('chemical', 'Chemical Test'),
        ('sampling', 'Sampling'),
    ], 'Inspection Method')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('na', 'N/A'),
    ], 'Result', default='na')
    comments = fields.Text('Comments')
    photo_ids = fields.One2many('wms.quality.photo', 'checklist_id', 'Photos')
    criticality = fields.Selection([
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
    ], 'Criticality', default='minor')
    owner_id = fields.Many2one('wms.owner', 'Owner', related='qc_id.owner_id', store=True)


class WmsQualityIssue(models.Model):
    _name = 'wms.quality.issue'
    _description = 'WMS Quality Issue'
    _order = 'create_date desc'

    qc_id = fields.Many2one('wms.quality.control', 'Quality Control', required=True, ondelete='cascade')
    name = fields.Char('Issue Description', required=True)
    severity = fields.Selection([
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
    ], 'Severity', required=True)
    category = fields.Selection([
        ('product', 'Product Defect'),
        ('packaging', 'Packaging Issue'),
        ('labeling', 'Labeling Error'),
        ('quantity', 'Quantity Discrepancy'),
        ('temperature', 'Temperature Control'),
        ('contamination', 'Contamination'),
        ('damage', 'Physical Damage'),
        ('other', 'Other'),
    ], 'Category', required=True)
    quantity_affected = fields.Float('Quantity Affected')
    corrective_action_required = fields.Boolean('Corrective Action Required', default=True)
    status = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], 'Status', default='open')
    notes = fields.Text('Notes')
    root_cause = fields.Text('Root Cause')
    owner_id = fields.Many2one('wms.owner', 'Owner', related='qc_id.owner_id', store=True)


class WmsQualityCorrectiveAction(models.Model):
    _name = 'wms.quality.corrective.action'
    _description = 'WMS Quality Corrective Action'

    qc_id = fields.Many2one('wms.quality.control', 'Quality Control', required=True, ondelete='cascade')
    issue_id = fields.Many2one('wms.quality.issue', 'Quality Issue', ondelete='cascade')
    description = fields.Text('Action Description', required=True)
    assigned_to = fields.Many2one('res.users', 'Assigned To')
    due_date = fields.Date('Due Date')
    completion_date = fields.Date('Completion Date')
    status = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
    ], 'Status', default='open')
    verification_notes = fields.Text('Verification Notes')
    owner_id = fields.Many2one('wms.owner', 'Owner', related='qc_id.owner_id', store=True)

    def action_complete_action(self):
        """Mark corrective action as completed"""
        self.write({
            'status': 'completed',
            'completion_date': fields.Date.today()
        })

    def action_verify_action(self):
        """Verify corrective action completion"""
        self.write({'status': 'verified'})


class WmsQualityPhoto(models.Model):
    _name = 'wms.quality.photo'
    _description = 'WMS Quality Photo'

    checklist_id = fields.Many2one('wms.quality.checklist', 'Checklist Item', required=True, ondelete='cascade')
    name = fields.Char('Photo Name')
    image = fields.Binary('Image')
    description = fields.Text('Description')
    taken_by = fields.Many2one('res.users', 'Taken By', default=lambda self: self.env.user)
    taken_date = fields.Datetime('Taken Date', default=fields.Datetime.now)
    owner_id = fields.Many2one('wms.owner', 'Owner', related='checklist_id.qc_id.owner_id', store=True)


class WmsQualityControlWizard(models.TransientModel):
    _name = 'wms.quality.control.wizard'
    _description = 'WMS Quality Control Wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    qc_type = fields.Selection([
        ('incoming', 'Incoming Inspection'),
        ('outgoing', 'Outgoing Inspection'),
        ('storage', 'Storage Inspection'),
        ('random', 'Random Sampling'),
        ('complaint', 'Complaint Driven'),
    ], 'QC Type', required=True, default='incoming')
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    notes = fields.Text('Notes')

    def action_create_qc(self):
        """Create quality control record"""
        self.ensure_one()

        # Create the quality control record
        qc = self.env['wms.quality.control'].create({
            'picking_id': self.picking_id.id,
            'qc_type': self.qc_type,
            'owner_id': self.owner_id.id,
            'notes': self.notes,
            'status': 'draft',
        })

        # Add default checklist items based on QC type
        self._add_default_checklist_items(qc)

        # Start the QC process
        qc.action_start_qc()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.quality.control',
            'res_id': qc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _add_default_checklist_items(self, qc):
        """Add default checklist items based on QC type"""
        default_items = {
            'incoming': [
                {'name': 'Packaging Integrity', 'criticality': 'major'},
                {'name': 'Product Condition', 'criticality': 'critical'},
                {'name': 'Label Accuracy', 'criticality': 'major'},
                {'name': 'Quantity Verification', 'criticality': 'critical'},
                {'name': 'Temperature Check', 'criticality': 'major'},
            ],
            'outgoing': [
                {'name': 'Order Accuracy', 'criticality': 'critical'},
                {'name': 'Packaging Condition', 'criticality': 'major'},
                {'name': 'Label Verification', 'criticality': 'major'},
                {'name': 'Weight Check', 'criticality': 'minor'},
            ],
            'storage': [
                {'name': 'Storage Condition', 'criticality': 'major'},
                {'name': 'Pest Control', 'criticality': 'critical'},
                {'name': 'Temperature/Humidity', 'criticality': 'major'},
                {'name': 'Damage Assessment', 'criticality': 'major'},
            ],
            'random': [
                {'name': 'Product Quality', 'criticality': 'major'},
                {'name': 'Packaging Quality', 'criticality': 'major'},
                {'name': 'Label Accuracy', 'criticality': 'minor'},
            ],
            'complaint': [
                {'name': 'Issue Verification', 'criticality': 'critical'},
                {'name': 'Root Cause Analysis', 'criticality': 'major'},
                {'name': 'Corrective Action Plan', 'criticality': 'critical'},
            ],
        }

        items = default_items.get(qc.qc_type, default_items['incoming'])
        for item in items:
            self.env['wms.quality.checklist'].create({
                'qc_id': qc.id,
                'name': item['name'],
                'criticality': item['criticality'],
            })


class WmsQualityIssueWizard(models.TransientModel):
    _name = 'wms.quality.issue.wizard'
    _description = 'WMS Quality Issue Wizard'

    qc_id = fields.Many2one('wms.quality.control', 'Quality Control', required=True)
    name = fields.Char('Issue Description', required=True)
    severity = fields.Selection([
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
    ], 'Severity', required=True, default='major')
    category = fields.Selection([
        ('product', 'Product Defect'),
        ('packaging', 'Packaging Issue'),
        ('labeling', 'Labeling Error'),
        ('quantity', 'Quantity Discrepancy'),
        ('temperature', 'Temperature Control'),
        ('contamination', 'Contamination'),
        ('damage', 'Physical Damage'),
        ('other', 'Other'),
    ], 'Category', required=True, default='product')
    quantity_affected = fields.Float('Quantity Affected')
    notes = fields.Text('Notes')

    def action_create_issue(self):
        """Create quality issue record"""
        self.ensure_one()
        self.env['wms.quality.issue'].create({
            'qc_id': self.qc_id.id,
            'name': self.name,
            'severity': self.severity,
            'category': self.category,
            'quantity_affected': self.quantity_affected,
            'notes': self.notes,
        })
        return {'type': 'ir.actions.act_window_close'}