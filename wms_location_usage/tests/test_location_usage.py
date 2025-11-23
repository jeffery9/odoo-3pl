from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


@tagged('wms_location_usage', 'at_install')
class TestWmsLocationUsage(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsLocationUsage = self.env['wms.location.usage']
        self.WmsLocationUtilization = self.env['wms.location.utilization']
        self.WmsLocationUsageReport = self.env['wms.location.usage.report']
        self.Warehouse = self.env['stock.warehouse']
        self.Location = self.env['stock.location']
        self.Product = self.env['product.product']
        self.Owner = self.env['wms.owner']
        self.Picking = self.env['stock.picking']
        self.ProductCategory = self.env['product.category']
        self.Quant = self.env['stock.quant']

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

        # Create test product category
        self.category = self.ProductCategory.create({
            'name': 'Test Category'
        })

        # Create test products
        self.product1 = self.Product.create({
            'name': 'Test Product 1',
            'type': 'product',
            'default_code': 'TEST001',
            'weight': 1.0,
            'volume': 0.01,
            'length': 10,
            'width': 10,
            'height': 10
        })

        self.product2 = self.Product.create({
            'name': 'Test Product 2',
            'type': 'product',
            'default_code': 'TEST002',
            'weight': 2.0,
            'volume': 0.02,
            'length': 15,
            'width': 15,
            'height': 15
        })

        # Create test locations
        self.location1 = self.Location.create({
            'name': 'Test Location 1',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
            'volume_per_location': 1.0,  # Set capacity
        })

        self.location2 = self.Location.create({
            'name': 'Test Location 2',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
            'volume_per_location': 1.0,  # Set capacity
        })

        # Create test picking for analysis
        self.picking = self.Picking.create({
            'name': 'TEST_PICKING_LOC_01',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location1.id,
            'location_dest_id': self.location2.id,
            'owner_id': self.owner.id,
            'state': 'done',
            'date': datetime.now() - timedelta(days=1)
        })

    def test_location_usage_creation(self):
        """Test creation of location usage records"""
        location_usage = self.WmsLocationUsage.create({
            'name': 'Test Location Usage Analysis',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'analysis_type': 'all',
        })

        self.assertEqual(location_usage.name, 'Test Location Usage Analysis')
        self.assertEqual(location_usage.owner_id.id, self.owner.id)
        self.assertEqual(location_usage.warehouse_id.id, self.warehouse.id)
        self.assertEqual(location_usage.analysis_type, 'all')
        self.assertEqual(location_usage.state, 'draft')

    def test_location_usage_period_constraint(self):
        """Test location usage period validation"""
        # Test that start date cannot be after end date
        with self.assertRaises(ValidationError):
            self.WmsLocationUsage.create({
                'name': 'Test Location Usage Invalid Period',
                'period_start': datetime.now(),
                'period_end': datetime.now() - timedelta(days=7),
                'owner_id': self.owner.id,
                'warehouse_id': self.warehouse.id,
                'analysis_type': 'all',
            })

    def test_location_usage_methods_execution(self):
        """Test location usage methods execution"""
        location_usage = self.WmsLocationUsage.create({
            'name': 'Test Location Usage Methods',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'analysis_type': 'all',
        })

        # Test private methods
        turnover_rate = location_usage._calculate_turnover_rate()
        self.assertIsInstance(turnover_rate, float)

        avg_residence_time = location_usage._calculate_avg_residence_time()
        self.assertIsInstance(avg_residence_time, float)

        # Test stats by zone calculation
        stats_by_zone = location_usage._calculate_stats_by_zone([self.location1, self.location2])
        self.assertIsInstance(stats_by_zone, dict)

        # Test stats by category calculation
        stats_by_category = location_usage._calculate_stats_by_category([self.location1, self.location2])
        self.assertIsInstance(stats_by_category, dict)

        # Test usage trend calculation
        usage_trend = location_usage._calculate_usage_trend()
        self.assertIsInstance(usage_trend, list)

    def test_location_usage_generation(self):
        """Test location usage generation"""
        location_usage = self.WmsLocationUsage.create({
            'name': 'Test Location Usage Generation',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'analysis_type': 'all',
        })

        # Initially, stats should be 0
        self.assertEqual(location_usage.total_locations, 0)
        self.assertEqual(location_usage.occupied_locations, 0)
        self.assertEqual(location_usage.usage_rate, 0.0)

        # Generate analysis
        location_usage.action_generate_analysis()

        # After generation, state should be 'generated'
        self.assertEqual(location_usage.state, 'generated')

        # Check that stats have been calculated
        self.assertIsNotNone(location_usage.recommendations)

    def test_location_usage_report_wizard(self):
        """Test location usage report wizard"""
        wizard = self.WmsLocationUsageReport.create({
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'analysis_type': 'all',
        })

        self.assertEqual(wizard.period_start, datetime.now().date() - timedelta(days=7))
        self.assertEqual(wizard.period_end, datetime.now().date())
        self.assertEqual(wizard.owner_id.id, self.owner.id)
        self.assertEqual(wizard.warehouse_id.id, self.warehouse.id)
        self.assertEqual(wizard.analysis_type, 'all')

    def test_location_utilization_creation(self):
        """Test creation of location utilization records"""
        location_usage = self.WmsLocationUsage.create({
            'name': 'Test Location Utilization Creation',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'analysis_type': 'all',
        })

        utilization = self.WmsLocationUtilization.create({
            'analysis_id': location_usage.id,
            'location_id': self.location1.id,
            'is_occupied': True,
            'capacity': 1.0,
            'used_volume': 0.5,
            'usage_rate': 50.0,
        })

        self.assertEqual(utilization.analysis_id.id, location_usage.id)
        self.assertEqual(utilization.location_id.id, self.location1.id)
        self.assertTrue(utilization.is_occupied)
        self.assertEqual(utilization.usage_rate, 50.0)

    def test_efficiency_category_computation(self):
        """Test efficiency category computation"""
        location_usage = self.WmsLocationUsage.create({
            'name': 'Test Efficiency Category',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'analysis_type': 'all',
        })

        # Test high efficiency category (>80%)
        utilization_high = self.WmsLocationUtilization.create({
            'analysis_id': location_usage.id,
            'location_id': self.location1.id,
            'usage_rate': 85.0,
        })
        self.assertEqual(utilization_high.efficiency_category, 'high')

        # Test medium efficiency category (20%-80%)
        utilization_medium = self.WmsLocationUtilization.create({
            'analysis_id': location_usage.id,
            'location_id': self.location2.id,
            'usage_rate': 50.0,
        })
        self.assertEqual(utilization_medium.efficiency_category, 'medium')

        # Test low efficiency category (<20%)
        utilization_low = self.WmsLocationUtilization.create({
            'analysis_id': location_usage.id,
            'location_id': self.location1.id,
            'usage_rate': 10.0,
        })
        self.assertEqual(utilization_low.efficiency_category, 'low')

        # Test unused category (0%)
        utilization_unused = self.WmsLocationUtilization.create({
            'analysis_id': location_usage.id,
            'location_id': self.location2.id,
            'usage_rate': 0.0,
        })
        self.assertEqual(utilization_unused.efficiency_category, 'unused')

    def test_recommendations_generation(self):
        """Test recommendations generation"""
        location_usage = self.WmsLocationUsage.create({
            'name': 'Test Recommendations',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'analysis_type': 'all',
        })

        # Create sample stats
        stats = {
            'usage_rate': 45.0,
            'high_usage_locations': 2,
            'low_usage_locations': 3,
            'empty_locations': 10,
            'total_locations': 50,
            'capacity_usage_rate': 55.0,
        }

        # Generate recommendations
        recommendations_html = location_usage._generate_recommendations(stats)
        self.assertIn('<div>', recommendations_html)
        self.assertIn('<ul>', recommendations_html)
        self.assertIn('recommendations', recommendations_html.lower())