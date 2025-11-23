from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


@tagged('wms_courier', 'at_install')
class TestWmsCourier(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsCourierCompany = self.env['wms.courier.company']
        self.WmsCourierService = self.env['wms.courier.service']
        self.WmsShipmentOrder = self.env['wms.shipment.order']
        self.WmsShipmentProductLine = self.env['wms.shipment.product.line']
        self.Warehouse = self.env['stock.warehouse']
        self.Location = self.env['stock.location']
        self.Product = self.env['product.product']
        self.Owner = self.env['wms.owner']
        self.Picking = self.env['stock.picking']
        self.ProductCategory = self.env['product.category']

        # Create a test warehouse
        self.warehouse = self.Warehouse.create({
            'name': 'Test Warehouse',
            'code': 'TST'
        })

        # Create a test owner
        self.owner = self.Owner.create({
            'name': 'Test Owner',
            'code': 'TO',
            'email': 'test@example.com'
        })

        # Create test product category
        self.category = self.ProductCategory.create({
            'name': 'Test Category'
        })

        # Create test products
        self.product1 = self.Product.create({
            'name': 'Test Product 1',
            'type': 'product',
            'default_code': 'TEST001',
            'list_price': 10.0,
            'standard_price': 5.0,
            'weight': 1.0,
            'volume': 0.01,
            'length': 10,
            'width': 10,
            'height': 10
        })

        self.product2 = self.Product.create({
            'name': 'Test Product 2',
            'type': 'product',
            'default_code': 'TEST002',
            'list_price': 20.0,
            'standard_price': 10.0,
            'weight': 2.0,
            'volume': 0.02,
            'length': 15,
            'width': 15,
            'height': 15
        })

        # Create test courier company
        self.courier_company = self.WmsCourierCompany.create({
            'name': 'Test Courier Company',
            'code': 'TCC001',
            'contact_email': 'contact@courier.com',
            'contact_phone': '+1234567890',
            'website': 'https://courier.example.com',
            'tracking_prefix': 'TCC',
            'supports_cod': True,
            'supports_insurance': True,
            'supports_signature': True,
        })

        # Create test courier service
        self.courier_service = self.WmsCourierService.create({
            'name': 'Test Express Service',
            'code': 'TES001',
            'courier_company_id': self.courier_company.id,
            'service_type': 'express',
            'base_cost': 5.0,
            'cost_per_kg': 2.0,
            'cost_per_km': 0.1,
            'delivery_time_days': 2,
            'is_integrated': True,
            'requires_label_print': True,
            'requires_pickup': False,
        })

    def test_courier_company_creation(self):
        """Test creation of courier company records"""
        company = self.WmsCourierCompany.create({
            'name': 'Another Courier Company',
            'code': 'ACC002',
            'contact_email': 'contact@anothercourier.com',
            'contact_phone': '+0987654321',
            'website': 'https://anothercourier.example.com',
            'tracking_prefix': 'ACC',
            'supports_cod': False,
            'supports_insurance': True,
            'supports_signature': False,
        })

        self.assertEqual(company.name, 'Another Courier Company')
        self.assertEqual(company.code, 'ACC002')
        self.assertEqual(company.contact_email, 'contact@anothercourier.com')
        self.assertTrue(company.supports_insurance)
        self.assertTrue(company.active)

    def test_courier_service_creation(self):
        """Test creation of courier service records"""
        service = self.WmsCourierService.create({
            'name': 'Test Standard Service',
            'code': 'TSS002',
            'courier_company_id': self.courier_company.id,
            'service_type': 'standard',
            'base_cost': 3.0,
            'cost_per_kg': 1.5,
            'delivery_time_days': 5,
        })

        self.assertEqual(service.name, 'Test Standard Service')
        self.assertEqual(service.code, 'TSS002')
        self.assertEqual(service.courier_company_id.id, self.courier_company.id)
        self.assertEqual(service.service_type, 'standard')
        self.assertEqual(service.base_cost, 3.0)
        self.assertTrue(service.active)

    def test_courier_service_constraints(self):
        """Test courier service constraints"""
        # Test that service_type is required
        with self.assertRaises(ValidationError):
            self.WmsCourierService.create({
                'name': 'Invalid Service',
                'code': 'IS003',
                'courier_company_id': self.courier_company.id,
                'service_type': None,  # This should cause validation error
                'base_cost': 5.0,
            })

    def test_shipment_order_creation(self):
        """Test creation of shipment order records"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'sender_city': 'Sender City',
            'sender_state': 'Sender State',
            'sender_zip': '12345',
            'sender_country': 'Sender Country',
            'recipient_city': 'Recipient City',
            'recipient_state': 'Recipient State',
            'recipient_zip': '67890',
            'recipient_country': 'Recipient Country',
            'package_weight': 5.0,
            'package_length': 30.0,
            'package_width': 20.0,
            'package_height': 15.0,
            'declared_value': 100.0,
        })

        self.assertEqual(shipment.courier_company_id.id, self.courier_company.id)
        self.assertEqual(shipment.courier_service_id.id, self.courier_service.id)
        self.assertEqual(shipment.package_weight, 5.0)
        self.assertEqual(shipment.state, 'draft')
        self.assertEqual(shipment.package_volume, 0.009)  # (30*20*15)/1000000

    def test_shipment_order_state_transitions(self):
        """Test shipment order state transitions"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 2.0,
            'declared_value': 50.0,
        })

        # Initially should be in draft
        self.assertEqual(shipment.state, 'draft')

        # Confirm the shipment
        shipment.action_confirm_shipment()
        self.assertEqual(shipment.state, 'confirmed')
        self.assertIsNotNone(shipment.date_confirmed)

        # Ship the shipment
        shipment.action_ship_shipment()
        self.assertEqual(shipment.state, 'in_transit')
        self.assertIsNotNone(shipment.date_shipped)

        # Deliver the shipment
        shipment.action_deliver_shipment()
        self.assertEqual(shipment.state, 'delivered')
        self.assertIsNotNone(shipment.date_delivered)

    def test_shipment_order_cost_calculation(self):
        """Test shipment order cost calculation"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 3.0,  # 3kg
            'base_cost': 5.0,  # Base cost from service: 5.0
            'weight_cost': 6.0,  # 3kg * 2.0 per kg = 6.0
            'distance_cost': 5.0,  # 50km * 0.1 per km = 5.0
            'other_charges': 2.0,
        })

        # Total cost should be 5.0 + 6.0 + 5.0 + 2.0 = 18.0
        expected_total = 5.0 + 6.0 + 5.0 + 2.0
        self.assertEqual(shipment.total_cost, expected_total)

    def test_shipment_product_line_creation(self):
        """Test creation of shipment product line records"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 2.0,
        })

        product_line = self.WmsShipmentProductLine.create({
            'shipment_id': shipment.id,
            'product_id': self.product1.id,
            'quantity': 10.0,
            'unit_value': 10.0,
        })

        self.assertEqual(product_line.shipment_id.id, shipment.id)
        self.assertEqual(product_line.product_id.id, self.product1.id)
        self.assertEqual(product_line.quantity, 10.0)
        self.assertEqual(product_line.unit_value, 10.0)
        self.assertEqual(product_line.total_value, 100.0)  # quantity * unit_value

    def test_shipment_product_line_onchange(self):
        """Test onchange methods for shipment product lines"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 2.0,
        })

        # Create a product line without specifying unit_value
        product_line = self.WmsShipmentProductLine.create({
            'shipment_id': shipment.id,
            'product_id': self.product1.id,
            'quantity': 5.0,
        })

        # The unit_value should be automatically set from the product's list_price
        self.assertEqual(product_line.unit_value, self.product1.list_price)
        self.assertEqual(product_line.total_value, 50.0)  # 5 * 10.0

    def test_shipment_order_total_value_calculation(self):
        """Test total value calculation for shipment orders"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 2.0,
        })

        # Add product lines to the shipment
        line1 = self.WmsShipmentProductLine.create({
            'shipment_id': shipment.id,
            'product_id': self.product1.id,
            'quantity': 5.0,
            'unit_value': 10.0,
        })

        line2 = self.WmsShipmentProductLine.create({
            'shipment_id': shipment.id,
            'product_id': self.product2.id,
            'quantity': 3.0,
            'unit_value': 20.0,
        })

        # Total value should be (5 * 10) + (3 * 20) = 110
        expected_total = 50.0 + 60.0
        self.assertEqual(shipment.total_value, expected_total)

    def test_shipment_tracking(self):
        """Test shipment tracking functionality"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'tracking_number': '123456789',
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 2.0,
        })

        # Mock tracking number
        shipment.tracking_number = '123456789'

        # The action_track_shipment should return an action dictionary
        action = shipment.action_track_shipment()
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertIn('TCC123456789', action['url'])

    def test_onchange_courier_company(self):
        """Test onchange method for courier company"""
        shipment = self.WmsShipmentOrder.new({
            'courier_company_id': self.courier_company.id,
        })

        # When courier company changes, it should return domain for services
        result = shipment._onchange_courier_company()
        if result:
            self.assertIn('domain', result)
            self.assertIn('courier_service_id', result['domain'])

    def test_shipment_order_cancellation(self):
        """Test cancellation of shipment orders"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 2.0,
            'state': 'confirmed'
        })

        # Initially should be confirmed
        self.assertEqual(shipment.state, 'confirmed')

        # Cancel operation would require a manual state change in this model
        # since there's no dedicated cancel action
        shipment.write({'state': 'cancelled'})
        self.assertEqual(shipment.state, 'cancelled')

    def test_shipment_order_insurance_features(self):
        """Test insurance and special service features"""
        shipment = self.WmsShipmentOrder.create({
            'courier_company_id': self.courier_company.id,
            'courier_service_id': self.courier_service.id,
            'sender_address': '123 Sender St, City, State 12345',
            'recipient_address': '456 Recipient St, City, State 67890',
            'package_weight': 2.0,
            'is_insured': True,
            'insurance_value': 150.0,
            'requires_signature': True,
            'is_cod': True,
            'cod_amount': 200.0,
        })

        self.assertTrue(shipment.is_insured)
        self.assertEqual(shipment.insurance_value, 150.0)
        self.assertTrue(shipment.requires_signature)
        self.assertTrue(shipment.is_cod)
        self.assertEqual(shipment.cod_amount, 200.0)

    def test_courier_company_services_relationship(self):
        """Test the relationship between courier companies and services"""
        # Verify that the service is linked to the company
        self.assertEqual(len(self.courier_company.service_ids), 1)
        self.assertEqual(self.courier_company.service_ids[0].id, self.courier_service.id)

        # Create another service for the same company
        new_service = self.WmsCourierService.create({
            'name': 'Test Standard Service',
            'code': 'TSS002',
            'courier_company_id': self.courier_company.id,
            'service_type': 'standard',
            'base_cost': 3.0,
        })

        # Verify both services are linked to the company
        self.assertEqual(len(self.courier_company.service_ids), 2)
        service_ids = [s.id for s in self.courier_company.service_ids]
        self.assertIn(self.courier_service.id, service_ids)
        self.assertIn(new_service.id, service_ids)