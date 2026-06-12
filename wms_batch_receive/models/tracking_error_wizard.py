from odoo import models, fields, api


class WmsTrackingErrorWizard(models.TransientModel):
    _name = 'wms.tracking.error.wizard'
    _description = 'WMS Tracking Error Wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking')
    error_count = fields.Integer('Tracking Error Count')
    error_details = fields.Text('Error Details', compute='_compute_error_details')
    action = fields.Selection([
        ('proceed', 'Proceed Anyway'),
        ('fix', 'Fix Tracking Issues First'),
        ('cancel', 'Cancel Operation'),
    ], 'Action', default='fix', required=True)

    @api.depends('picking_id')
    def _compute_error_details(self):
        """Compute details of tracking errors"""
        for wizard in self:
            if wizard.picking_id:
                error_details = []
                for move_line in wizard.picking_id.move_line_ids:
                    product = move_line.product_id
                    if product.tracking != 'none':
                        if product.tracking == 'serial' and not move_line.lot_id:
                            error_details.append(f"Line {move_line.id}: Serial number missing for product {product.display_name}")
                        elif product.tracking == 'lot' and not move_line.lot_id and not move_line.lot_ids:
                            error_details.append(f"Line {move_line.id}: Lot number missing for product {product.display_name}")

                wizard.error_details = '\n'.join(error_details) if error_details else 'No tracking errors found'
            else:
                wizard.error_details = 'No picking selected'

    def action_proceed_anyway(self):
        """Proceed with the operation despite tracking errors"""
        self.ensure_one()
        # Return to the original action (batch receive wizard)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.batch.receive.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_ids': [(6, 0, self.picking_id.ids)], 'default_owner_id': self.picking_id.owner_id.id if hasattr(self.picking_id, 'owner_id') and self.picking_id.owner_id else False}
        }
    def action_fix_issues(self):
        """Redirect to picking form to fix tracking issues"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }
    def action_cancel_operation(self):
        """Cancel the operation"""
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}