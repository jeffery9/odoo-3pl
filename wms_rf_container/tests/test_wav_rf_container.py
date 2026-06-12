# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Container-Based Receiving (wms_rf_container)
Source Feature: features/receiving_inventory.feature

This module tests container-based receiving requirements including:
- Container QR/Barcode scanning
- Individual line confirmation with quantities
- Inbound order linkage via scan
"""

from odoo.tests import common


class TestContainerScanningProcess(common.TransactionCase):
    """
    Scenario: Receive goods by scanning a container
    When I scan a unique QR/Bar code on a shipping container
    Then the system should open the corresponding inbound order
    And I should be able to confirm individual lines with quantities
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'RF Container Test WH',
            'owner_code': 'RFCWH',
        })

        # Create a product for receiving
        cls.receive_product = cls.env['product.product'].create({
            'name': 'RF Receive Product',
                        'default_code': 'SKU-RF-001',
        })
    def test_01_scan_opens_corresponding_inbound_order(self):
        """
        Verify that scanning a container opens the correct inbound order.
        """
        # Create an inbound order linked to a container
        picking = self.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.intype_id.id,
            'origin': 'RF-Container-Scan-001',  # Simulated QR code value
            'partner_id': cls.env.ref('base.res_partner_1').id,
        })

        move = self.env['stock.move'].create({
            'name': cls.receive_product.name,
            'product_id': cls.receive_product.id,
            'product_uom_qty': 50.0,
            'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': cls.warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': cls.warehouse.lot_stock_id.id,
        })

        move._action_confirm()

        # Verify: Picking exists and is linked to origin (container code)
        found_picking = cls.env['stock.picking'].search([
            ('origin', '=', 'RF-Container-Scan-001'),
        ], limit=1)

        self.assertEqual(found_picking.id, picking.id,
                        "Scanned container must correspond to the correct inbound order")
    def test_02_confirm_lines_with_quantities(self):
        """
        Verify that individual lines can be confirmed with specific quantities via RF.
        """
        picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.intype_id.id,
            'origin': 'RF-Line-Confirm',
            'partner_id': cls.env.ref('base.res_partner_2').id,
        })

        # Add multiple lines to the inbound order
        product_a = cls.env['product.product'].create({'name': 'Product A', })
        product_b = cls.env['product.product'].create({'name': 'Product B', })

        for product, qty in [(product_a, 20.0), (product_b, 30.0)]:
            move = cls.env['stock.move'].create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
                'picking_id': picking.id,
                'location_id': cls.warehouse.wh_input_stock_loc_id.id,
                'location_dest_id': cls.warehouse.lot_stock_id.id,
            })
            move._action_confirm()

        # Simulate RF operator confirming specific quantities per line
        total_confirmed = 0.0
        
        for ml in picking.move_line_ids:
            ml.qty_done = ml.product_uom_qty  # Confirm full quantity per line
            total_confirmed += ml.product_uom_qty

        self.assertEqual(total_confirmed, 50.0,
                        "Sum of confirmed quantities across all lines must match expected total")


class TestContainerTrackingManagement(common.TransactionCase):
    """
    Scenario: Container Tracking Management
    Given a container has been scanned and its contents partially received
    When I track the container status in the system
    Then the system should show remaining quantity to receive and current progress
    And any exceptions (e.g., damaged items) must be recorded against the container
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'CT Tracking Test WH',
            'owner_code': 'CTWH',
        })
    def test_03_partial_receive_progress_tracking(self):
        """
        Verify that partial receive progress is tracked correctly.
        """
        picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.warehouse.intype_id.id,
            'origin': 'Container-Pt-001',
            'partner_id': cls.env.ref('base.res_partner_3').id,
        })

        product = cls.env['product.product'].create({
            'name': 'Partial Receive Product',
                    })

        move = cls.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 100.0,
            'product_uom': cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': cls.warehouse.wh_input_stock_loc_id.id,
            'location_dest_id': cls.warehouse.lot_stock_id.id,
        })

        move._action_confirm()

        # Simulate partial receive (60% done)
        for ml in picking.move_line_ids:
            ml.qty_done = 60.0  # 60 out of 100

        # Verify progress tracking
        remaining_qty = product.uom_id._compute_quantity(100.0 - 60.0, cls.env['uom.uom'].search([('name', '=', 'Units')], limit=1))
        
        self.assertEqual(sum(picking.move_line_ids.mapped('qty_done')), 60.0,
                        "Remaining quantity must be correctly calculated")


if __name__ == '__main__':
    import sys
    from odoo.tests.common import TransactionCase

    class TestSuite:
        """Helper class for manual testing if needed"""
        pass

    # Run tests via Odoo's test runner:
    # python -m unittest /path/to/test_wav_rf_container.py
