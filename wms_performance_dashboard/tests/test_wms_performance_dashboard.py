from odoo.tests import TransactionCase
from odoo import fields


class TestWmsPerformanceDashboard(TransactionCase):
    """Test cases for WMS Performance Dashboard module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Performance Dashboard Owner',
            'owner_code': 'TPDO',
            'is_warehouse_owner': True,
        })

        self.test_user = self.env['res.users'].create({
            'name': 'Test Performance User',
            'login': 'test_perf_user',
            'email': 'test.perf@example.com',
        })

        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'partner@example.com',
        })

        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Performance',
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
    def test_create_dashboard_template(self):
        """Test creating dashboard templates"""
        template = self.env['wms.dashboard.template'].create({
            'name': 'Test Executive Dashboard',
            'owner_code': 'TED',
            'dashboard_type': 'executive',
            'is_active': True,
            'default_period': 'month',
        })

        self.assertEqual(template.name, 'Test Executive Dashboard')
        self.assertEqual(template.owner_code, 'TED')
        self.assertEqual(template.dashboard_type, 'executive')
        self.assertTrue(template.is_active)
        self.assertEqual(template.default_period, 'month')
    def test_create_dashboard_widget(self):
        """Test creating dashboard widgets"""
        widget = self.env['wms.dashboard.widget'].create({
            'name': 'Test KPI Widget',
            'owner_code': 'TKW',
            'widget_type': 'kpi',
            'data_source': 'stock_picking',
            'size_x': 4,
            'size_y': 2,
            'is_active': True,
        })

        self.assertEqual(widget.name, 'Test KPI Widget')
        self.assertEqual(widget.owner_code, 'TKW')
        self.assertEqual(widget.widget_type, 'kpi')
        self.assertEqual(widget.data_source, 'stock_picking')
        self.assertEqual(widget.size_x, 4)
        self.assertEqual(widget.size_y, 2)
        self.assertTrue(widget.is_active)
    def test_create_performance_kpi(self):
        """Test creating performance KPIs"""
        kpi = self.env['wms.performance.kpi'].create({
            'name': 'Test Throughput KPI',
            'owner_code': 'TTK',
            'category': 'throughput',
            'calculation_method': 'count',
            'source_model': 'stock.picking',
            'source_field': 'id',
            'owner_id': self.test_owner.id,
        })

        self.assertEqual(kpi.name, 'Test Throughput KPI')
        self.assertEqual(kpi.owner_code, 'TTK')
        self.assertEqual(kpi.category, 'throughput')
        self.assertEqual(kpi.calculation_method, 'count')
        self.assertEqual(kpi.source_model, 'stock.picking')
        self.assertEqual(kpi.owner_id.id, self.test_owner.id)
        self.assertEqual(kpi.current_value, 0.0)  # Initially 0

    def test_performance_kpi_computed_values(self):
        """Test computed values for performance KPIs"""
        kpi = self.env['wms.performance.kpi'].create({
            'name': 'Computed Value Test',
            'owner_code': 'CVT',
            'category': 'efficiency',
            'calculation_method': 'count',
            'source_model': 'stock.picking',
            'source_field': 'id',
            'owner_id': self.test_owner.id,
        })

        # Verify initial computed values
        self.assertEqual(kpi.current_value, 0.0)
        self.assertEqual(kpi.previous_value, 0.0)
        self.assertEqual(kpi.trend, 0.0)
    def test_create_performance_report(self):
        """Test creating performance reports"""
        report = self.env['wms.performance.report'].create({
            'name': 'Test Performance Report',
            'owner_id': self.test_owner.id,
            'report_type': 'monthly',
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
        })

        self.assertTrue(report.report_code.startswith('PER'))
        self.assertEqual(report.name, 'Test Performance Report')
        self.assertEqual(report.owner_id.id, self.test_owner.id)
        self.assertEqual(report.report_type, 'monthly')
        self.assertEqual(report.status, 'draft')
    def test_performance_report_status_flow(self):
        """Test performance report status flow"""
        report = self.env['wms.performance.report'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'report_type': 'weekly',
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=7),
        })

        self.assertEqual(report.status, 'draft')

        # Generate the report
        report.action_generate_report()
        self.assertEqual(report.status, 'generated')

        # Validate the report
        report.action_validate_report()
        self.assertEqual(report.status, 'validated')

        # Publish the report
        report.action_publish_report()
        self.assertEqual(report.status, 'published')
    def test_create_alert(self):
        """Test creating alerts"""
        alert = self.env['wms.alert'].create({
            'name': 'Test Performance Alert',
            'alert_type': 'kpi_threshold',
            'severity': 'high',
            'message': 'KPI value exceeded threshold',
            'target_value': 95.0,
            'actual_value': 98.0,
        })

        self.assertEqual(alert.name, 'Test Performance Alert')
        self.assertEqual(alert.alert_type, 'kpi_threshold')
        self.assertEqual(alert.severity, 'high')
        self.assertEqual(alert.status, 'open')
        self.assertEqual(alert.target_value, 95.0)
        self.assertEqual(alert.actual_value, 98.0)
    def test_alert_status_flow(self):
        """Test alert status flow"""
        alert = self.env['wms.alert'].create({
            'name': 'Status Flow Test',
            'alert_type': 'performance_degradation',
            'severity': 'medium',
            'message': 'Performance degradation detected',
        })

        self.assertEqual(alert.status, 'open')

        # Acknowledge the alert
        alert.action_acknowledge()
        self.assertEqual(alert.status, 'acknowledged')

        # Start resolution
        alert.action_start_resolution()
        self.assertEqual(alert.status, 'in_progress')

        # Resolve the alert
        alert.action_resolve()
        self.assertEqual(alert.status, 'resolved')

        # Close the alert
        alert.action_close()
        self.assertEqual(alert.status, 'closed')
    def test_create_benchmark(self):
        """Test creating benchmarks"""
        benchmark = self.env['wms.benchmark'].create({
            'name': 'Test Throughput Benchmark',
            'owner_code': 'TTB',
            'category': 'throughput',
            'benchmark_type': 'industry',
            'value': 95.0,
            'unit_of_measure': '%',
            'year': 2024,
        })

        self.assertEqual(benchmark.name, 'Test Throughput Benchmark')
        self.assertEqual(benchmark.owner_code, 'TTB')
        self.assertEqual(benchmark.category, 'throughput')
        self.assertEqual(benchmark.benchmark_type, 'industry')
        self.assertEqual(benchmark.value, 95.0)
        self.assertEqual(benchmark.unit_of_measure, '%')
        self.assertEqual(benchmark.year, 2024)
        self.assertTrue(benchmark.is_current)
    def test_benchmark_with_owner(self):
        """Test benchmark with owner"""
        benchmark = self.env['wms.benchmark'].create({
            'name': 'Owner Benchmark Test',
            'owner_code': 'OBT',
            'category': 'efficiency',
            'benchmark_type': 'historical',
            'value': 85.0,
            'owner_id': self.test_owner.id,
        })

        self.assertEqual(benchmark.owner_id.id, self.test_owner.id)
    def test_performance_report_generation(self):
        """Test performance report generation"""
        report = self.env['wms.performance.report'].create({
            'name': 'Generation Test Report',
            'owner_id': self.test_owner.id,
            'report_type': 'daily',
            'period_start': fields.Date.today(),
            'period_end': fields.Date.today(),
        })

        self.assertEqual(report.status, 'draft')

        # Generate the report
        report.action_generate_report()
        self.assertEqual(report.status, 'generated')

        # Check that generated fields are populated
        self.assertIsNotNone(report.generation_date)
    def test_kpi_trend_calculation(self):
        """Test KPI trend calculation"""
        kpi = self.env['wms.performance.kpi'].create({
            'name': 'Trend Calculation Test',
            'owner_code': 'TCT',
            'category': 'quality',
            'calculation_method': 'average',
            'source_model': 'stock.picking',
            'source_field': 'weight',
            'owner_id': self.test_owner.id,
        })

        # Initially, with no data, the trend should be 0
        self.assertEqual(kpi.trend, 0.0)

        # With current_value = 0 and previous_value = 0, trend is 0
        # In a real scenario, the current_value and previous_value would be calculated
        # based on actual data from the source model

    def test_alert_assignment(self):
        """Test alert assignment to users"""
        alert = self.env['wms.alert'].create({
            'name': 'Assignment Test',
            'alert_type': 'safety_incident',
            'severity': 'critical',
            'message': 'Safety incident detected',
            'assigned_to': self.test_user.id,
        })

        self.assertEqual(alert.assigned_to.id, self.test_user.id)
    def test_dashboard_widget_layout(self):
        """Test dashboard widget layout properties"""
        widget = self.env['wms.dashboard.widget'].create({
            'name': 'Layout Test Widget',
            'owner_code': 'LTW',
            'widget_type': 'chart',
            'data_source': 'wms_labor_task',
            'size_x': 6,
            'size_y': 4,
            'col': 2,
            'row': 1,
        })

        self.assertEqual(widget.size_x, 6)
        self.assertEqual(widget.size_y, 4)
        self.assertEqual(widget.col, 2)
        self.assertEqual(widget.row, 1)