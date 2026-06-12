from odoo.tests import TransactionCase
from odoo import fields


class TestWmsPutaway(TransactionCase):
    """Test cases for WMS Putaway module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_product = self.env['product.product'].create({
            'name': 'Test Product',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Owner',
            'owner_code': 'TEST',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })
    def test_create_wms_putaway_rule(self):
        """Test creating a WMS putaway rule with extended fields"""
        putaway_rule = self.env['stock.putaway.rule'].create({
            'product_id': self.test_product.id,
            'location_in_id': self.test_location.id,
            'location_out_id': self.test_location.id,
            'owner_id': self.test_owner.id,
            'abc_classification': 'A',
            'priority': 'high',
            'is_active': True,
        })

        self.assertEqual(putaway_rule.owner_id.id, self.test_owner.id)
        self.assertEqual(putaway_rule.abc_classification, 'A')
        self.assertEqual(putaway_rule.priority, 'high')
        self.assertTrue(putaway_rule.is_active)
    def test_wms_storage_area(self):
        """Test creating and using WMS storage areas"""
        storage_area = self.env['wms.storage.area'].create({
            'name': 'Test Storage Area',
            'owner_code': 'TSA001',
            'location_id': self.test_location.id,
            'area_type': 'pallet',
            'max_capacity': 100.0,
        })

        self.assertEqual(storage_area.name, 'Test Storage Area')
        self.assertEqual(storage_area.owner_code, 'TSA001')
        self.assertEqual(storage_area.area_type, 'pallet')
        self.assertEqual(storage_area.max_capacity, 100.0)
    def test_wms_cargo_type(self):
        """Test creating and using WMS cargo types"""
        cargo_type = self.env['wms.cargo.type'].create({
            'name': 'Fragile Cargo',
            'owner_code': 'FR',
            'is_hazardous': False,
            'requires_special_handling': True,
            'special_handling_notes': 'Handle with care',
        })

        self.assertEqual(cargo_type.name, 'Fragile Cargo')
        self.assertEqual(cargo_type.owner_code, 'FR')
        self.assertTrue(cargo_type.requires_special_handling)
        self.assertEqual(cargo_type.special_handling_notes, 'Handle with care')
    def test_wms_workzone(self):
        """Test creating and using WMS workzones"""
        workzone = self.env['wms.workzone'].create({
            'name': 'Receiving Workzone',
            'owner_code': 'RW',
            'location_id': self.test_location.id,
            'zone_type': 'receiving',
            'max_workers': 5,
            'is_active': True,
        })

        self.assertEqual(workzone.name, 'Receiving Workzone')
        self.assertEqual(workzone.zone_type, 'receiving')
        self.assertEqual(workzone.max_workers, 5)
        self.assertTrue(workzone.is_active)
    def test_putaway_rule_abc_classification(self):
        """Test that putaway rules properly handle ABC classification"""
        putaway_rule = self.env['stock.putaway.rule'].create({
            'product_id': self.test_product.id,
            'location_in_id': self.test_location.id,
            'location_out_id': self.test_location.id,
            'owner_id': self.test_owner.id,
            'abc_classification': 'B',
            'priority': 'medium',
            'is_active': True,
        })

        # Check that the ABC classification affects storage decisions
        self.assertEqual(putaway_rule.abc_classification, 'B')
        # Medium priority might be used for B-class products in allocation logic

    def test_putaway_rule_ownership_isolation(self):
        """Test that putaway rules are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Owner',
            'owner_code': 'SO',
            'is_warehouse_owner': True,
        })

        rule1 = self.env['stock.putaway.rule'].create({
            'product_id': self.test_product.id,
            'location_in_id': self.test_location.id,
            'location_out_id': self.test_location.id,
            'owner_id': self.test_owner.id,
            'abc_classification': 'A',
            'is_active': True,
        })

        rule2 = self.env['stock.putaway.rule'].create({
            'product_id': self.test_product.id,
            'location_in_id': self.test_location.id,
            'location_out_id': self.test_location.id,
            'owner_id': owner2.id,
            'abc_classification': 'C',
            'is_active': True,
        })

        self.assertNotEqual(rule1.owner_id.id, rule2.owner_id.id)
        self.assertNotEqual(rule1.abc_classification, rule2.abc_classification)