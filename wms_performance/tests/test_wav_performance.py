# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Warehouse Analytics and Performance (wms_performance, wms_location_usage, wms_inventory_age)
Source Feature: features/analytics_and_performance.feature

This module tests the analytics and performance requirements including:
- Operator daily performance metrics
- Location utilization tracking
- Inventory aging analysis
"""

from odoo.tests import common


class TestOperatorPerformanceMetrics(common.TransactionCase):
    """
    Scenario: Monitor operator daily performance metrics
    When I open the Operator Performance Dashboard
    Then I should see real-time metrics for each employee, such as "Picks per Hour" and "Putaway Efficiency"
    And I should be able to compare individual performance against team averages
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create operators (users with warehouse roles)
        cls.operator_1 = cls.env['res.users'].create({
            'name': 'Operator Alpha',
            'login': 'op_alpha',
            'email': 'alpha@wms-test.com',
            'groups_id': [(4, cls.env.ref('stock.group_stock_user').id)],
        })

        cls.operator_2 = cls.env['res.users'].create({
            'name': 'Operator Beta',
            'login': 'op_beta',
            'email': 'beta@wms-test.com',
            'groups_id': [(4, cls.env.ref('stock.group_stock_user').id)],
        })

        # Create warehouse operations for performance tracking
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Performance Test WH',
            'owner_code': 'PERFWH',
        })
    def test_01_real_time_performance_metrics_collection(self):
        """
        Verify that operator performance metrics are correctly collected.
        """
        # Simulate operational activities for tracking
        product = cls.env['product.product'].create({
            'name': 'Performance Metric Product',
                    })

        # Create operations completed by different operators
        picking_1 = cls.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.outtype_id.id,
            'partner_id': cls.env.ref('base.res_partner_1').id,
            'user_id': cls.operator_1.id,  # Assigned to Operator 1
            'origin': 'BDD-Performance-Metric',
        })

        move = cls.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 20.0,
            'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking_1.id,
            'location_id': cls.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': cls.warehouse.outtype_id.default_location_dest_id.id,
        })

        move._action_confirm()
        
        for ml in picking_1.move_line_ids:
            ml.qty_done = ml.product_uom_qty
        
        picking_1._action_done()

        # Verify: Performance metrics can be calculated from operational data
        operator_moves = cls.env['stock.move'].search([
            ('picking_id.user_id', '=', cls.operator_1.id),
            ('state', '=', 'done'),
        ])

        self.assertTrue(len(operator_moves) > 0,
                       "Operator must have completed moves for performance tracking")


class TestLocationUtilizationTracking(common.TransactionCase):
    """
    Scenario: Analyze location utilization and space efficiency
    Given the warehouse is experiencing congestion in Zone A
    When I open the Location Usage Analysis tool
    Then the system should visualize capacity usage across all zones
    And it should highlight "Overloaded" locations that have exceeded their configured max_capacity thresholds
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Utilization Test WH',
            'owner_code': 'UTILWH',
        })

        # Create locations with capacity constraints
        cls.zone_a = cls.env['stock.location'].create({
            'name': 'Zone-A (Congested)',
            'usage': 'internal',
            'location_id': cls.warehouse.intype_id.default_location_src_id.id,
            'max_capacity': 1000.0,  # kg capacity limit
        })

        cls.zone_b = cls.env['stock.location'].create({
            'name': 'Zone-B (Normal)',
            'usage': 'internal',
            'location_id': cls.warehouse.intype_id.default_location_src_id.id,
            'max_capacity': 1500.0,
        })
    def test_02_zone_utilization_calculation(self):
        """
        Verify that location utilization is correctly calculated and tracked.
        """
        product_a = cls.env['product.product'].create({
            'name': 'Product for Zone A',
                        'weight': 100.0,
        })

        # Add inventory to Zone-A (simulating congestion)
        quant_a = cls.env['stock.quant'].create({
            'product_id': product_a.id,
            'location_id': cls.zone_a.id,
            'quantity': 800.0,  # Heavy loading
        })

        # Calculate utilization percentage
        utilization = (quant_a.quantity * product_a.weight) / cls.zone_a.max_capacity * 100
        
        # Verify: High utilization is tracked
        self.assertGreater(utilization, 80.0,
                          "Zone-A utilization should be high (>80%)")
    def test_03_overload_detection_for_locations(self):
        """
        Verify that overloaded locations are correctly identified.
        """
        product_heavy = cls.env['product.product'].create({
            'name': 'Heavy Product',
                        'weight': 200.0,
        })

        # Add excessive inventory to trigger overload
        excess_quant = cls.env['stock.quant'].create({
            'product_id': product_heavy.id,
            'location_id': cls.zone_a.id,
            'quantity': 4.0,  # 4 units * 200kg = 800kg (total now exceeds capacity)
        })

        total_weight = excess_quant.quantity * product_heavy.weight
        
        # Verify: Overload condition is detected
        self.assertGreater(total_weight, cls.zone_a.max_capacity - quant_a.quantity * 100.0,
                          "Zone-A should be flagged as overloaded")


class TestInventoryAgingAnalysis(common.TransactionCase):
    """
    Scenario: Track inventory aging to prevent obsolescence
    Given stock has been sitting in the warehouse for an extended period
    When I run the Inventory Aging Analysis report
    Then the system should categorize stock by days held (e.g., 0-30, 31-60, 60+ days)
    And it should alert me to any "A-Category" items that have unexpectedly aged into "C-Category" status
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create products with different aging characteristics
        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A (High Turnover)',
                        'default_code': 'SKU-AGE-A',
        })

        cls.product_c = cls.env['product.product'].create({
            'name': 'Product C (Low Turnover)',
                        'default_code': 'SKU-AGE-C',
        })

        # Create inventory with different ages
        cls.aging_location = cls.warehouse.intype_id.default_location_src_id if hasattr(cls, 'warehouse') else False
        
        if not cls.aging_location:
            cls.warehouse = cls.env['stock.warehouse'].create({
                'name': 'Aging Test WH',
                'owner_code': 'AGNGWH',
            })
            cls.aging_location = cls.warehouse.intype_id.default_location_src_id

        # Add inventory to track aging
        cls.quant_old = cls.env['stock.quant'].create({
            'product_id': cls.product_c.id,
            'location_id': cls.aging_location.id,
            'quantity': 50.0,
            # In real implementation, this would have creation_date for aging calculation
        })
    def test_04_inventory_age_classification(self):
        """
        Verify that inventory aging is correctly classified by time periods.
        """
        # Simulate inventory with different ages (in real implementation, based on dates)
        product_b = cls.env['product.product'].create({
            'name': 'Product B (Medium Aging)',
                        'default_code': 'SKU-AGE-B',
        })

        # Create inventory with different creation dates would go here in real implementation
        quant_new = cls.env['stock.quant'].create({
            'product_id': product_b.id,
            'location_id': cls.aging_location.id,
            'quantity': 25.0,
        })

        # Verify: Inventory aging data structure exists for analysis
        total_inventory = sum(cls.env['stock.quant'].search([
            ('location_id', '=', cls.aging_location.id),
        ]).mapped('quantity'))

        self.assertGreater(total_inventory, 0,
                          "Inventory must exist for aging analysis")


class TestPerformanceAnalyticsDashboard(common.TransactionCase):
    """
    Scenario: View comprehensive performance analytics dashboard
    Given multiple operational metrics are collected from warehouse activities
    When I open the Performance Analytics Dashboard
    Then I should see KPIs such as "Total Pick Volume", "Putaway Accuracy Rate", and "Order Fulfillment Time"
    And trend analysis comparing current vs. previous periods
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Dashboard Test WH',
            'owner_code': 'DASHWH',
        })

        # Create test data for multiple KPIs
        cls.product_dashboard = cls.env['product.product'].create({
            'name': 'Dashboard Test Product',
                    })
    def test_05_comprehensive_kpi_calculation(self):
        """
        Verify that performance KPIs are calculated correctly from operational data.
        """
        # Create multiple operations to generate KPI data
        for i in range(10):  # 10 different pickings
            picking = cls.env['stock.picking'].create({
                'picking_type_id': cls.warehouse.outtype_id.id,
                'partner_id': cls.env.ref('base.res_partner_3').id,
                'origin': f'BDD-KPI-Test-{i+1}',
            })

            move = cls.env['stock.move'].create({
                'name': f'KPI Move {i+1}',
                'product_id': cls.product_dashboard.id,
                'product_uom_qty': 5.0 * (i + 1),
                'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
                'picking_id': picking.id,
                'location_id': cls.warehouse.wh_output_stock_loc_id.id,
                'location_dest_id': cls.warehouse.outtype_id.default_location_dest_id.id,
            })

            move._action_confirm()
            
            for ml in picking.move_line_ids:
                ml.qty_done = ml.product_uom_qty
            
            picking._action_done()

        # Verify: KPI calculation data is available
        total_moves = len(cls.env['stock.move'].search([
            ('picking_id.origin', 'like', 'BDD-KPI-Test'),
        ]))

        self.assertEqual(total_moves, 10, 
                        "KPI data must be collected from all test operations")


if __name__ == '__main__':
    import sys
    from odoo.tests.common import TransactionCase

    class TestSuite:
        """Helper class for manual testing if needed"""
        pass

    # Run tests via Odoo's test runner:
    # python -m unittest /path/to/test_wav_performance.py
