from odoo.tests import TransactionCase
from odoo import fields


class TestWmsBlindReceive(TransactionCase):
    """Test cases for WMS RF Blind Receive module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Blind Receive Owner',
            'owner_code': 'TBRO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_picking_type = self.env['stock.picking.type'].create({
            'name': 'Test Picking Type',
            'code': 'incoming',
            'sequence_code': 'IN',
            'default_location_src_id': self.test_location.id,
            'default_location_dest_id': self.test_location.id,
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Blind Receive',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        # Create a test picking
        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Blind Receive',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        # Create a stock move for the picking
        self.env['stock.move'].create({
            'name': 'Test Move',
            'product_id': self.test_product.id,
            'product_uom_qty': 100.0,
            'product_uom': self.test_uom.id,
            'picking_id': self.test_picking.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
        })
    def test_create_blind_receive_session(self):
        """Test creating a blind receive session"""
        blind_receive = self.env['wms.blind.receive'].create({
            'name': 'Test Blind Receive',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'draft',
        })

        self.assertEqual(blind_receive.name, 'Test Blind Receive')
        self.assertEqual(blind_receive.owner_id.id, self.test_owner.id)
        self.assertEqual(blind_receive.picking_id.id, self.test_picking.id)
        self.assertEqual(blind_receive.status, 'draft')
    def test_blind_receive_expected_products(self):
        """Test adding expected products to blind receive"""
        blind_receive = self.env['wms.blind.receive'].create({
            'name': 'Expected Products Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'draft',
        })

        expected_product = self.env['wms.blind.receive.expected'].create({
            'blind_receive_id': blind_receive.id,
            'product_id': self.test_product.id,
            'expected_quantity': 50.0,
            'uom_id': self.test_uom.id,
        })

        self.assertEqual(len(blind_receive.expected_products), 1)
        self.assertEqual(blind_receive.expected_products[0].product_id.id, self.test_product.id)
        self.assertEqual(blind_receive.expected_products[0].expected_quantity, 50.0)
    def test_blind_receive_received_products(self):
        """Test adding received products to blind receive"""
        blind_receive = self.env['wms.blind.receive'].create({
            'name': 'Received Products Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        received_product = self.env['wms.blind.receive.received'].create({
            'blind_receive_id': blind_receive.id,
            'product_id': self.test_product.id,
            'received_quantity': 45.0,
            'uom_id': self.test_uom.id,
        })

        self.assertEqual(len(blind_receive.received_products), 1)
        self.assertEqual(blind_receive.received_products[0].product_id.id, self.test_product.id)
        self.assertEqual(blind_receive.received_products[0].received_quantity, 45.0)
    def test_blind_receive_status_flow(self):
        """Test the status flow of blind receive sessions"""
        blind_receive = self.env['wms.blind.receive'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'draft',
        })

        self.assertEqual(blind_receive.status, 'draft')

        # Start the blind receive
        blind_receive.action_start_blind_receive()
        self.assertEqual(blind_receive.status, 'in_progress')

        # Complete the blind receive
        blind_receive.action_complete_blind_receive()
        self.assertEqual(blind_receive.status, 'completed')
    def test_blind_receive_discrepancy_calculation(self):
        """Test discrepancy calculation between expected and received products"""
        blind_receive = self.env['wms.blind.receive'].create({
            'name': 'Discrepancy Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        # Add expected product
        self.env['wms.blind.receive.expected'].create({
            'blind_receive_id': blind_receive.id,
            'product_id': self.test_product.id,
            'expected_quantity': 100.0,
            'uom_id': self.test_uom.id,
        })

        # Add received product with different quantity (creating discrepancy)
        self.env['wms.blind.receive.received'].create({
            'blind_receive_id': blind_receive.id,
            'product_id': self.test_product.id,
            'received_quantity': 95.0,  # 5 less than expected
            'uom_id': self.test_uom.id,
        })

        # Refresh to get updated computed values
        blind_receive.refresh()

        # Should have 1 discrepancy (quantity mismatch)
        self.assertEqual(blind_receive.discrepancy_count, 1)
    def test_blind_receive_cancel(self):
        """Test cancelling a blind receive session"""
        blind_receive = self.env['wms.blind.receive'].create({
            'name': 'Cancel Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'draft',
        })

        blind_receive.action_cancel_blind_receive()
        self.assertEqual(blind_receive.status, 'cancelled')
    def test_blind_receive_wizard_creation(self):
        """Test creating a blind receive session using wizard"""
        wizard = self.env['wms.blind.receive.create.wizard'].create({
            'picking_id': self.test_picking.id,
            'owner_id': self.test_owner.id,
        })

        # Call the wizard method to create the blind receive session
        result = wizard.action_create_blind_receive()

        # Verify the result is an action to open the blind receive form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.blind.receive')
        self.assertEqual(result['view_mode'], 'form')
    def test_blind_receive_wizard_add_product(self):
        """Test adding received product using wizard"""
        blind_receive = self.env['wms.blind.receive'].create({
            'name': 'Wizard Add Product Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        wizard = self.env['wms.blind.receive.wizard'].create({
            'picking_id': self.test_picking.id,
            'product_id': self.test_product.id,
            'received_quantity': 25.0,
            'blind_receive_id': blind_receive.id,
        })

        # Call the wizard method to add the received product
        wizard.action_add_received_product()

        # Verify the product was added
        self.assertEqual(len(blind_receive.received_products), 1)
        self.assertEqual(blind_receive.received_products[0].received_quantity, 25.0)
    def test_blind_receive_ownership_isolation(self):
        """Test that blind receive sessions are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Blind Receive Owner',
            'owner_code': 'SBRO',
            'is_warehouse_owner': True,
        })

        # Create pickings for each owner
        picking1 = self.env['stock.picking'].create({
            'name': 'Picking for Owner 1',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        picking2 = self.env['stock.picking'].create({
            'name': 'Picking for Owner 2',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': owner2.id,
        })

        blind_receive1 = self.env['wms.blind.receive'].create({
            'name': 'Blind Receive for Owner 1',
            'owner_id': self.test_owner.id,
            'picking_id': picking1.id,
        })

        blind_receive2 = self.env['wms.blind.receive'].create({
            'name': 'Blind Receive for Owner 2',
            'owner_id': owner2.id,
            'picking_id': picking2.id,
        })

        self.assertNotEqual(blind_receive1.owner_id.id, blind_receive2.owner_id.id)
        self.assertNotEqual(blind_receive1.name, blind_receive2.name)
        self.assertNotEqual(blind_receive1.picking_id.id, blind_receive2.picking_id.id)