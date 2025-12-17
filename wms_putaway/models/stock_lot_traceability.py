from odoo import models, fields, api
from collections import defaultdict, deque


class StockLotTraceability(models.Model):
    _name = 'stock.lot.traceability'
    _description = 'Stock Lot Advanced Traceability'
    _order = 'id'

    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner')

    # Traceability data
    upstream_move_ids = fields.Many2many('stock.move', 'stock_lot_traceability_upstream_rel', 'traceability_id', 'move_id', 'Upstream Moves')
    downstream_move_ids = fields.Many2many('stock.move', 'stock_lot_traceability_downstream_rel', 'traceability_id', 'move_id', 'Downstream Moves')
    location_ids = fields.Many2many('stock.location', 'stock_lot_traceability_location_rel', 'traceability_id', 'location_id', 'Locations')

    # Computed fields
    upstream_move_count = fields.Integer('Upstream Moves Count', compute='_compute_move_counts')
    downstream_move_count = fields.Integer('Downstream Moves Count', compute='_compute_move_counts')
    location_count = fields.Integer('Location Count', compute='_compute_location_count')
    first_entry_date = fields.Datetime('First Entry Date', compute='_compute_dates')
    last_exit_date = fields.Datetime('Last Exit Date', compute='_compute_dates')

    # 3PL specific fields
    total_quantity = fields.Float('Total Quantity', compute='_compute_quantities')
    available_quantity = fields.Float('Available Quantity', compute='_compute_quantities')

    @api.depends('upstream_move_ids', 'downstream_move_ids')
    def _compute_move_counts(self):
        for record in self:
            record.upstream_move_count = len(record.upstream_move_ids)
            record.downstream_move_count = len(record.downstream_move_ids)

    @api.depends('location_ids')
    def _compute_location_count(self):
        for record in self:
            record.location_count = len(record.location_ids)

    @api.depends('lot_id', 'lot_id.quant_ids', 'lot_id.quant_ids.quantity', 'lot_id.quant_ids.reserved_quantity')
    def _compute_quantities(self):
        for record in self:
            quants = record.lot_id.quant_ids
            record.total_quantity = sum(quants.mapped('quantity'))
            record.available_quantity = sum(quant.quantity - quant.reserved_quantity for quant in quants)

    @api.depends('upstream_move_ids', 'upstream_move_ids.date', 'downstream_move_ids', 'downstream_move_ids.date')
    def _compute_dates(self):
        for record in self:
            all_moves = record.upstream_move_ids | record.downstream_move_ids
            if all_moves:
                record.first_entry_date = min(all_moves.mapped('date'))
                record.last_exit_date = max(all_moves.mapped('date'))
            else:
                record.first_entry_date = False
                record.last_exit_date = False

    def action_compute_full_traceability(self):
        """Compute full traceability for the lot using Odoo's native traceability methods"""
        for record in self:
            # Use Odoo's native traceability methods through the stock.traceability.report model
            traceability_report = self.env['stock.traceability.report']

            # Find all moves related to this lot using native Odoo methods
            move_lines = self.env['stock.move.line'].search([
                ('lot_id', '=', record.lot_id.id),
                ('state', '=', 'done'),
            ])

            # Use the native method to get full traceability
            all_related_lines = traceability_report._get_move_lines(move_lines)

            # Extract moves from the move lines
            all_moves = all_related_lines.mapped('move_id')

            # Separate upstream and downstream moves
            # Upstream: moves where lot was an input
            # Downstream: moves where lot was an output
            upstream_moves = self.env['stock.move']
            downstream_moves = self.env['stock.move']

            for move_line in move_lines:
                # In a typical scenario, we'd need to determine upstream vs downstream
                # based on the move's direction and relationships
                if move_line.move_id.move_orig_ids:  # Has origin moves -> downstream
                    downstream_moves |= move_line.move_id
                else:  # No origin moves -> likely upstream
                    upstream_moves |= move_line.move_id

            # Update the record
            record.upstream_move_ids = upstream_moves
            record.downstream_move_ids = downstream_moves

            # Update locations based on all moves
            all_locations = self.env['stock.location']
            for move in upstream_moves | downstream_moves:
                all_locations |= move.location_id | move.location_dest_id
            record.location_ids = all_locations

    def _find_upstream_moves(self, lot):
        """Find all upstream moves for a lot using Odoo's native methods"""
        # Find moves where this lot was consumed (input to production, consumption, etc.)
        upstream_moves = self.env['stock.move'].search([
            ('move_line_ids.lot_id', '=', lot.id),
            ('state', '=', 'done'),
        ])

        # Also include moves that link to this lot through chained relationships
        all_upstream = self.env['stock.move']
        queue = list(upstream_moves.ids)

        while queue:
            current_move_id = queue.pop(0)
            current_move = self.env['stock.move'].browse(current_move_id)

            # Find moves that supplied material to this move
            for move_line in current_move.move_line_ids:
                if move_line.lot_id == lot:
                    # Look for moves that produced this lot or supplied it
                    related_moves = self.env['stock.move'].search([
                        ('move_orig_ids', 'in', current_move.id),
                        ('state', '=', 'done'),
                    ])
                    new_moves = related_moves - all_upstream
                    all_upstream |= new_moves
                    queue.extend(new_moves.ids)

        return all_upstream

    def _find_downstream_moves(self, lot):
        """Find all downstream moves for a lot using Odoo's native methods"""
        # Find moves where this lot was output (production output, supply to other operations, etc.)
        downstream_moves = self.env['stock.move'].search([
            ('move_line_ids.lot_id', '=', lot.id),
            ('state', '=', 'done'),
        ])

        # Also include moves that this lot was used in or supplied to
        all_downstream = self.env['stock.move']
        queue = list(downstream_moves.ids)

        while queue:
            current_move_id = queue.pop(0)
            current_move = self.env['stock.move'].browse(current_move_id)

            # Find moves that this move supplied to
            for move_line in current_move.move_line_ids:
                if move_line.lot_id == lot:
                    # Look for moves that consumed from this move
                    related_moves = self.env['stock.move'].search([
                        ('id', 'in', current_move.move_dest_ids.ids),
                        ('state', '=', 'done'),
                    ])
                    new_moves = related_moves - all_downstream
                    all_downstream |= new_moves
                    queue.extend(new_moves.ids)

        return all_downstream

    def action_view_upstream_moves(self):
        """View upstream moves for this traceability record"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upstream Moves',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.upstream_move_ids.ids)],
            'context': {'default_company_id': self.company_id.id}
        }

    def action_view_downstream_moves(self):
        """View downstream moves for this traceability record"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Downstream Moves',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.downstream_move_ids.ids)],
            'context': {'default_company_id': self.company_id.id}
        }

    def action_view_location_history(self):
        """View location history for this lot"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Location History',
            'res_model': 'stock.location',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.location_ids.ids)],
        }

    @api.model
    def create_for_lot(self, lot_id):
        """Create a traceability record for a specific lot"""
        lot = self.env['stock.lot'].browse(lot_id)

        vals = {
            'lot_id': lot.id,
            'product_id': lot.product_id.id,
            'company_id': lot.company_id.id,
        }

        # Try to find owner from related moves
        related_move = self.env['stock.move.line'].search([('lot_id', '=', lot.id)], limit=1)
        if related_move and hasattr(related_move, 'owner_id') and related_move.owner_id:
            vals['owner_id'] = related_move.owner_id.id

        return self.create(vals)

    def action_refresh_traceability(self):
        """Refresh traceability information"""
        for record in self:
            record.action_compute_full_traceability()