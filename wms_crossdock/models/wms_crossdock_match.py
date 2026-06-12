from odoo import models, fields, api


class WmsCrossdockMatch(models.Model):
    _name = 'wms.crossdock.match'
    _description = 'WMS Crossdock Match'
    _order = 'match_date desc'

    name = fields.Char('Match Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    match_date = fields.Datetime('Match Date', required=True, default=fields.Datetime.now)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], 'Status', default='pending', required=True)
    inbound_picking_ids = fields.Many2many('stock.picking', 'crossdock_match_in_picking_rel',
                                          'match_id', 'picking_id', 'Inbound Pickings')
    outbound_picking_ids = fields.Many2many('stock.picking', 'crossdock_match_out_picking_rel',
                                           'match_id', 'picking_id', 'Outbound Pickings')
    total_inbound_qty = fields.Float('Total Inbound Quantity', compute='_compute_totals')
    total_outbound_qty = fields.Float('Total Outbound Quantity', compute='_compute_totals')
    match_score = fields.Float('Match Score (0-100)', help='Confidence score for the match')
    matching_algorithm = fields.Char('Matching Algorithm Used')
    notes = fields.Text('Notes')
    operation_ids = fields.One2many('wms.crossdock.operation', 'crossdock_match_id', 'Operations')

    @api.model_create_multi
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.crossdock.match') or '/'
        return super().create(vals)

    @api.depends('inbound_picking_ids', 'outbound_picking_ids')
    def _compute_totals(self):
        for match in self:
            match.total_inbound_qty = sum(
                pick.move_line_ids.mapped('quantity')
                for pick in match.inbound_picking_ids
            )
            match.total_outbound_qty = sum(
                pick.move_line_ids.mapped('quantity')
                for pick in match.outbound_picking_ids
            )
    def action_confirm_match(self):
        self.write({'status': 'confirmed'})
        # Create operations for the confirmed match
        for match in self:
            for inbound in match.inbound_picking_ids:
                for outbound in match.outbound_picking_ids:
                    # Create operation for each inbound-outbound pair
                    self.env['wms.crossdock.operation'].create({
                        'owner_id': match.owner_id.id,
                        'inbound_picking_id': inbound.id,
                        'outbound_picking_id': outbound.id,
                        'crossdock_match_id': match.id,
                        'warehouse_id': inbound.picking_type_id.warehouse_id.id,
                    })
    def action_start_transit(self):
        self.write({'status': 'in_transit'})
    def action_complete_match(self):
        self.write({'status': 'completed'})
    def action_fail_match(self):
        self.write({'status': 'failed'})

    @api.model
    def auto_match_incoming_orders(self):
        """
        Automated method to match incoming orders with outgoing orders based on:
        - Same product
        - Similar quantities
        - Compatible delivery dates
        - Same owner
        """
        # Find unassigned inbound pickings
        inbound_pickings = self.env['stock.picking'].search([
            ('is_crossdock', '=', True),
            ('crossdock_status', '=', 'pending'),
            ('state', '=', 'assigned')
        ])

        # Find unassigned outbound pickings
        outbound_pickings = self.env['stock.picking'].search([
            ('is_crossdock', '=', True),
            ('crossdock_status', '=', 'pending'),
            ('state', '=', 'assigned')
        ])

        matched_pairs = []

        for inbound in inbound_pickings:
            for outbound in outbound_pickings:
                # Check if they have matching products and are from the same owner
                inbound_products = set(inbound.move_lines.mapped('product_id').ids)
                outbound_products = set(outbound.move_lines.mapped('product_id').ids)

                if (inbound_products & outbound_products and  # Have common products
                    inbound.owner_id == outbound.owner_id and  # Same owner
                    abs(inbound.scheduled_date - outbound.scheduled_date).days <= 2):  # Close delivery dates
                    matched_pairs.append((inbound, outbound))

        # Create matches for the found pairs
        for inbound, outbound in matched_pairs:
            match = self.create({
                'owner_id': inbound.owner_id.id,
                'inbound_picking_ids': [(4, inbound.id)],
                'outbound_picking_ids': [(4, outbound.id)],
                'match_score': 85.0,  # Default high score for basic matching
                'matching_algorithm': 'Basic Product Match'
            })

            # Update picking statuses
            inbound.write({'crossdock_match_id': match.id, 'crossdock_status': 'matched'})
            outbound.write({'crossdock_match_id': match.id, 'crossdock_status': 'matched'})

        return matched_pairs