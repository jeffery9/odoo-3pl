# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    # Add a direct Many2one relationship to enforce one batch to one route
    tms_route_id = fields.Many2one(
        'tms.route',
        string='TMS Route',
        help='Direct reference to the single TMS route for this batch'
    )
    # Keep tms_route_ids for backward compatibility but ensure only one route per batch
    tms_route_ids = fields.One2many(
        'tms.route',
        'picking_batch_id',
        string='TMS Routes',
        help='TMS Routes for this batch (should only have one)'
    )
    tms_route_count = fields.Integer(
        compute='_compute_tms_route_count',
        string='TMS Route Count'
    )
    # Add a computed field to get the current route if exists (for convenience)
    current_route_id = fields.Many2one(
        'tms.route',
        compute='_compute_current_route',
        string='Current Route',
        store=False,  # Not stored since route status can change
    )
    # Add a route field as an alias to current_route_id
    route_id = fields.Many2one(
        'tms.route',
        string='Route',
        compute='_compute_current_route',
        store=False,  # Not stored to avoid duplication
        help='Current route associated with this batch'
    )
    route_stop_ids = fields.Many2many(
        'tms.route.stop',
        compute='_compute_route_stops',
        string='Route Stops',
        help='All route stops associated with this batch'
    )
    route_stop_count = fields.Integer(
        compute='_compute_route_stop_count',
        string='Route Stop Count'
    )

    @api.depends('tms_route_ids')
    def _compute_tms_route_count(self):
        for batch in self:
            batch.tms_route_count = len(batch.tms_route_ids)

    def _compute_current_route(self):
        """Get the current route (non-delivered) for this batch"""
        for batch in self:
            # Since each batch should only have one route, just get the route if it exists
            route = batch.tms_route_ids.filtered(lambda r: r.state in ['draft', 'confirmed', 'in_transit'])
            batch.current_route_id = batch.route_id = route[:1] if route else False
            # Also set the direct relationship
            batch.tms_route_id = route[:1] if route else False

    def _compute_route_stops(self):
        """Compute all route stops for this batch"""
        for batch in self:
            if batch.tms_route_ids:
                batch.route_stop_ids = batch.tms_route_ids.mapped('stop_ids')
            else:
                batch.route_stop_ids = self.env['tms.route.stop']

    @api.depends('tms_route_ids.stop_ids')
    def _compute_route_stop_count(self):
        """Compute the count of route stops"""
        for batch in self:
            batch.route_stop_count = len(batch.tms_route_ids.mapped('stop_ids'))

    def action_view_route_stops(self):
        """Action to view all route stops for this batch"""
        self.ensure_one()
        return {
            'name': _('Route Stops'),
            'type': 'ir.actions.act_window',
            'res_model': 'tms.route.stop',
            'view_mode': 'tree,form',
            'domain': [('route_id', 'in', self.tms_route_ids.ids)],
            'context': {'default_route_id': self.current_route_id.id if self.current_route_id else False},
        }

    def action_create_tms_route_single(self):
        """Create a single TMS route from this batch, enforcing one batch per route"""
        self.ensure_one()

        # Check if a route already exists for this batch
        existing_route = self.env['tms.route'].search([('picking_batch_id', '=', self.id)], limit=1)
        if existing_route:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Route Already Exists'),
                    'message': _('A route already exists for this batch. Each batch can only have one route.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Calculate area for this route based on customer areas in the batch
        area_ids = self.picking_ids.mapped('partner_id.route_area_id').ids
        main_area_id = False
        if area_ids:
            # Use the most common area if multiple exist, or the first one if single
            area_counts = {}
            for picking in self.picking_ids:
                if picking.partner_id.route_area_id:
                    area_id = picking.partner_id.route_area_id.id
                    area_counts[area_id] = area_counts.get(area_id, 0) + 1

            if area_counts:
                # Select the area with the most customers
                main_area_id = max(area_counts, key=area_counts.get)

        # Calculate total weight and volume for the batch
        total_weight = 0.0
        total_volume = 0.0
        picking_details = []

        for picking in self.picking_ids:
            picking_weight = 0.0
            picking_volume = 0.0
            for move in picking.move_lines:
                picking_weight += move.product_id.weight * move.product_uom_qty
                picking_volume += move.product_id.volume * move.product_uom_qty

            total_weight += picking_weight
            total_volume += picking_volume

            # Get priority, defaulting to '0' if not set or invalid
            priority = '0'
            if picking.sale_id and picking.sale_id.priority:
                priority = picking.sale_id.priority
                # Make sure priority is a valid value (1, 2, 3, 4)
                if priority not in ['0', '1', '2', '3', '4']:
                    priority = '0'

            picking_details.append({
                'picking': picking,
                'weight': picking_weight,
                'volume': picking_volume,
                'priority': priority,
                'partner_id': picking.partner_id.id,
                'time_window_start': picking.date_deadline or picking.scheduled_date,
                'area_id': picking.partner_id.route_area_id.id if picking.partner_id.route_area_id else False
            })

        # Check capacity before creating the route, and prevent creation if exceeded
        if (self.vehicle_id and
            hasattr(self.vehicle_id, 'max_weight') and
            hasattr(self.vehicle_id, 'max_volume')):

            # Calculate total weight and volume
            if (total_weight > (self.vehicle_id.max_weight or 0) or
                total_volume > (self.vehicle_id.max_volume or 0)):

                # Check if the batch should be pre-split at the warehouse level
                oversized_pickings = []
                for picking in self.picking_ids:
                    picking_weight = 0.0
                    picking_volume = 0.0
                    for move in picking.move_lines:
                        picking_weight += move.product_id.weight * move.product_uom_qty
                        picking_volume += move.product_id.volume * move.product_uom_qty

                    if (picking_weight > (self.vehicle_id.max_weight or 0) or
                        picking_volume > (self.vehicle_id.max_volume or 0)):
                        oversized_pickings.append({
                            'picking': picking,
                            'weight': picking_weight,
                            'volume': picking_volume
                        })

                if oversized_pickings:
                    message = "The following individual pickings exceed vehicle capacity:\n"
                    message += "\n".join([
                        f"- {item['picking'].name}: {item['weight']:.2f}kg / {item['volume']:.2f}m³"
                        for item in oversized_pickings
                    ])
                    message += "\n\nPlease split these pickings at the warehouse level before creating a TMS route."

                    raise ValidationError(_(message))
                else:
                    # The overall batch exceeds capacity but no single picking does
                    # In this case, warehouse staff should create multiple smaller batches
                    raise ValidationError(
                        _("The total batch weight (%.2f kg) or volume (%.2f m³) exceeds vehicle capacity (%.2f kg, %.2f m³). "
                          "Please create smaller batches at the warehouse level before creating TMS routes.") %
                        (total_weight, total_volume,
                         self.vehicle_id.max_weight or 0, self.vehicle_id.max_volume or 0)
                    )

        # If we reach here, capacity is sufficient - create single route
        route_vals = {
            'picking_batch_id': self.id,
            'state': 'draft',
        }
        if main_area_id:
            route_vals['area_id'] = main_area_id

        route = self.env['tms.route'].create(route_vals)

        # Update the batch's route relationship
        self.tms_route_id = route

        # Create stops from unique partners in the batch, considering priority and time windows
        partner_stops = {}
        for picking in self.picking_ids:
            if picking.partner_id.id not in partner_stops:
                partner_stops[picking.partner_id.id] = {
                    'partner_id': picking.partner_id.id,
                    'picking_ids': [],
                    'time_window_start': picking.date_deadline or picking.scheduled_date,
                    'is_priority': picking.sale_id and picking.sale_id.priority in ['3', '4'] if picking.sale_id else False,
                    'partner': picking.partner_id,  # Store partner for address information
                    'area_id': picking.partner_id.route_area_id.id if picking.partner_id.route_area_id else False,
                }
            partner_stops[picking.partner_id.id]['picking_ids'].append(picking.id)

        # Create stops for each partner
        for partner_id, data in partner_stops.items():
            stop_vals = {
                'route_id': route.id,
                'partner_id': partner_id,
                'picking_ids': [(6, 0, data['picking_ids'])],
                'time_window_start': data['time_window_start'],
                'state': 'pending'
            }
            if data.get('area_id'):
                stop_vals['area_id'] = data['area_id']

            stop = self.env['tms.route.stop'].create(stop_vals)

        # Suggest optimal sequence
        route.action_suggest_optimal_sequence()

        return {
            'name': _('TMS Route'),
            'type': 'ir.actions.act_window',
            'res_model': 'tms.route',
            'res_id': route.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_tms_route(self):
        """Create a TMS route from this batch - one batch per route"""
        return self.action_create_tms_route_single()

    def action_check_split_picking_requirements(self):
        """Check if the batch pickings should be split based on capacity requirements"""
        self.ensure_one()

        if not self.vehicle_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Vehicle Assigned'),
                    'message': _('Please assign a vehicle to the batch to check capacity requirements.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Check each picking to see if it should be split individually
        oversized_pickings = []
        for picking in self.picking_ids:
            picking_weight = 0.0
            picking_volume = 0.0
            for move in picking.move_lines:
                picking_weight += move.product_id.weight * move.product_uom_qty
                picking_volume += move.product_id.volume * move.product_uom_qty

            # Check if this single picking exceeds the vehicle capacity significantly
            if (hasattr(self.vehicle_id, 'max_weight') and
                self.vehicle_id.max_weight and
                picking_weight > self.vehicle_id.max_weight):
                oversized_pickings.append({
                    'picking': picking,
                    'weight': picking_weight,
                    'volume': picking_volume,
                    'capacity': self.vehicle_id.max_weight
                })
            elif (hasattr(self.vehicle_id, 'max_volume') and
                  self.vehicle_id.max_volume and
                  picking_volume > self.vehicle_id.max_volume):
                oversized_pickings.append({
                    'picking': picking,
                    'weight': picking_weight,
                    'volume': picking_volume,
                    'capacity': self.vehicle_id.max_volume
                })

        if oversized_pickings:
            message = "The following pickings exceed vehicle capacity and should be prepared separately:\n"
            message += "\n".join([
                f"- {item['picking'].name}: {item['weight']:.2f}kg / {item['volume']:.2f}m³ (Vehicle capacity: {item['capacity']})"
                for item in oversized_pickings
            ])
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Picking Split Required'),
                    'message': message,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Capacity Check'),
                    'message': _('All pickings fit within vehicle capacity. Ready to create TMS route.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_view_tms_routes(self):
        """View TMS routes for this batch"""
        self.ensure_one()
        return {
            'name': _('TMS Routes'),
            'type': 'ir.actions.act_window',
            'res_model': 'tms.route',
            'view_mode': 'tree,form',
            'domain': [('picking_batch_id', '=', self.id)],
            'context': {'default_picking_batch_id': self.id},
        }

    def action_create_batch_by_area(self):
        """Create batches based on route coverage areas"""
        # This method would group pickings by their customer's area
        # For now, this is called from an action to create area-based batches
        picking_ids = self.env.context.get('active_ids')
        if not picking_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Pickings Selected'),
                    'message': _('Please select pickings to create area-based batches.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get the selected pickings
        pickings = self.env['stock.picking'].browse(picking_ids)

        # Group pickings by area
        area_picking_map = {}
        for picking in pickings:
            area = picking.partner_id.route_area_id
            area_id = area.id if area else 0  # Use 0 for pickings without an area

            if area_id not in area_picking_map:
                area_picking_map[area_id] = {
                    'area': area,
                    'pickings': self.env['stock.picking']
                }
            area_picking_map[area_id]['pickings'] |= picking

        # Create a batch for each area
        created_batches = []
        for area_id, data in area_picking_map.items():
            if data['pickings']:
                # Create a new batch for this area
                batch = self.env['stock.picking.batch'].create({
                    'name': f"Area Batch - {data['area'].name if data['area'] else 'No Area'}",
                    'picking_ids': [(6, 0, data['pickings'].ids)],
                    'state': 'draft',  # Start in draft state
                })
                created_batches.append(batch.id)

        if created_batches:
            return {
                'name': _('Area-based Batches'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking.batch',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_batches)],
                'context': {'search_default_draft': 1},
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Batches Created'),
                    'message': _('No area-based batches were created.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def action_create_area_split_batch_if_needed(self):
        """
        Create an area-based split of the batch if the cargo in the main area
        exceeds vehicle capacity. This handles cases where cargo in a single
        area cannot be completed in one route and needs to be split across
        multiple vehicles.
        """
        self.ensure_one()

        # Check if we have a vehicle assigned to check capacity constraints
        if not self.vehicle_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Vehicle Assigned'),
                    'message': _('Please assign a vehicle to check capacity constraints.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Calculate area for this batch based on customer areas
        area_ids = self.picking_ids.mapped('partner_id.route_area_id').ids
        if not area_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Areas Defined'),
                    'message': _('No route areas are defined for the customers in this batch.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Group pickings by area to check capacity per area
        area_picking_map = {}
        for picking in self.picking_ids:
            area = picking.partner_id.route_area_id
            area_id = area.id if area else 0

            if area_id not in area_picking_map:
                area_picking_map[area_id] = {
                    'area': area,
                    'pickings': self.env['stock.picking'],
                    'total_weight': 0.0,
                    'total_volume': 0.0
                }

            area_picking_map[area_id]['pickings'] |= picking

            # Calculate weight and volume for this picking
            picking_weight = 0.0
            picking_volume = 0.0
            for move in picking.move_lines:
                picking_weight += move.product_id.weight * move.product_uom_qty
                picking_volume += move.product_id.volume * move.product_uom_qty

            area_picking_map[area_id]['total_weight'] += picking_weight
            area_picking_map[area_id]['total_volume'] += picking_volume

        # Check if any area's cargo exceeds vehicle capacity
        exceeded_areas = []
        for area_id, data in area_picking_map.items():
            if (data['total_weight'] > (self.vehicle_id.max_weight or 0) or
                data['total_volume'] > (self.vehicle_id.max_volume or 0)):
                exceeded_areas.append({
                    'area': data['area'],
                    'weight': data['total_weight'],
                    'volume': data['total_volume'],
                    'pickings': data['pickings']
                })

        if not exceeded_areas:
            # If no area exceeds capacity, just create a normal route
            return self.action_create_tms_route()
        else:
            # For areas that exceed capacity, we need to split
            split_success = True
            messages = []

            for area_data in exceeded_areas:
                # Calculate how many routes we need based on capacity
                max_weight = self.vehicle_id.max_weight or 0
                max_volume = self.vehicle_id.max_volume or 0

                # Calculate how many routes we need based on weight and volume constraints
                routes_needed_weight = int(area_data['weight'] / max_weight) + (1 if area_data['weight'] % max_weight > 0 else 0)
                routes_needed_volume = int(area_data['volume'] / max_volume) + (1 if area_data['volume'] % max_volume > 0 else 0)
                routes_needed = max(routes_needed_weight, routes_needed_volume, 1)

                # Split the pickings in this area into sub-batches if possible
                pickings_list = area_data['pickings'].sorted(key=lambda p: (
                    p.sale_id.priority or '0',
                    p.date_deadline or p.scheduled_date
                ))

                # Split pickings into approximately equal parts
                pickings_per_route = len(pickings_list) // routes_needed
                remaining_pickings = len(pickings_list) % routes_needed

                # Create sub-batches for each route
                start_idx = 0
                for route_idx in range(routes_needed):
                    # Determine how many pickings for this route
                    current_route_pickings = pickings_per_route
                    if route_idx < remaining_pickings:
                        current_route_pickings += 1

                    # Get the pickings for this route
                    route_pickings = pickings_list[start_idx:start_idx + current_route_pickings]
                    start_idx += current_route_pickings

                    if route_pickings:
                        # Create a sub-batch for this route
                        sub_batch = self.env['stock.picking.batch'].create({
                            'name': f"{self.name} - Area {area_data['area'].name if area_data['area'] else 'Unassigned'} - Part {route_idx + 1}",
                            'picking_ids': [(6, 0, route_pickings.ids)],
                            'vehicle_id': self.vehicle_id.id,
                            'driver_id': self.driver_id.id,
                        })

                        # Create route for this sub-batch
                        try:
                            route_result = sub_batch.action_create_tms_route()
                        except Exception as e:
                            split_success = False
                            messages.append(f"Failed to create route for {sub_batch.name}: {str(e)}")

            if split_success:
                message = f"Split batch for area(s) that exceeded capacity. Created multiple sub-routes for handling cargo."
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Batch Split Successfully'),
                        'message': message,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Partial Split Success'),
                        'message': f'Batch was partially split. Some routes could not be created: {"; ".join(messages)}',
                        'type': 'warning',
                        'sticky': True,
                    }
                }