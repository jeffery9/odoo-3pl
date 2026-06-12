from odoo.tests import TransactionCase
from odoo import fields


class TestWmsQualityControl(TransactionCase):
    """Test cases for WMS Quality Control module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Quality Control Owner',
            'owner_code': 'TQCO',
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
            'name': 'Test Product for Quality Control',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')

        # Create a test picking
        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Quality Control',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })
    def test_create_quality_control_session(self):
        """Test creating a quality control session"""
        qc_session = self.env['wms.quality.control'].create({
            'name': 'Test QC Session',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'date_start': fields.Datetime.now(),
            'status': 'draft',
        })

        self.assertEqual(qc_session.name, 'Test QC Session')
        self.assertEqual(qc_session.control_type, 'incoming')
        self.assertEqual(qc_session.owner_id.id, self.test_owner.id)
        self.assertEqual(qc_session.picking_id.id, self.test_picking.id)
        self.assertEqual(qc_session.status, 'draft')
    def test_quality_control_status_flow(self):
        """Test the status flow of quality control sessions"""
        qc_session = self.env['wms.quality.control'].create({
            'name': 'Status Flow Test',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'date_start': fields.Datetime.now(),
            'status': 'draft',
        })

        self.assertEqual(qc_session.status, 'draft')

        # Start the quality control
        qc_session.action_start_qc()
        self.assertEqual(qc_session.status, 'in_progress')

        # Complete the quality control
        qc_session.action_complete_qc()
        self.assertEqual(qc_session.status, 'passed')

        # Reset to draft
        qc_session.action_reset_to_draft()
        self.assertEqual(qc_session.status, 'draft')
    def test_quality_checklist_creation(self):
        """Test creating quality checklist items"""
        qc_session = self.env['wms.quality.control'].create({
            'name': 'Checklist Test',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'date_start': fields.Datetime.now(),
            'status': 'in_progress',
        })

        checklist_item = self.env['wms.quality.checklist'].create({
            'qc_session_id': qc_session.id,
            'item_id': 'Visual Inspection',
            'result': 'pass',
            'criticality': 'major',
        })

        self.assertEqual(len(qc_session.checklist_ids), 1)
        self.assertEqual(qc_session.checklist_ids[0].item_id, 'Visual Inspection')
        self.assertEqual(qc_session.checklist_ids[0].result, 'pass')
        self.assertEqual(qc_session.checklist_ids[0].criticality, 'major')
    def test_quality_issue_creation(self):
        """Test creating quality issues"""
        qc_session = self.env['wms.quality.control'].create({
            'name': 'Issue Test',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'date_start': fields.Datetime.now(),
            'status': 'in_progress',
        })

        quality_issue = self.env['wms.quality.issue'].create({
            'name': 'Test Quality Issue',
            'category': 'defect',
            'severity': 'major',
            'qc_session_id': qc_session.id,
            'owner_id': self.test_owner.id,
            'description': 'Test issue description',
        })

        self.assertEqual(quality_issue.name, 'Test Quality Issue')
        self.assertEqual(quality_issue.category, 'defect')
        self.assertEqual(quality_issue.severity, 'major')
        self.assertEqual(quality_issue.qc_session_id.id, qc_session.id)
    def test_corrective_action_creation(self):
        """Test creating corrective actions"""
        quality_issue = self.env['wms.quality.issue'].create({
            'name': 'Issue for Corrective Action',
            'category': 'defect',
            'severity': 'major',
            'owner_id': self.test_owner.id,
            'description': 'Issue requiring corrective action',
        })

        corrective_action = self.env['wms.quality.corrective_action'].create({
            'name': 'Test Corrective Action',
            'issue_id': quality_issue.id,
            'owner_id': self.test_owner.id,
            'description': 'Test action description',
        })

        self.assertEqual(corrective_action.name, 'Test Corrective Action')
        self.assertEqual(corrective_action.issue_id.id, quality_issue.id)
        self.assertEqual(corrective_action.owner_id.id, self.test_owner.id)
    def test_quality_photo_creation(self):
        """Test creating quality photos"""
        qc_session = self.env['wms.quality.control'].create({
            'name': 'Photo Test',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'date_start': fields.Datetime.now(),
            'status': 'in_progress',
        })

        quality_photo = self.env['wms.quality_photo'].create({
            'name': 'Test Quality Photo',
            'qc_session_id': qc_session.id,
            'owner_id': self.test_owner.id,
            'notes': 'Test photo notes',
        })

        self.assertEqual(quality_photo.name, 'Test Quality Photo')
        self.assertEqual(quality_photo.qc_session_id.id, qc_session.id)
        self.assertEqual(quality_photo.owner_id.id, self.test_owner.id)
    def test_quality_control_computed_fields(self):
        """Test computed fields in quality control"""
        qc_session = self.env['wms.quality.control'].create({
            'name': 'Computed Fields Test',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'date_start': fields.Datetime.now(),
            'status': 'in_progress',
        })

        # Add checklist items
        self.env['wms.quality.checklist'].create([
            {
                'qc_session_id': qc_session.id,
                'item_id': 'Check 1',
                'result': 'pass',
                'criticality': 'minor',
            },
            {
                'qc_session_id': qc_session.id,
                'item_id': 'Check 2',
                'result': 'fail',
                'criticality': 'major',
            },
        ])

        # Add quality issues
        self.env['wms.quality.issue'].create([
            {
                'name': 'Issue 1',
                'category': 'defect',
                'severity': 'minor',
                'qc_session_id': qc_session.id,
                'owner_id': self.test_owner.id,
            },
            {
                'name': 'Issue 2',
                'category': 'compliance',
                'severity': 'major',
                'qc_session_id': qc_session.id,
                'owner_id': self.test_owner.id,
            },
        ])

        # Refresh to get updated computed values
        qc_session.refresh()

        # Check that totals are computed correctly
        self.assertEqual(qc_session.checklist_count, 2)
        self.assertEqual(qc_session.issue_count, 2)
        # With 1 pass and 1 fail, pass rate should be 50%
        self.assertEqual(qc_session.pass_rate, 0.5)
    def test_quality_control_wizard(self):
        """Test creating quality control using wizard"""
        wizard = self.env['wms.quality.control.wizard'].create({
            'picking_id': self.test_picking.id,
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
        })

        result = wizard.action_create_quality_control()

        # Verify the result is an action to open the quality control form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.quality.control')

        # Get the created quality control session
        qc_session = self.env['wms.quality.control'].browse(result['res_id'])
        self.assertEqual(qc_session.control_type, 'incoming')
        self.assertEqual(qc_session.picking_id.id, self.test_picking.id)
        self.assertEqual(qc_session.status, 'in_progress')
    def test_quality_issue_wizard(self):
        """Test creating quality issue using wizard"""
        qc_session = self.env['wms.quality.control'].create({
            'name': 'Issue Wizard Test',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'date_start': fields.Datetime.now(),
            'status': 'in_progress',
        })

        wizard = self.env['wms.quality.issue.wizard'].create({
            'qc_session_id': qc_session.id,
            'category': 'defect',
            'severity': 'major',
            'description': 'Test issue from wizard',
        })

        result = wizard.action_create_quality_issue()

        # Verify the result is an action to open the quality issue form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.quality.issue')

        # Get the created quality issue
        quality_issue = self.env['wms.quality.issue'].browse(result['res_id'])
        self.assertEqual(quality_issue.category, 'defect')
        self.assertEqual(quality_issue.severity, 'major')
        self.assertEqual(quality_issue.qc_session_id.id, qc_session.id)
    def test_quality_control_ownership_isolation(self):
        """Test that quality control records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Quality Control Owner',
            'owner_code': 'SQCO',
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

        qc_session1 = self.env['wms.quality.control'].create({
            'name': 'QC Session for Owner 1',
            'control_type': 'incoming',
            'owner_id': self.test_owner.id,
            'picking_id': picking1_owner1.id,
        })

        qc_session2 = self.env['wms.quality.control'].create({
            'name': 'QC Session for Owner 2',
            'control_type': 'incoming',
            'owner_id': owner2.id,
            'picking_id': picking2_owner2.id,
        })

        self.assertNotEqual(qc_session1.owner_id.id, qc_session2.owner_id.id)
        self.assertNotEqual(qc_session1.name, qc_session2.name)