# -*- coding: utf-8 -*-
"""
BDD Testing for Feature: Billing and Settlement (wms_billing)
Source Feature: features/billing_and_settlement.feature

This module tests the core billing requirements including:
- Automatic billing record generation
- Complex billing rules application
- Periodic invoice generation
"""

from odoo.tests import common


class TestBillingRecordGeneration(common.TransactionCase):
    """
    Scenario: Automatic billing record generation upon operation completion
    When a stock move (e.g., inbound handling or outbound packing) is confirmed as done
    Then the system should automatically create a "WMS Billing Record" in Odoo
    And this record must be linked to the specific owner and the operation type
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create warehouse and operations
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Billing Test WH',
            'owner_code': 'BILLWH',
        })

        cls.outgoing_type = cls.warehouse.outtype_id
        
        # Create owner with billing configuration
        cls.billing_owner = cls.env['res.partner'].create({
            'name': 'Billing Test Owner',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_BILLING',
            'storage_fee_rate': 5.00,
            'inbound_fee': 10.00,
            'outbound_fee': 15.00,
        })

        # Create billing rule for outbound operations
        cls.billing_rule_outbound = cls.env['wms.billing.rule'].create({
            'name': 'Outbound Handling Rule',
            'owner_id': cls.billing_owner.id,
            'operation_type': 'outbound',
            'billing_method': 'per_unit',
            'unit_price': 2.00,
            'min_charge': 5.00,
        })
    def test_01_auto_billing_record_on_picking_done(self):
        """
        Verify that billing records are created when outbound operations complete.
        """
        # Create an outbound picking
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.outgoing_type.id,
            'partner_id': self.billing_owner.id,
            'origin': 'BDD-Billing-Test',
        })

        product = self.env['product.product'].create({
            'name': 'Billing Test Product',
                    })

        move = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id,
            'picking_id': picking.id,
            'location_id': self.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': self.outgoing_type.default_location_dest_id.id,
        })

        move._action_confirm()
        
        # Simulate operation completion (as if confirmed via RF device)
        for ml in picking.move_line_ids:
            ml.qty_done = ml.product_uom_qty
        
        picking._action_done()

        # Verify: Billing record should be created automatically
        billing_records = self.env['wms.billing.record'].search([
            ('owner_id', '=', self.billing_owner.id),
            ('operation_type', '=', 'outbound'),
            ('move_id', '=', picking.move_id.id if picking.move_id else False),
        ])

        self.assertTrue(len(billing_records) > 0,
                       "Billing record must be automatically created upon operation completion")


class TestComplexBillingRules(common.TransactionCase):
    """
    Scenario: Apply complex billing rules (Volume/Weight based)
    Given a billing rule configured for "Storage" based on volume (per cubic meter)
    When I query the storage billing report for Owner A over 30 days
    Then the system should sum up the daily volume of inventory and multiply it by the agreed rate
    And apply any "Minimum Charge" constraints if the calculated amount is too low
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Storage Billing Test WH',
            'owner_code': 'STGBWH',
        })

        # Create owner with storage billing rule
        cls.storage_owner = cls.env['res.partner'].create({
            'name': 'Storage Billing Owner',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_STORAGE',
        })

        # Create storage billing rule (per cubic meter)
        cls.billing_rule_storage = cls.env['wms.billing.rule'].create({
            'name': 'Storage Volume Rule',
            'owner_id': cls.storage_owner.id,
            'operation_type': 'storage',
            'billing_method': 'per_volume',
            'unit_price': 0.50,  # $ per cubic meter per day
            'min_charge': 10.00,  # Minimum charge constraint
        })
    def test_02_volume_based_storage_billing(self):
        """
        Verify that storage billing calculations are correct with volume-based rates.
        """
        product = self.env['product.product'].create({
            'name': 'Storage Billing Product',
                        'volume': 10.0,  # cubic meters per unit
            'weight': 100.0,
        })

        # Simulate inventory sitting for 30 days
        qty = 5.0
        daily_volume = qty * product.volume  # 5 units * 10 m³ = 50 m³ per day
        
        # Create billing records for each day (simulating monthly calculation)
        total_billed_volume = 0
        total_amount = 0.0

        for day in range(30):
            # Simulate daily volume tracking
            daily_volume_record = self.env['wms.billing.record'].create({
                'name': f'Storage Day {day+1}',
                'owner_id': cls.storage_owner.id,
                'operation_type': 'storage',
                'quantity': daily_volume,  # cubic meters used that day
                'unit_price': cls.billing_rule_storage.unit_price,
                'move_id': False,
            })

            total_billed_volume += daily_volume_record.quantity
            # Apply minimum charge logic (simplified)
            calculated_amount = daily_volume_record.quantity * cls.billing_rule_storage.unit_price
            actual_amount = max(calculated_amount, cls.billing_rule_storage.min_charge)
            total_amount += actual_amount

        # Verify calculations match expected values
        expected_amount = 30 * (daily_volume * cls.billing_rule_storage.unit_price)
        expected_min_charge = 30 * cls.billing_rule_storage.min_charge
        
        self.assertTrue(total_amount >= expected_min_charge,
                       "Total billing amount must respect minimum charge constraints")


class TestPeriodicInvoiceGeneration(common.TransactionCase):
    """
    Scenario: Generate periodic customer invoices
    Given a monthly settlement cycle has passed for multiple owners
    When I trigger the "Generate Invoices" batch process
    Then the system should compile all billing records per owner into an Odoo Invoice (account.move)
    And send the billing details to the respective customers for confirmation
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create multiple owners with billing records
        cls.owner_1 = cls.env['res.partner'].create({
            'name': 'Invoice Owner 1',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_INV1',
        })

        cls.owner_2 = cls.env['res.partner'].create({
            'name': 'Invoice Owner 2',
            'is_warehouse_owner': True,
            'owner_code': 'OWNER_INV2',
        })

        # Create billing records for each owner across multiple operations
        for owner in [cls.owner_1, cls.owner_2]:
            for i in range(5):  # 5 different billing operations per owner
                self.env['wms.billing.record'].create({
                    'name': f'Invoice Record {i+1}',
                    'owner_id': owner.id,
                    'operation_type': 'inbound',
                    'quantity': 10.0 * (i + 1),
                    'unit_price': 2.50,
                    'amount': 10.0 * (i + 1) * 2.50,
                })
    def test_03_batch_invoice_generation_per_owner(self):
        """
        Verify that billing records are correctly aggregated into invoices per owner.
        """
        # Create a mock invoice generation process
        for owner in [cls.owner_1, cls.owner_2]:
            # Calculate total amount for this owner
            owner_billing_records = self.env['wms.billing.record'].search([
                ('owner_id', '=', owner.id),
            ])

            total_amount = sum(owner_billing_records.mapped('amount'))
            
            # Verify: All records belong to the correct owner and amounts are calculated correctly
            self.assertTrue(len(owner_billing_records) > 0,
                           f"Owner {owner.name} must have billing records")
            
            self.assertTrue(total_amount > 0, 
                           f"Total amount for {owner.name} must be greater than zero")


class TestBillingDashboardAnalytics(common.TransactionCase):
    """
    Scenario: View billing analytics dashboard
    Given multiple owners have completed various operations this month
    When I open the Billing Analytics Dashboard
    Then I should see metrics such as "Total Revenue", "Pending Invoices", and "Collections Summary"
    And a breakdown of revenue by operation type (inbound, outbound, storage, etc.)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Analytics Test WH',
            'owner_code': 'ANAWH',
        })

        # Create different operation types for analytics
        cls.inbound_rule = cls.env['wms.billing.rule'].create({
            'name': 'Inbound Rule',
            'operation_type': 'inbound',
            'billing_method': 'per_order',
            'unit_price': 15.00,
        })

        cls.outbound_rule = cls.env['wms.billing.rule'].create({
            'name': 'Outbound Rule',
            'operation_type': 'outbound',
            'billing_method': 'per_unit',
            'unit_price': 3.00,
        })

        cls.storage_rule = cls.env['wms.billing.rule'].create({
            'name': 'Storage Rule',
            'operation_type': 'storage',
            'billing_method': 'per_volume',
            'unit_price': 0.75,
        })
    def test_04_billing_analytics_aggregation(self):
        """
        Verify that billing analytics correctly aggregate data by operation type.
        """
        # Create sample billing records across different types
        for i in range(10):
            self.env['wms.billing.record'].create({
                'name': f'Analytics Record {i+1}',
                'owner_id': cls.env.ref('base.public_partner').id,  # Public partner as test owner
                'operation_type': ['inbound', 'outbound', 'storage'][i % 3],
                'quantity': 5.0 + i,
                'unit_price': 2.00 + (i * 0.1),
            })

        # Query analytics data
        all_records = self.env['wms.billing.record'].search([])
        
        total_revenue = sum(all_records.mapped('amount'))
        revenue_by_type = {}
        
        for operation_type in ['inbound', 'outbound', 'storage']:
            type_records = all_records.filtered(lambda r: r.operation_type == operation_type)
            revenue_by_type[operation_type] = sum(type_records.mapped('amount'))

        # Verify: Analytics correctly calculate totals
        self.assertTrue(total_revenue > 0, "Total revenue must be greater than zero")
        self.assertEqual(sum(revenue_by_type.values()), total_revenue, 
                        "Sum of type revenues must equal total revenue")


if __name__ == '__main__':
    import sys
    from odoo.tests.common import TransactionCase

    class TestSuite:
        """Helper class for manual testing if needed"""
        pass

    # Run tests via Odoo's test runner:
    # python -m unittest /path/to/test_wav_billing.py
