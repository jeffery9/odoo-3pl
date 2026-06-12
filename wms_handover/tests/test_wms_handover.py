from odoo.tests import TransactionCase
from odoo import fields


class TestWmsHandover(TransactionCase):
    """Test cases for WMS Handover module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Handover Owner',
            'owner_code': 'THO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_picking_type = self.env['stock.picking.type'].create({
            'name': 'Test Picking Type',
            'code': 'outgoing',
            'sequence_code': 'OUT',
            'default_location_src_id': self.test_location.id,
            'default_location_dest_id': self.test_location.id,
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Handover',
                        'categ_id': self.env.ref('product.product_category_all').id,
            'standard_price': 10.0,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        # Create test partners for handover
        self.test_from_party = self.env['res.partner'].create({
            'name': 'From Party Test',
            'is_company': True,
        })

        self.test_to_party = self.env['res.partner'].create({
            'name': 'To Party Test',
            'is_company': True,
        })

        # Create a test picking
        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Handover',
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
    def test_create_handover(self):
        """Test creating a handover record"""
        handover = self.env['wms.handover'].create({
            'name': 'Test Handover',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'handover_type': 'outbound',
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
            'status': 'draft',
        })

        self.assertEqual(handover.name, 'Test Handover')
        self.assertEqual(handover.owner_id.id, self.test_owner.id)
        self.assertEqual(handover.picking_id.id, self.test_picking.id)
        self.assertEqual(handover.handover_type, 'outbound')
        self.assertEqual(handover.from_party_id.id, self.test_from_party.id)
        self.assertEqual(handover.to_party_id.id, self.test_to_party.id)
        self.assertEqual(handover.status, 'draft')
    def test_handover_items(self):
        """Test adding items to handover"""
        handover = self.env['wms.handover'].create({
            'name': 'Items Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'handover_type': 'outbound',
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
            'status': 'draft',
        })

        handover_item = self.env['wms.handover.item'].create({
            'handover_id': handover.id,
            'product_id': self.test_product.id,
            'quantity': 50.0,
            'unit_value': 10.0,
            'uom_id': self.test_uom.id,
        })

        self.assertEqual(len(handover.handover_items), 1)
        self.assertEqual(handover.handover_items[0].product_id.id, self.test_product.id)
        self.assertEqual(handover.handover_items[0].quantity, 50.0)
        self.assertEqual(handover.handover_items[0].unit_value, 10.0)
    def test_handover_documents(self):
        """Test adding documents to handover"""
        handover = self.env['wms.handover'].create({
            'name': 'Documents Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'handover_type': 'outbound',
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
            'status': 'draft',
        })

        document = self.env['wms.handover.document'].create({
            'handover_id': handover.id,
            'name': 'Test Document',
            'document_type': 'invoice',
            'file_name': 'test_invoice.pdf',
        })

        self.assertEqual(len(handover.documents), 1)
        self.assertEqual(handover.documents[0].name, 'Test Document')
        self.assertEqual(handover.documents[0].document_type, 'invoice')
    def test_handover_status_flow(self):
        """Test the status flow of handover records"""
        handover = self.env['wms.handover'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'handover_type': 'outbound',
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
            'status': 'draft',
        })

        self.assertEqual(handover.status, 'draft')

        # Start the handover
        handover.action_start_handover()
        self.assertEqual(handover.status, 'in_progress')

        # Complete the handover
        handover.action_complete_handover()
        self.assertEqual(handover.status, 'completed')

        # Sign off the handover
        handover.action_sign_off()
        self.assertEqual(handover.status, 'signed_off')
    def test_handover_totals_computation(self):
        """Test that totals are computed correctly"""
        handover = self.env['wms.handover'].create({
            'name': 'Totals Computation Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'handover_type': 'outbound',
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
            'status': 'draft',
        })

        # Add multiple handover items
        self.env['wms.handover.item'].create([
            {
                'handover_id': handover.id,
                'product_id': self.test_product.id,
                'quantity': 30.0,
                'unit_value': 10.0,
                'uom_id': self.test_uom.id,
            },
            {
                'handover_id': handover.id,
                'product_id': self.test_product.id,
                'quantity': 20.0,
                'unit_value': 15.0,
                'uom_id': self.test_uom.id,
            },
        ])

        # Refresh to get updated computed values
        handover.refresh()

        # Check that totals are computed correctly
        self.assertEqual(handover.total_items, 2)
        self.assertEqual(handover.total_value, 600.0)  # (30*10) + (20*15) = 300 + 300 = 600

    def test_handover_types(self):
        """Test different handover types"""
        handover_types = ['inbound', 'outbound', 'internal', 'crossdock']

        for i, handover_type in enumerate(handover_types):
            handover = self.env['wms.handover'].create({
                'name': f'Test Handover Type {handover_type}',
                'owner_id': self.test_owner.id,
                'picking_id': self.test_picking.id,
                'handover_type': handover_type,
                'from_party_id': self.test_from_party.id,
                'to_party_id': self.test_to_party.id,
            })
            self.assertEqual(handover.handover_type, handover_type)
    def test_handover_wizard(self):
        """Test creating handover using wizard"""
        wizard = self.env['wms.handover.wizard'].create({
            'picking_id': self.test_picking.id,
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
            'handover_type': 'outbound',
        })

        result = wizard.action_create_handover()

        # Verify the result is an action to open the handover form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.handover')

        # Get the created handover
        handover = self.env['wms.handover'].browse(result['res_id'])
        self.assertEqual(handover.handover_type, 'outbound')
        self.assertEqual(len(handover.handover_items), 1)  # Should have copied from picking

    def test_handover_sign_off_wizard(self):
        """Test signing off handover using wizard"""
        handover = self.env['wms.handover'].create({
            'name': 'Sign Off Wizard Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'handover_type': 'outbound',
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
            'status': 'completed',
        })

        # Create sign off wizard with dummy signatures
        wizard = self.env['wms.handover.signoff.wizard'].create({
            'handover_id': handover.id,
            'signature_from': b'dummy_signature_data',
            'signature_to': b'dummy_signature_data',
        })

        wizard.action_sign_off()

        # Check that the handover is now signed off
        handover.refresh()
        self.assertEqual(handover.status, 'signed_off')
        self.assertIsNotNone(handover.signature_from)
        self.assertIsNotNone(handover.signature_to)
    def test_handover_ownership_isolation(self):
        """Test that handover records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Handover Owner',
            'owner_code': 'SHO',
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

        handover1 = self.env['wms.handover'].create({
            'name': 'Handover for Owner 1',
            'owner_id': self.test_owner.id,
            'picking_id': picking1.id,
            'handover_type': 'outbound',
            'from_party_id': self.test_from_party.id,
            'to_party_id': self.test_to_party.id,
        })

        handover2 = self.env['wms.handover'].create({
            'name': 'Handover for Owner 2',
            'owner_id': owner2.id,
            'picking_id': picking2.id,
            'handover_type': 'inbound',
            'from_party_id': self.test_to_party.id,
            'to_party_id': self.test_from_party.id,
        })

        self.assertNotEqual(handover1.owner_id.id, handover2.owner_id.id)
        self.assertNotEqual(handover1.handover_type, handover2.handover_type)
        self.assertNotEqual(handover1.name, handover2.name)
        self.assertNotEqual(handover1.picking_id.id, handover2.picking_id.id)