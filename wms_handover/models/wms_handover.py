from odoo import models, fields, api


class WmsHandover(models.Model):
    _name = 'wms.handover'
    _description = 'WMS Handover'
    _order = 'handover_date desc'

    name = fields.Char('Handover Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    handover_type = fields.Selection([
        ('inbound', 'Inbound Handover'),
        ('outbound', 'Outbound Handover'),
        ('internal', 'Internal Transfer'),
        ('crossdock', 'Crossdock Handover'),
    ], 'Handover Type', required=True)
    from_party_id = fields.Many2one('res.partner', 'From Party', required=True)
    to_party_id = fields.Many2one('res.partner', 'To Party', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('signed_off', 'Signed Off'),
        ('archived', 'Archived'),
    ], 'Status', default='draft', required=True)
    handover_date = fields.Datetime('Handover Date', required=True, default=fields.Datetime.now)
    completion_date = fields.Datetime('Completion Date')
    signed_off_date = fields.Datetime('Signed Off Date')
    from_employee_id = fields.Many2one('hr.employee', 'From Employee')
    to_employee_id = fields.Many2one('hr.employee', 'To Employee')
    total_items = fields.Integer('Total Items', compute='_compute_totals', store=True)
    total_value = fields.Float('Total Value', compute='_compute_totals', store=True)
    notes = fields.Text('Notes')
    handover_items = fields.One2many('wms.handover.item', 'handover_id', 'Handover Items')
    documents = fields.One2many('wms.handover.document', 'handover_id', 'Documents')
    signature_from = fields.Binary('From Signature')
    signature_to = fields.Binary('To Signature')
    signature_date = fields.Datetime('Signature Date')
    container_ids = fields.Many2many('wms.container', 'wms_handover_container_rel',
                                     'handover_id', 'container_id', 'Containers')

    @api.model_create_multi
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.handover') or '/'
        return super().create(vals)

    @api.depends('handover_items', 'handover_items.quantity', 'handover_items.unit_value')
    def _compute_totals(self):
        for record in self:
            record.total_items = len(record.handover_items)
            record.total_value = sum(item.quantity * item.unit_value for item in record.handover_items)
    def action_start_handover(self):
        """Start the handover process"""
        self.write({
            'status': 'in_progress',
            'handover_date': fields.Datetime.now()
        })
    def action_complete_handover(self):
        """Complete the handover process"""
        self.write({
            'status': 'completed',
            'completion_date': fields.Datetime.now()
        })
    def action_sign_off(self):
        """Sign off on the handover"""
        self.write({
            'status': 'signed_off',
            'signed_off_date': fields.Datetime.now(),
            'signature_date': fields.Datetime.now()
        })
    def action_archive_handover(self):
        """Archive the handover record"""
        self.write({'status': 'archived'})
    def action_generate_report(self):
        """Generate handover report"""
        self.ensure_one()
        return self.env.ref('wms_handover.action_report_handover').report_action(self)


class WmsHandoverItem(models.Model):
    _name = 'wms.handover.item'
    _description = 'WMS Handover Item'

    handover_id = fields.Many2one('wms.handover', 'Handover', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    quantity = fields.Float('Quantity', required=True)
    unit_value = fields.Float('Unit Value', required=True)
    uom_id = fields.Many2one('uom.uom', 'UOM', required=True)
    notes = fields.Text('Notes')
    container_id = fields.Many2one('wms.container', 'Container')
    owner_id = fields.Many2one('wms.owner', 'Owner', related='handover_id.owner_id', store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-set UOM and unit value when product is selected"""
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.unit_value = self.product_id.standard_price


class WmsHandoverDocument(models.Model):
    _name = 'wms.handover.document'
    _description = 'WMS Handover Document'

    handover_id = fields.Many2one('wms.handover', 'Handover', required=True, ondelete='cascade')
    name = fields.Char('Document Name', required=True)
    document_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('packing_list', 'Packing List'),
        ('delivery_note', 'Delivery Note'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ], 'Document Type', required=True)
    document_file = fields.Binary('Document File')
    file_name = fields.Char('File Name')
    upload_date = fields.Datetime('Upload Date', default=fields.Datetime.now)
    uploaded_by = fields.Many2one('res.users', 'Uploaded By', default=lambda self: self.env.user)


class WmsHandoverWizard(models.TransientModel):
    _name = 'wms.handover.wizard'
    _description = 'WMS Handover Wizard'

    handover_id = fields.Many2one('wms.handover', 'Handover', required=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    from_party_id = fields.Many2one('res.partner', 'From Party', required=True)
    to_party_id = fields.Many2one('res.partner', 'To Party', required=True)
    handover_type = fields.Selection([
        ('inbound', 'Inbound Handover'),
        ('outbound', 'Outbound Handover'),
        ('internal', 'Internal Transfer'),
        ('crossdock', 'Crossdock Handover'),
    ], 'Handover Type', required=True, default='outbound')
    notes = fields.Text('Notes')
    def action_create_handover(self):
        """Create handover record"""
        self.ensure_one()

        handover = self.env['wms.handover'].create({
            'picking_id': self.picking_id.id,
            'owner_id': self.picking_id.owner_id.id if hasattr(self.picking_id, 'owner_id') and self.picking_id.owner_id else False,
            'handover_type': self.handover_type,
            'from_party_id': self.from_party_id.id,
            'to_party_id': self.to_party_id.id,
            'notes': self.notes,
            'status': 'draft',
        })

        # Copy items from picking moves
        for move in self.picking_id.move_ids_without_package:
            self.env['wms.handover.item'].create({
                'handover_id': handover.id,
                'product_id': move.product_id.id,
                'quantity': move.product_uom_qty,
                'unit_value': move.product_id.standard_price,
                'uom_id': move.product_uom.id,
            })

        # Start the handover
        handover.action_start_handover()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.handover',
            'res_id': handover.id,
            'view_mode': 'form',
            'target': 'current',
        }


class WmsHandoverSignOffWizard(models.TransientModel):
    _name = 'wms.handover.signoff.wizard'
    _description = 'WMS Handover Sign Off Wizard'

    handover_id = fields.Many2one('wms.handover', 'Handover', required=True)
    signature_from = fields.Binary('From Signature', required=True)
    signature_to = fields.Binary('To Signature', required=True)
    notes = fields.Text('Notes')
    def action_sign_off(self):
        """Sign off the handover"""
        self.ensure_one()
        self.handover_id.write({
            'signature_from': self.signature_from,
            'signature_to': self.signature_to,
            'notes': self.notes,
        })
        self.handover_id.action_sign_off()
        return {'type': 'ir.actions.act_window_close'}