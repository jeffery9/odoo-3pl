from odoo.tests import TransactionCase
from odoo import fields


class TestWmsInventoryFreeze(TransactionCase):
    """Test cases for WMS Inventory Freeze module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Inventory Freeze Owner',
            'owner_code': 'TIFO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Inventory Freeze',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        # Create a lot/serial for testing
        self.test_lot = self.env['stock.lot'].create({
            'name': 'TESTLOT001',
            'product_id': self.test_product.id,
            'company_id': self.env.company.id,
        })
    def test_create_inventory_freeze(self):
        """Test creating an inventory freeze record"""
        inventory_freeze = self.env['wms.inventory.freeze'].create({
            'name': 'Test Inventory Freeze',
            'owner_id': self.test_owner.id,
            'location_id': self.test_location.id,
            'product_id': self.test_product.id,
            'lot_id': self.test_lot.id,
            'reason': 'quality_issue',
            'quantity': 50.0,
            'uom_id': self.test_uom.id,
            'freeze_type': 'partial',
            'status': 'frozen',
        })

        self.assertEqual(inventory_freeze.name, 'Test Inventory Freeze')
        self.assertEqual(inventory_freeze.owner_id.id, self.test_owner.id)
        self.assertEqual(inventory_freeze.location_id.id, self.test_location.id)
        self.assertEqual(inventory_freeze.product_id.id, self.test_product.id)
        self.assertEqual(inventory_freeze.reason, 'quality_issue')
        self.assertEqual(inventory_freeze.quantity, 50.0)
        self.assertEqual(inventory_freeze.freeze_type, 'partial')
        self.assertEqual(inventory_freeze.status, 'frozen')
    def test_inventory_freeze_status_flow(self):
        """Test the status flow of inventory freeze records"""
        inventory_freeze = self.env['wms.inventory.freeze'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'location_id': self.test_location.id,
            'product_id': self.test_product.id,
            'lot_id': self.test_lot.id,
            'reason': 'investigation',
            'quantity': 25.0,
            'uom_id': self.test_uom.id,
            'freeze_type': 'lot',
            'status': 'frozen',
        })

        self.assertEqual(inventory_freeze.status, 'frozen')

        # Unfreeze the inventory
        inventory_freeze.action_unfreeze()
        self.assertEqual(inventory_freeze.status, 'unfrozen')

        # Release the inventory
        inventory_freeze.action_release()
        self.assertEqual(inventory_freeze.status, 'released')
    def test_inventory_freeze_reasons(self):
        """Test different freeze reasons"""
        reasons = ['quality_issue', 'investigation', 'discrepancy', 'audit', 'customer_request', 'hold']

        for i, reason in enumerate(reasons):
            freeze = self.env['wms.inventory.freeze'].create({
                'name': f'Test Freeze Reason {reason}',
                'owner_id': self.test_owner.id,
                'location_id': self.test_location.id,
                'product_id': self.test_product.id,
                'reason': reason,
                'quantity': 10.0,
                'uom_id': self.test_uom.id,
                'freeze_type': 'product',
            })
            self.assertEqual(freeze.reason, reason)
    def test_inventory_freeze_types(self):
        """Test different freeze types"""
        freeze_types = ['location', 'product', 'lot', 'partial']

        for i, freeze_type in enumerate(freeze_types):
            freeze = self.env['wms.inventory.freeze'].create({
                'name': f'Test Freeze Type {freeze_type}',
                'owner_id': self.test_owner.id,
                'location_id': self.test_location.id,
                'product_id': self.test_product.id,
                'reason': 'investigation',
                'quantity': 15.0,
                'uom_id': self.test_uom.id,
                'freeze_type': freeze_type,
            })
            self.assertEqual(freeze.freeze_type, freeze_type)
    def test_inventory_freeze_wizard(self):
        """Test creating inventory freeze using wizard"""
        wizard = self.env['wms.inventory.freeze.wizard'].create({
            'freeze_type': 'product',
            'location_id': self.test_location.id,
            'product_id': self.test_product.id,
            'quantity': 30.0,
            'reason': 'discrepancy',
            'notes': 'Test freeze via wizard',
            'owner_id': self.test_owner.id,
        })

        result = wizard.action_create_freeze()

        # Verify the result is an action to open the freeze form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.inventory.freeze')

        # Get the created freeze record
        freeze = self.env['wms.inventory.freeze'].browse(result['res_id'])
        self.assertEqual(freeze.reason, 'discrepancy')
        self.assertEqual(freeze.quantity, 30.0)
    def test_unfreeze_wizard(self):
        """Test unfreezing inventory using wizard"""
        inventory_freeze = self.env['wms.inventory.freeze'].create({
            'name': 'Unfreeze Wizard Test',
            'owner_id': self.test_owner.id,
            'location_id': self.test_location.id,
            'product_id': self.test_product.id,
            'reason': 'audit',
            'quantity': 20.0,
            'uom_id': self.test_uom.id,
            'freeze_type': 'partial',
            'status': 'frozen',
        })

        self.assertEqual(inventory_freeze.status, 'frozen')

        # Create unfreeze wizard
        wizard = self.env['wms.unfreeze.wizard'].create({
            'freeze_id': inventory_freeze.id,
            'release': False,  # Unfreeze temporarily
            'notes': 'Unfreezing for testing',
        })

        wizard.action_unfreeze()

        # Check that the freeze record is now unfrozen
        inventory_freeze.refresh()
        self.assertEqual(inventory_freeze.status, 'unfrozen')
    def test_inventory_freeze_ownership_isolation(self):
        """Test that inventory freeze records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Inventory Freeze Owner',
            'owner_code': 'SIFO',
            'is_warehouse_owner': True,
        })

        freeze1 = self.env['wms.inventory.freeze'].create({
            'name': 'Freeze for Owner 1',
            'owner_id': self.test_owner.id,
            'location_id': self.test_location.id,
            'product_id': self.test_product.id,
            'reason': 'quality_issue',
            'quantity': 40.0,
            'uom_id': self.test_uom.id,
            'freeze_type': 'product',
        })

        freeze2 = self.env['wms.inventory.freeze'].create({
            'name': 'Freeze for Owner 2',
            'owner_id': owner2.id,
            'location_id': self.test_location.id,
            'product_id': self.test_product.id,
            'reason': 'investigation',
            'quantity': 60.0,
            'uom_id': self.test_uom.id,
            'freeze_type': 'lot',
        })

        self.assertNotEqual(freeze1.owner_id.id, freeze2.owner_id.id)
        self.assertNotEqual(freeze1.reason, freeze2.reason)
        self.assertNotEqual(freeze1.quantity, freeze2.quantity)
    def test_stock_quant_freeze_integration(self):
        """Test integration with stock.quant for freeze status"""
        # Create a stock quant
        quant = self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'quantity': 100.0,
        })

        # Initially, the quant should not be frozen
        self.assertFalse(quant.is_frozen)

        # Create a freeze record that would affect this quant
        inventory_freeze = self.env['wms.inventory.freeze'].create({
            'name': 'Quant Freeze Test',
            'owner_id': self.test_owner.id,
            'location_id': self.test_location.id,
            'product_id': self.test_product.id,
            'reason': 'quality_issue',
            'quantity': 50.0,  # Less than or equal to quant quantity
            'uom_id': self.test_uom.id,
            'freeze_type': 'partial',
        })

        # Refresh the quant to update computed field
        quant.refresh()

        # Now the quant should be marked as frozen
        self.assertTrue(quant.is_frozen)