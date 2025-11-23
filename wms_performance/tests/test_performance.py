from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


@tagged('wms_performance', 'at_install')
class TestWmsPerformance(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsPerformanceIndicator = self.env['wms.performance.indicator']
        self.WmsPerformanceReport = self.env['wms.performance.report']
        self.WmsOperatorPerformance = self.env['wms.operator.performance']
        self.WmsPerformanceWizard = self.env['wms.performance.wizard']
        self.Warehouse = self.env['stock.warehouse']
        self.Location = self.env['stock.location']
        self.Product = self.env['product.product']
        self.Owner = self.env['wms.owner']
        self.Picking = self.env['stock.picking']
        self.ProductCategory = self.env['product.category']
        self.Employee = self.env['hr.employee']

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

        # Create test employee/operator
        self.employee = self.Employee.create({
            'name': 'Test Operator',
            'work_location': 'Test Location'
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

        # Create test picking for performance tracking
        self.picking = self.Picking.create({
            'name': 'TEST_PICKING_PERF_01',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
            'owner_id': self.owner.id,
            'state': 'done',
            'date': datetime.now() - timedelta(days=1),
            'date_done': datetime.now() - timedelta(days=1, hours=2)
        })

    def test_performance_indicator_creation(self):
        """Test creation of performance indicator records"""
        indicator = self.WmsPerformanceIndicator.create({
            'name': 'Test Performance Indicator',
            'code': 'TPI001',
            'category': 'throughput',
            'calculation_method': 'count',
            'target_value': 100.0,
            'benchmark_value': 90.0,
        })

        self.assertEqual(indicator.name, 'Test Performance Indicator')
        self.assertEqual(indicator.code, 'TPI001')
        self.assertEqual(indicator.category, 'throughput')
        self.assertEqual(indicator.target_value, 100.0)
        self.assertTrue(indicator.active)

    def test_performance_indicator_constraints(self):
        """Test performance indicator constraints"""
        # Test negative target value constraint
        with self.assertRaises(ValidationError):
            self.WmsPerformanceIndicator.create({
                'name': 'Test Negative Target',
                'code': 'TNT001',
                'category': 'efficiency',
                'calculation_method': 'average',
                'target_value': -10.0,
                'benchmark_value': 50.0,
            })

        # Test negative benchmark value constraint
        with self.assertRaises(ValidationError):
            self.WmsPerformanceIndicator.create({
                'name': 'Test Negative Benchmark',
                'code': 'TNB001',
                'category': 'quality',
                'calculation_method': 'percentage',
                'target_value': 100.0,
                'benchmark_value': -5.0,
            })

    def test_performance_report_creation(self):
        """Test creation of performance report records"""
        report = self.WmsPerformanceReport.create({
            'name': 'Test Performance Report',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'report_type': 'weekly',
        })

        self.assertEqual(report.name, 'Test Performance Report')
        self.assertEqual(report.owner_id.id, self.owner.id)
        self.assertEqual(report.warehouse_id.id, self.warehouse.id)
        self.assertEqual(report.report_type, 'weekly')
        self.assertEqual(report.status, 'draft')

    def test_performance_report_period_constraint(self):
        """Test performance report period validation"""
        # Test that start date cannot be after end date
        with self.assertRaises(ValidationError):
            self.WmsPerformanceReport.create({
                'name': 'Test Performance Report Invalid Period',
                'period_start': datetime.now(),
                'period_end': datetime.now() - timedelta(days=7),
                'owner_id': self.owner.id,
                'warehouse_id': self.warehouse.id,
                'report_type': 'weekly',
            })

    def test_performance_report_methods_execution(self):
        """Test performance report methods execution"""
        report = self.WmsPerformanceReport.create({
            'name': 'Test Performance Report Methods',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'report_type': 'weekly',
        })

        # Test metric calculation methods
        throughput_metrics = report._calculate_throughput_metrics()
        self.assertIsInstance(throughput_metrics, dict)
        self.assertIn('score', throughput_metrics)

        efficiency_metrics = report._calculate_efficiency_metrics()
        self.assertIsInstance(efficiency_metrics, dict)
        self.assertIn('score', efficiency_metrics)

        quality_metrics = report._calculate_quality_metrics()
        self.assertIsInstance(quality_metrics, dict)
        self.assertIn('score', quality_metrics)

        # Test report content generation methods
        performance_data = report._calculate_performance_metrics()
        self.assertIsInstance(performance_data, dict)
        self.assertIn('overall_score', performance_data)

        exec_summary = report._generate_executive_summary(performance_data)
        self.assertIn('Performance Summary', exec_summary)

        detailed_analysis = report._generate_detailed_analysis(performance_data)
        self.assertIn('Detailed Metrics Analysis', detailed_analysis)

        recommendations = report._generate_recommendations(performance_data)
        self.assertIn('<div>', recommendations)

        trends = report._generate_trends()
        self.assertIn('Trend Analysis', trends)

        alerts = report._generate_alerts()
        self.assertIn('<div>', alerts)

    def test_performance_report_generation(self):
        """Test performance report generation"""
        report = self.WmsPerformanceReport.create({
            'name': 'Test Performance Report Generation',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'report_type': 'weekly',
        })

        # Initially, stats should be 0
        self.assertEqual(report.overall_score, 0.0)
        self.assertEqual(report.total_indicators, 0)

        # Generate report
        report.action_generate_report()

        # After generation, status should be 'generated'
        self.assertEqual(report.status, 'generated')

        # Check that metrics have been calculated
        self.assertIsNotNone(report.performance_data)
        self.assertIsNotNone(report.executive_summary)

    def test_operator_performance_creation(self):
        """Test creation of operator performance records"""
        operator_perf = self.WmsOperatorPerformance.create({
            'operator_id': self.employee.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'operations_completed': 50,
            'operations_assigned': 55,
            'time_spent_hours': 8.0,
            'standard_time_hours': 7.5,
        })

        self.assertEqual(operator_perf.operator_id.id, self.employee.id)
        self.assertEqual(operator_perf.owner_id.id, self.owner.id)
        self.assertEqual(operator_perf.operations_completed, 50)
        self.assertEqual(operator_perf.operations_assigned, 55)

        # Check that efficiency rate was calculated automatically
        expected_efficiency = (7.5 / 8.0 * 100) if 8.0 > 0 else 0
        self.assertAlmostEqual(operator_perf.efficiency_rate, expected_efficiency, places=1)

    def test_operator_performance_score_calculation(self):
        """Test operator performance score calculation"""
        operator_perf = self.WmsOperatorPerformance.create({
            'operator_id': self.employee.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'operations_completed': 100,
            'error_count': 5,
            'time_spent_hours': 8.0,
            'standard_time_hours': 7.0,
        })

        # Check initial values
        self.assertEqual(operator_perf.error_count, 5)
        expected_accuracy = ((100 - 5) / 100 * 100)  # 95%
        self.assertAlmostEqual(operator_perf.accuracy_rate, expected_accuracy, places=1)

        # Calculate performance score manually
        operator_perf.calculate_performance_score()

        # Check that scores were updated
        self.assertGreaterEqual(operator_perf.overall_score, 0)
        self.assertLessEqual(operator_perf.overall_score, 100)

    def test_performance_wizard(self):
        """Test performance report wizard"""
        wizard = self.WmsPerformanceWizard.create({
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'report_type': 'weekly',
        })

        self.assertEqual(wizard.period_start, datetime.now().date() - timedelta(days=7))
        self.assertEqual(wizard.period_end, datetime.now().date())
        self.assertEqual(wizard.owner_id.id, self.owner.id)
        self.assertEqual(wizard.warehouse_id.id, self.warehouse.id)
        self.assertEqual(wizard.report_type, 'weekly')

        # Test that it can generate an action
        action = wizard.action_generate_report()
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'wms.performance.report')

    def test_cost_metrics_calculation(self):
        """Test cost metrics calculation"""
        report = self.WmsPerformanceReport.create({
            'name': 'Test Cost Metrics',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'report_type': 'weekly',
        })

        cost_metrics = report._calculate_cost_metrics()
        self.assertIsInstance(cost_metrics, dict)
        self.assertIn('score', cost_metrics)
        self.assertIn('cost_per_operation', cost_metrics)

    def test_service_metrics_calculation(self):
        """Test service metrics calculation"""
        report = self.WmsPerformanceReport.create({
            'name': 'Test Service Metrics',
            'period_start': datetime.now() - timedelta(days=7),
            'period_end': datetime.now(),
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'report_type': 'weekly',
        })

        service_metrics = report._calculate_service_metrics()
        self.assertIsInstance(service_metrics, dict)
        self.assertIn('score', service_metrics)
        self.assertIn('service_rate', service_metrics)