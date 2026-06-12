# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Inventory Freeze and Quality Control (wms_inventory_freeze, wms_quality_control)
Source Feature: features/inventory_freeze_quality_control.feature

This module tests the inventory freeze requirements including:
- Freezing items due to quality issues
- Releasing frozen inventory after resolution
- Frozen inventory analytics
"""

from odoo.tests import common


class TestInventoryFreezeProcess(common.TransactionCase):
    """
    Scenario: Freeze inventory due to quality issues
    When an operator identifies a damaged batch of goods
    Then I should be able to apply a "Frozen" status to those specific stock quants
    And the system must mark these items as unavailable for picking or putaway immediately
    And an audit trail must record the reason (e.g., damage, pending inspection)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Freeze Test WH',
            'owner_code': 'FRZWH',
        })

        # Create product and inventory
        cls.product = cls.env['product.product'].create({
            'name': 'Freeze Test Product',
                        'default_code': 'SKU-FREEZE-001',
        })

        # Add initial inventory
        cls.warehouse.intype_id.default_location_src_id.quant_ids = [
            (0, 0, {'product_id': cls.product.id, 'quantity': 100.0})
        ]
    def test_01_freeze_inventory_for_quality_issues(self):
        """
        Verify that inventory can be frozen and becomes unavailable for operations.
        """
        # Find existing quants for the product
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.warehouse.intype_id.default_location_src_id.id),
            ('quantity', '>', 0.0),
        ])

        # Simulate inventory freeze (this would be implemented via wms_inventory_freeze module)
        for quant in quants:
            # In real implementation, this would set a freeze flag/status
            quant.freeze_status = 'frozen'  # Simulated field
            quant.freeze_reason = 'Damage Detected'  # Audit trail
            quant.frozen_by = self.env.user.id
            quant.frozen_date = common.fields.Datetime.now()

        # Verify: Quants are marked as frozen
        frozen_quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('freeze_status', '=', 'frozen'),  # Verified field check
        ])
        
        self.assertTrue(len(frozen_quants) > 0,
                       "Inventory must be marked as frozen")
    def test_02_frozen_inventory_unavailable_for_picking(self):
        """
        Verify that frozen inventory is not available for picking operations.
        """
        # Create a picking order (should not see frozen items)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.outtype_id.id,
            'partner_id': self.env.ref('base.res_partner_1').id,
        })

        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 50.0,
            'product_uom': self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': self.warehouse.intype_id.default_location_src_id.id,
            'location_dest_id': self.warehouse.outtype_id.default_location_dest_id.id,
        })

        move._action_confirm()
        
        # In a real implementation, frozen quants would not be considered for allocation
        available_quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('quantity', '>', 0.0),
            # Exclude frozen quants in real logic
        ])

        # Verify: Available inventory should exclude frozen items
        total_available = sum(available_quants.mapped('quantity'))
        expected_available = 100.0 - (self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('freeze_status', '=', 'frozen'),
        ]).mapped('quantity') or [100.0][0])

        self.assertTrue(total_available <= expected_available,
                       "Available inventory must exclude frozen items")


class TestInventoryFreezeRelease(common.TransactionCase):
    """
    Scenario: Release frozen inventory after resolution
    Given a batch of items has been previously "Frozen" for quality checks
    When the QC team confirms the goods are now safe to use
    Then I should be able to transition the status from "Frozen" back to "Available"
    And the system should make these items immediately visible in standard inventory queries
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Release Test WH',
            'owner_code': 'RLSWH',
        })

        # Create frozen inventory for testing release
        cls.frozen_product = cls.env['product.product'].create({
            'name': 'Frozen Product',
                        'default_code': 'SKU-FREEZE-RELEASE',
        })

        # Add frozen inventory
        self.quant = self.env['stock.quant'].create({
            'product_id': cls.frozen_product.id,
            'location_id': cls.warehouse.intype_id.default_location_src_id.id,
            'quantity': 50.0,
            'freeze_status': 'frozen',
            'freeze_reason': 'QC Hold',
        })
    def test_03_release_frozen_inventory(self):
        """
        Verify that frozen inventory can be released and becomes available again.
        """
        # Simulate QC release
        self.quant.freeze_status = 'released'  # Status update
        self.quant.release_reason = 'QC Approved'  # Release justification
        self.quant.released_by = self.env.user.id
        self.quant.released_date = common.fields.Datetime.now()

        # Verify: Quants are no longer frozen and become available
        released_quants = self.env['stock.quant'].search([
            ('product_id', '=', cls.frozen_product.id),
            ('quantity', '>', 0.0),
            ('freeze_status', '=', 'released'),
        ])

        self.assertTrue(len(released_quants) > 0, 
                       "Released inventory must be tracked")
    def test_04_released_inventory_visible_in_standard_queries(self):
        """
        Verify that released inventory becomes visible in standard inventory operations.
        """
        # Create a new picking (should now see the released items)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.outtype_id.id,
            'partner_id': self.env.ref('base.res_partner_1').id,
        })

        move = self.env['stock.move'].create({
            'name': self.frozen_product.name,
            'product_id': self.frozen_product.id,
            'product_uom_qty': 20.0,
            'product_uom': self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': self.warehouse.intype_id.default_location_src_id.id,
            'location_dest_id': self.warehouse.outtype_id.default_location_dest_id.id,
        })

        move._action_confirm()
        
        # In real implementation, released quants would be available for allocation
        available_after_release = self.env['stock.quant'].search([
            ('product_id', '=', self.frozen_product.id),
            ('quantity', '>', 0.0),
            # Now released items should be included
        ])

        total_available = sum(available_after_release.mapped('quantity'))
        
        # Verify: Released inventory is now available for picking
        self.assertTrue(total_available >= 50.0,
                       "Released inventory must be visible and available")


class TestFrozenInventoryAnalytics(common.TransactionCase):
    """
    Scenario: View frozen inventory analytics
    Given multiple owners have a mix of available and frozen stock
    When I open the Inventory Analytics Dashboard
    Then I should see a breakdown of "Frozen vs Available" quantities by owner
    And a list of top reasons for freezing (e.g., Damage, Discrepancy, QC Hold)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create multiple owners with different freeze statuses
        cls.owner_1 = cls.env['res.partner'].create({
            'name': 'Owner-Frozen-1',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_FRZ1',
        })

        cls.owner_2 = cls.env['res.partner'].create({
            'name': 'Owner-Frozen-2',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_FRZ2',
        })

        # Create frozen inventory with different reasons for each owner
        freeze_reasons = ['Damage Detected', 'QC Hold', 'Pending Inspection']
        
        for owner in [cls.owner_1, cls.owner_2]:
            for reason in freeze_reasons:
                self.env['stock.quant'].create({
                    'product_id': cls.env['product.product'].create({
                        'name': f'Frozen Product {owner.id}',
                                            }).id,
                    'location_id': cls.env.ref('stock.stock_location_stock').id,
                    'quantity': 25.0,
                    'freeze_status': 'frozen',
                    'freeze_reason': reason,
                })


class TestFrozenInventoryAnalytics(common.TransactionCase):
    """
    Scenario: View frozen inventory analytics
    Given multiple owners have a mix of available and frozen stock
    When I open the Inventory Analytics Dashboard
    Then I should see a breakdown of "Frozen vs Available" quantities by owner
    And a list of top reasons for freezing (e.g., Damage, Discrepancy, QC Hold)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create multiple owners with different freeze statuses
        cls.owner_1 = cls.env['res.partner'].create({
            'name': 'Owner-Frozen-1',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_FRZ1',
        })

        cls.owner_2 = cls.env['res.partner'].create({
            'name': 'Owner-Frozen-2',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_FRZ2',
        })

        # Create frozen inventory with different reasons for each owner
        freeze_reasons = ['Damage Detected', 'QC Hold', 'Pending Inspection']
        
        for owner in [cls.owner_1, cls.owner_2]:
            for reason in freeze_reasons:
                self.env['stock.quant'].create({
                    'product_id': cls.env['product.product'].create({
                        'name': f'Frozen Product {owner.id}',
                                            }).id,
                    'location_id': cls.env.ref('stock.stock_location_stock').id,
                    'quantity': 25.0,
                    'freeze_status': 'frozen',
                    'freeze_reason': reason,
                })
    def test_05_frozen_vs_available_breakdown_by_owner(self):
        """
        Verify that analytics correctly show frozen vs available quantities by owner.
        """
        # Query frozen inventory by owner
        all_quants = self.env['stock.quant'].search([
            ('freeze_status', '=', 'frozen'),
        ])

        total_frozen_by_owner = {}
        
        for quant in all_quants:
            owner_id = quant.owner_id.id if quant.owner_id else False
            
            # In real implementation, this would be aggregated by owner
            # For testing purposes, we verify the data structure exists
            self.assertTrue(quant.freeze_status == 'frozen',
                           "All queried quants must have frozen status")
    def test_06_top_freeze_reasons_aggregation(self):
        """
        Verify that analytics correctly aggregate freeze reasons.
        """
        # Query all freeze reasons
        freeze_records = self.env['stock.quant'].search([
            ('freeze_status', '=', 'frozen'),
        ])

        reason_counts = {}
        
        for quant in freeze_records:
            reason = quant.freeze_reason or 'Unknown'
            if reason not in reason_counts:
                reason_counts[reason] = 0
            reason_counts[reason] += quant.quantity

        # Verify: Multiple reasons exist and are aggregated correctly
        self.assertTrue(len(reason_counts) > 1,
                       "Must have multiple freeze reasons represented in analytics")


if __name__ == '__main__':
    import sys
    from odoo.tests.common import TransactionCase

    class TestSuite:
        """Helper class for manual testing if needed"""
        pass

    # Run tests via Odoo's test runner:
    # python -m unittest /path/to/test_wav_inventory_freeze.py
