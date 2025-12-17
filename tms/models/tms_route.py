# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TmsRoute(models.Model):
    _name = 'tms.route'
    _description = 'TMS Route'
    _order = 'departure_time desc'

    name = fields.Char(
        string='Route Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    # Driver familiarity tracking
    driver_familiarity_score = fields.Float(
        string='Driver Familiarity Score',
        help='Score indicating how familiar the driver is with this route (0-100)',
        default=0.0
    )
    driver_notes = fields.Text(
        string='Driver Notes',
        help='Special notes from the driver about this route'
    )
    last_driver_id = fields.Many2one(
        'res.partner',
        string='Last Driver',
        help='The last driver who handled this route'
    )
    area_id = fields.Many2one(
        'route.area',
        string='Route Coverage Area',
        help='The coverage area that this route operates in'
    )
    picking_batch_id = fields.Many2one(
        'stock.picking.batch',
        string='Picking Batch',
        required=True,
        domain=[('state', '=', 'assigned')]
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehicle',
        related='picking_batch_id.vehicle_id',
        store=True
    )
    driver_id = fields.Many2one(
        'res.partner',
        string='Driver',
        related='picking_batch_id.driver_id',
        store=True
    )
    departure_time = fields.Datetime(
        related='picking_batch_id.departure_time',
        string='Departure Time',
        store=True
    )
    return_time = fields.Datetime(
        related='picking_batch_id.return_time',
        string='Return Time',
        store=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True)
    stop_ids = fields.One2many(
        'tms.route.stop',
        'route_id',
        string='Route Stops',
        copy=True
    )
    total_distance = fields.Float(
        string='Total Distance (km)',
        digits=(10, 2)
    )
    total_deliveries = fields.Integer(
        compute='_compute_totals',
        string='Total Deliveries'
    )
    total_customers = fields.Integer(
        compute='_compute_totals',
        string='Total Customers'
    )
    total_weight = fields.Float(
        compute='_compute_route_totals',
        string='Total Weight (kg)'
    )
    total_volume = fields.Float(
        compute='_compute_route_totals',
        string='Total Volume (m³)'
    )
    # Add sale order reference to track original orders
    related_sale_order_ids = fields.Many2many(
        'sale.order',
        compute='_compute_related_sale_orders',
        string='Related Sales Orders'
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tms.route') or _('New')
        route = super().create(vals)

        # Automatically calculate driver familiarity if driver is assigned
        if route.driver_id:
            route.action_calculate_driver_familiarity()

        return route

    @api.depends('stop_ids')
    def _compute_totals(self):
        for route in self:
            route.total_deliveries = sum(stop.delivery_count for stop in route.stop_ids)
            route.total_customers = len(route.stop_ids)

    @api.depends('stop_ids')
    def _compute_route_totals(self):
        for route in self:
            route.total_weight = sum(stop.total_weight for stop in route.stop_ids)
            route.total_volume = sum(stop.total_volume for stop in route.stop_ids)

    @api.depends('stop_ids', 'stop_ids.picking_ids')
    def _compute_related_sale_orders(self):
        for route in self:
            sale_orders = self.env['sale.order']
            for stop in route.stop_ids:
                for picking in stop.picking_ids:
                    # Check if the sale_id field exists before accessing it
                    if hasattr(picking, 'sale_id') and picking.sale_id:
                        sale_orders |= picking.sale_id
            route.related_sale_order_ids = sale_orders

    def action_confirm(self):
        for route in self:
            route.state = 'confirmed'

    def action_start_route(self):
        for route in self:
            route.state = 'in_transit'
            if not route.departure_time:
                route.picking_batch_id.departure_time = fields.Datetime.now()

    def action_complete_route(self):
        for route in self:
            route.state = 'delivered'
            route.picking_batch_id.return_time = fields.Datetime.now()
            # Check if all routes for related sale orders are completed
            route._check_and_update_sale_orders()

    def action_optimize_route(self):
        """Optimize the route based on time windows, priority, and geographic proximity"""
        for route in self:
            if not route.stop_ids:
                continue

            # Sort by multiple criteria: priority first, then time window, then geography
            sorted_stops = route.stop_ids.sorted(
                key=lambda s: (
                    0 if s.is_priority_stop else 1,  # Priority stops first
                    s.time_window_start or fields.Datetime.now(),  # Then by time window
                    s.partner_id.name  # Finally by name
                )
            )

            # Update sequence based on optimization
            for i, stop in enumerate(sorted_stops, start=1):
                stop.sequence = i

    def action_suggest_optimal_sequence(self):
        """
        Suggest an optimal sequence considering multiple factors:
        - Priority orders
        - Time windows
        - Geographic proximity (if coordinates available)
        - Vehicle capacity constraints
        """
        for route in self:
            if not route.stop_ids:
                continue

            # Consider vehicle capacity constraints
            if route.vehicle_id:
                # Check if total weight/volume exceeds vehicle capacity
                if route.total_weight > route.vehicle_id.max_weight:
                    raise ValidationError(_("Total weight exceeds vehicle capacity!"))
                if route.total_volume > route.vehicle_id.max_volume:
                    raise ValidationError(_("Total volume exceeds vehicle capacity!"))

            # Update coordinates for all stops to ensure we have the latest
            route.stop_ids.update_coordinates()

            # Sort stops using a more comprehensive algorithm considering geographic factors
            sorted_stops = self._get_optimal_stop_sequence(route.stop_ids)

            # Update sequence and return suggestions
            for i, stop in enumerate(sorted_stops, start=1):
                stop.sequence = i

            # Return action to reload the view with suggestions
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Route Optimization'),
                    'message': _('Stops have been re-ordered based on priority, time windows, and geographic proximity.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def _get_optimal_stop_sequence(self, stops):
        """
        Calculate optimal sequence considering priority, time windows, and geographic proximity.
        This method implements an algorithm that considers the addresses of the pickings
        in the batch to optimize route arrangement geographically.
        """
        if not stops:
            return stops

        # First, separate priority and time-critical stops
        priority_stops = stops.filtered(lambda s: s.is_priority_stop)
        time_critical_stops = stops.filtered(lambda s: s.time_window_start and s.time_window_start <= fields.Datetime.now())
        regular_stops = stops - priority_stops - time_critical_stops

        # Create a list of all stops that need to be ordered
        ordered_stops = []

        # Add priority stops first
        ordered_stops.extend(priority_stops)

        # Add time-critical stops next
        ordered_stops.extend(time_critical_stops)

        # For the remaining stops, sort by geographic proximity starting from the warehouse
        # Get warehouse location (assuming it's the departure location or vehicle location)
        warehouse_lat = self.vehicle_id and self.vehicle_id.partner_id and self.vehicle_id.partner_id.partner_latitude
        warehouse_lng = self.vehicle_id and self.vehicle_id.partner_id and self.vehicle_id.partner_id.partner_longitude

        # If no warehouse location available, try to get location from default address
        if not warehouse_lat or not warehouse_lng:
            warehouse_partner = self.env['res.partner'].search([], limit=1)  # Default to first partner
            warehouse_lat = warehouse_partner.partner_latitude if warehouse_partner else 0
            warehouse_lng = warehouse_partner.partner_longitude if warehouse_partner else 0

        # Sort remaining stops by proximity to warehouse initially, then by proximity to each other
        remaining_stops = regular_stops
        current_lat, current_lng = warehouse_lat, warehouse_lng
        processed_stops = self.env['tms.route.stop']

        while remaining_stops:
            # Find the stop closest to the current location
            closest_stop = min(remaining_stops, key=lambda s: self._calculate_distance(
                current_lat, current_lng, s.latitude or 0, s.longitude or 0))

            ordered_stops.append(closest_stop)
            processed_stops |= closest_stop
            remaining_stops -= closest_stop

            # Update current location to the closest stop's location for next iteration
            if closest_stop.latitude and closest_stop.longitude:
                current_lat, current_lng = closest_stop.latitude, closest_stop.longitude

        return ordered_stops

    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate the distance between two coordinates using the Haversine formula.
        Returns a float distance in kilometers.
        """
        import math

        # If any coordinates are zero, return a large number so the stop is less prioritized
        if lat1 == 0 and lng1 == 0 or lat2 == 0 and lng2 == 0:
            return 999999

        # Convert latitude and longitude from degrees to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    def action_check_capacity_constraints(self):
        """Check if the route fits within vehicle capacity"""
        for route in self:
            if not route.vehicle_id:
                continue

            # Check weight constraint
            if route.total_weight > route.vehicle_id.max_weight:
                excess_weight = route.total_weight - route.vehicle_id.max_weight
                raise ValidationError(
                    _("Vehicle capacity exceeded by %.2f kg. Vehicle max: %.2f kg, Route total: %.2f kg") %
                    (excess_weight, route.vehicle_id.max_weight, route.total_weight)
                )

            # Check volume constraint
            if route.total_volume > route.vehicle_id.max_volume:
                excess_volume = route.total_volume - route.vehicle_id.max_volume
                raise ValidationError(
                    _("Vehicle volume exceeded by %.2f m³. Vehicle max: %.2f m³, Route total: %.2f m³") %
                    (excess_volume, route.vehicle_id.max_volume, route.total_volume)
                )

    def _check_and_update_sale_orders(self):
        """Check if all routes for related sale orders are completed and update sale order state"""
        for route in self:
            if route.state == 'delivered':
                # For each related sale order, check if all associated routes are delivered
                for sale_order in route.related_sale_order_ids:
                    # Find all routes related to this sale order
                    all_routes_for_so = self.env['tms.route'].search([
                        ('related_sale_order_ids', 'in', sale_order.id),
                    ])

                    # Check if all routes for this sale order are delivered
                    if all(r.state == 'delivered' for r in all_routes_for_so):
                        # Update sale order state to done if all pickings are done
                        if sale_order.state in ['sale']:
                            # Check if all related pickings are done
                            related_picking_ids = []
                            for search_route in all_routes_for_so:
                                for stop in search_route.stop_ids:
                                    related_picking_ids.extend(stop.picking_ids.ids)

                            all_related_pickings = self.env['stock.picking'].browse(related_picking_ids)
                            if all(p.state == 'done' for p in all_related_pickings):
                                # In a real implementation, you might want to call the proper SO done method
                                # For now, just log that the SO is ready to be marked as done
                                _logger.info(f"Sale Order {sale_order.name} has all related routes delivered and pickings completed.")

    def action_get_related_sale_orders_status(self):
        """Get the status of related sale orders"""
        self.ensure_one()
        if not self.related_sale_order_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Related Sales Orders'),
                    'message': _('This route has no related sales orders.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # For each related sale order, check the status
        status_message = f"Related Sales Orders for Route {self.name}:\n\n"
        for so in self.related_sale_order_ids:
            # Find all routes for this SO
            all_routes_for_so = self.env['tms.route'].search([
                ('related_sale_order_ids', 'in', so.id),
            ])

            delivered_routes = sum(1 for r in all_routes_for_so if r.state == 'delivered')
            total_routes = len(all_routes_for_so)

            so_status = f"Sales Order: {so.name}\n"
            so_status += f"  - Total Routes: {total_routes}\n"
            so_status += f"  - Delivered Routes: {delivered_routes}\n"
            so_status += f"  - SO State: {so.state}\n"

            if delivered_routes == total_routes and total_routes > 0:
                so_status += f"  - Status: ✅ All routes delivered\n"
            elif delivered_routes > 0:
                so_status += f"  - Status: 🔄 Partially delivered ({delivered_routes}/{total_routes})\n"
            else:
                so_status += f"  - Status: 📦 Awaiting delivery\n"

            status_message += so_status + "\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sale Order Status'),
                'message': status_message,
                'type': 'info',
                'sticky': True,
            }
        }

    def action_calculate_driver_familiarity(self):
        """Calculate driver familiarity score based on previous routes"""
        self.ensure_one()
        if not self.driver_id:
            return

        # Get all previous routes for this driver
        previous_routes = self.env['tms.route'].search([
            ('driver_id', '=', self.driver_id.id),
            ('id', '!=', self.id),
            ('state', '=', 'delivered')
        ])

        # Calculate familiarity score based on number of similar routes
        # and successful deliveries
        familiarity_score = min(len(previous_routes) * 5, 100)  # Max 100 points
        self.driver_familiarity_score = familiarity_score

        # Update last driver
        self.last_driver_id = self.driver_id.id

    def action_assign_familiar_driver(self):
        """Assign a familiar driver to this route based on previous experience"""
        self.ensure_one()

        # Get all drivers who have driven similar routes
        # For simplicity, we'll look for drivers who have driven routes with similar customers
        customer_ids = self.stop_ids.mapped('partner_id').ids

        # Find routes with similar customers
        similar_routes = self.env['tms.route'].search([
            ('stop_ids.partner_id', 'in', customer_ids),
            ('driver_id', '!=', False),
            ('state', '=', 'delivered')
        ])

        # Group by driver and count occurrences
        driver_experience = {}
        for route in similar_routes:
            driver_id = route.driver_id.id
            if driver_id not in driver_experience:
                driver_experience[driver_id] = 0
            driver_experience[driver_id] += 1

        # Find the most experienced driver
        if driver_experience:
            most_experienced_driver = max(driver_experience, key=driver_experience.get)

            # Assign this driver to the route
            self.driver_id = most_experienced_driver

            # Calculate familiarity score
            self.driver_familiarity_score = min(driver_experience[most_experienced_driver] * 10, 100)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Driver Assigned'),
                    'message': _('Familiar driver has been assigned to this route based on previous experience.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Familiar Driver Found'),
                    'message': _('No driver with previous experience on similar routes was found.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def action_split_route_for_multiple_drivers(self):
        """
        Split route for multiple drivers when volume is too much for one driver.
        This method splits a route into multiple routes for the same area if volume is too high.
        """
        self.ensure_one()

        # Only split if the route's total weight or volume exceeds the vehicle capacity
        if (self.total_weight <= self.vehicle_id.max_weight and
            self.total_volume <= self.vehicle_id.max_volume):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Split Required'),
                    'message': _('Route volume is within capacity limits, no split required.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Find stops that can be grouped by geographic proximity
        stops_by_area = {}
        for stop in self.stop_ids:
            # Group stops by partner's city/area - this can be enhanced based on actual address
            area = stop.partner_id.city or 'Unknown'
            if area not in stops_by_area:
                stops_by_area[area] = self.env['tms.route.stop']
            stops_by_area[area] |= stop

        # For each area, try to create sub-routes that fit within capacity
        created_routes = []
        for area, area_stops in stops_by_area.items():
            # Sort stops in this area by priority and time window
            sorted_stops = area_stops.sorted(key=lambda s: (
                0 if s.is_priority_stop else 1,
                s.time_window_start or fields.Datetime.now()
            ))

            # Split stops into multiple routes if needed
            current_route_weight = 0
            current_route_volume = 0
            current_route_stops = []

            for stop in sorted_stops:
                stop_weight = stop.total_weight
                stop_volume = stop.total_volume

                # Check if adding this stop would exceed capacity
                if (current_route_weight + stop_weight > self.vehicle_id.max_weight or
                    current_route_volume + stop_volume > self.vehicle_id.max_volume):

                    # If we already have stops for a route, create it
                    if current_route_stops:
                        new_route = self._create_sub_route_from_stops(current_route_stops)
                        created_routes.append(new_route.id)

                        # Reset for next route
                        current_route_weight = stop_weight
                        current_route_volume = stop_volume
                        current_route_stops = [stop]
                    else:
                        # If this single stop exceeds capacity, it's a problem
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Capacity Issue'),
                                'message': _('A single stop exceeds vehicle capacity and needs to be split at the picking level.'),
                                'type': 'warning',
                                'sticky': True,
                            }
                        }
                else:
                    # Add stop to current route
                    current_route_weight += stop_weight
                    current_route_volume += stop_volume
                    current_route_stops.append(stop)

            # Create route for remaining stops
            if current_route_stops:
                new_route = self._create_sub_route_from_stops(current_route_stops)
                created_routes.append(new_route.id)

        if created_routes:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Routes Created'),
                    'message': _('Split route into {} routes for multiple drivers.').format(len(created_routes)),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Routes Created'),
                    'message': _('Unable to split route for multiple drivers.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def _create_sub_route_from_stops(self, stops):
        """Helper method to create a sub-route from a list of stops"""
        # Create new route with the same batch and basic info
        new_route = self.env['tms.route'].create({
            'picking_batch_id': self.picking_batch_id.id,
            'area_id': self.area_id.id if self.area_id else False,  # Inherit area from parent route
            'state': 'draft',
            'driver_familiarity_score': self.driver_familiarity_score,  # Inherit familiarity score
        })

        # Move stops to the new route
        for stop in stops:
            stop.route_id = new_route.id

        return new_route

    def action_split_route_by_area_capacity(self):
        """
        Split route into multiple routes for the same area when capacity is exceeded.
        This method handles cases where the cargo in a single area cannot be completed
        in one route and needs to be split across multiple vehicles.
        """
        self.ensure_one()

        # Check if the route's total weight or volume exceeds the vehicle capacity
        if (self.total_weight <= (self.vehicle_id.max_weight or 0) and
            self.total_volume <= (self.vehicle_id.max_volume or 0)):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Split Required'),
                    'message': _('Route cargo fits within vehicle capacity, no split required.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Group stops by area to handle area-specific splitting
        area_stops = {}
        for stop in self.stop_ids:
            area_id = stop.area_id.id if stop.area_id else 0  # Use 0 for stops without area
            if area_id not in area_stops:
                area_stops[area_id] = self.env['tms.route.stop']
            area_stops[area_id] |= stop

        created_routes = []
        # Process each area separately
        for area_id, stops_in_area in area_stops.items():
            # Create sub-routes for this area if needed
            current_route_weight = 0
            current_route_volume = 0
            current_route_stops = []

            # Sort stops by priority and time window
            sorted_stops = stops_in_area.sorted(key=lambda s: (
                0 if s.is_priority_stop else 1,
                s.time_window_start or fields.Datetime.now()
            ))

            for stop in sorted_stops:
                stop_weight = stop.total_weight
                stop_volume = stop.total_volume

                # Check if adding this stop would exceed capacity
                would_exceed_weight = (current_route_weight + stop_weight > (self.vehicle_id.max_weight or 0))
                would_exceed_volume = (current_route_volume + stop_volume > (self.vehicle_id.max_volume or 0))

                if would_exceed_weight or would_exceed_volume:
                    # If we already have stops for a route, create it
                    if current_route_stops:
                        new_route = self._create_sub_route_for_stops(current_route_stops)
                        created_routes.append(new_route.id)

                        # Reset for next route
                        current_route_weight = stop_weight
                        current_route_volume = stop_volume
                        current_route_stops = [stop]
                    else:
                        # If this single stop exceeds capacity, it's an issue that needs manual handling
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Capacity Issue'),
                                'message': _('A single stop exceeds vehicle capacity and needs to be split at the picking level.'),
                                'type': 'warning',
                                'sticky': True,
                            }
                        }
                else:
                    # Add stop to current route
                    current_route_weight += stop_weight
                    current_route_volume += stop_volume
                    current_route_stops.append(stop)

            # Create route for remaining stops in this area
            if current_route_stops:
                new_route = self._create_sub_route_for_stops(current_route_stops)
                created_routes.append(new_route.id)

        if created_routes:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Routes Created'),
                    'message': _('Split route into {} routes for area {} to handle capacity constraints.').format(
                        len(created_routes),
                        self.area_id.name if self.area_id else 'Unassigned'
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Routes Created'),
                    'message': _('Unable to split route for area {} based on capacity constraints.').format(
                        self.area_id.name if self.area_id else 'Unassigned'
                    ),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def action_combine_nearby_areas_route(self):
        """
        Combine nearby areas into a single route if they are geographically close
        and their combined cargo fits within vehicle capacity.
        This method handles cases where multiple nearby areas are individually small
        but together don't exceed capacity, allowing consolidation into fewer routes.
        """
        self.ensure_one()

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

        # Get nearby areas that could potentially be combined
        partner_ids = self.stop_ids.mapped('partner_id').ids
        if not partner_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Partners'),
                    'message': _('No partners found in this route to evaluate for combination.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Get all other routes in the system that are in draft state and have the same area or nearby areas
        # This is a simplified approach - in a real implementation, you might want to look for nearby areas
        # based on geographic coordinates
        other_draft_routes = self.env['tms.route'].search([
            ('id', '!=', self.id),
            ('state', '=', 'draft'),
            ('picking_batch_id.vehicle_id', '=', self.vehicle_id.id),  # Same vehicle
        ])

        combined_route = None
        combined_stops = []
        combined_weight = self.total_weight
        combined_volume = self.total_volume

        # Try to find compatible routes to merge with
        for other_route in other_draft_routes:
            # Check if combined cargo would fit in vehicle capacity
            new_total_weight = combined_weight + other_route.total_weight
            new_total_volume = combined_volume + other_route.total_volume

            if (new_total_weight <= (self.vehicle_id.max_weight or 0) and
                new_total_volume <= (self.vehicle_id.max_volume or 0)):

                # Check if areas are compatible (either same area or nearby)
                # For now, we'll consider them compatible if they have the same area or if area info is missing
                areas_compatible = False
                if not self.area_id and not other_route.area_id:
                    areas_compatible = True
                elif self.area_id and other_route.area_id:
                    # In a real implementation, you could check geographic proximity
                    # Here we just check if they are the same area
                    areas_compatible = (self.area_id.id == other_route.area_id.id)
                else:
                    # One has area, one doesn't - consider compatible for consolidation
                    areas_compatible = True

                if areas_compatible:
                    # Add stops from the other route to this one
                    combined_stops.extend(other_route.stop_ids.ids)
                    combined_weight = new_total_weight
                    combined_volume = new_total_volume

                    # Mark other route as cancelled since it's being merged
                    other_route.write({'state': 'cancelled'})

        # If we found compatible stops to combine, add them to the current route
        if combined_stops:
            # Update the current route with combined stops
            self.stop_ids = [(4, stop_id) for stop_id in combined_stops]

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Routes Combined'),
                    'message': _('Combined with {} other route(s) to optimize vehicle capacity usage.').format(len(combined_stops)),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Routes Combined'),
                    'message': _('No compatible nearby routes found to combine with this route.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def action_smart_split_combine_route(self):
        """
        Smart splitting and combining of routes that considers both capacity constraints and area proximity.
        This method handles the most complex scenario where:
        1. Areas that exceed capacity are split appropriately
        2. Nearby smaller areas are combined to form efficient routes
        """
        self.ensure_one()

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

        # Group stops by area
        area_data = {}
        for stop in self.stop_ids:
            area_id = stop.area_id.id if stop.area_id else 0
            if area_id not in area_data:
                area_data[area_id] = {
                    'stops': self.env['tms.route.stop'],
                    'weight': 0.0,
                    'volume': 0.0,
                    'area': stop.area_id if stop.area_id else None
                }

            area_data[area_id]['stops'] |= stop
            area_data[area_id]['weight'] += stop.total_weight
            area_data[area_id]['volume'] += stop.total_volume

        # Identify which areas need to be split (exceed capacity) vs which can be combined
        areas_to_split = []
        areas_to_combine = []

        max_weight = self.vehicle_id.max_weight or 0
        max_volume = self.vehicle_id.max_volume or 0

        for area_id, data in area_data.items():
            if data['weight'] > max_weight or data['volume'] > max_volume:
                # This area needs to be split
                areas_to_split.append({
                    'area_id': area_id,
                    'data': data
                })
            else:
                # This area could potentially be combined with others
                areas_to_combine.append({
                    'area_id': area_id,
                    'data': data
                })

        # Process areas that need to be split
        split_routes = []
        for area_info in areas_to_split:
            data = area_info['data']

            # Split this area's stops into multiple routes based on capacity
            stops_list = data['stops'].sorted(key=lambda s: (
                0 if s.is_priority_stop else 1,
                s.time_window_start or fields.Datetime.now()
            ))

            current_route_weight = 0
            current_route_volume = 0
            current_route_stops = []

            for stop in stops_list:
                stop_weight = stop.total_weight
                stop_volume = stop.total_volume

                # Check if adding this stop would exceed capacity
                would_exceed_weight = (current_route_weight + stop_weight > max_weight)
                would_exceed_volume = (current_route_volume + stop_volume > max_volume)

                if would_exceed_weight or would_exceed_volume:
                    # If we have stops accumulated, create a route
                    if current_route_stops:
                        new_route = self._create_sub_route_for_stops(current_route_stops)
                        split_routes.append(new_route)

                        # Reset for next route
                        current_route_weight = stop_weight
                        current_route_volume = stop_volume
                        current_route_stops = [stop]
                    else:
                        # Single stop exceeds capacity - need manual handling
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Capacity Issue'),
                                'message': _('A single stop exceeds vehicle capacity and needs to be split at the picking level.'),
                                'type': 'warning',
                                'sticky': True,
                            }
                        }
                else:
                    # Add stop to current route
                    current_route_weight += stop_weight
                    current_route_volume += stop_volume
                    current_route_stops.append(stop)

            # Create route for any remaining stops
            if current_route_stops:
                new_route = self._create_sub_route_for_stops(current_route_stops)
                split_routes.append(new_route)

        # Enhanced processing to combine areas during splitting
        # Now we'll process the areas_to_combine list with better adjacent area logic
        combined_routes = []

        # Create a list of all areas to consider for combination
        all_areas_to_process = areas_to_combine[:]

        # Process combining areas with special attention to adjacent areas
        while all_areas_to_process:
            # Start a new route with the first available area
            current_route = all_areas_to_process.pop(0)
            current_area_weight = current_route['data']['weight']
            current_area_volume = current_route['data']['volume']
            current_route_stops = current_route['data']['stops'].ids[:]

            # Now look for adjacent areas that can be added to this route
            remaining_areas = all_areas_to_process[:]
            all_areas_to_process = []  # Reset the list

            for area_to_check in remaining_areas:
                area_weight = area_to_check['data']['weight']
                area_volume = area_to_check['data']['volume']

                # Check if this area fits in the current route
                if (current_area_weight + area_weight <= max_weight and
                    current_area_volume + area_volume <= max_volume):

                    # Check if areas are potentially adjacent (same area or nearby)
                    is_adjacent = self._check_areas_adjacent(current_route['data']['area'], area_to_check['data']['area'])

                    if is_adjacent or not current_route['data']['area'] or not area_to_check['data']['area']:
                        # Add this area to the current route
                        current_route_stops.extend(area_to_check['data']['stops'].ids)
                        current_area_weight += area_weight
                        current_area_volume += area_volume
                    else:
                        # This area is not adjacent, add it back to the processing list
                        all_areas_to_process.append(area_to_check)
                else:
                    # This area doesn't fit in current route, add it back to the processing list
                    all_areas_to_process.append(area_to_check)

            # Create a route for the accumulated stops
            if current_route_stops:
                stop_ids = [s.id for s in current_route_stops]
                new_route = self._create_sub_route_for_stops_stops(stop_ids)
                combined_routes.append(new_route)

        total_new_routes = len(split_routes) + len(combined_routes)

        if total_new_routes > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Smart Route Optimization'),
                    'message': _('Created {} new routes through smart splitting and combining of areas.').format(total_new_routes),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Optimization Needed'),
                    'message': _('Current route is already optimally organized.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def _check_areas_adjacent(self, area1, area2):
        """
        Check if two areas are adjacent/overlapping based on geographic proximity.
        """
        if not area1 and not area2:
            return True
        elif not area1 or not area2:
            # One has area, one doesn't - consider compatible for consolidation
            return True
        elif area1.id == area2.id:
            # Same area
            return True
        else:
            # Check geographic proximity based on coordinates if available
            return self._check_geographic_proximity(area1, area2)

    def _check_geographic_proximity(self, area1, area2, max_distance_km=50.0):
        """
        Check if two areas are geographically close based on their coordinates.
        """
        # If geographic coordinates are stored in the area, use them
        # For now, we'll use a simplified approach based on partner locations
        area1_partners = self.env['res.partner'].search([('route_area_id', '=', area1.id)])
        area2_partners = self.env['res.partner'].search([('route_area_id', '=', area2.id)])

        # If we have geographic coordinates for partners in these areas,
        # we can calculate the distance between the closest partners
        for partner1 in area1_partners:
            for partner2 in area2_partners:
                if partner1.partner_latitude and partner1.partner_longitude and \
                   partner2.partner_latitude and partner2.partner_longitude:
                    distance = self._calculate_haversine_distance(
                        partner1.partner_latitude, partner1.partner_longitude,
                        partner2.partner_latitude, partner2.partner_longitude
                    )
                    if distance <= max_distance_km:
                        return True
        return False

    def _calculate_haversine_distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate the distance between two coordinates using the Haversine formula.
        Returns distance in kilometers.
        """
        import math

        # If any coordinates are zero, return a large number so the areas are not considered close
        if lat1 == 0 and lng1 == 0 or lat2 == 0 and lng2 == 0:
            return 999999

        # Convert latitude and longitude from degrees to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    def _calculate_route_distance(self, stops):
        """
        Calculate total distance for a route visiting all stops in sequence.
        """
        if len(stops) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(stops) - 1):
            stop1 = stops[i]
            stop2 = stops[i + 1]

            if stop1.partner_id.partner_latitude and stop1.partner_id.partner_longitude and \
               stop2.partner_id.partner_latitude and stop2.partner_id.partner_longitude:

                distance = self._calculate_haversine_distance(
                    stop1.partner_id.partner_latitude,
                    stop1.partner_id.partner_longitude,
                    stop2.partner_id.partner_latitude,
                    stop2.partner_id.partner_longitude
                )
                total_distance += distance

        return total_distance

    def action_optimize_route_by_distance(self):
        """
        Optimize route to minimize total distance traveled.
        This considers geographic proximity to arrange stops efficiently.
        """
        self.ensure_one()

        # Get all stops in the route
        stops = self.stop_ids

        if len(stops) < 2:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Optimization Needed'),
                    'message': _('Route has fewer than 2 stops, no optimization possible.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Sort stops by geographic proximity to minimize travel distance
        optimized_stops = self._optimize_stops_by_distance(stops)

        # Update sequence numbers
        for i, stop in enumerate(optimized_stops, 1):
            stop.sequence = i

        # Calculate and show the improvement in distance
        original_distance = self._calculate_route_distance(stops.sorted('sequence'))
        optimized_distance = self._calculate_route_distance(optimized_stops)

        improvement = original_distance - optimized_distance
        status_msg = f'Route distance optimized from {original_distance:.2f}km to {optimized_distance:.2f}km'
        if improvement > 0:
            status_msg += f' (improved by {improvement:.2f}km)'
        else:
            status_msg += f' (change: {improvement:.2f}km)'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Route Distance Optimized'),
                'message': status_msg,
                'type': 'success',
                'sticky': False,
            }
        }

    def _optimize_stops_by_distance(self, stops):
        """
        Optimize stop sequence to minimize total travel distance using a nearest neighbor algorithm.
        """
        if not stops:
            return stops

        # Start from the first stop (or depot if available)
        stops_list = list(stops)
        if not stops_list:
            return stops

        # For the nearest neighbor approach, start with a reference point
        # (in real usage, this might be the depot/warehouse location)
        optimized_sequence = [stops_list[0]]  # Start with first stop
        remaining_stops = stops_list[1:]

        while remaining_stops:
            current_stop = optimized_sequence[-1]
            nearest_stop = None
            nearest_distance = float('inf')

            for stop in remaining_stops:
                if current_stop.partner_id.partner_latitude and current_stop.partner_id.partner_longitude and \
                   stop.partner_id.partner_latitude and stop.partner_id.partner_longitude:

                    distance = self._calculate_haversine_distance(
                        current_stop.partner_id.partner_latitude,
                        current_stop.partner_id.partner_longitude,
                        stop.partner_id.partner_latitude,
                        stop.partner_id.partner_longitude
                    )

                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_stop = stop

            if nearest_stop:
                optimized_sequence.append(nearest_stop)
                remaining_stops.remove(nearest_stop)
            else:
                # If no distance could be calculated, just add the next available stop
                optimized_sequence.append(remaining_stops.pop(0))

        return optimized_sequence

    def action_split_combine_for_adjacent_areas(self):
        """
        Enhanced method specifically for splitting when needed but prioritizing
        combining adjacent areas in the same route with focus on minimizing distance.
        """
        self.ensure_one()

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

        # Group stops by area
        area_data = {}
        for stop in self.stop_ids:
            area_id = stop.area_id.id if stop.area_id else 0
            if area_id not in area_data:
                area_data[area_id] = {
                    'stops': self.env['tms.route.stop'],
                    'weight': 0.0,
                    'volume': 0.0,
                    'area': stop.area_id if stop.area_id else None,
                    'total_distance': 0.0  # Estimated total distance impact
                }

            area_data[area_id]['stops'] |= stop
            area_data[area_id]['weight'] += stop.total_weight
            area_data[area_id]['volume'] += stop.total_volume

        max_weight = self.vehicle_id.max_weight or 0
        max_volume = self.vehicle_id.max_volume or 0

        created_routes = []

        # First, handle areas that exceed capacity (these must be split)
        oversized_areas = []
        for area_id, data in area_data.items():
            if data['weight'] > max_weight or data['volume'] > max_volume:
                oversized_areas.append((area_id, data))

        # Process oversized areas by splitting them
        for area_id, data in oversized_areas:
            stops_list = data['stops'].sorted(key=lambda s: (
                0 if s.is_priority_stop else 1,
                s.time_window_start or fields.Datetime.now()
            ))

            current_route_weight = 0
            current_route_volume = 0
            current_route_stops = []

            for stop in stops_list:
                stop_weight = stop.total_weight
                stop_volume = stop.total_volume

                would_exceed_capacity = (
                    current_route_weight + stop_weight > max_weight or
                    current_route_volume + stop_volume > max_volume
                )

                if would_exceed_capacity:
                    if current_route_stops:
                        new_route = self._create_sub_route_for_stops(current_route_stops)
                        created_routes.append(new_route)

                        current_route_weight = stop_weight
                        current_route_volume = stop_volume
                        current_route_stops = [stop]
                    else:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Capacity Issue'),
                                'message': _('A single stop exceeds vehicle capacity and needs to be split at the picking level.'),
                                'type': 'warning',
                                'sticky': True,
                            }
                        }
                else:
                    current_route_weight += stop_weight
                    current_route_volume += stop_volume
                    current_route_stops.append(stop)

            if current_route_stops:
                new_route = self._create_sub_route_for_stops(current_route_stops)
                created_routes.append(new_route)

        # Remove oversized areas from the area_data so they're not processed again
        for area_id, _ in oversized_areas:
            if area_id in area_data:
                del area_data[area_id]

        # Now handle smaller areas by combining nearby ones based on distance optimization
        remaining_areas = list(area_data.items())
        processed_areas = set()

        # Sort areas by total weight/volume to start with larger areas first (better packing)
        remaining_areas.sort(key=lambda x: x[1]['weight'] + x[1]['volume'], reverse=True)

        for area_id, data in remaining_areas:
            if area_id in processed_areas:
                continue

            # Start a new route with this area
            current_route_weight = data['weight']
            current_route_volume = data['volume']
            current_route_stops = data['stops'].ids[:]

            processed_areas.add(area_id)

            # Look for nearby areas that can be combined while optimizing for distance
            for other_area_id, other_data in remaining_areas:
                if other_area_id in processed_areas:
                    continue

                # Check if this area fits in the current route
                potential_weight = current_route_weight + other_data['weight']
                potential_volume = current_route_volume + other_data['volume']

                if (potential_weight <= max_weight and
                    potential_volume <= max_volume):

                    # Check if areas are geographically adjacent/compatible
                    is_geographically_compatible = self._check_areas_adjacent(data['area'], other_data['area'])

                    if is_geographically_compatible:
                        # Add this nearby area to current route to minimize distance
                        current_route_stops.extend(other_data['stops'].ids)
                        current_route_weight = potential_weight
                        current_route_volume = potential_volume
                        processed_areas.add(other_area_id)

            # Create route for the combined stops
            if current_route_stops:
                stop_ids = [s.id for s in current_route_stops]
                new_route = self._create_sub_route_for_stops_stops(stop_ids)
                created_routes.append(new_route)

        if created_routes:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Route Optimization Complete'),
                    'message': _('Created {} routes by splitting oversized areas and combining geographically nearby smaller areas to minimize total distance.').format(len(created_routes)),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Changes Needed'),
                    'message': _('Route is already optimally organized.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def action_optimize_all_routes_for_distance(self):
        """
        Optimize all routes in the system for minimal total distance.
        This method considers all routes and reorganizes them to minimize overall travel distance
        while respecting capacity constraints and geographic proximity.
        """
        self.ensure_one()

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

        # Get all stops in the route
        all_stops = self.stop_ids

        # Group stops by area to maintain geographic clustering
        area_stop_groups = {}
        for stop in all_stops:
            area_id = stop.area_id.id if stop.area_id else 0
            if area_id not in area_stop_groups:
                area_stop_groups[area_id] = []
            area_stop_groups[area_id].append(stop)

        max_weight = self.vehicle_id.max_weight or 0
        max_volume = self.vehicle_id.max_volume or 0

        # Create new routes optimized for distance
        new_routes = []
        processed_stops = set()

        # Process each area group
        for area_id, stops_in_area in area_stop_groups.items():
            # Calculate total weight and volume for this area
            area_weight = sum(stop.total_weight for stop in stops_in_area)
            area_volume = sum(stop.total_volume for stop in stops_in_area)

            # If this area's cargo exceeds capacity, split it
            if area_weight > max_weight or area_volume > max_volume:
                # Split this area's stops into multiple routes based on capacity
                current_route_weight = 0
                current_route_volume = 0
                current_route_stops = []

                # Sort stops by priority and time window
                sorted_stops = sorted(stops_in_area,
                                    key=lambda s: (0 if s.is_priority_stop else 1,
                                                 s.time_window_start or fields.Datetime.now()))

                for stop in sorted_stops:
                    if (current_route_weight + stop.total_weight > max_weight or
                        current_route_volume + stop.total_volume > max_volume):
                        # If we have stops, create a route
                        if current_route_stops:
                            new_route = self._create_sub_route_for_stops(current_route_stops)
                            new_routes.append(new_route)
                            current_route_weight = stop.total_weight
                            current_route_volume = stop.total_volume
                            current_route_stops = [stop]
                        else:
                            # Single stop exceeds capacity
                            return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': _('Capacity Issue'),
                                    'message': _('A single stop exceeds vehicle capacity and needs to be split at the picking level.'),
                                    'type': 'warning',
                                    'sticky': True,
                                }
                            }
                    else:
                        current_route_weight += stop.total_weight
                        current_route_volume += stop.total_volume
                        current_route_stops.append(stop)

                # Create route for remaining stops
                if current_route_stops:
                    new_route = self._create_sub_route_for_stops(current_route_stops)
                    new_routes.append(new_route)
            else:
                # Area fits in one route, but we might be able to combine with nearby areas
                # Check for nearby areas that can be combined
                current_route_weight = area_weight
                current_route_volume = area_volume
                current_route_stops = stops_in_area[:]

                # Look for nearby areas to combine with this one
                for other_area_id, other_stops in area_stop_groups.items():
                    if other_area_id == area_id or other_area_id in processed_stops:
                        continue

                    other_weight = sum(stop.total_weight for stop in other_stops)
                    other_volume = sum(stop.total_volume for stop in other_stops)

                    # Check if combining would still be within capacity
                    combined_weight = current_route_weight + other_weight
                    combined_volume = current_route_volume + other_volume

                    if combined_weight <= max_weight and combined_volume <= max_volume:
                        # Check if areas are geographically compatible
                        area_obj = self.env['route.area'].browse(area_id) if area_id != 0 else None
                        other_area_obj = self.env['route.area'].browse(other_area_id) if other_area_id != 0 else None

                        if self._check_areas_adjacent(area_obj, other_area_obj):
                            # Combine the areas
                            current_route_stops.extend(other_stops)
                            current_route_weight = combined_weight
                            current_route_volume = combined_volume
                            processed_stops.add(other_area_id)

                # Create route for the combined stops
                if current_route_stops:
                    # Optimize the stop sequence within this route for distance
                    optimized_stops = self._optimize_stops_by_distance(current_route_stops)
                    stop_ids = [s.id for s in optimized_stops]
                    new_route = self._create_sub_route_for_stops_stops(stop_ids)
                    new_routes.append(new_route)

                processed_stops.add(area_id)

        if new_routes:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Routes Optimized for Distance'),
                    'message': _('Reorganized route stops into {} routes optimized for minimal total distance traveled.').format(len(new_routes)),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Reorganization Needed'),
                    'message': _('Routes are already organized optimally.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def _create_sub_route_for_stops_stops(self, stop_ids_list):
        """Helper method to create a sub-route for a list of stop IDs"""
        # Create new route with same batch, area, and basic info
        new_route = self.env['tms.route'].create({
            'picking_batch_id': self.picking_batch_id.id,
            'area_id': self.area_id.id if self.area_id else False,  # Maintain same area
            'state': 'draft',
            'driver_familiarity_score': self.driver_familiarity_score,
        })

        # Move stops to the new route
        for stop_id in stop_ids_list:
            stop = self.env['tms.route.stop'].browse(stop_id)
            stop.route_id = new_route.id

        return new_route

    def _create_sub_route_for_stops(self, stops):
        """Helper method to create a sub-route for a specific set of stops"""
        # Create new route with same batch, area, and basic info
        new_route = self.env['tms.route'].create({
            'picking_batch_id': self.picking_batch_id.id,
            'area_id': self.area_id.id if self.area_id else False,  # Maintain same area
            'state': 'draft',
            'driver_familiarity_score': self.driver_familiarity_score,
        })

        # Move stops to the new route
        for stop in stops:
            stop.route_id = new_route.id

        return new_route

    def action_reorder_stops_dynamically(self):
        """
        Reorder stops dynamically based on actual conditions like traffic,
        weather, customer preferences, etc.
        """
        self.ensure_one()

        for stop in self.stop_ids:
            if stop.is_adjusted and stop.adjusted_sequence:
                stop.sequence = stop.adjusted_sequence

        # Update all sequences to ensure they are in order
        sorted_stops = self.stop_ids.sorted(key=lambda s: s.sequence or 0)
        for i, stop in enumerate(sorted_stops, start=1):
            stop.sequence = i

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stops Reordered'),
                'message': _('Route stops have been reordered based on actual conditions and adjustments.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_calculate_stop_timing(self):
        """
        Calculate timing for all stops in the route
        """
        if not self.stop_ids:
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

        # Call the timing calculation method on the first stop which will calculate for all
        return self.stop_ids[0].action_calculate_timing()

    def action_check_for_oversized_pickings(self):
        """
        Check if any picking in the route is oversized and needs to be split.
        This method identifies pickings that cannot fit in a single route due to capacity constraints.
        """
        self.ensure_one()

        oversized_picking_info = []

        for stop in self.stop_ids:
            # Get the pickings associated with this stop
            for picking in stop.picking_ids:
                # Calculate total weight and volume for this picking
                total_weight = 0.0
                total_volume = 0.0

                for move_line in picking.move_line_ids:
                    total_weight += move_line.product_id.weight * move_line.qty_done
                    total_volume += move_line.product_id.volume * move_line.qty_done

                # Check if this single picking exceeds vehicle capacity
                vehicle_max_weight = self.vehicle_id.max_weight or 0
                vehicle_max_volume = self.vehicle_id.max_volume or 0

                if (total_weight > vehicle_max_weight or total_volume > vehicle_max_volume):
                    oversized_picking_info.append({
                        'picking': picking,
                        'stop': stop,
                        'weight': total_weight,
                        'volume': total_volume,
                        'max_weight': vehicle_max_weight,
                        'max_volume': vehicle_max_volume
                    })

        return oversized_picking_info

    def action_split_oversized_picking(self, picking, max_splits=10):
        """
        Split an oversized picking into multiple smaller pickings that fit within vehicle capacity.
        """
        if not picking or not self.vehicle_id:
            return []

        # Calculate the total size of the original picking
        total_weight = 0.0
        total_volume = 0.0
        total_qty = 0

        for move_line in picking.move_line_ids:
            total_weight += move_line.product_id.weight * move_line.qty_done
            total_volume += move_line.product_id.volume * move_line.qty_done
            total_qty += move_line.qty_done

        if total_qty <= 0:
            return []

        # Determine if the picking is truly oversized
        vehicle_max_weight = self.vehicle_id.max_weight or 0
        vehicle_max_volume = self.vehicle_id.max_volume or 0

        if (total_weight <= vehicle_max_weight and total_volume <= vehicle_max_volume):
            # Picking is not oversized, no need to split
            return [picking]

        # Calculate split ratios based on capacity constraints
        weight_splits = 1
        volume_splits = 1

        if vehicle_max_weight > 0:
            weight_splits = int(total_weight / vehicle_max_weight) + (1 if total_weight % vehicle_max_weight > 0 else 0)

        if vehicle_max_volume > 0:
            volume_splits = int(total_volume / vehicle_max_volume) + (1 if total_volume % vehicle_max_volume > 0 else 0)

        # Use the maximum splits needed to satisfy both constraints
        required_splits = max(weight_splits, volume_splits, 1)
        required_splits = min(required_splits, max_splits)  # Limit the number of splits

        if required_splits <= 1:
            # If no splits are needed, return original
            return [picking]

        # Create new pickings by splitting the original moves
        created_pickings = []
        remaining_moves = []

        # First, get all move lines and their quantities
        original_move_lines = []
        for move_line in picking.move_line_ids:
            original_move_lines.append({
                'product_id': move_line.product_id.id,
                'qty': move_line.qty_done,
                'uom_id': move_line.product_uom_id.id,
                'lot_ids': move_line.lot_ids,
                'result_package_id': move_line.result_package_id,
                'location_dest_id': move_line.location_dest_id
            })

        # Calculate quantity per split (approximately equal distribution)
        qty_per_split = total_qty / required_splits

        for split_idx in range(required_splits):
            # Calculate how much quantity should go to this split
            remaining_qty = sum(m['qty'] for m in original_move_lines)
            if split_idx == required_splits - 1:
                # Last split gets any remaining quantity
                this_split_qty = remaining_qty
            else:
                this_split_qty = qty_per_split

            if remaining_qty <= 0:
                break

            # Create new picking for this split
            new_picking_vals = {
                'picking_type_id': picking.picking_type_id.id,
                'partner_id': picking.partner_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'origin': f"{picking.name} (Split {split_idx + 1}/{required_splits})",
                'note': f"Split from original picking {picking.name}",
                'batch_id': picking.batch_id.id if picking.batch_id else False,
            }

            new_picking = self.env['stock.picking'].create(new_picking_vals)

            # Distribute move lines to this new picking
            qty_assigned = 0
            moves_for_this_split = []

            for move_data in original_move_lines[:]:  # Copy list so we can modify it
                if qty_assigned >= this_split_qty:
                    break

                remaining_qty_needed = this_split_qty - qty_assigned
                qty_for_this_move = min(move_data['qty'], remaining_qty_needed)

                if qty_for_this_move > 0:
                    # Create move line in new picking
                    move_vals = {
                        'product_id': move_data['product_id'],
                        'product_uom_qty': qty_for_this_move,
                        'product_uom': move_data['uom_id'],
                        'location_id': new_picking.location_id.id,
                        'location_dest_id': new_picking.location_dest_id.id,
                        'state': 'confirmed'  # Set to confirmed to be ready for assignment
                    }

                    # Create the stock move for this picking
                    stock_move = self.env['stock.move'].create({
                        'name': f"Split of {move_data.get('product_id', 'product')}",
                        'product_id': move_data['product_id'],
                        'product_uom_qty': qty_for_this_move,
                        'product_uom': move_data['uom_id'],
                        'picking_id': new_picking.id,
                        'location_id': new_picking.location_id.id,
                        'location_dest_id': new_picking.location_dest_id.id,
                        'state': 'confirmed'
                    })

                    # Update original move data
                    move_data['qty'] -= qty_for_this_move
                    qty_assigned += qty_for_this_move

                    if move_data['qty'] <= 0:
                        # Remove this move from our list as it's fully allocated
                        original_move_lines.remove(move_data)

            created_pickings.append(new_picking)

        # Mark original picking as cancelled since it's been split
        if picking.state not in ['done', 'cancel']:
            picking.action_cancel()

        return created_pickings

    def action_handle_oversized_pickings_in_route(self):
        """
        Main method to handle oversized pickings in the route by splitting them.
        This method identifies oversized pickings and splits them into smaller ones that fit capacity.
        """
        self.ensure_one()

        if not self.vehicle_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Vehicle Assigned'),
                    'message': _('Please assign a vehicle to check capacity constraints.'),
                    'type': 'warning',
                    'sticky': True,
                }
            }

        # Check for oversized pickings
        oversized_info = self.action_check_for_oversized_pickings()

        if not oversized_info:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Oversized Pickings'),
                    'message': _('All pickings in the route fit within vehicle capacity.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Process each oversized picking
        split_count = 0
        for info in oversized_info:
            picking = info['picking']
            original_stop = info['stop']

            # Split the oversized picking
            new_pickings = self.action_split_oversized_picking(picking)

            if len(new_pickings) > 1:
                split_count += 1

                # Create new stops for the new pickings if needed
                for i, new_picking in enumerate(new_pickings):
                    # If this is not the first split, create a new stop for it
                    if i > 0:
                        # Create a new route stop for the additional picking
                        new_stop = self.env['tms.route.stop'].create({
                            'route_id': self.id,
                            'partner_id': new_picking.partner_id.id,
                            'picking_ids': [(4, new_picking.id)],
                            'time_window_start': original_stop.time_window_start,
                            'state': 'pending'
                        })
                    else:
                        # For the first split, update the original stop's picking_ids
                        original_stop.picking_ids = [(4, new_picking.id)]

        message = f"Processed {split_count} oversized picking(s)."
        if split_count > 0:
            message += f" Created additional stops as needed to fit within vehicle capacity."

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Oversized Pickings Handled'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }


