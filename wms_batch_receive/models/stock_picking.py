from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    batch_receive_picking_ids = fields.One2many('wms.batch.receive.picking', 'picking_id', 'Batch Receive Pickings')
    batch_receive_count = fields.Integer('Batch Receive Count', compute='_compute_batch_receive_count')
    # Traceability fields
    lot_ids = fields.Many2many('stock.lot', compute='_compute_lot_ids', string='Lots/Serials',
                               help="All lots/serial numbers associated with this picking")
    tracking_error_count = fields.Integer('Tracking Errors', compute='_compute_tracking_errors',
                                          help="Number of tracking errors found in this picking")

    @api.depends('batch_receive_picking_ids')
    def _compute_batch_receive_count(self):
        for picking in self:
            picking.batch_receive_count = len(picking.batch_receive_picking_ids)

    @api.depends('move_line_ids', 'move_line_ids.lot_id')
    def _compute_lot_ids(self):
        for picking in self:
            all_lots = self.env['stock.lot']
            for line in picking.move_line_ids:
                if line.lot_id:
                    all_lots |= line.lot_id
            picking.lot_ids = all_lots

    def _compute_tracking_errors(self):
        """Compute tracking errors for products that require tracking"""
        for picking in self:
            error_count = 0
            for move_line in picking.move_line_ids:
                product = move_line.product_id
                if product.tracking != 'none':
                    # Check if required tracking information is missing
                    if product.tracking == 'serial' and not move_line.lot_id:
                        error_count += 1
                    elif product.tracking == 'lot' and not move_line.lot_id:
                        error_count += 1
            picking.tracking_error_count = error_count

    def action_add_to_batch_receive(self):
        """Add picking to an existing batch receive session"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.batch.receive.add.picking.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_ids': [(6, 0, self.ids)]}
        }

    def action_start_batch_receive(self):
        """Start a batch receive session with this picking"""
        self.ensure_one()
        # Check for tracking issues before starting
        if self.tracking_error_count > 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tracking Issues Found',
                'res_model': 'wms.tracking.error.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_picking_id': self.id,
                    'default_error_count': self.tracking_error_count
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.batch.receive.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_ids': [(6, 0, self.ids)], 'default_owner_id': self.owner_id.id if hasattr(self, 'owner_id') and self.owner_id else False}
        }

    def action_view_batch_receives(self):
        """View batch receives for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Batch Receives',
            'res_model': 'wms.batch.receive.picking',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id}
        }

    def action_view_lots(self):
        """View lots/serials for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lots/Serials',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.lot_ids.ids)],
            'context': {'default_company_id': self.company_id.id}
        }