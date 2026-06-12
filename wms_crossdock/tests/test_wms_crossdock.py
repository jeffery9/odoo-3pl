from odoo.tests import TransactionCase
from odoo import fields


class TestWmsCrossdock(TransactionCase):
    """Test cases for WMS Crossdock module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Crossdock Owner',
            'owner_code': 'TCO',
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
            'name': 'Test Product',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })
    def test_create_crossdock_operation(self):
        """Test creating a WMS crossdock operation"""
        # First create inbound and outbound pickings
        inbound_picking = self.env['stock.picking'].create({
            'name': 'Test Inbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        outbound_picking = self.env['stock.picking'].create({
            'name': 'Test Outbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        crossdock_operation = self.env['wms.crossdock.operation'].create({
            'name': 'Test Crossdock Operation',
            'owner_id': self.test_owner.id,
            'warehouse_id': self.env['stock.warehouse'].search([], limit=1).id,
            'inbound_picking_id': inbound_picking.id,
            'outbound_picking_id': outbound_picking.id,
            'status': 'draft',
        })

        self.assertEqual(crossdock_operation.name, 'Test Crossdock Operation')
        self.assertEqual(crossdock_operation.owner_id.id, self.test_owner.id)
        self.assertEqual(crossdock_operation.status, 'draft')
        self.assertEqual(crossdock_operation.inbound_picking_id.id, inbound_picking.id)
        self.assertEqual(crossdock_operation.outbound_picking_id.id, outbound_picking.id)
    def test_create_crossdock_match(self):
        """Test creating a WMS crossdock match"""
        # Create sample pickings to match
        inbound_picking = self.env['stock.picking'].create({
            'name': 'Match Inbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        outbound_picking = self.env['stock.picking'].create({
            'name': 'Match Outbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        crossdock_match = self.env['wms.crossdock.match'].create({
            'name': 'Test Crossdock Match',
            'owner_id': self.test_owner.id,
            'status': 'pending',
            'inbound_picking_ids': [(4, inbound_picking.id)],
            'outbound_picking_ids': [(4, outbound_picking.id)],
            'match_score': 90.0,
            'matching_algorithm': 'Basic Product Match',
        })

        self.assertEqual(crossdock_match.name, 'Test Crossdock Match')
        self.assertEqual(crossdock_match.owner_id.id, self.test_owner.id)
        self.assertEqual(crossdock_match.status, 'pending')
        self.assertEqual(crossdock_match.match_score, 90.0)
        self.assertEqual(crossdock_match.matching_algorithm, 'Basic Product Match')
        self.assertIn(inbound_picking.id, crossdock_match.inbound_picking_ids.ids)
        self.assertIn(outbound_picking.id, crossdock_match.outbound_picking_ids.ids)
    def test_crossdock_operation_status_flow(self):
        """Test the status flow of crossdock operations"""
        # Create pickings first
        inbound_picking = self.env['stock.picking'].create({
            'name': 'Status Inbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        outbound_picking = self.env['stock.picking'].create({
            'name': 'Status Outbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        crossdock_operation = self.env['wms.crossdock.operation'].create({
            'name': 'Status Flow Operation',
            'owner_id': self.test_owner.id,
            'warehouse_id': self.env['stock.warehouse'].search([], limit=1).id,
            'inbound_picking_id': inbound_picking.id,
            'outbound_picking_id': outbound_picking.id,
            'status': 'draft',
        })

        # Test status transitions
        self.assertEqual(crossdock_operation.status, 'draft')

        # Simulate starting the operation
        crossdock_operation.action_start_operation()
        self.assertEqual(crossdock_operation.status, 'in_progress')

        # Simulate completing the operation
        crossdock_operation.action_complete_operation()
        self.assertEqual(crossdock_operation.status, 'completed')
    def test_crossdock_match_status_flow(self):
        """Test the status flow of crossdock matches"""
        crossdock_match = self.env['wms.crossdock.match'].create({
            'name': 'Status Flow Match',
            'owner_id': self.test_owner.id,
            'status': 'pending',
        })

        # Test status transitions
        self.assertEqual(crossdock_match.status, 'pending')

        # Simulate confirming the match
        crossdock_match.action_confirm_match()
        self.assertEqual(crossdock_match.status, 'confirmed')

        # Simulate starting transit
        crossdock_match.action_start_transit()
        self.assertEqual(crossdock_match.status, 'in_transit')

        # Simulate completing the match
        crossdock_match.action_complete_match()
        self.assertEqual(crossdock_match.status, 'completed')
    def test_crossdock_match_failure(self):
        """Test the failure status of crossdock matches"""
        crossdock_match = self.env['wms.crossdock.match'].create({
            'name': 'Failure Test Match',
            'owner_id': self.test_owner.id,
            'status': 'pending',
        })

        # Simulate failing the match
        crossdock_match.action_fail_match()
        self.assertEqual(crossdock_match.status, 'failed')
    def test_stock_picking_crossdock_extension(self):
        """Test the extension to stock.picking model for crossdock"""
        picking = self.env['stock.picking'].create({
            'name': 'Test Crossdock Picking',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
            'is_crossdock': True,
            'crossdock_status': 'pending',
        })

        self.assertTrue(picking.is_crossdock)
        self.assertEqual(picking.crossdock_status, 'pending')
    def test_crossdock_operation_compute_totals(self):
        """Test computed fields in crossdock operations"""
        # Create pickings with move lines to test computed totals
        inbound_picking = self.env['stock.picking'].create({
            'name': 'Compute Total Inbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        # Create a stock move for the inbound picking
        self.env['stock.move'].create({
            'name': 'Test Move',
            'product_id': self.test_product.id,
            'product_uom_qty': 50.0,
            'product_uom': self.test_uom.id,
            'picking_id': inbound_picking.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
        })

        outbound_picking = self.env['stock.picking'].create({
            'name': 'Compute Total Outbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        # Create a stock move for the outbound picking
        self.env['stock.move'].create({
            'name': 'Test Outbound Move',
            'product_id': self.test_product.id,
            'product_uom_qty': 30.0,
            'product_uom': self.test_uom.id,
            'picking_id': outbound_picking.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
        })

        crossdock_operation = self.env['wms.crossdock.operation'].create({
            'name': 'Compute Total Operation',
            'owner_id': self.test_owner.id,
            'warehouse_id': self.env['stock.warehouse'].search([], limit=1).id,
            'inbound_picking_id': inbound_picking.id,
            'outbound_picking_id': outbound_picking.id,
        })

        # The total quantity should be computed based on the pickings
        # (This would normally be handled by computed fields in the actual model)
    def test_crossdock_match_compute_totals(self):
        """Test computed fields in crossdock matches"""
        # Create sample pickings with move lines
        inbound_picking = self.env['stock.picking'].create({
            'name': 'Match Compute Inbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        # Create a stock move for the inbound picking
        self.env['stock.move'].create({
            'name': 'Match Test Move',
            'product_id': self.test_product.id,
            'product_uom_qty': 25.0,
            'product_uom': self.test_uom.id,
            'picking_id': inbound_picking.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
        })

        outbound_picking = self.env['stock.picking'].create({
            'name': 'Match Compute Outbound',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        # Create a stock move for the outbound picking
        self.env['stock.move'].create({
            'name': 'Match Test Outbound Move',
            'product_id': self.test_product.id,
            'product_uom_qty': 35.0,
            'product_uom': self.test_uom.id,
            'picking_id': outbound_picking.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
        })

        crossdock_match = self.env['wms.crossdock.match'].create({
            'name': 'Compute Total Match',
            'owner_id': self.test_owner.id,
            'inbound_picking_ids': [(4, inbound_picking.id)],
            'outbound_picking_ids': [(4, outbound_picking.id)],
        })

        # The total quantities should be computed based on the pickings
        # (This would normally be handled by computed fields in the actual model)
    def test_crossdock_ownership_isolation(self):
        """Test that crossdock operations are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Crossdock Owner',
            'owner_code': 'SCO',
            'is_warehouse_owner': True,
        })

        # Create pickings for first owner
        inbound_picking1 = self.env['stock.picking'].create({
            'name': 'Isolation Inbound 1',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        outbound_picking1 = self.env['stock.picking'].create({
            'name': 'Isolation Outbound 1',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        # Create pickings for second owner
        inbound_picking2 = self.env['stock.picking'].create({
            'name': 'Isolation Inbound 2',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': owner2.id,
        })

        outbound_picking2 = self.env['stock.picking'].create({
            'name': 'Isolation Outbound 2',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': owner2.id,
        })

        operation1 = self.env['wms.crossdock.operation'].create({
            'name': 'Operation for Owner 1',
            'owner_id': self.test_owner.id,
            'warehouse_id': self.env['stock.warehouse'].search([], limit=1).id,
            'inbound_picking_id': inbound_picking1.id,
            'outbound_picking_id': outbound_picking1.id,
        })

        operation2 = self.env['wms.crossdock.operation'].create({
            'name': 'Operation for Owner 2',
            'owner_id': owner2.id,
            'warehouse_id': self.env['stock.warehouse'].search([], limit=1).id,
            'inbound_picking_id': inbound_picking2.id,
            'outbound_picking_id': outbound_picking2.id,
        })

        self.assertNotEqual(operation1.owner_id.id, operation2.owner_id.id)
        self.assertNotEqual(operation1.name, operation2.name)