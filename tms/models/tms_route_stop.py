# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TmsRouteStop(models.Model):
    _name = 'tms.route.stop'
    _description = 'TMS Route Stop'
    _order = 'sequence'

    route_id = fields.Many2one(
        'tms.route',
        string='Route',
        required=True,
        ondelete='cascade'
    )
    # Fields for dynamic stop adjustments
    is_adjusted = fields.Boolean(
        string='Adjusted',
        help='Indicates if this stop has been adjusted based on real-world conditions',
        default=False
    )
    adjustment_reason = fields.Selection([
        ('traffic', 'Traffic Conditions'),
        ('weather', 'Weather Conditions'),
        ('customer', 'Customer Request'),
        ('vehicle', 'Vehicle Issue'),
        ('other', 'Other Reason')
    ], string='Adjustment Reason')
    adjusted_sequence = fields.Integer(
        string='Adjusted Sequence',
        help='The sequence after adjustment based on real-world conditions'
    )
    adjusted_time_window_start = fields.Datetime(
        string='Adjusted Time Window Start',
        help='Adjusted time window start based on real-world conditions'
    )
    adjusted_time_window_end = fields.Datetime(
        string='Adjusted Time Window End',
        help='Adjusted time window end based on real-world conditions'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )
    area_id = fields.Many2one(
        'route.area',
        string='Route Coverage Area',
        related='partner_id.route_area_id',
        store=True,
        readonly=True
    )
    address = fields.Char(
        string='Delivery Address',
        compute='_compute_address'
    )
    # Get related delivery orders from associated pickings
    delivery_order_ids = fields.Many2many(
        'sale.order',
        compute='_compute_delivery_orders',
        string='Delivery Orders'
    )

    picking_ids = fields.Many2many(
        'stock.picking',
        string='Deliveries',
        domain="[('state', '=', 'assigned'), ('partner_id', '=', partner_id)]",
        ondelete='cascade'
    )
    planned_arrival = fields.Datetime(
        string='Planned Arrival Time'
    )
    planned_departure = fields.Datetime(
        string='Planned Departure Time'
    )
    actual_arrival = fields.Datetime(
        string='Actual Arrival'
    )
    actual_departure = fields.Datetime(
        string='Actual Departure'
    )
    delivery_count = fields.Integer(
        compute='_compute_delivery_count',
        string='Delivery Count'
    )
    # Calculate total weight and volume for this stop
    total_weight = fields.Float(
        compute='_compute_stop_totals',
        string='Total Weight (kg)'
    )
    total_volume = fields.Float(
        compute='_compute_stop_totals',
        string='Total Volume (m³)'
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('arrived', 'Arrived'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ], default='pending', required=True)
    signature = fields.Binary(
        string='Proof of Delivery Signature'
    )
    notes = fields.Text(
        string='Stop Notes'
    )
    latitude = fields.Float(
        string='Latitude',
        digits=(10, 7)
    )
    longitude = fields.Float(
        string='Longitude',
        digits=(10, 7)
    )
    time_window_start = fields.Datetime(
        string='Time Window Start'
    )
    time_window_end = fields.Datetime(
        string='Time Window End'
    )
    is_return_warehouse = fields.Boolean(
        string='Return to Warehouse',
        help='Mark this stop as the return to warehouse stop'
    )

    @api.depends('partner_id')
    def _compute_address(self):
        for stop in self:
            if stop.partner_id:
                stop.address = stop.partner_id._display_address()
            else:
                stop.address = False

    @api.depends('picking_ids')
    def _compute_delivery_count(self):
        for stop in self:
            stop.delivery_count = len(stop.picking_ids)

    @api.depends('picking_ids')
    def _compute_delivery_orders(self):
        for stop in self:
            # Get all related sale orders from the pickings
            sale_orders = self.picking_ids.mapped('sale_id')
            stop.delivery_order_ids = sale_orders

    @api.depends('picking_ids')
    def _compute_stop_totals(self):
        for stop in self:
            total_weight = 0.0
            total_volume = 0.0
            for picking in stop.picking_ids:
                for move in picking.move_lines:
                    # Use the move's product weight and quantity
                    total_weight += move.product_id.weight * move.product_uom_qty
                    total_volume += move.product_id.volume * move.product_uom_qty
            stop.total_weight = total_weight
            stop.total_volume = total_volume

    def _compute_is_priority_stop(self):
        """Check if this stop is high priority based on order urgency"""
        for stop in self:
            is_priority = False
            for picking in stop.picking_ids:
                if picking.sale_id:
                    # Check if the sale order priority is high (3 or 4)
                    if picking.sale_id.priority and picking.sale_id.priority in ['3', '4']:
                        is_priority = True
                        break
            stop.is_priority_stop = is_priority

    is_priority_stop = fields.Boolean(
        compute='_compute_is_priority_stop',
        string='High Priority',
        store=True
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            # Auto-select pickings for this partner that belong to the route's batch
            batch = self.route_id.picking_batch_id
            pickings = self.env['stock.picking'].search([
                ('id', 'in', batch.picking_ids.ids),
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'assigned')
            ])
            self.picking_ids = pickings

    def action_arrive_stop(self):
        for stop in self:
            stop.state = 'arrived'
            stop.actual_arrival = fields.Datetime.now()

    def action_start_delivery(self):
        for stop in self:
            stop.state = 'in_progress'
            stop.actual_departure = fields.Datetime.now()

    def action_complete_stop(self):
        for stop in self:
            stop.state = 'delivered'
            stop.actual_departure = fields.Datetime.now()
            # Mark associated pickings as done
            for picking in stop.picking_ids:
                if picking.state == 'assigned':
                    picking._action_done()

    def action_fail_stop(self):
        for stop in self:
            stop.state = 'failed'

    @api.constrains('time_window_start', 'time_window_end')
    def _check_time_window(self):
        for stop in self:
            if stop.time_window_start and stop.time_window_end and stop.time_window_start > stop.time_window_end:
                raise ValidationError(_("Time window start must be before end time."))

    def update_coordinates(self):
        """Update coordinates from partner's address"""
        for stop in self:
            if stop.partner_id:
                stop.latitude = stop.partner_id.partner_latitude
                stop.longitude = stop.partner_id.partner_longitude

    def action_split_oversized_pickings_in_stop(self):
        """
        Split oversized pickings within this stop if they exceed capacity constraints.
        This method handles the case where a single picking is too large to be accommodated.
        """
        for stop in self:
            oversized_pickings = []

            # Check each picking in the stop to see if it exceeds capacity
            for picking in stop.picking_ids:
                picking_weight = 0.0
                picking_volume = 0.0

                # Calculate total weight and volume for the picking
                for move_line in picking.move_line_ids:
                    picking_weight += move_line.product_id.weight * move_line.qty_done
                    picking_volume += move_line.product_id.volume * move_line.qty_done

                # Check if the picking exceeds vehicle capacity
                if stop.route_id and stop.route_id.vehicle_id:
                    vehicle_max_weight = stop.route_id.vehicle_id.max_weight or 0
                    vehicle_max_volume = stop.route_id.vehicle_id.max_volume or 0

                    if (picking_weight > vehicle_max_weight or picking_volume > vehicle_max_volume):
                        oversized_pickings.append(picking)

            if not oversized_pickings:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Oversized Pickings'),
                        'message': _('No pickings in this stop exceed the vehicle capacity constraints.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }

            # Handle each oversized picking by splitting it
            for oversized_picking in oversized_pickings:
                # Use the route-level method to split the picking
                created_pickings = stop.route_id.action_split_oversized_picking(oversized_picking)

                if created_pickings:
                    # Remove the original oversized picking from this stop
                    current_picking_ids = stop.picking_ids.ids
                    if oversized_picking.id in current_picking_ids:
                        current_picking_ids.remove(oversized_picking.id)

                    # Add the newly created split pickings to the current stop
                    # Note: The routing logic will place them in appropriate stops later
                    for new_picking in created_pickings:
                        if new_picking.id not in current_picking_ids:
                            current_picking_ids.append(new_picking.id)

                    stop.picking_ids = [(6, 0, current_picking_ids)]

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Oversized Pickings Processed'),
                    'message': f'Successfully processed and split {len(oversized_pickings)} oversized picking(s).',
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_split_stop(self):
        """Split this stop if it exceeds capacity constraints"""
        # This would be a more advanced feature to split a stop if it exceeds capacity
        # For now, this is a placeholder for future implementation
        for stop in self:
            # Check if vehicle exists and has max_weight
            if stop.route_id and stop.route_id.vehicle_id and hasattr(stop.route_id.vehicle_id, 'max_weight'):
                # Check if this stop's deliveries together exceed some threshold
                if stop.total_weight > (stop.route_id.vehicle_id.max_weight or 0) * 0.9:  # 90% of capacity
                    # This would involve creating a new stop and redistributing pickings
                    picking_ids = stop.picking_ids.ids
                    if len(picking_ids) > 1:
                        # Split the pickings between this stop and a new one
                        mid_point = len(picking_ids) // 2
                        first_half = picking_ids[:mid_point]
                        second_half = picking_ids[mid_point:]

                        # Update current stop
                        stop.picking_ids = [(6, 0, first_half)]

                        # Create new stop
                        new_stop = stop.copy({
                            'picking_ids': [(6, 0, second_half)],
                            'sequence': stop.sequence + 1,
                        })

                        # Adjust sequences for subsequent stops
                        remaining_stops = stop.route_id.stop_ids.filtered(lambda s: s.sequence > stop.sequence)
                        for rs in remaining_stops:
                            rs.sequence += 1

                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Stop Split'),
                                'message': _('Stop has been split into two stops to comply with capacity constraints.'),
                                'type': 'success',
                                'sticky': False,
                            }
                        }

    @api.model
    def create(self, vals):
        """Override create to check capacity constraints after creation"""
        result = super(TmsRouteStop, self).create(vals)
        # Optionally, check capacity after creating the stop
        if result.route_id and result.route_id.vehicle_id:
            result.route_id.action_check_capacity_constraints()
        return result

    def action_open_adjust_wizard(self):
        """Open the adjust wizard"""
        return {
            'name': _('Adjust Route Stop'),
            'type': 'ir.actions.act_window',
            'res_model': 'tms.route.stop.adjust.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_stop_id': self.id,
                'default_adjustment_reason': self.adjustment_reason or 'other',
            }
        }

    def action_adjust_stop(self):
        """Adjust stop based on real-world conditions"""
        # This method will be called from the UI, parameters will be passed through context
        reason = self.env.context.get('default_reason', 'other')
        new_sequence = self.env.context.get('default_sequence')
        new_time_window_start = self.env.context.get('default_time_window_start')
        new_time_window_end = self.env.context.get('default_time_window_end')

        for stop in self:
            stop.is_adjusted = True
            stop.adjustment_reason = reason

            if new_sequence is not None:
                stop.adjusted_sequence = new_sequence

            if new_time_window_start:
                stop.adjusted_time_window_start = new_time_window_start

            if new_time_window_end:
                stop.adjusted_time_window_end = new_time_window_end

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stop Adjusted'),
                'message': _('Stop has been adjusted based on real-world conditions.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_adjustment(self):
        """Reset stop adjustment to original values"""
        for stop in self:
            stop.is_adjusted = False
            stop.adjustment_reason = False
            stop.adjusted_sequence = False
            stop.adjusted_time_window_start = False
            stop.adjusted_time_window_end = False

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Adjustment Reset'),
                'message': _('Stop adjustment has been reset to original values.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_apply_adjustments(self):
        """Apply adjusted values to the actual stop fields"""
        for stop in self:
            if stop.is_adjusted:
                if stop.adjusted_sequence:
                    stop.sequence = stop.adjusted_sequence
                if stop.adjusted_time_window_start:
                    stop.time_window_start = stop.adjusted_time_window_start
                if stop.adjusted_time_window_end:
                    stop.time_window_end = stop.adjusted_time_window_end

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Adjustments Applied'),
                'message': _('Adjusted values have been applied to the stop.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _calculate_travel_time(self, distance_km, avg_speed_kmh=40):
        """
        Calculate travel time based on distance and average speed
        Returns timedelta object
        """
        if distance_km <= 0:
            return fields.timedelta(seconds=0)
        hours = distance_km / avg_speed_kmh
        minutes = hours * 60
        return fields.timedelta(minutes=minutes)

    def _get_distance_to_next_stop(self, current_stop, next_stop):
        """
        Calculate distance between two stops
        """
        if not current_stop.latitude or not current_stop.longitude or \
           not next_stop.latitude or not next_stop.longitude:
            # If coordinates are missing, return a default distance
            return 5.0  # 5 km default distance

        from math import radians, cos, sin, asin, sqrt

        # Convert latitude and longitude from degrees to radians
        lat1, lng1, lat2, lng2 = map(radians, [
            current_stop.latitude, current_stop.longitude,
            next_stop.latitude, next_stop.longitude
        ])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    def action_calculate_timing(self):
        """
        Calculate arrival and departure times for all stops in the route
        based on distance, time windows, and service duration
        """
        if not self.route_id:
            return

        route = self.route_id
        stops = route.stop_ids.sorted(key=lambda s: s.sequence)

        if not stops:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Stops'),
                    'message': _('No stops in this route to calculate timing for.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Start from departure time of the route or current time if not set
        current_time = route.departure_time or fields.Datetime.now()

        # Get warehouse location for first leg of the route (using vehicle's partner address)
        warehouse_lat = route.vehicle_id and route.vehicle_id.partner_id and route.vehicle_id.partner_id.partner_latitude or 0
        warehouse_lng = route.vehicle_id and route.vehicle_id.partner_id and route.vehicle_id.partner_id.partner_longitude or 0

        for i, stop in enumerate(stops):
            # Calculate distance from previous stop (or warehouse for first stop)
            if i == 0:
                # Distance from warehouse to first stop
                if warehouse_lat != 0 and warehouse_lng != 0 and stop.latitude and stop.longitude:
                    distance_to_stop = self._get_distance_to_next_stop(
                        type('obj', (object,), {'latitude': warehouse_lat, 'longitude': warehouse_lng})(),
                        stop
                    )
                else:
                    distance_to_stop = 5.0  # Default distance if coordinates unavailable
            else:
                # Distance from previous stop
                prev_stop = stops[i-1]
                distance_to_stop = self._get_distance_to_next_stop(prev_stop, stop)

            # Calculate travel time to this stop
            travel_time = self._calculate_travel_time(distance_to_stop)

            # Calculate planned arrival time
            planned_arrival = current_time + travel_time

            # Check if arrival time fits within time window
            if stop.time_window_start and planned_arrival < stop.time_window_start:
                # Wait until time window opens
                planned_arrival = stop.time_window_start

            # Set planned arrival time
            stop.planned_arrival = planned_arrival

            # Service time (for delivery) - estimate based on deliveries count, 15 mins per delivery min
            delivery_count = stop.delivery_count
            service_time_minutes = max(15, 5 * delivery_count)  # At least 15 mins, 5 mins per additional delivery
            service_time = fields.timedelta(minutes=service_time_minutes)

            # Calculate planned departure time
            planned_departure = planned_arrival + service_time
            stop.planned_departure = planned_departure

            # Update current time for next stop
            current_time = planned_departure

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Timing Calculated'),
                'message': _('Arrival and departure times have been calculated for all stops in the route.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def action_reorder_stops(self):
        """Reorder stops based on actual conditions after adjustments"""
        if not self.route_id:
            return

        # Call the route-level reordering method which handles all stops in the route
        return self.route_id.action_reorder_stops_dynamically()