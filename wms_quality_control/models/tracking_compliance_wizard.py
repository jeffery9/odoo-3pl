from odoo import models, fields, api


class WmsTrackingComplianceWizard(models.TransientModel):
    _name = 'wms.tracking.compliance.wizard'
    _description = 'WMS Tracking Compliance Wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking')
    compliance_rate = fields.Float('Tracking Compliance Rate')
    non_compliant_lines = fields.Integer('Non-Compliant Lines', compute='_compute_non_compliant_lines')
    action = fields.Selection([
        ('proceed', 'Proceed with QC Anyway'),
        ('fix', 'Fix Tracking Issues First'),
        ('review', 'Review Non-Compliant Lines'),
    ], 'Action', default='review', required=True)

    @api.depends('picking_id')
    def _compute_non_compliant_lines(self):
        """Compute number of non-compliant tracking lines"""
        for wizard in self:
            if wizard.picking_id:
                non_compliant = 0
                for line in wizard.picking_id.move_line_ids:
                    if line.product_id.tracking != 'none':
                        if (line.product_id.tracking == 'serial' and not line.lot_id) or \
                           (line.product_id.tracking == 'lot' and not line.lot_id and not line.lot_ids):
                            non_compliant += 1
                wizard.non_compliant_lines = non_compliant
            else:
                wizard.non_compliant_lines = 0

    def action_proceed_anyway(self):
        """Proceed with quality control despite compliance issues"""
        self.ensure_one()
        # Create a quality control wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.quality.control.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_owner_id': self.picking_id.owner_id.id if hasattr(self.picking_id, 'owner_id') and self.picking_id.owner_id else False,
                'tracking_warning_ignored': True
            }
        }
    def action_fix_issues(self):
        """Redirect to picking to fix tracking issues"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def action_review_lines(self):
        """Show non-compliant lines for review"""
        self.ensure_one()
        # Return to picking form but highlight the non-compliant lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'show_non_compliant_tracking': True}
        }