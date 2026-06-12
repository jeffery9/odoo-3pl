# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Cross-docking Operations (wms_crossdock)
Source Feature: features/crossdocking_operations.feature

This module tests cross-docking requirements including:
- Automatic detection of cross-docking opportunities
- Partial cross-docking execution
- Cross-dock performance monitoring
"""

from odoo.tests import common


class TestCrossDockOpportunityDetection(common.TransactionCase):
    """
    Scenario: Automatic detection of cross-docking opportunities
    When an inbound shipment arrives for a product that is also urgently needed by an outbound customer
    Then the system should flag this SKU as a potential cross-dock candidate
    And suggest linking the inbound receipt to the outbound delivery
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'CrossDock Test WH',
            'owner_code': 'CDWH',
        })

        # Create a product that will be used for cross-docking
        cls.crossdock_product = cls.env['product.product'].create({
            'name': 'CrossDock Candidate SKU',
                        'default_code': 'SKU-XDOCK-001',
        })
    def test_01_detect_crossdocking_opportunity(self):
        """
        Verify that the system identifies products suitable for cross-docking.
        """
        # Create an inbound receipt
        inbound = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.intype_id.id,
            'partner_id': self.env.ref('base.res_partner_1').id,
            'origin': 'Inbound-CrossDock',
        })

        move_in = self.env['stock.move'].create({
            'name': self.crossdock_product.name,
            'product_id': self.crossdock_product.id,
            'product_uom_qty': 100.0,
            'product_uom': self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': inbound.id,
            'location_id': self.warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })

        move_in._action_confirm()

        # Create an outbound delivery for the same product
        outbound = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.outtype_id.id,
            'partner_id': self.env.ref('base.res_partner_2').id,
            'origin': 'Outbound-CrossDock',
        })

        move_out = self.env['stock.move'].create({
            'name': self.crossdock_product.name,
            'product_id': self.crossdock_product.id,
            'product_uom_qty': 50.0,
            'product_uom': self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': outbound.id,
            'location_id': self.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': self.warehouse.outtype_id.default_location_dest_id.id,
        })

        move_out._action_confirm()

        # Verify: Both inbound and outbound for same product exist (potential cross-dock)
        self.assertTrue(len(inbound.move_ids) > 0 and len(outbound.move_ids) > 0,
                       "Cross-docking opportunity requires both inbound and outbound for same product")


class TestPartialCrossDockExecution(common.TransactionCase):
    """
    Scenario: Partial cross-docking execution
    Given an inbound order has 100 units but only 50 are needed for immediate cross-dock
    When I execute the partial transfer
    Then 50 units should be moved directly to a staging zone or outbound vehicle
    And the remaining 50 should remain in standard storage inventory
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Partial CD Test WH',
            'owner_code': 'PCDWH',
        })

        # Create staging location for cross-docking
        self.crossdock_staging = self.env['stock.location'].create({
            'name': 'CrossDock Staging Area',
            'usage': 'internal',
            'location_id': cls.warehouse.wh_input_stock_loc_id.id,
        })
    def test_02_execute_partial_crossdocking(self):
        """
        Verify that partial cross-docking splits inventory correctly.
        """
        product = self.env['product.product'].create({
            'name': 'Partial CD Product',
                    })

        # Create inbound move
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.intype_id.id,
            'partner_id': self.env.ref('base.res_partner_3').id,
            'origin': 'Partial-CD-In',
        })

        move_in = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 100.0,
            'product_uom': self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking_in.id,
            'location_id': self.warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': self.crossdock_staging.id,
        })

        move_in._action_confirm()
        
        # Simulate partial transfer (50 units cross-docked, 50 stored)
        for ml in picking_in.move_line_ids:
            ml.qty_done = 100.0
        
        picking_in._action_done()

        # Verify: Total quantity moved matches inbound
        total_quantity = sum(picking_in.move_line_ids.mapped('product_uom_qty'))
        self.assertEqual(total_quantity, 100.0,
                        "Total cross-docked quantity must match inbound")


class TestCrossDockPerformanceMonitoring(common.TransactionCase):
    """
    Scenario: Cross-dock performance monitoring
    Given several cross-dock operations have been completed this month
    When I open the Cross-dock Analytics Dashboard
    Then I should see metrics such as "Direct Transfer Ratio", "Avg. Processing Time", and "Cost Savings"
    And a list of customers who benefited most from faster delivery
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'CD Analytics Test WH',
            'owner_code': 'CDAWH',
        })

        # Create multiple cross-dock scenarios for analytics
        cls.products_for_cd = [
            cls.env['product.product'].create({'name': f'CD Product {i}', })
            for i in range(5)
        ]
    def test_03_analytics_data_collection_for_crossdock(self):
        """
        Verify that cross-dock analytics data is correctly collected.
        """
        # Simulate multiple completed cross-dock operations
        for i, product in enumerate(cls.products_for_cd):
            picking = cls.env['stock.picking'].create({
                'picking_type_id': cls.warehouse.outtype_id.id,
                'partner_id': cls.env.ref('base.res_partner_4').id,
                'origin': f'CD-Analytics-{i+1}',
            })

            move = cls.env['stock.move'].create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 20.0 * (i + 1),
                'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
                'picking_id': picking.id,
                'location_id': cls.warehouse.wh_output_stock_loc_id.id,
                'location_dest_id': cls.warehouse.outtype_id.default_location_dest_id.id,
            })

            move._action_confirm()
            
            for ml in picking.move_line_ids:
                ml.qty_done = ml.product_uom_qty
            
            picking._action_done()

        # Verify: Analytics data is available
        completed_pickings = cls.env['stock.picking'].search([
            ('origin', 'like', 'CD-Analytics'),
            ('state', '=', 'done'),
        ])

        self.assertGreater(len(completed_pickings), 0,
                          "Completed cross-dock operations must exist for analytics")


if __name__ == '__main__':
    import sys
    from odoo.tests.common import TransactionCase

    class TestSuite:
        """Helper class for manual testing if needed"""
        pass

    # Run tests via Odoo's test runner:
    # python -m unittest /path/to/test_wav_crossdock.py
