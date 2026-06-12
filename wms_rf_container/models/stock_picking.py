from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    container_ids = fields.Many2many('wms.container', 'stock_picking_container_rel',
                                     'picking_id', 'container_id', 'Containers')
    container_count = fields.Integer('Container Count', compute='_compute_container_count')

    @api.depends('container_ids')
    def _compute_container_count(self):
        for picking in self:
            picking.container_count = len(picking.container_ids)
    def action_scan_container(self):
        """RF scan container action for picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.picking.container.scan.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id}
        }


class WmsPickingContainerScanWizard(models.TransientModel):
    _name = 'wms.picking.container.scan.wizard'
    _description = 'WMS Picking Container Scan Wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking', readonly=True)
    container_barcode = fields.Char('Container Barcode', required=True)
    container_id = fields.Many2one('wms.container', 'Container', compute='_compute_container')

    @api.depends('container_barcode')
    def _compute_container(self):
        for wizard in self:
            container = self.env['wms.container'].search([('barcode', '=', wizard.container_barcode)], limit=1)
            wizard.container_id = container

    def action_add_container(self):
        self.ensure_one()
        if self.container_id:
            self.picking_id.container_ids = [(4, self.container_id.id)]
        return {'type': 'ir.actions.act_window_close'}