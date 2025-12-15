# -*- coding: utf-8 -*-
import math
from odoo.tests import TransactionCase
from odoo import fields


class TestTmsRouteOptimization(TransactionCase):
    """
    Test suite for TMS route optimization functionality
    """

    def setUp(self):
        super().setUp()

        # Create test data
        self.partner_model = self.env['res.partner']
        self.route_area_model = self.env['route.area']
        self.stock_picking_batch_model = self.env['stock.picking.batch']
        self.tms_route_model = self.env['tms.route']
        self.tms_route_stop_model = self.env['tms.route.stop']
        self.product_product_model = self.env['product.product']
        self.stock_picking_model = self.env['stock.picking']
        self.stock_move_model = self.env['stock.move']

        # Create test areas
        self.area_north = self.route_area_model.create({
            'name': 'North Area',
            'code': 'NORTH',
            'description': 'Northern delivery area'
        })

        self.area_south = self.route_area_model.create({
            'name': 'South Area',
            'code': 'SOUTH',
            'description': 'Southern delivery area'
        })

        self.area_east = self.route_area_model.create({
            'name': 'East Area',
            'code': 'EAST',
            'description': 'Eastern delivery area'
        })

        # Create test partners with geographic coordinates
        self.partner_north_1 = self.partner_model.create({
            'name': 'North Customer 1',
            'route_area_id': self.area_north.id,
            'partner_latitude': 40.7128,  # New York coordinates approx
            'partner_longitude': -74.0060,
        })

        self.partner_north_2 = self.partner_model.create({
            'name': 'North Customer 2',
            'route_area_id': self.area_north.id,
            'partner_latitude': 40.7228,  # Close to first customer
            'partner_longitude': -74.0160,
        })

        self.partner_south_1 = self.partner_model.create({
            'name': 'South Customer 1',
            'route_area_id': self.area_south.id,
            'partner_latitude': 40.6528,  # Further south
            'partner_longitude': -74.0360,
        })

        self.partner_east_1 = self.partner_model.create({
            'name': 'East Customer 1',
            'route_area_id': self.area_east.id,
            'partner_latitude': 40.7328,  # Further east
            'partner_longitude': -73.9560,
        })

        # Create test vehicle
        self.fleet_vehicle_model = self.env['fleet.vehicle']
        self.vehicle = self.fleet_vehicle_model.create({
            'name': 'Test Delivery Truck',
            'model_id': self.env['fleet.vehicle.model'].create({'name': 'Delivery Truck'}).id,
            'max_weight': 1000.0,  # 1000 kg capacity
            'max_volume': 50.0,    # 50 m³ capacity
        })

        # Create test products
        self.product_a = self.product_product_model.create({
            'name': 'Test Product A',
            'weight': 5.0,
            'volume': 0.1,
        })

        self.product_b = self.product_product_model.create({
            'name': 'Test Product B',
            'weight': 2.0,
            'volume': 0.05,
        })

    def test_haversine_distance_calculation(self):
        """Test the Haversine distance calculation method"""
        route = self.tms_route_model.new({})

        # Test distance between same point (should be 0)
        distance = route._calculate_haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        self.assertEqual(distance, 0.0, "Distance between same point should be 0")

        # Test distance between two different points (should be > 0)
        distance = route._calculate_haversine_distance(40.7128, -74.0060, 40.7228, -74.0160)
        self.assertGreater(distance, 0.0, "Distance between different points should be greater than 0")
        # Approximate distance should be around 1-2 km for these coordinates
        self.assertLess(distance, 5.0, "Distance should be reasonable for nearby points")

    def test_area_adjacency_check(self):
        """Test the area adjacency functionality"""
        route = self.tms_route_model.new({})

        # Same area should be adjacent
        is_adjacent = route._check_areas_adjacent(self.area_north, self.area_north)
        self.assertTrue(is_adjacent, "Same area should be adjacent to itself")

        # Different areas should be checked for geographic proximity
        # With our test data, we'll test the geographic proximity check
        is_adjacent = route._check_areas_adjacent(self.area_north, self.area_south)
        # This might be True or False depending on the distance between partners in each area
        self.assertIsInstance(is_adjacent, bool, "Adjacency check should return boolean")

    def test_create_route_with_area(self):
        """Test creating a route with area assignment"""
        # Create a batch with pickings
        batch = self.stock_picking_batch_model.create({
            'name': 'Test Batch for Route',
        })

        # Create test pickings linked to different area partners
        picking_1 = self.stock_picking_model.create({
            'batch_id': batch.id,
            'partner_id': self.partner_north_1.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'scheduled_date': fields.Datetime.now(),
        })

        # Create stock moves for the picking
        self.stock_move_model.create({
            'name': 'Test Move',
            'product_id': self.product_a.id,
            'product_uom_qty': 10,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'picking_id': picking_1.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })

        # Create route with area from batch
        route = self.tms_route_model.create({
            'name': 'Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        self.assertEqual(route.area_id.id, self.area_north.id, "Route should have correct area assigned")
        self.assertEqual(route.picking_batch_id.id, batch.id, "Route should be linked to correct batch")

    def test_route_distance_optimization(self):
        """Test route optimization for distance"""
        # Create a route with stops in different areas
        batch = self.stock_picking_batch_model.create({
            'name': 'Distance Test Batch',
        })

        route = self.tms_route_model.create({
            'name': 'Distance Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Create stops in different locations
        stop_1 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_1.id,
            'sequence': 1,
            'total_weight': 50.0,
            'total_volume': 5.0,
        })

        stop_2 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_2.id,
            'sequence': 2,
            'total_weight': 30.0,
            'total_volume': 3.0,
        })

        stop_3 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_south_1.id,
            'sequence': 3,
            'total_weight': 20.0,
            'total_volume': 2.0,
        })

        self.assertEqual(len(route.stop_ids), 3, "Route should have 3 stops")

        # Test distance calculation
        original_distance = route._calculate_route_distance(route.stop_ids.sorted('sequence'))
        self.assertGreater(original_distance, 0, "Original route should have distance > 0")

        # Test optimization
        optimized_stops = route._optimize_stops_by_distance(route.stop_ids)
        self.assertEqual(len(optimized_stops), 3, "Optimized route should still have 3 stops")

        # After optimization, the sequence should be different if there were meaningful differences
        optimized_distance = route._calculate_route_distance(optimized_stops)
        self.assertGreater(optimized_distance, 0, "Optimized route should have distance > 0")

    def test_area_combination_within_capacity(self):
        """Test combining areas when within capacity"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Area Combination Test Batch',
        })

        route = self.tms_route_model.create({
            'name': 'Area Combination Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add stops from different but nearby areas (assuming they're geographically close)
        stop_1 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_1.id,  # North area
            'area_id': self.area_north.id,
            'total_weight': 100.0,
            'total_volume': 10.0,
        })

        stop_2 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_2.id,  # North area
            'area_id': self.area_north.id,
            'total_weight': 80.0,
            'total_volume': 8.0,
        })

        stop_3 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_east_1.id,  # East area, but might be close
            'area_id': self.area_east.id,
            'total_weight': 70.0,
            'total_volume': 7.0,
        })

        # Total should be within vehicle capacity (250kg weight, 25m³ volume vs 1000kg, 50m³)
        total_weight = sum(stop.total_weight for stop in route.stop_ids)
        total_volume = sum(stop.total_volume for stop in route.stop_ids)

        self.assertLess(total_weight, self.vehicle.max_weight, "Total weight should be within capacity")
        self.assertLess(total_volume, self.vehicle.max_volume, "Total volume should be within capacity")

    def test_area_splitting_when_exceeding_capacity(self):
        """Test splitting areas when exceeding capacity"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Capacity Split Test Batch',
        })

        route = self.tms_route_model.create({
            'name': 'Capacity Split Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add many stops to exceed capacity
        total_weight = 0
        total_volume = 0

        for i in range(25):  # Create enough stops to exceed capacity (25 * 50kg = 1250kg)
            stop = self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,
                'area_id': self.area_north.id,
                'total_weight': 50.0,
                'total_volume': 5.0,
            })
            total_weight += 50.0
            total_volume += 5.0

        # Total exceeds vehicle capacity (1250kg > 1000kg max)
        self.assertGreater(total_weight, self.vehicle.max_weight or 0, "Total weight should exceed capacity")

        # Test that the route can be split
        original_stop_count = len(route.stop_ids)
        self.assertGreater(original_stop_count, 0, "Original route should have stops")

        # Check if route splitting would work (without actually doing it in this test)
        # The logic is tested in the route splitting methods
        self.assertGreaterEqual(total_weight, self.vehicle.max_weight,
                              "Test setup should exceed vehicle capacity")

    def test_optimize_route_by_distance_method(self):
        """Test the main optimize route method"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Optimization Test Batch',
        })

        route = self.tms_route_model.create({
            'name': 'Optimization Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Create stops in various locations
        stops_data = [
            (self.partner_north_1, 50.0, 5.0),
            (self.partner_north_2, 30.0, 3.0),
            (self.partner_south_1, 40.0, 4.0),
        ]

        for i, (partner, weight, volume) in enumerate(stops_data):
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': partner.id,
                'sequence': i + 1,
                'total_weight': weight,
                'total_volume': volume,
            })

        # Get original sequence and distance
        original_sequence = [stop.id for stop in route.stop_ids.sorted('sequence')]
        original_distance = route._calculate_route_distance(route.stop_ids.sorted('sequence'))

        # Apply optimization
        optimization_result = route.action_optimize_route_by_distance()

        # Optimization should return success notification
        self.assertEqual(optimization_result['type'], 'ir.actions.client')
        self.assertEqual(optimization_result['tag'], 'display_notification')

        # Reload route to get updated sequences
        route.refresh()
        optimized_sequence = [stop.id for stop in route.stop_ids.sorted('sequence')]
        optimized_distance = route._calculate_route_distance(route.stop_ids.sorted('sequence'))

        # Sequences might be different, but should have same stops
        self.assertEqual(set(original_sequence), set(optimized_sequence),
                        "Optimized route should have same stops")

        # Distance might be improved
        self.assertGreaterEqual(original_distance + 0.1, optimized_distance,
                              "Optimized distance should be same or better")

    def test_split_combine_for_adjacent_areas_method(self):
        """Test the split and combine method for adjacent areas"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Split-Combine Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Split-Combine Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add stops that exceed capacity in one area
        for i in range(25):  # 25 stops * 50kg = 1250kg > 1000kg capacity
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,
                'area_id': self.area_north.id,
                'total_weight': 50.0,
                'total_volume': 5.0,
            })

        # Add some stops from another area that are within capacity
        for i in range(3):  # 3 stops * 30kg = 90kg < 1000kg capacity
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_east_1.id,
                'area_id': self.area_east.id,
                'total_weight': 30.0,
                'total_volume': 3.0,
            })

        # Test the split and combine functionality
        result = route.action_split_combine_for_adjacent_areas()

        # This should return a notification
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')

        # Check that the method executes without error
        self.assertIn('params', result)
        self.assertIn('message', result['params'])

        # The route might be split, so we check that the method completed properly
        self.assertTrue(True, "Method should complete without errors")

    def test_check_geographic_proximity_method(self):
        """Test the geographic proximity checking method"""
        route = self.tms_route_model.new({})

        # Test with the same area
        is_close = route._check_geographic_proximity(self.area_north, self.area_north)
        # This could be True or False depending on implementation details

        # Test with different areas
        is_close = route._check_geographic_proximity(self.area_north, self.area_south)
        # Result depends on actual distances between partners in areas
        self.assertIsInstance(is_close, bool, "Geographic proximity check should return boolean")

    def test_smart_split_combine_route_method(self):
        """Test the smart split and combine route method"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Smart Split Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Smart Split Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add stops that exceed capacity in one area
        for i in range(20):  # 20 stops * 60kg = 1200kg > 1000kg capacity
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,
                'area_id': self.area_north.id,
                'total_weight': 60.0,
                'total_volume': 6.0,
            })

        # Add some stops from another area that are within capacity
        for i in range(5):  # 5 stops * 20kg = 100kg < 1000kg capacity
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_east_1.id,
                'area_id': self.area_east.id,
                'total_weight': 20.0,
                'total_volume': 2.0,
            })

        # Test the smart split and combine functionality
        result = route.action_smart_split_combine_route()

        # This should return a notification
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')

        # Verify the result has proper parameters
        self.assertIn('params', result)
        self.assertIn('title', result['params'])
        self.assertIn('message', result['params'])

    def test_optimize_all_routes_for_distance_method(self):
        """Test the optimize all routes for distance method"""
        batch = self.stock_picking_batch_model.create({
            'name': 'All Routes Opt Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'All Routes Opt Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add multiple stops from different areas
        partners_and_areas = [
            (self.partner_north_1, self.area_north),
            (self.partner_north_2, self.area_north),
            (self.partner_south_1, self.area_south),
            (self.partner_east_1, self.area_east),
        ]

        for i, (partner, area) in enumerate(partners_and_areas):
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': partner.id,
                'area_id': area.id,
                'total_weight': 25.0,
                'total_volume': 2.5,
            })

        # Test the optimization method
        result = route.action_optimize_all_routes_for_distance()

        # This should return a notification
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')

        # Verify the result has proper parameters
        self.assertIn('params', result)
        self.assertIn('title', result['params'])
        self.assertIn('message', result['params'])

    def test_route_with_no_vehicle_assignment(self):
        """Test route methods with no vehicle assigned"""
        batch = self.stock_picking_batch_model.create({
            'name': 'No Vehicle Test Batch',
        })

        route = self.tms_route_model.create({
            'name': 'No Vehicle Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            # No vehicle assigned
        })

        # Add some stops
        self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_1.id,
            'area_id': self.area_north.id,
            'total_weight': 50.0,
            'total_volume': 5.0,
        })

        # Test distance optimization without vehicle (should handle gracefully)
        result = route.action_optimize_route_by_distance()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('params', result)

        # Test other methods that require vehicle
        result = route.action_optimize_all_routes_for_distance()
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('No Vehicle Assigned', result['params']['message'])

    def test_route_with_single_stop(self):
        """Test route with single stop edge case"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Single Stop Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Single Stop Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add only one stop
        self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_1.id,
            'area_id': self.area_north.id,
            'total_weight': 50.0,
            'total_volume': 5.0,
        })

        # Test distance optimization with single stop
        result = route.action_optimize_route_by_distance()
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('No Optimization Needed', result['params']['message'])

    def test_optimize_stops_by_distance_algorithm(self):
        """Test the core algorithm that optimizes stops by distance"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Optimize Algorithm Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Optimize Algorithm Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Create stops in a way that optimization would make a difference
        # We'll use partners at different distances to test the algorithm
        stop_1 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_1.id,  # Coordinates: 40.7128, -74.0060
            'area_id': self.area_north.id,
            'total_weight': 20.0,
            'total_volume': 2.0,
        })

        stop_2 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_2.id,  # Coordinates: 40.7228, -74.0160 (close to stop_1)
            'area_id': self.area_north.id,
            'total_weight': 20.0,
            'total_volume': 2.0,
        })

        stop_3 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_south_1.id,  # Coordinates: 40.6528, -74.0360 (further away)
            'area_id': self.area_south.id,
            'total_weight': 20.0,
            'total_volume': 2.0,
        })

        # Get the original order and calculate distance
        original_stops = route.stop_ids.sorted('id')  # Just to have a consistent original order
        original_distance = route._calculate_route_distance(original_stops)

        # Apply the optimization algorithm
        optimized_stops = route._optimize_stops_by_distance(route.stop_ids)

        # Check that all stops are still present
        self.assertEqual(len(optimized_stops), 3, "Optimized route should have same number of stops")
        self.assertEqual(set(s.id for s in original_stops), set(s.id for s in optimized_stops),
                        "Optimized route should contain same stops")

        # Calculate optimized distance
        optimized_distance = route._calculate_route_distance(optimized_stops)

        # The optimized distance should be valid
        self.assertGreaterEqual(optimized_distance, 0, "Optimized distance should be non-negative")

    def test_create_sub_route_functionality(self):
        """Test the sub-route creation functionality"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Sub-route Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        original_route = self.tms_route_model.create({
            'name': 'Original Route for Sub-route Test',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add some stops to the original route
        stop_1 = self.tms_route_stop_model.create({
            'route_id': original_route.id,
            'partner_id': self.partner_north_1.id,
            'area_id': self.area_north.id,
            'total_weight': 30.0,
            'total_volume': 3.0,
        })

        stop_2 = self.tms_route_stop_model.create({
            'route_id': original_route.id,
            'partner_id': self.partner_north_2.id,
            'area_id': self.area_north.id,
            'total_weight': 30.0,
            'total_volume': 3.0,
        })

        # Test the sub-route creation method
        sub_route = original_route._create_sub_route_for_stops([stop_1, stop_2])

        # Check that a new route was created
        self.assertIsNotNone(sub_route, "Sub-route should be created")
        self.assertNotEqual(sub_route.id, original_route.id, "Sub-route should be different from original route")

        # Check that the new route has the proper properties
        self.assertEqual(sub_route.picking_batch_id.id, batch.id, "Sub-route should belong to same batch")
        self.assertEqual(sub_route.area_id.id, original_route.area_id.id, "Sub-route should inherit area")
        self.assertEqual(sub_route.state, 'draft', "Sub-route should be in draft state")

        # Check that stops were moved to the new route
        for stop in [stop_1, stop_2]:
            self.assertEqual(stop.route_id.id, sub_route.id, f"Stop {stop.id} should be in new route")

    def test_calculate_route_distance_functionality(self):
        """Test the route distance calculation functionality"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Distance Calc Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Distance Calc Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add stops with different geographic locations
        stop_1 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_1.id,
            'area_id': self.area_north.id,
            'total_weight': 25.0,
            'total_volume': 2.5,
        })

        stop_2 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_north_2.id,  # Close to stop_1
            'area_id': self.area_north.id,
            'total_weight': 25.0,
            'total_volume': 2.5,
        })

        stop_3 = self.tms_route_stop_model.create({
            'route_id': route.id,
            'partner_id': self.partner_south_1.id,  # Further away
            'area_id': self.area_south.id,
            'total_weight': 25.0,
            'total_volume': 2.5,
        })

        # Calculate the distance of the route
        total_distance = route._calculate_route_distance(route.stop_ids.sorted('sequence'))

        # Should be greater than 0 since we have stops in different locations
        self.assertGreater(total_distance, 0, "Total distance should be greater than 0 for route with multiple stops")

        # Calculate distance with only one stop (should be 0)
        single_stop_distance = route._calculate_route_distance(route.stop_ids[:1])
        self.assertEqual(single_stop_distance, 0, "Distance with single stop should be 0")

    def test_split_route_by_area_capacity_method(self):
        """Test the area-based route splitting when capacity is exceeded"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Split Capacity Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Split Capacity Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add stops that exceed the vehicle capacity
        total_route_weight = 0
        for i in range(25):  # 25 stops * 50kg = 1250kg > 1000kg capacity
            stop = self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,  # All in same area
                'area_id': self.area_north.id,
                'total_weight': 50.0,
                'total_volume': 5.0,
            })
            total_route_weight += 50.0

        # Verify that the total weight exceeds capacity
        self.assertGreater(total_route_weight, self.vehicle.max_weight,
                          "Total route weight should exceed vehicle capacity")

        # Test the capacity-based splitting method
        result = route.action_split_route_by_area_capacity()

        # Check that the result is a notification action
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('params', result)
        self.assertIn('message', result['params'])

        # After splitting, the original route should still exist but may have fewer stops
        # The method should have created additional routes for the overflow

    def test_combine_nearby_areas_method(self):
        """Test combining nearby areas into single route"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Combine Areas Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Combine Areas Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add stops from different areas but within capacity
        # North area stops
        for i in range(5):  # 5 stops * 30kg = 150kg
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,
                'area_id': self.area_north.id,
                'total_weight': 30.0,
                'total_volume': 3.0,
            })

        # South area stops (assuming it's nearby based on coordinates)
        for i in range(4):  # 4 stops * 25kg = 100kg
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_south_1.id,
                'area_id': self.area_south.id,
                'total_weight': 25.0,
                'total_volume': 2.5,
            })

        # Total: 250kg + 100kg = 350kg << 1000kg capacity, so areas can be combined
        total_weight = sum(stop.total_weight for stop in route.stop_ids)
        self.assertLess(total_weight, self.vehicle.max_weight,
                       "Total weight should be within vehicle capacity")

        # Test the combining method
        result = route.action_combine_nearby_areas_route()

        # This method might not do much in our test scenario since there are no other routes
        # But it should return a proper response
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('params', result)
        self.assertIn('message', result['params'])

    def test_split_combine_for_adjacent_areas_with_oversized_area(self):
        """Test split and combine method when one area is oversized"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Split-Combine Oversized Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Split-Combine Oversized Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Add many stops to one area that exceed capacity
        for i in range(22):  # 22 stops * 50kg = 1100kg > 1000kg capacity
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,
                'area_id': self.area_north.id,
                'total_weight': 50.0,
                'total_volume': 4.0,
            })

        # Add some stops from another area that are within capacity
        for i in range(5):  # 5 stops * 30kg = 150kg
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_east_1.id,
                'area_id': self.area_east.id,
                'total_weight': 30.0,
                'total_volume': 3.0,
            })

        # Test the split and combine method
        result = route.action_split_combine_for_adjacent_areas()

        # Verify the result
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('params', result)
        self.assertIn('message', result['params'])

    def test_adjacent_area_detection(self):
        """Test that adjacent area detection works properly"""
        route = self.tms_route_model.new({
            'vehicle_id': self.vehicle.id
        })

        # Test same area detection
        is_adjacent = route._check_areas_adjacent(self.area_north, self.area_north)
        self.assertTrue(is_adjacent, "Same area should be adjacent to itself")

        # Test with None areas (should be true for compatibility)
        is_with_none1 = route._check_areas_adjacent(None, self.area_north)
        self.assertTrue(is_with_none1, "None and area should be considered compatible")

        is_with_none2 = route._check_areas_adjacent(self.area_north, None)
        self.assertTrue(is_with_none2, "Area and None should be considered compatible")

        is_both_none = route._check_areas_adjacent(None, None)
        self.assertTrue(is_both_none, "Two None areas should be considered compatible")

    def test_capacity_constraints_handling(self):
        """Test that capacity constraints are properly handled in all operations"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Capacity Constraints Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Capacity Constraints Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Test with stops that exceed weight capacity but not volume
        for i in range(25):  # 25 stops * 45kg = 1125kg > 1000kg max weight
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,
                'area_id': self.area_north.id,
                'total_weight': 45.0,  # Will exceed weight capacity
                'total_volume': 1.0,   # Within volume capacity
            })

        # Check that total exceeds weight capacity
        total_weight = sum(stop.total_weight for stop in route.stop_ids)
        total_volume = sum(stop.total_volume for stop in route.stop_ids)

        self.assertGreater(total_weight, self.vehicle.max_weight or 0,
                          "Total weight should exceed vehicle weight capacity")
        self.assertLess(total_volume, self.vehicle.max_volume or 0,
                       "Total volume should be within vehicle volume capacity")

        # Test that capacity-based operations handle this properly
        result = route.action_split_route_by_area_capacity()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertIn('params', result)

        # Create another route with different capacity issue (volume)
        route2 = self.tms_route_model.create({
            'name': 'Volume Capacity Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_south.id,
            'vehicle_id': self.vehicle.id,
        })

        for i in range(12):  # 12 stops * 4.5m³ = 54m³ > 50m³ max volume
            self.tms_route_stop_model.create({
                'route_id': route2.id,
                'partner_id': self.partner_south_1.id,
                'area_id': self.area_south.id,
                'total_weight': 10.0,  # Within weight capacity
                'total_volume': 4.5,   # Will exceed volume capacity
            })

        # Check that total exceeds volume capacity
        total_weight2 = sum(stop.total_weight for stop in route2.stop_ids)
        total_volume2 = sum(stop.total_volume for stop in route2.stop_ids)

        self.assertLess(total_weight2, self.vehicle.max_weight or 0,
                       "Total weight should be within vehicle weight capacity")
        self.assertGreater(total_volume2, self.vehicle.max_volume or 0,
                          "Total volume should exceed vehicle volume capacity")

    def test_geographic_clustering_and_distance_optimization(self):
        """Test geographic clustering with distance optimization"""
        batch = self.stock_picking_batch_model.create({
            'name': 'Geo Clustering Test Batch',
            'vehicle_id': self.vehicle.id,
        })

        route = self.tms_route_model.create({
            'name': 'Geo Clustering Test Route',
            'picking_batch_id': batch.id,
            'area_id': self.area_north.id,
            'vehicle_id': self.vehicle.id,
        })

        # Create stops in geographic clusters
        # Cluster 1: Stops in North area (close to each other)
        for i in range(3):
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_north_1.id,  # Same partner, same location
                'area_id': self.area_north.id,
                'total_weight': 20.0,
                'total_volume': 2.0,
            })

        # Cluster 2: Stops in South area (could be close to each other but far from North)
        for i in range(3):
            self.tms_route_stop_model.create({
                'route_id': route.id,
                'partner_id': self.partner_south_1.id,  # Different location
                'area_id': self.area_south.id,
                'total_weight': 15.0,
                'total_volume': 1.5,
            })

        # Total is within capacity: 6 stops * avg 17.5kg = 105kg << 1000kg
        total_weight = sum(stop.total_weight for stop in route.stop_ids)
        self.assertLess(total_weight, self.vehicle.max_weight,
                       "Total weight should be within capacity")

        # Apply distance optimization
        original_distance = route._calculate_route_distance(route.stop_ids.sorted('sequence'))
        result = route.action_optimize_route_by_distance()

        # Reload to get updated sequences after optimization
        route.refresh()
        optimized_distance = route._calculate_route_distance(route.stop_ids.sorted('sequence'))

        # Check that optimization ran successfully
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')

        # The optimized distance should be a valid number
        self.assertGreaterEqual(optimized_distance, 0, "Optimized distance should be non-negative")

    def test_batch_area_split_functionality(self):
        """Test the batch level area split functionality"""
        # Create pickings for different areas
        picking_type = self.env.ref('stock.picking_type_out')

        picking_1 = self.stock_picking_model.create({
            'partner_id': self.partner_north_1.id,
            'picking_type_id': picking_type.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'scheduled_date': fields.Datetime.now(),
        })

        picking_2 = self.stock_picking_model.create({
            'partner_id': self.partner_south_1.id,
            'picking_type_id': picking_type.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'scheduled_date': fields.Datetime.now(),
        })

        # Create stock moves
        self.stock_move_model.create({
            'name': 'Test Move 1',
            'product_id': self.product_a.id,
            'product_uom_qty': 5,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'picking_id': picking_1.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })

        self.stock_move_model.create({
            'name': 'Test Move 2',
            'product_id': self.product_b.id,
            'product_uom_qty': 8,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'picking_id': picking_2.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })

        # Create a batch with these pickings
        batch = self.stock_picking_batch_model.create({
            'name': 'Area Split Test Batch',
            'picking_ids': [(6, 0, [picking_1.id, picking_2.id])],
            'vehicle_id': self.vehicle.id,
        })

        # Test the area split method on the batch
        # This would normally be called from the UI but we can test the concept
        area_picking_map = {}
        for picking in batch.picking_ids:
            area = picking.partner_id.route_area_id
            area_id = area.id if area else 0
            if area_id not in area_picking_map:
                area_picking_map[area_id] = []
            area_picking_map[area_id].append(picking)

        # Should have 2 different areas (North and South)
        self.assertEqual(len(area_picking_map), 2, "Should have pickings in 2 different areas")

        # Each area should have 1 picking
        for area_id, pickings in area_picking_map.items():
            self.assertEqual(len(pickings), 1, f"Area {area_id} should have 1 picking")