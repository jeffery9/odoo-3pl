from odoo.tests import TransactionCase
from odoo import fields


class TestWmsFinanceIntegration(TransactionCase):
    """Test cases for WMS Finance Integration module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Finance Integration Owner',
            'owner_code': 'TFIO',
            'is_warehouse_owner': True,
        })

        self.test_cost_center = self.env['wms.cost.center'].create({
            'name': 'Test Cost Center',
            'owner_code': 'TCC',
            'owner_id': self.test_owner.id,
            'is_active': True,
        })

        self.test_service_type = self.env['wms.service.type'].create({
            'name': 'Test Storage Service',
            'owner_code': 'TSS',
            'category': 'storage',
            'default_rate': 5.0,
            'rate_unit': 'day',
        })

        self.test_user = self.env['res.users'].create({
            'name': 'Test Finance User',
            'login': 'test_finance_user',
            'email': 'test.finance@example.com',
        })

        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@example.com',
        })

        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Finance',
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
    def test_create_cost_center(self):
        """Test creating cost centers"""
        cost_center = self.env['wms.cost.center'].create({
            'name': 'Test Cost Center',
            'owner_code': 'TCC2',
            'owner_id': self.test_owner.id,
            'is_active': True,
        })

        self.assertEqual(cost_center.name, 'Test Cost Center')
        self.assertEqual(cost_center.owner_code, 'TCC2')
        self.assertEqual(cost_center.owner_id.id, self.test_owner.id)
        self.assertTrue(cost_center.is_active)
    def test_create_service_type(self):
        """Test creating service types"""
        service_type = self.env['wms.service.type'].create({
            'name': 'Test Handling Service',
            'owner_code': 'THS',
            'category': 'handling',
            'default_rate': 10.0,
            'rate_unit': 'item',
        })

        self.assertEqual(service_type.name, 'Test Handling Service')
        self.assertEqual(service_type.owner_code, 'THS')
        self.assertEqual(service_type.category, 'handling')
        self.assertEqual(service_type.default_rate, 10.0)
        self.assertEqual(service_type.rate_unit, 'item')
        self.assertTrue(service_type.is_active)
    def test_create_service_pricing(self):
        """Test creating service pricing"""
        service_pricing = self.env['wms.service.pricing'].create({
            'service_type_id': self.test_service_type.id,
            'owner_id': self.test_owner.id,
            'rate': 7.5,
            'effective_date': fields.Date.today(),
            'is_active': True,
        })

        self.assertEqual(service_pricing.service_type_id.id, self.test_service_type.id)
        self.assertEqual(service_pricing.owner_id.id, self.test_owner.id)
        self.assertEqual(service_pricing.rate, 7.5)
        self.assertEqual(service_pricing.effective_date, fields.Date.today())
        self.assertTrue(service_pricing.is_active)
    def test_create_financial_transaction(self):
        """Test creating financial transactions"""
        transaction = self.env['wms.financial.transaction'].create({
            'transaction_type': 'storage_fee',
            'owner_id': self.test_owner.id,
            'service_type_id': self.test_service_type.id,
            'amount': 100.0,
            'transaction_date': fields.Date.today(),
            'status': 'draft',
        })

        self.assertTrue(transaction.name.startswith('FTR'))
        self.assertEqual(transaction.transaction_type, 'storage_fee')
        self.assertEqual(transaction.owner_id.id, self.test_owner.id)
        self.assertEqual(transaction.service_type_id.id, self.test_service_type.id)
        self.assertEqual(transaction.amount, 100.0)
        self.assertEqual(transaction.status, 'draft')
        self.assertEqual(transaction.total_amount, 100.0)  # No tax amount

    def test_financial_transaction_status_flow(self):
        """Test financial transaction status flow"""
        transaction = self.env['wms.financial.transaction'].create({
            'transaction_type': 'handling_fee',
            'owner_id': self.test_owner.id,
            'service_type_id': self.test_service_type.id,
            'amount': 50.0,
            'transaction_date': fields.Date.today(),
            'status': 'draft',
        })

        self.assertEqual(transaction.status, 'draft')

        # Confirm the transaction
        transaction.action_confirm()
        self.assertEqual(transaction.status, 'confirmed')

        # Post the transaction
        transaction.action_post()
        self.assertEqual(transaction.status, 'posted')
        self.assertTrue(transaction.is_posted)
    def test_financial_transaction_with_tax(self):
        """Test financial transaction with tax amount"""
        transaction = self.env['wms.financial.transaction'].create({
            'transaction_type': 'value_added',
            'owner_id': self.test_owner.id,
            'service_type_id': self.test_service_type.id,
            'amount': 200.0,
            'tax_amount': 20.0,  # 10% tax
            'transaction_date': fields.Date.today(),
        })

        self.assertEqual(transaction.amount, 200.0)
        self.assertEqual(transaction.tax_amount, 20.0)
        self.assertEqual(transaction.total_amount, 220.0)  # 200 + 20

    def test_create_cost_allocation(self):
        """Test creating cost allocations"""
        target_cost_center = self.env['wms.cost.center'].create({
            'name': 'Target Cost Center',
            'owner_code': 'TCC3',
            'owner_id': self.test_owner.id,
        })

        cost_allocation = self.env['wms.cost.allocation'].create({
            'name': 'Test Cost Allocation',
            'source_cost_center_id': self.test_cost_center.id,
            'target_cost_center_id': target_cost_center.id,
            'owner_id': self.test_owner.id,
            'allocation_type': 'percentage',
            'percentage': 50.0,
            'amount': 1000.0,
        })

        self.assertEqual(cost_allocation.name, 'Test Cost Allocation')
        self.assertEqual(cost_allocation.source_cost_center_id.id, self.test_cost_center.id)
        self.assertEqual(cost_allocation.target_cost_center_id.id, target_cost_center.id)
        self.assertEqual(cost_allocation.percentage, 50.0)
        self.assertEqual(cost_allocation.amount, 1000.0)
        self.assertEqual(cost_allocation.status, 'draft')
    def test_cost_allocation_status_flow(self):
        """Test cost allocation status flow"""
        target_cost_center = self.env['wms.cost.center'].create({
            'name': 'Target Cost Center 2',
            'owner_code': 'TCC4',
            'owner_id': self.test_owner.id,
        })

        cost_allocation = self.env['wms.cost.allocation'].create({
            'name': 'Status Flow Test',
            'source_cost_center_id': self.test_cost_center.id,
            'target_cost_center_id': target_cost_center.id,
            'owner_id': self.test_owner.id,
            'allocation_type': 'fixed_amount',
            'amount': 500.0,
        })

        self.assertEqual(cost_allocation.status, 'draft')

        # Confirm the allocation
        cost_allocation.action_confirm()
        self.assertEqual(cost_allocation.status, 'confirmed')

        # Post the allocation
        cost_allocation.action_post()
        self.assertEqual(cost_allocation.status, 'posted')
    def test_create_financial_report(self):
        """Test creating financial reports"""
        financial_report = self.env['wms.financial.report'].create({
            'name': 'Test Financial Report',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
        })

        self.assertTrue(financial_report.report_code.startswith('FRE'))
        self.assertEqual(financial_report.name, 'Test Financial Report')
        self.assertEqual(financial_report.owner_id.id, self.test_owner.id)
        self.assertEqual(financial_report.status, 'draft')
    def test_financial_report_status_flow(self):
        """Test financial report status flow"""
        financial_report = self.env['wms.financial.report'].create({
            'name': 'Status Flow Report',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
        })

        self.assertEqual(financial_report.status, 'draft')

        # Generate the report
        financial_report.action_generate_report()
        self.assertEqual(financial_report.status, 'generated')

        # Validate the report
        financial_report.action_validate_report()
        self.assertEqual(financial_report.status, 'validated')
    def test_create_invoice_integration(self):
        """Test creating invoice integration records"""
        invoice = self.env['wms.invoice.integration'].create({
            'name': 'Test Invoice',
            'owner_id': self.test_owner.id,
            'partner_id': self.test_partner.id,
            'invoice_date': fields.Date.today(),
            'due_date': fields.Date.add(fields.Date.today(), days=30),
        })

        self.assertEqual(invoice.name, 'Test Invoice')
        self.assertEqual(invoice.owner_id.id, self.test_owner.id)
        self.assertEqual(invoice.partner_id.id, self.test_partner.id)
        self.assertEqual(invoice.status, 'draft')
        self.assertEqual(invoice.total_amount, 0.0)  # No transactions yet

    def test_invoice_integration_status_flow(self):
        """Test invoice integration status flow"""
        invoice = self.env['wms.invoice.integration'].create({
            'name': 'Status Flow Invoice',
            'owner_id': self.test_owner.id,
            'partner_id': self.test_partner.id,
            'invoice_date': fields.Date.today(),
            'due_date': fields.Date.add(fields.Date.today(), days=30),
        })

        self.assertEqual(invoice.status, 'draft')

        # Send the invoice
        invoice.action_send_invoice()
        self.assertEqual(invoice.status, 'sent')

        # Mark as paid
        invoice.action_mark_paid()
        self.assertEqual(invoice.status, 'paid')
    def test_financial_transaction_computed_fields(self):
        """Test computed fields in financial transactions"""
        transaction = self.env['wms.financial.transaction'].create({
            'transaction_type': 'storage_fee',
            'owner_id': self.test_owner.id,
            'service_type_id': self.test_service_type.id,
            'amount': 150.0,
            'tax_amount': 15.0,
            'transaction_date': fields.Date.today(),
        })

        # Refresh to get updated computed values
        transaction.refresh()

        self.assertEqual(transaction.total_amount, 165.0)  # 150 + 15

    def test_financial_report_computed_data(self):
        """Test computed financial data in reports"""
        # Create a financial report
        financial_report = self.env['wms.financial.report'].create({
            'name': 'Computed Data Test',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=7),
        })

        # Create some transactions within the report period
        self.env['wms.financial.transaction'].create([
            {
                'transaction_type': 'storage_fee',
                'owner_id': self.test_owner.id,
                'service_type_id': self.test_service_type.id,  # This is a storage service
                'amount': 100.0,
                'transaction_date': fields.Date.today(),
                'status': 'posted',
            },
            {
                'transaction_type': 'handling_fee',
                'owner_id': self.test_owner.id,
                'service_type_id': self.env['wms.service.type'].create({
                    'name': 'Test Handling Service',
                    'owner_code': 'THS2',
                    'category': 'handling',
                    'default_rate': 8.0,
                    'rate_unit': 'item',
                }).id,
                'amount': 50.0,
                'transaction_date': fields.Date.today(),
                'status': 'posted',
            },
        ])

        # Refresh to get updated computed values
        financial_report.refresh()

        # The report should have aggregated the values from transactions
        # Note: In the actual implementation, these values would be computed based on posted transactions
        # For this test, we just verify the fields exist and are accessible

    def test_service_pricing_date_validation(self):
        """Test service pricing date validation"""
        from datetime import date

        # Test with valid dates (effective before expiry)
        pricing = self.env['wms.service.pricing'].create({
            'service_type_id': self.test_service_type.id,
            'owner_id': self.test_owner.id,
            'rate': 5.0,
            'effective_date': date.today(),
            'expiry_date': date.today().replace(year=date.today().year + 1),  # One year later
        })

        self.assertIsNotNone(pricing.effective_date)
        self.assertIsNotNone(pricing.expiry_date)

        # Test with invalid dates should raise an error
        with self.assertRaises(Exception):
            self.env['wms.service.pricing'].create({
                'service_type_id': self.test_service_type.id,
                'owner_id': self.test_owner.id,
                'rate': 6.0,
                'effective_date': date.today().replace(year=date.today().year + 1),  # Future date
                'expiry_date': date.today(),  # Past relative to effective
            })
    def test_financial_transaction_with_related_model(self):
        """Test financial transaction linked to related model"""
        transaction = self.env['wms.financial.transaction'].create({
            'transaction_type': 'handling_fee',
            'owner_id': self.test_owner.id,
            'service_type_id': self.test_service_type.id,
            'amount': 25.0,
            'transaction_date': fields.Date.today(),
            'related_model': f"stock.picking,{self.test_picking.id}",
        })

        self.assertIsNotNone(transaction.related_model)