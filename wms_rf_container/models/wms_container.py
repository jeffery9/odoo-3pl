from odoo import models, fields, api


class WmsContainer(models.Model):
    _name = 'wms.container'
    _description = 'WMS Container'
    _order = 'name'

    name = fields.Char('Container Reference', required=True, copy=False, readonly=True)
    container_type = fields.Selection([
        ('pallet', 'Pallet'),
        ('box', 'Box'),
        ('cart', 'Cart'),
        ('tote', 'Tote'),
        ('bin', 'Bin'),
        ('roll', 'Roll Cage'),
    ], 'Container Type', required=True, default='pallet')
    barcode = fields.Char('Barcode', required=True, copy=False)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    location_id = fields.Many2one('stock.location', 'Current Location')
    status = fields.Selection([
        ('empty', 'Empty'),
        ('partial', 'Partial'),
        ('full', 'Full'),
        ('in_transit', 'In Transit'),
        ('frozen', 'Frozen'),
        ('damaged', 'Damaged'),
    ], 'Status', default='empty', required=True)
    capacity = fields.Float('Capacity (CBM)', help='Total capacity in cubic meters')
    current_load = fields.Float('Current Load (CBM)', compute='_compute_current_load', store=True)
    load_percentage = fields.Float('Load %', compute='_compute_load_percentage', store=True)
    contents = fields.One2many('wms.container.content', 'container_id', 'Contents')
    is_active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')
    parent_container_id = fields.Many2one('wms.container', 'Parent Container')
    child_containers = fields.One2many('wms.container', 'parent_container_id', 'Child Containers')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.container') or '/'
        return super().create(vals)

    @api.depends('contents', 'contents.quantity', 'contents.product_id.volume')
    def _compute_current_load(self):
        for container in self:
            total_volume = sum(
                content.quantity * content.product_id.volume
                for content in container.contents
            )
            container.current_load = total_volume

    @api.depends('current_load', 'capacity')
    def _compute_load_percentage(self):
        for container in self:
            if container.capacity > 0:
                container.load_percentage = (container.current_load / container.capacity) * 100
            else:
                container.load_percentage = 0

    def action_assign_to_location(self):
        """Assign container to a specific location"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.container.location.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_container_id': self.id}
        }
    def action_scan_container(self):
        """RF scan container action"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.container.scan.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_container_barcode': self.barcode}
        }
    def action_pack_contents(self):
        """Pack items into container"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.container.pack.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_container_id': self.id}
        }


class WmsContainerContent(models.Model):
    _name = 'wms.container.content'
    _description = 'WMS Container Content'

    container_id = fields.Many2one('wms.container', 'Container', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    quantity = fields.Float('Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', 'UOM', required=True)
    expiry_date = fields.Date('Expiry Date')
    owner_id = fields.Many2one('wms.owner', 'Owner', related='container_id.owner_id', store=True)

    @api.model
    def create(self, vals):
        if 'uom_id' not in vals and 'product_id' in vals:
            vals['uom_id'] = self.env['product.product'].browse(vals['product_id']).uom_id.id
        return super().create(vals)


class WmsContainerLocationWizard(models.TransientModel):
    _name = 'wms.container.location.wizard'
    _description = 'WMS Container Location Assignment Wizard'

    container_id = fields.Many2one('wms.container', 'Container', readonly=True)
    location_id = fields.Many2one('stock.location', 'New Location', required=True)
    def action_assign_location(self):
        self.ensure_one()
        self.container_id.location_id = self.location_id
        return {'type': 'ir.actions.act_window_close'}


class WmsContainerScanWizard(models.TransientModel):
    _name = 'wms.container.scan.wizard'
    _description = 'WMS Container Scan Wizard'

    container_barcode = fields.Char('Container Barcode', readonly=True)
    container_id = fields.Many2one('wms.container', 'Container', compute='_compute_container')
    location_id = fields.Many2one('stock.location', 'Current Location')
    contents_count = fields.Integer('Contents Count', compute='_compute_contents')

    @api.depends('container_barcode')
    def _compute_container(self):
        for wizard in self:
            container = self.env['wms.container'].search([('barcode', '=', wizard.container_barcode)], limit=1)
            wizard.container_id = container
            wizard.location_id = container.location_id if container else False

    @api.depends('container_id', 'container_id.contents')
    def _compute_contents(self):
        for wizard in self:
            wizard.contents_count = len(wizard.container_id.contents) if wizard.container_id else 0


class WmsContainerPackWizard(models.TransientModel):
    _name = 'wms.container.pack.wizard'
    _description = 'WMS Container Pack Wizard'

    container_id = fields.Many2one('wms.container', 'Container', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    quantity = fields.Float('Quantity', required=True, default=1.0)
    picking_id = fields.Many2one('stock.picking', 'Source Picking')
    def action_pack_product(self):
        self.ensure_one()
        self.env['wms.container.content'].create({
            'container_id': self.container_id.id,
            'product_id': self.product_id.id,
            'lot_id': self.lot_id.id,
            'quantity': self.quantity,
            'uom_id': self.product_id.uom_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}