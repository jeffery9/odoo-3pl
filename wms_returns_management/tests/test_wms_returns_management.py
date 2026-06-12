from odoo.tests import TransactionCase
from odoo import fields


class TestWmsReturnsManagement(TransactionCase):
    """Test cases for WMS Returns Management module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Returns Management Owner',
            'owner_code': 'TRMO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'owner_code': 'TW',
        })

        self.test_picking_type = self.env['stock.picking.type'].create({
            'name': 'Test Picking Type',
            'code': 'incoming',
            'sequence_code': 'IN',
            'default_location_src_id': self.test_location.id,
            'default_location_dest_id': self.test_location.id,
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Returns',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        self.test_customer = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
        })

        # Create a test sale order
        self.test_sale_order = self.env['sale.order'].create({
            'partner_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
        })

        self.env['sale.order.line'].create({
            'order_id': self.test_sale_order.id,
            'product_id': self.test_product.id,
            'product_uom_qty': 10,
            'product_uom': self.test_uom.id,
        })
    def test_create_return_authorization(self):
        """Test creating a return authorization"""
        rma = self.env['wms.return.authorization'].create({
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
            'state': 'draft',
        })

        self.assertTrue(rma.name.startswith('RMA'))
        self.assertEqual(rma.owner_id.id, self.test_owner.id)
        self.assertEqual(rma.customer_id.id, self.test_customer.id)
        self.assertEqual(rma.return_reason, 'defective')
        self.assertEqual(rma.state, 'draft')
    def test_return_authorization_status_flow(self):
        """Test the status flow of return authorizations"""
        rma = self.env['wms.return.authorization'].create({
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
            'state': 'draft',
        })

        self.assertEqual(rma.state, 'draft')

        # Confirm the RMA
        rma.action_confirm()
        self.assertEqual(rma.state, 'confirmed')

        # Send for return
        rma.action_send_for_return()
        self.assertEqual(rma.state, 'in_transit')

        # Receive return
        rma.action_receive_return()
        self.assertEqual(rma.state, 'received')
        self.assertIsNotNone(rma.received_date)

        # Approve return
        rma.action_approve()
        self.assertEqual(rma.state, 'approved')

        # Complete return
        rma.action_complete()
        self.assertEqual(rma.state, 'completed')
    def test_return_line_creation(self):
        """Test creating return line items"""
        rma = self.env['wms.return.authorization'].create({
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
        })

        return_line = self.env['wms.return.line'].create({
            'rma_id': rma.id,
            'product_id': self.test_product.id,
            'quantity': 5.0,
            'unit_price': 10.0,
        })

        self.assertEqual(len(rma.return_line_ids), 1)
        self.assertEqual(rma.return_line_ids[0].product_id.id, self.test_product.id)
        self.assertEqual(rma.return_line_ids[0].quantity, 5.0)
        self.assertEqual(rma.return_line_ids[0].unit_price, 10.0)
        self.assertEqual(rma.return_line_ids[0].subtotal, 50.0)
    def test_return_line_subtotal_computation(self):
        """Test computed subtotal for return lines"""
        rma = self.env['wms.return.authorization'].create({
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
        })

        return_line = self.env['wms.return.line'].create({
            'rma_id': rma.id,
            'product_id': self.test_product.id,
            'quantity': 3.0,
            'unit_price': 25.0,
        })

        self.assertEqual(return_line.subtotal, 75.0)  # 3 * 25

    def test_return_authorization_totals_computation(self):
        """Test computed total quantity for return authorizations"""
        rma = self.env['wms.return.authorization'].create({
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
        })

        # Add multiple return lines
        self.env['wms.return.line'].create([
            {
                'rma_id': rma.id,
                'product_id': self.test_product.id,
                'quantity': 5.0,
                'unit_price': 10.0,
            },
            {
                'rma_id': rma.id,
                'product_id': self.test_product.id,
                'quantity': 3.0,
                'unit_price': 15.0,
            },
        ])

        # Refresh to get updated computed values
        rma.refresh()

        # Check that total quantity is computed correctly
        self.assertEqual(rma.product_qty, 8.0)  # 5 + 3

    def test_return_reason_creation(self):
        """Test creating return reasons"""
        return_reason = self.env['wms.return.reason'].create({
            'name': 'Test Return Reason',
            'description': 'Test return reason description',
            'category': 'quality',
        })

        self.assertEqual(return_reason.name, 'Test Return Reason')
        self.assertEqual(return_reason.description, 'Test return reason description')
        self.assertEqual(return_reason.category, 'quality')
    def test_return_disposition_creation(self):
        """Test creating return dispositions"""
        return_disposition = self.env['wms.return.disposition'].create({
            'name': 'Test Return Disposition',
            'description': 'Test return disposition description',
            'action_type': 'refund',
        })

        self.assertEqual(return_disposition.name, 'Test Return Disposition')
        self.assertEqual(return_disposition.description, 'Test return disposition description')
        self.assertEqual(return_disposition.action_type, 'refund')
    def test_return_authorization_with_sale_order(self):
        """Test creating RMA with associated sale order"""
        rma = self.env['wms.return.authorization'].create({
            'sale_order_id': self.test_sale_order.id,
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'wrong_item',
        })

        self.assertEqual(rma.sale_order_id.id, self.test_sale_order.id)
        self.assertEqual(rma.customer_id.id, self.test_customer.id)
    def test_return_authorization_ownership_isolation(self):
        """Test that return authorization records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Returns Management Owner',
            'owner_code': 'SRMO',
            'is_warehouse_owner': True,
        })

        customer2 = self.env['res.partner'].create({
            'name': 'Second Test Customer',
            'email': 'test2@example.com',
        })

        rma1 = self.env['wms.return.authorization'].create({
            'name': 'RMA for Owner 1',
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
        })

        rma2 = self.env['wms.return.authorization'].create({
            'name': 'RMA for Owner 2',
            'owner_id': owner2.id,
            'customer_id': customer2.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
        })

        self.assertNotEqual(rma1.owner_id.id, rma2.owner_id.id)
        self.assertNotEqual(rma1.customer_id.id, rma2.customer_id.id)
    def test_return_authorization_financial_fields(self):
        """Test financial fields in return authorization"""
        rma = self.env['wms.return.authorization'].create({
            'owner_id': self.test_owner.id,
            'customer_id': self.test_customer.id,
            'warehouse_id': self.test_warehouse.id,
            'return_reason': 'defective',
            'refund_amount': 100.0,
            'refund_reference': 'REF-001',
        })

        self.assertEqual(rma.refund_amount, 100.0)
        self.assertEqual(rma.refund_reference, 'REF-001')
        self.assertIsNone(rma.refund_date)  # Should be None initially

        # Complete the RMA to set refund_date
        rma.action_confirm()
        rma.action_receive_return()
        rma.action_approve()
        rma.action_complete()

        self.assertIsNotNone(rma.refund_date)