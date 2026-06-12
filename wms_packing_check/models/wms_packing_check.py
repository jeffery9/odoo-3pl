from odoo import models, fields, api


class WmsPackingCheck(models.Model):
    _name = 'wms.packing.check'
    _description = 'WMS Packing Check'
    _order = 'name desc'

    name = fields.Char('Packing Check Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], 'Status', default='draft', required=True)
    checker_id = fields.Many2one('res.users', 'Checker', default=lambda self: self.env.user)
    check_date = fields.Datetime('Check Date')
    completion_date = fields.Datetime('Completion Date')
    total_items = fields.Integer('Total Items', compute='_compute_totals', store=True)
    passed_items = fields.Integer('Passed Items', compute='_compute_totals', store=True)
    failed_items = fields.Integer('Failed Items', compute='_compute_totals', store=True)
    pass_rate = fields.Float('Pass Rate %', compute='_compute_pass_rate', store=True)
    notes = fields.Text('Notes')
    required_checks = fields.One2many('wms.packing.check.required', 'packing_check_id', 'Required Checks')
    performed_checks = fields.One2many('wms.packing.check.performed', 'packing_check_id', 'Performed Checks')
    container_ids = fields.Many2many('wms.container', 'wms_packing_check_container_rel',
                                     'packing_check_id', 'container_id', 'Containers')

    @api.model_create_multi
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.packing.check') or '/'
        return super().create(vals)

    @api.depends('performed_checks', 'performed_checks.result')
    def _compute_totals(self):
        for record in self:
            total = len(record.performed_checks)
            passed = len(record.performed_checks.filtered(lambda c: c.result == 'pass'))
            failed = len(record.performed_checks.filtered(lambda c: c.result == 'fail'))

            record.total_items = total
            record.passed_items = passed
            record.failed_items = failed

    @api.depends('total_items', 'passed_items')
    def _compute_pass_rate(self):
        for record in self:
            if record.total_items > 0:
                record.pass_rate = (record.passed_items / record.total_items) * 100
            else:
                record.pass_rate = 100.0

    def action_start_check(self):
        """Start the packing check process"""
        self.write({
            'status': 'in_progress',
            'check_date': fields.Datetime.now()
        })
    def action_complete_check(self):
        """Complete the packing check process"""
        # Determine final status based on pass rate
        final_status = 'passed' if self.pass_rate >= 95.0 else 'failed'
        self.write({
            'status': final_status,
            'completion_date': fields.Datetime.now()
        })
    def action_reject_check(self):
        """Manually reject the packing check"""
        self.write({'status': 'failed'})
    def action_approve_check(self):
        """Manually approve the packing check"""
        self.write({'status': 'passed'})
    def action_generate_report(self):
        """Generate packing check report"""
        self.ensure_one()
        return self.env.ref('wms_packing_check.action_report_packing_check').report_action(self)


class WmsPackingCheckRequired(models.Model):
    _name = 'wms.packing.check.required'
    _description = 'WMS Packing Check Required Items'

    packing_check_id = fields.Many2one('wms.packing.check', 'Packing Check', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    expected_quantity = fields.Float('Expected Quantity', required=True)
    lot_id = fields.Many2one('stock.lot', 'Expected Lot/Serial')
    uom_id = fields.Many2one('uom.uom', 'UOM', required=True)
    notes = fields.Text('Notes')


class WmsPackingCheckPerformed(models.Model):
    _name = 'wms.packing.check.performed'
    _description = 'WMS Packing Check Performed Items'

    packing_check_id = fields.Many2one('wms.packing.check', 'Packing Check', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    checked_quantity = fields.Float('Checked Quantity', required=True)
    lot_id = fields.Many2one('stock.lot', 'Checked Lot/Serial')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('conditional', 'Conditional'),
    ], 'Result', required=True, default='pass')
    notes = fields.Text('Notes')
    checked_by = fields.Many2one('res.users', 'Checked By', default=lambda self: self.env.user)
    check_date = fields.Datetime('Check Date', default=fields.Datetime.now)
    uom_id = fields.Many2one('uom.uom', 'UOM', required=True)
    container_id = fields.Many2one('wms.container', 'Container')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-set UOM when product is selected"""
        if self.product_id:
            self.uom_id = self.product_id.uom_id


class WmsPackingCheckWizard(models.TransientModel):
    _name = 'wms.packing.check.wizard'
    _description = 'WMS Packing Check Wizard'

    packing_check_id = fields.Many2one('wms.packing.check', 'Packing Check', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    checked_quantity = fields.Float('Checked Quantity', required=True, default=1.0)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('conditional', 'Conditional'),
    ], 'Result', required=True, default='pass')
    notes = fields.Text('Notes')
    container_id = fields.Many2one('wms.container', 'Container')
    def action_add_performed_check(self):
        """Add performed check to the packing check session"""
        self.ensure_one()
        self.env['wms.packing.check.performed'].create({
            'packing_check_id': self.packing_check_id.id,
            'product_id': self.product_id.id,
            'checked_quantity': self.checked_quantity,
            'lot_id': self.lot_id.id,
            'result': self.result,
            'notes': self.notes,
            'uom_id': self.product_id.uom_id.id,
            'container_id': self.container_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}


class WmsStartPackingCheckWizard(models.TransientModel):
    _name = 'wms.start.packing.check.wizard'
    _description = 'WMS Start Packing Check Wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    container_ids = fields.Many2many('wms.container', string='Containers to Check')
    def action_create_packing_check(self):
        """Create a new packing check session from picking"""
        self.ensure_one()

        # Create the packing check record
        packing_check = self.env['wms.packing.check'].create({
            'picking_id': self.picking_id.id,
            'owner_id': self.owner_id.id,
            'status': 'draft',
        })

        # Copy required items from picking moves
        for move in self.picking_id.move_ids_without_package:
            self.env['wms.packing.check.required'].create({
                'packing_check_id': packing_check.id,
                'product_id': move.product_id.id,
                'expected_quantity': move.product_uom_qty,
                'uom_id': move.product_uom.id,
            })

        # Add containers if specified
        if self.container_ids:
            packing_check.container_ids = self.container_ids

        # Start the packing check process
        packing_check.action_start_check()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.packing.check',
            'res_id': packing_check.id,
            'view_mode': 'form',
            'target': 'current',
        }