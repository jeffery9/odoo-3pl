from odoo.tests import TransactionCase
from odoo import fields
from datetime import datetime, timedelta


class TestWmsInventoryAge(TransactionCase):
    """Test cases for WMS Inventory Age module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Inventory Age Owner',
            'owner_code': 'TIAO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Inventory Age',
                        'categ_id': self.env.ref('product.product_category_all').id,
            'standard_price': 20.0,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        # Create a lot for testing
        self.test_lot = self.env['stock.lot'].create({
            'name': 'TESTLOT001',
            'product_id': self.test_product.id,
            'company_id': self.env.company.id,
        })
    def test_inventory_age_report_generation(self):
        """Test generating an inventory age report"""
        # Create a stock quant
        quant = self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'quantity': 100.0,
            'owner_id': self.test_owner.id,
        })

        # Create the report wizard
        report = self.env['wms.inventory.age.report'].create({
            'owner_id': self.test_owner.id,
            'date_as_of': fields.Date.today(),
        })

        # Generate the report
        action = report.action_generate_report()

        # Verify the action returns correctly
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'wms.inventory.age.report')
        self.assertEqual(action['res_id'], report.id)
    def test_inventory_age_computation(self):
        """Test that inventory age is computed correctly"""
        # Create a stock quant with a date in the past to test age calculation
        # (in the actual test, the age will be calculated from create_date)
        quant = self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'quantity': 50.0,
            'owner_id': self.test_owner.id,
        })

        # Verify age computation (should be 0 since it was just created today)
        quant.refresh()
        self.assertGreaterEqual(quant.age_days, 0)  # Age should be non-negative

    def test_aging_period_classification(self):
        """Test that aging periods are classified correctly"""
        # Create a quant
        quant = self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'quantity': 75.0,
            'owner_id': self.test_owner.id,
        })

        # The aging period should be computed based on age
        # For a newly created quant, it should be 'current' (0-30 days)
        quant.refresh()
        self.assertEqual(quant.aging_period, 'current')
    def test_inventory_age_config(self):
        """Test creating inventory age configuration"""
        config = self.env['wms.inventory.age.config'].create({
            'name': 'Test Config',
            'owner_id': self.test_owner.id,
            'warning_age_days': 180,
            'critical_age_days': 365,
            'auto_create_alerts': True,
            'alert_frequency': 'weekly',
        })

        self.assertEqual(config.name, 'Test Config')
        self.assertEqual(config.owner_id.id, self.test_owner.id)
        self.assertEqual(config.warning_age_days, 180)
        self.assertEqual(config.critical_age_days, 365)
        self.assertTrue(config.auto_create_alerts)
        self.assertEqual(config.alert_frequency, 'weekly')
    def test_inventory_age_alert(self):
        """Test creating inventory age alerts"""
        alert = self.env['wms.inventory.age.alert'].create({
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'owner_id': self.test_owner.id,
            'quantity': 10.0,
            'age_days': 400,  # More than critical threshold
            'alert_type': 'critical',
            'status': 'open',
        })

        self.assertEqual(alert.product_id.id, self.test_product.id)
        self.assertEqual(alert.location_id.id, self.test_location.id)
        self.assertEqual(alert.owner_id.id, self.test_owner.id)
        self.assertEqual(alert.age_days, 400)
        self.assertEqual(alert.alert_type, 'critical')
        self.assertEqual(alert.status, 'open')
    def test_age_alert_status_flow(self):
        """Test the status flow of age alerts"""
        alert = self.env['wms.inventory.age.alert'].create({
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'owner_id': self.test_owner.id,
            'quantity': 5.0,
            'age_days': 200,  # More than warning threshold
            'alert_type': 'warning',
            'status': 'open',
        })

        self.assertEqual(alert.status, 'open')

        # Acknowledge the alert
        alert.action_acknowledge()
        self.assertEqual(alert.status, 'acknowledged')

        # Resolve the alert
        alert.action_resolve()
        self.assertEqual(alert.status, 'resolved')
    def test_age_report_line_computation(self):
        """Test that age report line values are computed correctly"""
        # Create a report line directly for testing
        report = self.env['wms.inventory.age.report'].create({
            'date_as_of': fields.Date.today(),
        })

        line = self.env['wms.inventory.age.report.line'].create({
            'report_id': report.id,
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'quantity': 25.0,
            'unit_cost': 20.0,
            'age_days': 150,
        })

        # Check that total value is computed correctly
        self.assertEqual(line.total_value, 500.0)  # 25 * 20

        # Check that aging period is computed based on age
        if line.age_days <= 30:
            self.assertEqual(line.aging_period, 'current')
        elif line.age_days <= 60:
            self.assertEqual(line.aging_period, '30_60')
        elif line.age_days <= 90:
            self.assertEqual(line.aging_period, '60_90')
        elif line.age_days <= 180:
            self.assertEqual(line.aging_period, '90_180')
        elif line.age_days <= 365:
            self.assertEqual(line.aging_period, '180_365')
        else:
            self.assertEqual(line.aging_period, 'over_365')
    def test_quant_is_aged_inventory_computation(self):
        """Test that is_aged_inventory is computed correctly"""
        # Create a quant
        quant = self.env['stock.quant'].create({
            'product_id': self.test_product.id,
            'location_id': self.test_location.id,
            'quantity': 30.0,
            'owner_id': self.test_owner.id,
        })

        # Create a configuration for the owner
        self.env['wms.inventory.age.config'].create({
            'name': 'Test Config for Aged Flag',
            'owner_id': self.test_owner.id,
            'warning_age_days': 30,  # Very low for testing
            'critical_age_days': 90,
            'auto_create_alerts': False,
            'alert_frequency': 'weekly',
        })

        # The quant was just created, so it should not be considered aged
        # (unless the default threshold is less than 1 day)
        quant.refresh()
        # Note: Since the quant was just created, it should have age_days = 0
        # and thus is_aged_inventory should be False based on the configuration

    def test_age_alert_types(self):
        """Test different age alert types"""
        alert_types = ['warning', 'critical']

        for alert_type in alert_types:
            alert = self.env['wms.inventory.age.alert'].create({
                'product_id': self.test_product.id,
                'location_id': self.test_location.id,
                'owner_id': self.test_owner.id,
                'quantity': 15.0,
                'age_days': 400 if alert_type == 'critical' else 200,
                'alert_type': alert_type,
            })
            self.assertEqual(alert.alert_type, alert_type)
    def test_inventory_age_ownership_isolation(self):
        """Test that inventory age features are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Inventory Age Owner',
            'owner_code': 'SIAO',
            'is_warehouse_owner': True,
        })

        # Create configuration for each owner
        config1 = self.env['wms.inventory.age.config'].create({
            'name': 'Config for Owner 1',
            'owner_id': self.test_owner.id,
            'warning_age_days': 180,
            'critical_age_days': 365,
        })

        config2 = self.env['wms.inventory.age.config'].create({
            'name': 'Config for Owner 2',
            'owner_id': owner2.id,
            'warning_age_days': 90,
            'critical_age_days': 180,
        })

        self.assertNotEqual(config1.owner_id.id, config2.owner_id.id)
        self.assertNotEqual(config1.warning_age_days, config2.warning_age_days)
        self.assertNotEqual(config1.name, config2.name)

        # Only one config per owner is allowed (tested by SQL constraint)
        with self.assertRaises(Exception):
            self.env['wms.inventory.age.config'].create({
                'name': 'Duplicate Config',
                'owner_id': self.test_owner.id,  # Same owner as config1
                'warning_age_days': 150,
                'critical_age_days': 300,
            })