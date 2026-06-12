from odoo import models, fields, api


class WmsBatchReceive(models.Model):
    _name = 'wms.batch.receive'
    _description = 'WMS Batch Receive'
    _order = 'name desc'

    name = fields.Char('Batch Receive Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('partial', 'Partial'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], 'Status', default='draft', required=True)
    receive_date = fields.Datetime('Receive Date', required=True, default=fields.Datetime.now)
    completion_date = fields.Datetime('Completion Date')
    received_by = fields.Many2one('res.users', 'Received By', default=lambda self: self.env.user)
    total_pickings = fields.Integer('Total Pickings', compute='_compute_totals', store=True)
    completed_pickings = fields.Integer('Completed Pickings', compute='_compute_totals', store=True)
    progress_percentage = fields.Float('Progress %', compute='_compute_progress', store=True)
    notes = fields.Text('Notes')
    batch_picking_ids = fields.One2many('wms.batch.receive.picking', 'batch_receive_id', 'Batch Pickings')
    location_id = fields.Many2one('stock.location', 'Receive Location')
    expected_arrival_date = fields.Datetime('Expected Arrival Date')

    @api.model_create_multi
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.batch.receive') or '/'
        return super().create(vals)

    @api.depends('batch_picking_ids', 'batch_picking_ids.status')
    def _compute_totals(self):
        for record in self:
            record.total_pickings = len(record.batch_picking_ids)
            record.completed_pickings = len(record.batch_picking_ids.filtered(lambda bp: bp.status == 'completed'))

    @api.depends('total_pickings', 'completed_pickings')
    def _compute_progress(self):
        for record in self:
            if record.total_pickings > 0:
                record.progress_percentage = (record.completed_pickings / record.total_pickings) * 100
            else:
                record.progress_percentage = 0.0

    def action_start_batch_receive(self):
        """Start the batch receive process"""
        self.write({
            'status': 'in_progress',
            'receive_date': fields.Datetime.now()
        })
    def action_complete_batch_receive(self):
        """Complete the batch receive process"""
        all_completed = all(bp.status == 'completed' for bp in self.batch_picking_ids)
        if all_completed:
            self.write({
                'status': 'completed',
                'completion_date': fields.Datetime.now()
            })
        else:
            self.write({'status': 'partial'})
    def action_cancel_batch_receive(self):
        """Cancel the batch receive process"""
        self.write({'status': 'cancelled'})
    def action_add_picking(self):
        """Add picking to batch receive"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.batch.receive.add.picking.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_batch_receive_id': self.id}
        }
    def action_generate_report(self):
        """Generate batch receive report"""
        self.ensure_one()
        return self.env.ref('wms_batch_receive.action_report_batch_receive').report_action(self)


class WmsBatchReceivePicking(models.Model):
    _name = 'wms.batch.receive.picking'
    _description = 'WMS Batch Receive Picking'
    _order = 'sequence'

    batch_receive_id = fields.Many2one('wms.batch.receive', 'Batch Receive', required=True, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    sequence = fields.Integer('Sequence', default=10)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], 'Status', default='pending', required=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], 'Priority', default='normal', required=True)
    receive_date = fields.Datetime('Receive Date')
    completion_date = fields.Datetime('Completion Date')
    received_by = fields.Many2one('res.users', 'Received By')
    notes = fields.Text('Notes')
    expected_quantity = fields.Float('Expected Quantity', compute='_compute_expected_quantity', store=True)
    received_quantity = fields.Float('Received Quantity', compute='_compute_received_quantity', store=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', related='batch_receive_id.owner_id', store=True)
    location_id = fields.Many2one('stock.location', 'Location', related='picking_id.location_dest_id', store=True)

    @api.depends('picking_id', 'picking_id.move_ids_without_package')
    def _compute_expected_quantity(self):
        for record in self:
            if record.picking_id:
                record.expected_quantity = sum(record.picking_id.move_ids_without_package.mapped('product_uom_qty'))
            else:
                record.expected_quantity = 0.0

    @api.depends('picking_id', 'picking_id.move_line_ids')
    def _compute_received_quantity(self):
        for record in self:
            if record.picking_id:
                record.received_quantity = sum(record.picking_id.move_line_ids.mapped('qty_done'))
            else:
                record.received_quantity = 0.0

    def action_start_receiving(self):
        """Start receiving this picking"""
        self.write({
            'status': 'in_progress',
            'receive_date': fields.Datetime.now(),
            'received_by': self.env.user.id
        })
    def action_complete_receiving(self):
        """Complete receiving this picking"""
        self.write({
            'status': 'completed',
            'completion_date': fields.Datetime.now()
        })
    def action_cancel_receiving(self):
        """Cancel receiving this picking"""
        self.write({'status': 'cancelled'})


class WmsBatchReceiveAddPickingWizard(models.TransientModel):
    _name = 'wms.batch.receive.add.picking.wizard'
    _description = 'WMS Batch Receive Add Picking Wizard'

    batch_receive_id = fields.Many2one('wms.batch.receive', 'Batch Receive', required=True)
    picking_ids = fields.Many2many('stock.picking', string='Pickings to Add')
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], 'Priority', default='normal')
    def action_add_pickings(self):
        """Add selected pickings to batch receive"""
        self.ensure_one()
        for picking in self.picking_ids:
            self.env['wms.batch.receive.picking'].create({
                'batch_receive_id': self.batch_receive_id.id,
                'picking_id': picking.id,
                'priority': self.priority,
            })
        return {'type': 'ir.actions.act_window_close'}


class WmsBatchReceiveWizard(models.TransientModel):
    _name = 'wms.batch.receive.wizard'
    _description = 'WMS Batch Receive Wizard'

    picking_ids = fields.Many2many('stock.picking', string='Pickings to Receive')
    location_id = fields.Many2one('stock.location', 'Receive Location')
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], 'Priority', default='normal')
    notes = fields.Text('Notes')
    def action_create_batch_receive(self):
        """Create batch receive session with selected pickings"""
        self.ensure_one()

        # Create the batch receive record
        batch_receive = self.env['wms.batch.receive'].create({
            'owner_id': self.owner_id.id,
            'location_id': self.location_id.id,
            'notes': self.notes,
            'status': 'draft',
        })

        # Add selected pickings to the batch
        for picking in self.picking_ids:
            self.env['wms.batch.receive.picking'].create({
                'batch_receive_id': batch_receive.id,
                'picking_id': picking.id,
                'priority': self.priority,
            })

        # Start the batch receive process
        batch_receive.action_start_batch_receive()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.batch.receive',
            'res_id': batch_receive.id,
            'view_mode': 'form',
            'target': 'current',
        }