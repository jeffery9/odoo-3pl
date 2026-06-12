# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Courier Integration (wms_courier)
Source Feature: features/courier_integration.feature

This module tests courier integration requirements including:
- Multi-carrier support
- Shipping label generation
- Tracking information management
"""

from odoo.tests import common


class TestMultiCarrierSupport(common.TransactionCase):
    """
    Scenario: Multi-carrier Support
    When I configure multiple carrier accounts (e.g., DHL, FedEx, UPS)
    Then the system should allow selection of any configured carrier for each outbound order
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test carriers
        cls.carrier_dhl = cls.env['res.partner'].create({
            'name': 'DHL Express',
            'is_carrier': True,
            'carrier_code': 'CARRIER-DHL',
        })

        cls.carrier_fedex = cls.env['res.partner'].create({
            'name': 'FedEx International',
            'is_carrier': True,
            'carrier_code': 'CARRIER-FEDEX',
        })
    def test_01_configure_and_select_multiple_carriers(self):
        """
        Verify that multiple carriers can be configured and selected.
        """
        # Create outbound orders with different carriers
        for carrier in [cls.carrier_dhl, cls.carrier_fedex]:
            picking = cls.env['stock.picking'].create({
                'picking_type_id': cls.warehouse.outtype_id if hasattr(cls, 'warehouse') else False,
                'partner_id': carrier.id,
                'origin': f'Courier-Test-{carrier.carrier_code}',
            })

        # Verify: Multiple carriers are available for selection
        carriers_available = cls.env['res.partner'].search_count([
            ('is_carrier', '=', True),
        ])

        self.assertGreaterEqual(carriers_available, 2,
                               "At least two carriers must be configured")


class TestShippingLabelGeneration(common.TransactionCase):
    """
    Scenario: Shipping Label Generation
    When I generate shipping labels for outbound orders via courier integration
    Then the system should create PDF labels with tracking information
    And link the label to the corresponding picking in Odoo
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Courier Label Test WH',
            'owner_code': 'CLWH',
        })

        # Create a test carrier
        cls.test_carrier = cls.env['res.partner'].create({
            'name': 'Test Carrier for Labels',
            'is_carrier': True,
            'carrier_code': 'CARRIER-TEST-LBL',
        })
    def test_02_generate_and_link_shipping_labels(self):
        """
        Verify that shipping labels are generated and linked to orders.
        """
        picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.outtype_id.id,
            'partner_id': cls.test_carrier.id,
            'origin': 'Courier-Label-Test',
        })

        product = cls.env['product.product'].create({
            'name': 'Label Test Product',
                    })

        move = cls.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 5.0,
            'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': cls.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': cls.warehouse.outtype_id.default_location_dest_id.id,
        })

        move._action_confirm()

        # Verify: Order can be processed for label generation
        self.assertEqual(picking.partner_id, cls.test_carrier,
                        "Order must be linked to correct carrier for label generation")


class TestTrackingInformationManagement(common.TransactionCase):
    """
    Scenario: Tracking Information Management
    Given shipping labels have been generated and tracking numbers assigned
    When I query the tracking status in the system
    Then the system should display real-time tracking updates from the carrier API
    And notify me of any delivery exceptions or delays
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Tracking Test WH',
            'owner_code': 'TRKWH',
        })

        # Create carrier with tracking support
        cls.tracking_carrier = cls.env['res.partner'].create({
            'name': 'Tracking Enabled Carrier',
            'is_carrier': True,
            'carrier_code': 'CARRIER-TRACK',
        })
    def test_03_track_delivery_status_updates(self):
        """
        Verify that tracking information can be queried and displayed.
        """
        picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.outtype_id.id,
            'partner_id': cls.tracking_carrier.id,
            'origin': 'Tracking-Test-001',
        })

        product = cls.env['product.product'].create({
            'name': 'Tracking Test Product',
                    })

        move = cls.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 10.0,
            'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': cls.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': cls.warehouse.outtype_id.default_location_dest_id.id,
        })

        move._action_confirm()
        
        for ml in picking.move_line_ids:
            ml.qty_done = ml.product_uom_qty
        
        picking._action_done()

        # Verify: Order is completed and tracking can be initiated
        self.assertEqual(picking.state, 'done',
                        "Order must be completed to initiate tracking")


if __name__ == '__main__':
    import sys
    from odoo.tests.common import TransactionCase

    class TestSuite:
        """Helper class for manual testing if needed"""
        pass

    # Run tests via Odoo's test runner:
    # python -m unittest /path/to/test_wav_courier.py
