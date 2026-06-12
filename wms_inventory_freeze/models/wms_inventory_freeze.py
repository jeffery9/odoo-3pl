from odoo import models, fields, api


class WmsInventoryFreeze(models.Model):
    _name = 'wms.inventory.freeze'
    _description = 'WMS Inventory Freeze'
    _order = 'freeze_date desc'

    name = fields.Char('Freeze Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    product_id = fields.Many2one('product.product', 'Product')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    reason = fields.Selection([
        ('quality_issue', 'Quality Issue'),
        ('investigation', 'Investigation'),
        ('discrepancy', 'Discrepancy'),
        ('audit', 'Audit'),
        ('customer_request', 'Customer Request'),
        ('hold', 'Hold'),
    ], 'Reason', required=True)
    freeze_date = fields.Datetime('Freeze Date', required=True, default=fields.Datetime.now)
    unfreeze_date = fields.Datetime('Unfreeze Date')
    status = fields.Selection([
        ('frozen', 'Frozen'),
        ('unfrozen', 'Unfrozen'),
        ('released', 'Released'),
    ], 'Status', default='frozen', required=True)
    frozen_by = fields.Many2one('res.users', 'Frozen By', default=lambda self: self.env.user)
    unfrozen_by = fields.Many2one('res.users', 'Unfrozen By')
    quantity = fields.Float('Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', 'UOM', required=True)
    notes = fields.Text('Notes')
    freeze_type = fields.Selection([
        ('location', 'Location Freeze'),
        ('product', 'Product Freeze'),
        ('lot', 'Lot Freeze'),
        ('partial', 'Partial Freeze'),
    ], 'Freeze Type', required=True)
    related_inventory_id = fields.Many2one('stock.inventory', 'Related Inventory Adjustment')
    expiry_date = fields.Date('Expiry Date', compute='_compute_expiry_date', store=True)

    @api.depends('lot_id')
    def _compute_expiry_date(self):
        for record in self:
            if record.lot_id and hasattr(record.lot_id, 'expiry_date'):
                record.expiry_date = record.lot_id.expiry_date
            else:
                record.expiry_date = False

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.inventory.freeze') or '/'
        return super().create(vals)
    def action_unfreeze(self):
        """Unfreeze the inventory"""
        self.write({
            'status': 'unfrozen',
            'unfreeze_date': fields.Datetime.now(),
            'unfrozen_by': self.env.user.id
        })
    def action_release(self):
        """Release the inventory (unfreeze permanently)"""
        self.write({
            'status': 'released',
            'unfreeze_date': fields.Datetime.now(),
            'unfrozen_by': self.env.user.id
        })
    def action_freeze_report(self):
        """Generate freeze report"""
        self.ensure_one()
        return self.env.ref('wms_inventory_freeze.action_report_inventory_freeze').report_action(self)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-set UOM when product is selected"""
        if self.product_id:
            self.uom_id = self.product_id.uom_id


class WmsInventoryFreezeWizard(models.TransientModel):
    _name = 'wms.inventory.freeze.wizard'
    _description = 'WMS Inventory Freeze Wizard'

    freeze_type = fields.Selection([
        ('location', 'Location Freeze'),
        ('product', 'Product Freeze'),
        ('lot', 'Lot Freeze'),
        ('partial', 'Partial Freeze'),
    ], 'Freeze Type', required=True, default='partial')
    location_id = fields.Many2one('stock.location', 'Location')
    product_id = fields.Many2one('product.product', 'Product')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    quantity = fields.Float('Quantity', default=1.0)
    reason = fields.Selection([
        ('quality_issue', 'Quality Issue'),
        ('investigation', 'Investigation'),
        ('discrepancy', 'Discrepancy'),
        ('audit', 'Audit'),
        ('customer_request', 'Customer Request'),
        ('hold', 'Hold'),
    ], 'Reason', required=True)
    notes = fields.Text('Notes')
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    def action_create_freeze(self):
        """Create inventory freeze record"""
        self.ensure_one()

        freeze = self.env['wms.inventory.freeze'].create({
            'owner_id': self.owner_id.id,
            'location_id': self.location_id.id,
            'product_id': self.product_id.id,
            'lot_id': self.lot_id.id,
            'reason': self.reason,
            'quantity': self.quantity,
            'uom_id': self.product_id.uom_id.id if self.product_id else self.env.ref('uom.product_uom_unit').id,
            'freeze_type': self.freeze_type,
            'notes': self.notes,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.inventory.freeze',
            'res_id': freeze.id,
            'view_mode': 'form',
            'target': 'current',
        }


class WmsUnfreezeWizard(models.TransientModel):
    _name = 'wms.unfreeze.wizard'
    _description = 'WMS Unfreeze Wizard'

    freeze_id = fields.Many2one('wms.inventory.freeze', 'Freeze Record', required=True)
    release = fields.Boolean('Release Permanently', help='Check to release permanently, uncheck to unfreeze temporarily')
    notes = fields.Text('Notes')
    def action_unfreeze(self):
        """Unfreeze or release the inventory"""
        self.ensure_one()
        if self.release:
            self.freeze_id.action_release()
        else:
            self.freeze_id.action_unfreeze()
        return {'type': 'ir.actions.act_window_close'}