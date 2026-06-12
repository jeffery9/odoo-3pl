from odoo.tests import TransactionCase
from odoo import fields


class TestWmsBatchReceive(TransactionCase):
    """Test cases for WMS Batch Receive module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Batch Receive Owner',
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
            'name': 'Test Product for Batch Receive',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        # Create multiple test pickings
        self.test_picking1 = self.env['stock.picking'].create({
            'name': 'Test Picking 1 for Batch Receive',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        self.env['stock.move'].create({
            'name': 'Test Move 1',
            'product_id': self.test_product.id,
            'product_uom_qty': 100.0,
            'product_uom': self.test_uom.id,
            'picking_id': self.test_picking1.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
        })

        self.test_picking2 = self.env['stock.picking'].create({
            'name': 'Test Picking 2 for Batch Receive',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        self.env['stock.move'].create({
            'name': 'Test Move 2',
            'product_id': self.test_product.id,
            'product_uom_qty': 200.0,
            'product_uom': self.test_uom.id,
            'picking_id': self.test_picking2.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
        })
    def test_create_batch_receive(self):
        """Test creating a batch receive record"""
        batch_receive = self.env['wms.batch.receive'].create({
            'name': 'Test Batch Receive',
            'owner_id': self.test_owner.id,
            'status': 'draft',
        })

        self.assertEqual(batch_receive.name, 'Test Batch Receive')
        self.assertEqual(batch_receive.owner_id.id, self.test_owner.id)
        self.assertEqual(batch_receive.status, 'draft')
    def test_add_picking_to_batch_receive(self):
        """Test adding a picking to batch receive"""
        batch_receive = self.env['wms.batch.receive'].create({
            'name': 'Picking Add Test',
            'owner_id': self.test_owner.id,
            'status': 'draft',
        })

        batch_picking = self.env['wms.batch.receive.picking'].create({
            'batch_receive_id': batch_receive.id,
            'picking_id': self.test_picking1.id,
            'priority': 'normal',
        })

        self.assertEqual(len(batch_receive.batch_picking_ids), 1)
        self.assertEqual(batch_receive.batch_picking_ids[0].picking_id.id, self.test_picking1.id)
        self.assertEqual(batch_receive.batch_picking_ids[0].priority, 'normal')
    def test_batch_receive_status_flow(self):
        """Test the status flow of batch receive records"""
        batch_receive = self.env['wms.batch.receive'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'status': 'draft',
        })

        # Add a picking to the batch
        self.env['wms.batch.receive.picking'].create({
            'batch_receive_id': batch_receive.id,
            'picking_id': self.test_picking1.id,
            'priority': 'normal',
        })

        self.assertEqual(batch_receive.status, 'draft')

        # Start the batch receive
        batch_receive.action_start_batch_receive()
        self.assertEqual(batch_receive.status, 'in_progress')

        # Complete the batch receive
        batch_receive.action_complete_batch_receive()
        # Should be 'partial' since we didn't complete all pickings
        self.assertEqual(batch_receive.status, 'partial')
    def test_batch_picking_status_flow(self):
        """Test the status flow of individual batch pickings"""
        batch_receive = self.env['wms.batch.receive'].create({
            'name': 'Batch Picking Status Test',
            'owner_id': self.test_owner.id,
            'status': 'draft',
        })

        batch_picking = self.env['wms.batch.receive.picking'].create({
            'batch_receive_id': batch_receive.id,
            'picking_id': self.test_picking1.id,
            'priority': 'normal',
        })

        self.assertEqual(batch_picking.status, 'pending')

        # Start receiving the picking
        batch_picking.action_start_receiving()
        self.assertEqual(batch_picking.status, 'in_progress')

        # Complete receiving the picking
        batch_picking.action_complete_receiving()
        self.assertEqual(batch_picking.status, 'completed')
    def test_batch_receive_totals_computation(self):
        """Test that batch receive totals are computed correctly"""
        batch_receive = self.env['wms.batch.receive'].create({
            'name': 'Totals Computation Test',
            'owner_id': self.test_owner.id,
            'status': 'draft',
        })

        # Add multiple pickings to the batch
        self.env['wms.batch.receive.picking'].create([
            {
                'batch_receive_id': batch_receive.id,
                'picking_id': self.test_picking1.id,
                'priority': 'normal',
            },
            {
                'batch_receive_id': batch_receive.id,
                'picking_id': self.test_picking2.id,
                'priority': 'high',
            },
        ])

        # Refresh to get updated computed values
        batch_receive.refresh()

        # Check that totals are computed correctly
        self.assertEqual(batch_receive.total_pickings, 2)
        # Initially, no pickings are completed
        self.assertEqual(batch_receive.completed_pickings, 0)
        self.assertEqual(batch_receive.progress_percentage, 0.0)

        # Complete one picking
        batch_receive.batch_picking_ids[0].action_complete_receiving()
        batch_receive.refresh()

        # Now one out of two is completed (50%)
        self.assertEqual(batch_receive.completed_pickings, 1)
        self.assertEqual(batch_receive.progress_percentage, 50.0)
    def test_batch_receive_wizard(self):
        """Test creating batch receive using wizard"""
        wizard = self.env['wms.batch.receive.wizard'].create({
            'picking_ids': [(6, 0, [self.test_picking1.id, self.test_picking2.id])],
            'owner_id': self.test_owner.id,
            'priority': 'high',
        })

        result = wizard.action_create_batch_receive()

        # Verify the result is an action to open the batch receive form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.batch.receive')

        # Get the created batch receive
        batch_receive = self.env['wms.batch.receive'].browse(result['res_id'])
        self.assertEqual(batch_receive.status, 'in_progress')
        self.assertEqual(len(batch_receive.batch_picking_ids), 2)
    def test_batch_receive_add_picking_wizard(self):
        """Test adding pickings to existing batch receive using wizard"""
        batch_receive = self.env['wms.batch.receive'].create({
            'name': 'Add Picking Wizard Test',
            'owner_id': self.test_owner.id,
            'status': 'in_progress',
        })

        wizard = self.env['wms.batch.receive.add.picking.wizard'].create({
            'batch_receive_id': batch_receive.id,
            'picking_ids': [(6, 0, [self.test_picking2.id])],
            'priority': 'urgent',
        })

        wizard.action_add_pickings()

        # Check that the picking was added to the batch
        batch_receive.refresh()
        self.assertEqual(len(batch_receive.batch_picking_ids), 1)
        self.assertEqual(batch_receive.batch_picking_ids[0].picking_id.id, self.test_picking2.id)
        self.assertEqual(batch_receive.batch_picking_ids[0].priority, 'urgent')
    def test_batch_picking_computed_fields(self):
        """Test computed fields for expected and received quantities"""
        batch_receive = self.env['wms.batch.receive'].create({
            'name': 'Computed Fields Test',
            'owner_id': self.test_owner.id,
            'status': 'draft',
        })

        batch_picking = self.env['wms.batch.receive.picking'].create({
            'batch_receive_id': batch_receive.id,
            'picking_id': self.test_picking1.id,
            'priority': 'normal',
        })

        # Check expected quantity from the picking moves
        self.assertEqual(batch_picking.expected_quantity, 100.0)  # From test move

    def test_batch_receive_priorities(self):
        """Test different priority levels"""
        priorities = ['low', 'normal', 'high', 'urgent']

        for i, priority in enumerate(priorities):
            batch_receive = self.env['wms.batch.receive'].create({
                'name': f'Test Batch Priority {priority}',
                'owner_id': self.test_owner.id,
                'status': 'draft',
            })

            batch_picking = self.env['wms.batch.receive.picking'].create({
                'batch_receive_id': batch_receive.id,
                'picking_id': self.test_picking1.id,
                'priority': priority,
            })

            self.assertEqual(batch_picking.priority, priority)
    def test_batch_receive_ownership_isolation(self):
        """Test that batch receive records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Batch Receive Owner',
            'owner_code': 'SBRO',
            'is_warehouse_owner': True,
        })

        # Create pickings for each owner
        picking1_owner1 = self.env['stock.picking'].create({
            'name': 'Picking 1 for Owner 1',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })

        picking2_owner2 = self.env['stock.picking'].create({
            'name': 'Picking 2 for Owner 2',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': owner2.id,
        })

        batch_receive1 = self.env['wms.batch.receive'].create({
            'name': 'Batch Receive for Owner 1',
            'owner_id': self.test_owner.id,
        })

        batch_receive2 = self.env['wms.batch.receive'].create({
            'name': 'Batch Receive for Owner 2',
            'owner_id': owner2.id,
        })

        # Add pickings to respective batches
        self.env['wms.batch.receive.picking'].create({
            'batch_receive_id': batch_receive1.id,
            'picking_id': picking1_owner1.id,
        })

        self.env['wms.batch.receive.picking'].create({
            'batch_receive_id': batch_receive2.id,
            'picking_id': picking2_owner2.id,
        })

        self.assertNotEqual(batch_receive1.owner_id.id, batch_receive2.owner_id.id)
        self.assertNotEqual(batch_receive1.name, batch_receive2.name)
        self.assertNotEqual(len(batch_receive1.batch_picking_ids), len(batch_receive2.batch_picking_ids))