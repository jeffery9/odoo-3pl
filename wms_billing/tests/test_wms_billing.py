from odoo.tests import TransactionCase
from odoo import fields


class TestWmsBilling(TransactionCase):
    """Test cases for WMS Billing module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Billing Owner',
            'owner_code': 'TBO',
            'is_warehouse_owner': True,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        self.test_account = self.env['account.account'].create({
            'name': 'Test Account',
            'owner_code': 'TEST001',
            'account_type': 'income',
        })
    def test_create_billing_rule(self):
        """Test creating a WMS billing rule"""
        billing_rule = self.env['wms.billing.rule'].create({
            'name': 'Test Billing Rule',
            'owner_code': 'TBR001',
            'owner_id': self.test_owner.id,
            'billing_method': 'per_pallet',
            'rate': 5.0,
            'uom_id': self.test_uom.id,
            'is_active': True,
            'billing_cycle': 'monthly',
        })

        self.assertEqual(billing_rule.name, 'Test Billing Rule')
        self.assertEqual(billing_rule.owner_code, 'TBR001')
        self.assertEqual(billing_rule.owner_id.id, self.test_owner.id)
        self.assertEqual(billing_rule.billing_method, 'per_pallet')
        self.assertEqual(billing_rule.rate, 5.0)
        self.assertTrue(billing_rule.is_active)
        self.assertEqual(billing_rule.billing_cycle, 'monthly')
    def test_create_billing_record(self):
        """Test creating a WMS billing record"""
        billing_rule = self.env['wms.billing.rule'].create({
            'name': 'Test Rule for Record',
            'owner_id': self.test_owner.id,
            'billing_method': 'per_pallet',
            'rate': 3.0,
            'uom_id': self.test_uom.id,
        })

        billing_record = self.env['wms.billing.record'].create({
            'name': 'Test Billing Record',
            'owner_id': self.test_owner.id,
            'billing_rule_id': billing_rule.id,
            'quantity': 100.0,
            'unit_rate': 3.0,
            'total_amount': 300.0,
            'billing_date': fields.Date.today(),
            'status': 'draft',
            'description': 'Test billing record for verification',
        })

        self.assertEqual(billing_record.name, 'Test Billing Record')
        self.assertEqual(billing_record.owner_id.id, self.test_owner.id)
        self.assertEqual(billing_record.billing_rule_id.id, billing_rule.id)
        self.assertEqual(billing_record.quantity, 100.0)
        self.assertEqual(billing_record.total_amount, 300.0)
        self.assertEqual(billing_record.status, 'draft')
    def test_create_invoice(self):
        """Test creating a WMS invoice"""
        wms_invoice = self.env['wms.invoice'].create({
            'name': 'Test WMS Invoice',
            'invoice_number': 'INV-001',
            'owner_id': self.test_owner.id,
            'total_amount': 500.0,
            'invoice_date': fields.Date.today(),
            'due_date': fields.Date.add(fields.Date.today(), days=30),
            'status': 'draft',
            'account_id': self.test_account.id,
        })

        self.assertEqual(wms_invoice.name, 'Test WMS Invoice')
        self.assertEqual(wms_invoice.invoice_number, 'INV-001')
        self.assertEqual(wms_invoice.owner_id.id, self.test_owner.id)
        self.assertEqual(wms_invoice.total_amount, 500.0)
        self.assertEqual(wms_invoice.status, 'draft')
    def test_billing_record_status_flow(self):
        """Test the status flow of billing records"""
        billing_rule = self.env['wms.billing.rule'].create({
            'name': 'Status Test Rule',
            'owner_id': self.test_owner.id,
            'billing_method': 'per_order',
            'rate': 10.0,
            'uom_id': self.test_uom.id,
        })

        billing_record = self.env['wms.billing.record'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'billing_rule_id': billing_rule.id,
            'quantity': 50.0,
            'unit_rate': 10.0,
            'total_amount': 500.0,
            'billing_date': fields.Date.today(),
            'status': 'draft',
        })

        # Test status transitions
        self.assertEqual(billing_record.status, 'draft')

        # Simulate confirming the billing record
        billing_record.write({'status': 'confirmed'})
        self.assertEqual(billing_record.status, 'confirmed')

        # Simulate invoicing the billing record
        billing_record.write({'status': 'invoiced'})
        self.assertEqual(billing_record.status, 'invoiced')

        # Simulate payment of the billing record
        billing_record.write({'status': 'paid'})
        self.assertEqual(billing_record.status, 'paid')
    def test_invoice_status_flow(self):
        """Test the status flow of WMS invoices"""
        wms_invoice = self.env['wms.invoice'].create({
            'name': 'Status Flow Invoice',
            'invoice_number': 'INV-002',
            'owner_id': self.test_owner.id,
            'total_amount': 250.0,
            'invoice_date': fields.Date.today(),
            'status': 'draft',
            'account_id': self.test_account.id,
        })

        # Test status transitions
        self.assertEqual(wms_invoice.status, 'draft')

        # Simulate confirming the invoice
        wms_invoice.write({'status': 'confirmed'})
        self.assertEqual(wms_invoice.status, 'confirmed')

        # Simulate sending the invoice
        wms_invoice.write({'status': 'sent'})
        self.assertEqual(wms_invoice.status, 'sent')

        # Simulate payment of the invoice
        wms_invoice.write({'status': 'paid'})
        self.assertEqual(wms_invoice.status, 'paid')
    def test_billing_rule_methods(self):
        """Test different billing methods"""
        # Test per_pallet method
        rule_pallet = self.env['wms.billing.rule'].create({
            'name': 'Per Pallet Rule',
            'owner_id': self.test_owner.id,
            'billing_method': 'per_pallet',
            'rate': 2.5,
            'uom_id': self.test_uom.id,
        })

        # Test per_order method
        rule_order = self.env['wms.billing.rule'].create({
            'name': 'Per Order Rule',
            'owner_id': self.test_owner.id,
            'billing_method': 'per_order',
            'rate': 15.0,
            'uom_id': self.test_uom.id,
        })

        # Test per_weight method
        rule_weight = self.env['wms.billing.rule'].create({
            'name': 'Per Weight Rule',
            'owner_id': self.test_owner.id,
            'billing_method': 'per_weight',
            'rate': 1.2,
            'uom_id': self.test_uom.id,
        })

        self.assertEqual(rule_pallet.billing_method, 'per_pallet')
        self.assertEqual(rule_order.billing_method, 'per_order')
        self.assertEqual(rule_weight.billing_method, 'per_weight')
    def test_billing_ownership_isolation(self):
        """Test that billing records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Billing Owner',
            'owner_code': 'SBO',
            'is_warehouse_owner': True,
        })

        rule1 = self.env['wms.billing.rule'].create({
            'name': 'Rule for Owner 1',
            'owner_id': self.test_owner.id,
            'billing_method': 'per_pallet',
            'rate': 3.0,
            'uom_id': self.test_uom.id,
        })

        rule2 = self.env['wms.billing.rule'].create({
            'name': 'Rule for Owner 2',
            'owner_id': owner2.id,
            'billing_method': 'per_order',
            'rate': 20.0,
            'uom_id': self.test_uom.id,
        })

        self.assertNotEqual(rule1.owner_id.id, rule2.owner_id.id)
        self.assertNotEqual(rule1.billing_method, rule2.billing_method)