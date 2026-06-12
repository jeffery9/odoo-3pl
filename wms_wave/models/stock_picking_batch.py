from odoo import models, fields, api


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    owner_id = fields.Many2one('wms.owner', 'Owner')
    batch_type = fields.Selection([
        ('wave', 'Wave'),
        ('zone', 'Zone'),
        ('order', 'Order Group'),
        ('route', 'Route'),
        ('priority', 'Priority')
    ], 'Batch Type', default='wave')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], 'Priority', default='0', index=True)
    estimated_completion_time = fields.Float('Estimated Completion Time (Hours)')
    actual_completion_time = fields.Float('Actual Completion Time (Hours)')
    user_ids = fields.Many2many('res.users', 'batch_user_rel', 'batch_id', 'user_id', 'Assigned Users')
    progress = fields.Float('Progress (%)', compute='_compute_progress')
    def _compute_progress(self):
        for batch in self:
            if batch.picking_ids:
                done_pickings = len(batch.picking_ids.filtered(lambda p: p.state == 'done'))
                batch.progress = (done_pickings / len(batch.picking_ids)) * 100
            else:
                batch.progress = 0.0

    def action_assign_users(self):
        """Assign users to the batch"""
        self.ensure_one()
        return {
            'name': 'Assign Users to Batch',
            'type': 'ir.actions.act_window',
            'res_model': 'wms.batch.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_batch_id': self.id}
        }