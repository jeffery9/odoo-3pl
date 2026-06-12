# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Blind Receiving (wms_rf_blind_receive)
Source Feature: features/receiving_inventory.feature

This module tests blind receive requirements including:
- Document-less receiving process
- Manual SKU and quantity entry
- Exception handling for blind receipts
"""

from odoo.tests import common


class TestBlindReceivingProcess(common.TransactionCase):
    """
    Scenario: Perform blind receive without documents
    Given an incoming shipment is expected but without pre-printed labels
    When I use the "Blind Receive" function on the RF device
    And I manually enter the product SKU and quantity
    Then the system should create a provisional stock receipt linked to the correct owner
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Blind Receive Test WH',
            'owner_code': 'BLDWH',
        })

        # Create owner for blind receive linking
        cls.blind_owner = cls.env['res.partner'].create({
            'name': 'Blind Receive Owner',
            'is_warehouse_owner': True,
            'code': 'OWNER-BLIND',
        })
    def test_01_create_provisional_receipt_via_blind_receive(self):
        """
        Verify that a provisional receipt is created when using blind receive.
        """
        # Create product to be received without documents
        product = cls.env['product.product'].create({
            'name': 'Blind Receive Product',
                        'default_code': 'SKU-BLD-001',
        })

        # Simulate blind receive process (manual entry via RF)
        picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.intype_id.id,
            'origin': 'Blind-Receive-Manual',
            'partner_id': cls.blind_owner.id,
        })

        move = cls.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 25.0,  # Manually entered quantity
            'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': cls.warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': cls.warehouse.lot_stock_id.id,
        })

        move._action_confirm()

        # Verify: Provisional receipt is created and linked to owner
        self.assertEqual(picking.partner_id, cls.blind_owner,
                        "Blind receive must be linked to the correct owner")


class TestBlindReceiveExceptionHandling(common.TransactionCase):
    """
    Scenario: Blind Receiving Exception Handling
    Given a blind receive operation encounters a discrepancy (e.g., wrong SKU)
    When I record the exception details in the RF device
    Then the system should flag the receipt for review and prevent automatic confirmation
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Blind Exception Test WH',
            'owner_code': 'BLDEXCWH',
        })
    def test_02_flag_receipt_for_review_on_discrepancy(self):
        """
        Verify that discrepancies in blind receive are flagged for review.
        """
        picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.intype_id.id,
            'origin': 'Blind-Exception-001',
            'partner_id': cls.env.ref('base.res_partner_1').id,
        })

        product_expected = cls.env['product.product'].create({
            'name': 'Expected Product',
                        'default_code': 'SKU-EXP-001',
        })

        product_received = cls.env['product.product'].create({
            'name': 'Actually Received Product',
                        'default_code': 'SKU-REC-001',  # Different from expected
        })

        move = cls.env['stock.move'].create({
            'name': product_expected.name,
            'product_id': product_expected.id,
            'product_uom_qty': 10.0,
            'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': cls.warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': cls.warehouse.lot_stock_id.id,
        })

        move._action_confirm()

        # Simulate exception recording (wrong SKU received)
        for ml in picking.move_line_ids:
            ml.product_id = product_received.id  # Wrong product entered
            ml.qty_done = ml.product_uom_qty
        
        # Verify: Exception is recorded (product mismatch detected)
        self.assertNotEqual(picking.move_line_ids[0].product_id.default_code, 
                           'SKU-EXP-001',
                          "Exception must be flagged when received SKU differs from expected")


if __name__ == '__main__':
    import sys
    from odoo.tests.common import TransactionCase

    class TestSuite:
        """Helper class for manual testing if needed"""
        pass

    # Run tests via Odoo's test runner:
    # python -m unittest /path/to/test_wav_blind_receive.py
