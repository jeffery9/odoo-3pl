from odoo import models, fields, api


class WmsCrossdockOperation(models.Model):
    _name = 'wms.crossdock.operation'
    _description = 'WMS Crossdock Operation'

    name = fields.Char('Operation Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    operation_date = fields.Datetime('Operation Date', required=True, default=fields.Datetime.now)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], 'Status', default='draft', required=True)
    inbound_picking_id = fields.Many2one('stock.picking', 'Inbound Picking', required=True)
    outbound_picking_id = fields.Many2one('stock.picking', 'Outbound Picking', required=True)
    total_quantity = fields.Float('Total Quantity', compute='_compute_total_quantity')
    total_weight = fields.Float('Total Weight (KG)', compute='_compute_total_weight')
    estimated_duration = fields.Float('Estimated Duration (Hours)')
    actual_duration = fields.Float('Actual Duration (Hours)')
    crossdock_location_id = fields.Many2one('stock.location', 'Crossdock Location')
    notes = fields.Text('Notes')
    crossdock_match_id = fields.Many2one('wms.crossdock.match', 'Crossdock Match', ondelete='cascade')
    matched_by = fields.Many2one('res.users', 'Matched By', default=lambda self: self.env.user)
    matched_date = fields.Datetime('Matched Date', default=fields.Datetime.now)

    @api.model_create_multi
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.crossdock.operation') or '/'
        return super().create(vals)

    @api.depends('inbound_picking_id', 'outbound_picking_id')
    def _compute_total_quantity(self):
        for operation in self:
            total = 0
            if operation.inbound_picking_id:
                total += sum(operation.inbound_picking_id.move_line_ids.mapped('quantity'))
            if operation.outbound_picking_id:
                total += sum(operation.outbound_picking_id.move_line_ids.mapped('quantity'))
            operation.total_quantity = total

    @api.depends('inbound_picking_id', 'outbound_picking_id')
    def _compute_total_weight(self):
        for operation in self:
            total = 0
            if operation.inbound_picking_id:
                for line in operation.inbound_picking_id.move_line_ids:
                    total += line.product_id.weight * line.quantity
            if operation.outbound_picking_id:
                for line in operation.outbound_picking_id.move_line_ids:
                    total += line.product_id.weight * line.quantity
            operation.total_weight = total

    def action_start_operation(self):
        self.write({'status': 'in_progress'})
    def action_complete_operation(self):
        # Update related pickings
        if self.inbound_picking_id:
            self.inbound_picking_id.write({'state': 'done'})
        if self.outbound_picking_id:
            self.outbound_picking_id.write({'state': 'done'})
        self.write({'status': 'completed'})
    def action_cancel_operation(self):
        # Reset related pickings if needed
        self.write({'status': 'cancelled'})