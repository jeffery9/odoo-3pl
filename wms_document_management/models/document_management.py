from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64


class WmsDocumentCategory(models.Model):
    _name = 'wms.document.category'
    _description = 'WMS Document Category'
    _order = 'name'
    _parent_store = True

    name = fields.Char('Category Name', required=True)
    code = fields.Char('Category Code', required=True)
    parent_id = fields.Many2one('wms.document.category', 'Parent Category', ondelete='cascade')
    child_ids = fields.One2many('wms.document.category', 'parent_id', 'Child Categories')
    parent_path = fields.Char(index=True)
    description = fields.Text('Description')
    is_active = fields.Boolean('Active', default=True)
    document_count = fields.Integer('Document Count', compute='_compute_document_count')

    def _compute_document_count(self):
        for category in self:
            documents = self.env['wms.document'].search([('category_id', '=', category.id)])
            category.document_count = len(documents)


class WmsDocumentTag(models.Model):
    _name = 'wms.document.tag'
    _description = 'WMS Document Tag'

    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color Index')
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'Tag name already exists!'),
    ]


class WmsDocument(models.Model):
    _name = 'wms.document'
    _description = 'WMS Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Document Name', required=True)
    document_code = fields.Char('Document Code', required=True, copy=False, readonly=True,
                                default=lambda self: _('New'))
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True,
                               default=lambda self: self.env['wms.owner'].get_default_owner())
    category_id = fields.Many2one('wms.document.category', 'Category', required=True)
    tags = fields.Many2many('wms.document.tag', 'wms_document_tag_rel', 'document_id', 'tag_id', 'Tags')

    # File information
    file = fields.Binary('File', attachment=True)
    filename = fields.Char('Filename')
    file_size = fields.Integer('File Size (bytes)', compute='_compute_file_size')
    file_type = fields.Char('File Type', compute='_compute_file_type')

    # Content
    content = fields.Text('Content', help='For text-based documents')
    description = fields.Text('Description')

    # Versioning
    version = fields.Char('Version', default='1.0', required=True)
    revision_date = fields.Date('Revision Date', default=fields.Date.context_today)
    is_latest = fields.Boolean('Latest Version', default=True, compute='_compute_latest_version', store=True)

    # Status and approval
    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)

    approved_by = fields.Many2one('res.users', 'Approved By')
    approved_date = fields.Datetime('Approved Date')
    rejected_reason = fields.Text('Rejection Reason')

    # Related to operations
    related_model = fields.Reference([
        ('stock.picking', 'Stock Picking'),
        ('stock.inventory', 'Stock Inventory'),
        ('wms.quality.control', 'Quality Control'),
        ('wms.return.authorization', 'Return Authorization'),
        ('wms.labor.task', 'Labor Task'),
        ('wms.safety.incident', 'Safety Incident'),
    ], string='Related To')

    related_id = fields.Char('Related ID')

    # Retention and archival
    retention_period = fields.Integer('Retention Period (days)', help='Number of days to retain document')
    expiry_date = fields.Date('Expiry Date', compute='_compute_expiry_date', store=True)
    auto_archive = fields.Boolean('Auto Archive', help='Automatically archive when expired')

    # Access control
    allowed_users = fields.Many2many('res.users', 'wms_document_user_rel', 'document_id', 'user_id', 'Allowed Users')
    allowed_groups = fields.Many2many('res.groups', 'wms_document_group_rel', 'document_id', 'group_id', 'Allowed Groups')

    # Metadata
    author = fields.Char('Author')
    keywords = fields.Char('Keywords')
    created_date = fields.Datetime('Created Date', default=fields.Datetime.now, readonly=True)
    last_updated = fields.Datetime('Last Updated', default=fields.Datetime.now)
    download_count = fields.Integer('Download Count', default=0, readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('document_code', _('New')) == _('New'):
            vals['document_code'] = self.env['ir.sequence'].next_by_code('wms.document') or _('New')
        return super().create(vals)

    @api.depends('file')
    def _compute_file_size(self):
        for document in self:
            if document.file:
                document.file_size = len(base64.b64decode(document.file))
            else:
                document.file_size = 0

    @api.depends('filename')
    def _compute_file_type(self):
        for document in self:
            if document.filename:
                document.file_type = document.filename.split('.')[-1].upper()
            else:
                document.file_type = False

    @api.depends('name', 'version')
    def _compute_latest_version(self):
        for document in self:
            # A document is latest if no other version of the same document exists with a higher version
            latest_doc = self.search([
                ('name', '=', document.name),
                ('owner_id', '=', document.owner_id.id),
                ('category_id', '=', document.category_id.id)
            ], order='version desc', limit=1)
            document.is_latest = (document.id == latest_doc.id)

    @api.depends('created_date', 'retention_period')
    def _compute_expiry_date(self):
        for document in self:
            if document.created_date and document.retention_period:
                import datetime
                expiry = fields.Date.from_string(document.created_date) + datetime.timedelta(days=document.retention_period)
                document.expiry_date = expiry
            else:
                document.expiry_date = False

    def action_approve(self):
        """Approve the document"""
        for document in self:
            if document.status in ['draft', 'pending_approval']:
                document.status = 'approved'
                document.approved_by = self.env.user
                document.approved_date = fields.Datetime.now()

    def action_reject(self):
        """Reject the document"""
        for document in self:
            if document.status == 'pending_approval':
                document.status = 'rejected'

    def action_archive(self):
        """Archive the document"""
        for document in self:
            document.status = 'archived'

    def action_make_current(self):
        """Make this version the current version"""
        for document in self:
            # Set all other versions of this document to not be latest
            other_versions = self.search([
                ('name', '=', document.name),
                ('owner_id', '=', document.owner_id.id),
                ('category_id', '=', document.category_id.id),
                ('id', '!=', document.id)
            ])
            other_versions.write({'is_latest': False})

            # Set this document as the latest
            document.is_latest = True

    def action_download(self):
        """Increment download count when document is downloaded"""
        for document in self:
            document.download_count += 1

    @api.constrains('version')
    def _check_version_format(self):
        for document in self:
            if document.version:
                # Basic version format check (X.Y or X.Y.Z)
                import re
                if not re.match(r'^\d+\.\d+(\.\d+)?$', document.version):
                    raise ValidationError(_('Version must be in format X.Y or X.Y.Z'))


class WmsDocumentTemplate(models.Model):
    _name = 'wms.document.template'
    _description = 'WMS Document Template'

    name = fields.Char('Template Name', required=True)
    code = fields.Char('Template Code', required=True)
    category_id = fields.Many2one('wms.document.category', 'Category', required=True)
    description = fields.Text('Description')

    # Template structure
    template_type = fields.Selection([
        ('form', 'Form'),
        ('report', 'Report'),
        ('procedure', 'Procedure'),
        ('policy', 'Policy'),
        ('checklist', 'Checklist'),
        ('certificate', 'Certificate'),
    ], string='Template Type', required=True)

    content_template = fields.Text('Content Template', help='Template for document content')
    required_fields = fields.Char('Required Fields', help='Comma-separated list of required fields')

    # Auto-fill rules
    auto_fill_model = fields.Reference([
        ('stock.picking', 'Stock Picking'),
        ('stock.inventory', 'Stock Inventory'),
        ('wms.quality.control', 'Quality Control'),
    ], string='Auto-fill From')

    is_active = fields.Boolean('Active', default=True)

    def create_document_from_template(self, related_record=None):
        """Create a document using this template"""
        if not related_record:
            # If no related record is provided, create an empty document
            return self.env['wms.document'].create({
                'name': f"Document from {self.name}",
                'category_id': self.category_id.id,
                'content': self.content_template,
                'template_id': self.id,
            })
        else:
            # In a real implementation, this would handle auto-filling based on the related record
            # For now, just create a document with the template content
            return self.env['wms.document'].create({
                'name': f"Document from {self.name} for {related_record.display_name}",
                'category_id': self.category_id.id,
                'content': self.content_template,
                'related_model': f"{related_record._name},{related_record.id}",
                'template_id': self.id,
            })


class WmsDocumentWorkflow(models.Model):
    _name = 'wms.document.workflow'
    _description = 'WMS Document Workflow'

    name = fields.Char('Workflow Name', required=True)
    code = fields.Char('Workflow Code', required=True)
    document_category_ids = fields.Many2many('wms.document.category', 'wms_workflow_category_rel', 'workflow_id', 'category_id', 'Applicable Categories')
    initial_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
    ], string='Initial Status', default='draft', required=True)

    # Approval process
    require_approval = fields.Boolean('Require Approval', default=True)
    approval_steps = fields.Integer('Approval Steps', default=1)
    auto_approval = fields.Boolean('Auto Approval', help='Auto-approve based on criteria')
    auto_approval_criteria = fields.Char('Auto Approval Criteria', help='Conditions for auto-approval')

    # Retention
    default_retention = fields.Integer('Default Retention (days)')

    is_active = fields.Boolean('Active', default=True)


class WmsDocumentArchive(models.Model):
    _name = 'wms.document.archive'
    _description = 'WMS Document Archive'
    _order = 'archived_date desc'

    name = fields.Char('Archive Name', required=True)
    document_ids = fields.Many2many('wms.document', 'wms_archive_document_rel', 'archive_id', 'document_id', 'Archived Documents')
    archived_date = fields.Date('Archived Date', default=fields.Date.context_today, required=True)
    reason = fields.Selection([
        ('retention_expired', 'Retention Period Expired'),
        ('manual_archive', 'Manually Archived'),
        ('replaced', 'Replaced by Newer Version'),
        ('project_completion', 'Project Completed'),
    ], string='Reason', required=True)
    notes = fields.Text('Notes')
    archived_by = fields.Many2one('res.users', 'Archived By', default=lambda self: self.env.user)

    def restore_documents(self):
        """Restore documents from archive"""
        for archive in self:
            for document in archive.document_ids:
                document.action_make_current()
                document.status = 'approved'  # Restore to approved status