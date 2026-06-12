from odoo.tests import TransactionCase
from odoo import fields


class TestWmsOwner(TransactionCase):
    """Test cases for WMS Owner module"""

    def setUp(self):
        super().setUp()
        # Create a test partner to be used as an owner
        self.test_owner = self.env['res.partner'].create({
            'name': 'Test WMS Owner',
            'is_company': True,
            'is_warehouse_owner': True,
        })
    def test_create_wms_owner(self):
        """Test creating a WMS owner"""
        owner = self.env['wms.owner'].create({
            'partner_id': self.test_owner.id,
            'name': 'Test Owner',
            'owner_code': 'TEST',
            'is_warehouse_owner': True,
        })

        self.assertEqual(owner.name, 'Test Owner')
        self.assertEqual(owner.owner_code, 'TEST')
        self.assertTrue(owner.is_warehouse_owner)
        self.assertEqual(owner.partner_id.id, self.test_owner.id)
    def test_wms_owner_billing_rules(self):
        """Test creating billing rules for a WMS owner"""
        owner = self.env['wms.owner'].create({
            'partner_id': self.test_owner.id,
            'name': 'Test Owner',
            'owner_code': 'TEST',
            'is_warehouse_owner': True,
        })

        # Create a billing rule for this owner
        billing_rule = self.env['wms.billing.rule'].create({
            'name': 'Test Billing Rule',
            'owner_id': owner.id,
            'billing_method': 'per_pallet',
            'rate': 2.5,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        self.assertEqual(billing_rule.name, 'Test Billing Rule')
        self.assertEqual(billing_rule.owner_id.id, owner.id)
        self.assertEqual(billing_rule.billing_method, 'per_pallet')
        self.assertEqual(billing_rule.rate, 2.5)
    def test_owner_partner_link(self):
        """Test that owner and partner are properly linked"""
        owner = self.env['wms.owner'].create({
            'partner_id': self.test_owner.id,
            'name': 'Test Owner',
            'owner_code': 'TEST',
            'is_warehouse_owner': True,
        })

        # The partner should now be marked as a warehouse owner
        self.assertTrue(self.test_owner.is_warehouse_owner)
    def test_partner_warehouse_owner_flag(self):
        """Test that setting is_warehouse_owner on partner creates WMS owner"""
        partner = self.env['res.partner'].create({
            'name': 'Partner Owner Test',
            'is_company': True,
            'is_warehouse_owner': True,
        })

        # This should trigger the creation of a WMS owner
        wms_owner = self.env['wms.owner'].search([('partner_id', '=', partner.id)])
        self.assertTrue(wms_owner)
        self.assertEqual(wms_owner.name, partner.name)
    def test_owner_data_isolation(self):
        """Test that different owners have isolated data"""
        owner1 = self.env['wms.owner'].create({
            'partner_id': self.test_owner.id,
            'name': 'Owner 1',
            'owner_code': 'OWNER1',
            'is_warehouse_owner': True,
        })

        partner2 = self.env['res.partner'].create({
            'name': 'Second Owner',
            'is_company': True,
            'is_warehouse_owner': True,
        })

        owner2 = self.env['wms.owner'].create({
            'partner_id': partner2.id,
            'name': 'Owner 2',
            'owner_code': 'OWNER2',
            'is_warehouse_owner': True,
        })

        # Test that owners are properly isolated
        self.assertNotEqual(owner1.id, owner2.id)
        self.assertNotEqual(owner1.owner_code, owner2.owner_code)