from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    quality_control_ids = fields.One2many('wms.quality.control', 'picking_id', 'Quality Controls')
    quality_control_count = fields.Integer('QC Count', compute='_compute_quality_control_count')
    # Traceability fields
    lot_ids = fields.Many2many('stock.lot', compute='_compute_picking_lot_ids', string='Lots/Serials',
                               help="All lots/serial numbers associated with this picking")
    tracked_products_count = fields.Integer('Tracked Products', compute='_compute_tracked_products_count',
                                            help="Number of products that require tracking in this picking")
    tracking_compliance = fields.Float('Tracking Compliance %', compute='_compute_tracking_compliance',
                                       help="Percentage of tracking-compliant lines in this picking", store=True)

    @api.depends('quality_control_ids')
    def _compute_quality_control_count(self):
        for picking in self:
            picking.quality_control_count = len(picking.quality_control_ids)

    @api.depends('move_line_ids', 'move_line_ids.lot_id')
    def _compute_picking_lot_ids(self):
        for picking in self:
            all_lots = self.env['stock.lot']
            for line in picking.move_line_ids:
                if line.lot_id:
                    all_lots |= line.lot_id
            picking.lot_ids = all_lots

    @api.depends('move_line_ids', 'move_line_ids.product_id', 'move_line_ids.product_id.tracking')
    def _compute_tracked_products_count(self):
        """Compute number of products that require tracking in this picking"""
        for picking in self:
            tracked_count = 0
            for line in picking.move_line_ids:
                if line.product_id.tracking != 'none':
                    tracked_count += 1
            picking.tracked_products_count = tracked_count

    def _compute_tracking_compliance(self):
        """Compute tracking compliance percentage"""
        for picking in self:
            if picking.move_line_ids:
                compliant_lines = 0
                total_tracked_lines = 0

                for line in picking.move_line_ids:
                    if line.product_id.tracking != 'none':
                        total_tracked_lines += 1
                        if (line.product_id.tracking == 'serial' and line.lot_id) or \
                           (line.product_id.tracking == 'lot' and line.lot_id):
                            compliant_lines += 1

                if total_tracked_lines > 0:
                    picking.tracking_compliance = (compliant_lines / total_tracked_lines) * 100
                else:
                    picking.tracking_compliance = 100.0  # If no tracked products, compliance is 100%
            else:
                picking.tracking_compliance = 100.0

    def action_create_quality_control(self):
        """Create a quality control session for this picking"""
        self.ensure_one()
        # Check tracking compliance before creating QC
        if self.tracking_compliance < 100:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tracking Compliance Warning',
                'res_model': 'wms.tracking.compliance.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_picking_id': self.id,
                    'default_compliance_rate': self.tracking_compliance
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.quality.control.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id, 'default_owner_id': self.owner_id.id if hasattr(self, 'owner_id') and self.owner_id else False}
        }

    def action_view_quality_controls(self):
        """View quality controls for this picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Controls',
            'res_model': 'wms.quality.control',
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

    def action_view_traceability_report(self):
        """View full traceability report for this picking"""
        self.ensure_one()
        # Create a new traceability report instance
        report = self.env['wms.stock.traceability.report'].create({
            'product_id': False,  # Will be auto-populated based on picking
            'location_id': False,  # Will be auto-populated based on picking
            'date_from': self.scheduled_date or False,
            'date_to': self.date_done or fields.Datetime.now(),
            'include_upstream': True,
            'include_downstream': True,
            'owner_id': self.owner_id.id if hasattr(self, 'owner_id') and self.owner_id else False,
        })
        # Link to the picking to auto-populate the report
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.stock.traceability.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_lot_traceability(self):
        """View detailed traceability report for all lots in this picking"""
        self.ensure_one()
        if not self.lot_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Lots Found',
                    'message': 'There are no lots associated with this picking to trace.',
                    'type': 'warning'
                }
            }

        # Return action for native Odoo traceability report
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lot Traceability Report',
            'res_model': 'stock.traceability.report',  # Using native Odoo report
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'active_model': 'stock.lot',
                'active_ids': self.lot_ids.ids,
                'search_default_lot_id': self.lot_ids[:1].id if self.lot_ids else False
            }
        }