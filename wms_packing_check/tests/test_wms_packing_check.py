from odoo.tests import TransactionCase
from odoo import fields


class TestWmsPackingCheck(TransactionCase):
    """Test cases for WMS Packing Check module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Packing Check Owner',
            'owner_code': 'TPCO',
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
            'name': 'Test Product for Packing Check',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        # Create a test picking
        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Packing Check',
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
    def test_create_packing_check(self):
        """Test creating a packing check record"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Test Packing Check',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'draft',
        })

        self.assertEqual(packing_check.name, 'Test Packing Check')
        self.assertEqual(packing_check.owner_id.id, self.test_owner.id)
        self.assertEqual(packing_check.picking_id.id, self.test_picking.id)
        self.assertEqual(packing_check.status, 'draft')
    def test_packing_check_required_items(self):
        """Test adding required items to packing check"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Required Items Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'draft',
        })

        required_item = self.env['wms.packing.check.required'].create({
            'packing_check_id': packing_check.id,
            'product_id': self.test_product.id,
            'expected_quantity': 50.0,
            'uom_id': self.test_uom.id,
        })

        self.assertEqual(len(packing_check.required_checks), 1)
        self.assertEqual(packing_check.required_checks[0].product_id.id, self.test_product.id)
        self.assertEqual(packing_check.required_checks[0].expected_quantity, 50.0)
    def test_packing_check_performed_items(self):
        """Test adding performed items to packing check"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Performed Items Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        performed_check = self.env['wms.packing.check.performed'].create({
            'packing_check_id': packing_check.id,
            'product_id': self.test_product.id,
            'checked_quantity': 45.0,
            'result': 'pass',
            'uom_id': self.test_uom.id,
        })

        self.assertEqual(len(packing_check.performed_checks), 1)
        self.assertEqual(packing_check.performed_checks[0].product_id.id, self.test_product.id)
        self.assertEqual(packing_check.performed_checks[0].checked_quantity, 45.0)
        self.assertEqual(packing_check.performed_checks[0].result, 'pass')
    def test_packing_check_status_flow(self):
        """Test the status flow of packing check records"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'draft',
        })

        self.assertEqual(packing_check.status, 'draft')

        # Start the packing check
        packing_check.action_start_check()
        self.assertEqual(packing_check.status, 'in_progress')

        # Add some performed checks to simulate the process
        self.env['wms.packing.check.performed'].create({
            'packing_check_id': packing_check.id,
            'product_id': self.test_product.id,
            'checked_quantity': 100.0,
            'result': 'pass',
            'uom_id': self.test_uom.id,
        })

        # Complete the packing check (should pass since all items pass)
        packing_check.action_complete_check()
        self.assertEqual(packing_check.status, 'passed')
    def test_packing_check_with_failed_items(self):
        """Test packing check with failed items"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Failed Items Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        # Add a passed item
        self.env['wms.packing.check.performed'].create({
            'packing_check_id': packing_check.id,
            'product_id': self.test_product.id,
            'checked_quantity': 50.0,
            'result': 'pass',
            'uom_id': self.test_uom.id,
        })

        # Add a failed item
        self.env['wms.packing.check.performed'].create({
            'packing_check_id': packing_check.id,
            'product_id': self.test_product.id,
            'checked_quantity': 50.0,
            'result': 'fail',
            'uom_id': self.test_uom.id,
        })

        # Refresh to get updated computed values
        packing_check.refresh()

        # Complete the packing check (should fail due to failed items)
        packing_check.action_complete_check()
        # Since we have 50% failure rate, it should fail based on the 95% threshold
        self.assertEqual(packing_check.status, 'failed')
        self.assertEqual(packing_check.pass_rate, 50.0)
    def test_packing_check_totals_computation(self):
        """Test that totals are computed correctly"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Totals Computation Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        # Add multiple performed checks
        self.env['wms.packing.check.performed'].create([
            {
                'packing_check_id': packing_check.id,
                'product_id': self.test_product.id,
                'checked_quantity': 30.0,
                'result': 'pass',
                'uom_id': self.test_uom.id,
            },
            {
                'packing_check_id': packing_check.id,
                'product_id': self.test_product.id,
                'checked_quantity': 10.0,
                'result': 'fail',
                'uom_id': self.test_uom.id,
            },
            {
                'packing_check_id': packing_check.id,
                'product_id': self.test_product.id,
                'checked_quantity': 5.0,
                'result': 'pass',
                'uom_id': self.test_uom.id,
            },
        ])

        # Refresh to get updated computed values
        packing_check.refresh()

        # Check that totals are computed correctly
        self.assertEqual(packing_check.total_items, 3)
        self.assertEqual(packing_check.passed_items, 2)
        self.assertEqual(packing_check.failed_items, 1)
        self.assertAlmostEqual(packing_check.pass_rate, 66.67, places=2)  # 2/3 = 66.67%

    def test_packing_check_manual_approval_rejection(self):
        """Test manual approval and rejection of packing checks"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Manual Approval Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        # Manually approve the packing check
        packing_check.action_approve_check()
        self.assertEqual(packing_check.status, 'passed')

        # Create another packing check to test rejection
        packing_check2 = self.env['wms.packing.check'].create({
            'name': 'Manual Rejection Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        # Manually reject the packing check
        packing_check2.action_reject_check()
        self.assertEqual(packing_check2.status, 'failed')
    def test_packing_check_wizard(self):
        """Test creating performed checks using wizard"""
        packing_check = self.env['wms.packing.check'].create({
            'name': 'Wizard Test',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'status': 'in_progress',
        })

        wizard = self.env['wms.packing.check.wizard'].create({
            'packing_check_id': packing_check.id,
            'product_id': self.test_product.id,
            'checked_quantity': 25.0,
            'result': 'pass',
        })

        # Call the wizard method to add the performed check
        wizard.action_add_performed_check()

        # Verify the check was added
        self.assertEqual(len(packing_check.performed_checks), 1)
        self.assertEqual(packing_check.performed_checks[0].checked_quantity, 25.0)
        self.assertEqual(packing_check.performed_checks[0].result, 'pass')
    def test_start_packing_check_wizard(self):
        """Test creating packing check using start wizard"""
        wizard = self.env['wms.start.packing.check.wizard'].create({
            'picking_id': self.test_picking.id,
            'owner_id': self.test_owner.id,
        })

        # Call the wizard method to create the packing check
        result = wizard.action_create_packing_check()

        # Verify the result is an action to open the packing check form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.packing.check')

        # Get the created packing check
        packing_check = self.env['wms.packing.check'].browse(result['res_id'])
        self.assertEqual(packing_check.status, 'in_progress')
    def test_packing_check_ownership_isolation(self):
        """Test that packing check records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Packing Check Owner',
            'owner_code': 'SPCO',
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

        packing_check1 = self.env['wms.packing.check'].create({
            'name': 'Packing Check for Owner 1',
            'owner_id': self.test_owner.id,
            'picking_id': picking1.id,
        })

        packing_check2 = self.env['wms.packing.check'].create({
            'name': 'Packing Check for Owner 2',
            'owner_id': owner2.id,
            'picking_id': picking2.id,
        })

        self.assertNotEqual(packing_check1.owner_id.id, packing_check2.owner_id.id)
        self.assertNotEqual(packing_check1.name, packing_check2.name)
        self.assertNotEqual(packing_check1.picking_id.id, packing_check2.picking_id.id)