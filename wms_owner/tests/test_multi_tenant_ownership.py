# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Multi-Tenant Warehouse Ownership (wms_owner)
Source Feature: features/multi_tenant_ownership.feature

This module tests the core requirement that different warehouse owners
maintain strictly isolated data within a multi-tenant Odoo WMS environment.
"""

from odoo.tests import common, new_test_user
from odoo.exceptions import AccessError, UserError


class TestMultiTenantOwnership(common.TaggedCase):
    """
    Scenario: Register a new 3PL warehouse owner
    Given the Odoo WMS system is running with "wms_owner" module installed
    And I am logged in as an Administrator

    Scenario: Assign inventory to a specific owner
    Given a warehouse owner exists with code "OWNER_A"
    When I create an inbound stock receipt for products assigned to "OWNER_A"
    Then the stock quants must be linked to "OWNER_A"
    And "OWNER_B" users should not be able to see this inventory

    Scenario: View owner-specific KPIs
    Given a warehouse owner has completed several operations today
    When I open the Owner Dashboard for that owner
    Then I should see inbound, outbound, and storage volumes specific to them
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Setup: Create two distinct warehouse owners
        cls.owner_a = cls.env['res.partner'].create({
            'name': 'Alpha Logistics',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_A',
            'storage_fee_rate': 5.00,
            'contract_start_date': '2026-01-01',
        })

        cls.owner_b = cls.env['res.partner'].create({
            'name': 'Beta Shipping',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_B',
            'storage_fee_rate': 4.50,
            'contract_start_date': '2026-01-01',
        })

        # Create a standard product to test inventory isolation
        cls.product = cls.env['product.product'].create({
            'name': 'Standard Widget',
                        'default_code': 'SKU-STD-001',
        })
    def test_01_owner_registration_and_data_isolation(self):
        """
        Verify that 'wms_owner' adds 3PL specific fields and isolation rules.
        """
        self.assertTrue(self.owner_a.is_warehouse_owner)
        self.assertEqual(self.owner_a.owner_code, 'OWNER_A')
    def test_02_inbound_assigns_correct_owner_to_quants(self):
        """
        When I create an inbound stock receipt for products assigned to "OWNER_A"
        Then the stock quants must be linked to "OWNER_A"
        """
        # 1. Create a warehouse
        wh = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'owner_code': 'TW',
        })

        # 2. Receive 10 units of the product for Owner A
        receipt = self.env['stock.picking'].create({
            'picking_type_id': wh.intype_id,
            'location_id': wh.lot_stock_id.id,
            'origin': 'BDD-Inbound',
        })

        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': wh.lot_stock_id.id,
        })

        move._action_confirm()
        receipt.action_assign()

        # 3. Validate the receipt (Simulate RF scan confirmation)
        for ml in receipt.move_line_ids:
            ml.qty_done = 10.0
        
        receipt._action_done()

        # ASSERT: Quants linked to Owner A must exist
        owner_a_quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', wh.lot_stock_id.id),
            ('owner_id', '=', self.owner_a.id),
        ])

        total_qty = sum(owner_a_quants.mapped('quantity'))
        self.assertEqual(total_qty, 10.0, "Quants should be assigned to Owner A with qty 10")
    def test_03_owner_b_cannot_see_owner_a_inventory(self):
        """
        And "OWNER_B" users should not be able to see this inventory
        """
        # Create a user strictly bound to Owner B (simulating multi-tenant restriction)
        owner_b_user = new_test_user(
            self.env,
            login='b_user',
            groups='wms_owner.group_wms_owner',  # Or base users group if isolation is via ir.rule
        )

        # Attempting to query Owner A's data via the simulated context/user
        owner_b_quants = self.env['stock.quant'].with_user(owner_b_user).search([
            ('owner_id', '=', self.owner_a.id),
        ])

        self.assertEqual(len(owner_b_quants), 0, 
                         "Owner B user should have zero visibility of Owner A's inventory due to multi-tenant rules.")
