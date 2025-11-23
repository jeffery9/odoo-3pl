from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


@tagged('wms_wave_auto', 'at_install')
class TestWmsWaveAuto(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsWaveRule = self.env['wms.wave.rule']
        self.Warehouse = self.env['stock.warehouse']
        self.Location = self.env['stock.location']
        self.Product = self.env['product.product']
        self.Owner = self.env['wms.owner']
        self.Picking = self.env['stock.picking']
        self.PickingBatch = self.env['stock.picking.batch']

        # Create a test warehouse
        self.warehouse = self.Warehouse.create({
            'name': 'Test Warehouse',
            'code': 'TST'
        })

        # Create a test owner
        self.owner = self.Owner.create({
            'name': 'Test Owner',
            'code': 'TO',
            'email': 'test@example.com'
        })

        # Create test products
        self.product1 = self.Product.create({
            'name': 'Test Product 1',
            'type': 'product',
            'default_code': 'TEST001'
        })

        self.product2 = self.Product.create({
            'name': 'Test Product 2',
            'type': 'product',
            'default_code': 'TEST002'
        })

        # Create test locations
        self.location_src = self.Location.create({
            'name': 'Test Source Location',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id
        })

        self.location_dst = self.Location.create({
            'name': 'Test Destination Location',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id
        })

        # Create a test picking
        self.picking = self.Picking.create({
            'name': 'TEST_PICKING_01',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
            'owner_id': self.owner.id,
        })

    def test_wave_rule_creation(self):
        """Test creation of wave rules"""
        wave_rule = self.WmsWaveRule.create({
            'name': 'Test Wave Rule',
            'code': 'TWR001',
            'warehouse_id': self.warehouse.id,
            'trigger_type': 'quantity_based',
            'min_quantity': 10,
            'max_quantity': 100,
            'priority': 1,
            'active': True,
        })

        self.assertEqual(wave_rule.name, 'Test Wave Rule')
        self.assertEqual(wave_rule.code, 'TWR001')
        self.assertEqual(wave_rule.warehouse_id.id, self.warehouse.id)
        self.assertTrue(wave_rule.active)
        self.assertEqual(wave_rule.trigger_type, 'quantity_based')

    def test_wave_rule_methods(self):
        """Test wave rule methods"""
        wave_rule = self.WmsWaveRule.create({
            'name': 'Test Wave Rule for Methods',
            'code': 'TWR002',
            'warehouse_id': self.warehouse.id,
            'trigger_type': 'time_based',
            'time_interval': 30,
            'active': True,
        })

        # Test constraint validation
        with self.assertRaises(ValidationError):
            invalid_rule = self.WmsWaveRule.create({
                'name': 'Invalid Rule',
                'code': 'IR001',
                'warehouse_id': self.warehouse.id,
                'trigger_type': 'quantity_based',
                'min_orders': 10,  # Greater than max_orders which defaults to False/0
                'max_orders': 5,   # Less than min_orders
                'active': True,
            })

    def test_wave_rule_methods_execution(self):
        """Test wave rule execution methods"""
        wave_rule = self.WmsWaveRule.create({
            'name': 'Test Wave Rule for Methods',
            'code': 'TWR003',
            'warehouse_id': self.warehouse.id,
            'trigger_type': 'time_based',
            'time_interval': 30,
            'active': True,
        })

        # Test action_execute_rule (will create a picking batch since we have a picking)
        picking = self.Picking.create({
            'name': 'TEST_PICKING_02',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
            'owner_id': self.owner.id,
            'state': 'assigned',
        })

        # Execute the rule - this should create a picking batch
        wave_rule.action_execute_rule()
        # Check that last execution time was updated
        self.assertIsNotNone(wave_rule.last_execution)
        self.assertEqual(wave_rule.execution_count, 1)

    def test_wave_auto_generation(self):
        """Test automated wave generation"""
        # Create a valid wave rule
        wave_rule = self.WmsWaveRule.create({
            'name': 'Auto Generation Rule',
            'code': 'AGR001',
            'warehouse_id': self.warehouse.id,
            'trigger_type': 'quantity_based',
            'min_orders': 1,
            'active': True,
        })

        # Create pickings that should match the rule
        picking1 = self.Picking.create({
            'name': 'AUTO_PICKING_01',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
            'owner_id': self.owner.id,
            'state': 'assigned',
        })

        # Test that wave generation works with proper criteria
        wave_rule.action_execute_rule()

        # Check that a picking batch was created
        picking_batches = self.PickingBatch.search([('name', 'like', 'Auto-Wave%')])
        self.assertGreaterEqual(len(picking_batches), 1)

        # Test the filter methods
        filtered = wave_rule._filter_by_volume_weight([picking1], wave_rule)
        self.assertIsInstance(filtered, list)

        sorted_pickings = wave_rule._sort_pickings_by_strategy([picking1], wave_rule)
        self.assertIsInstance(sorted_pickings, list)