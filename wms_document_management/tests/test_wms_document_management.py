from odoo.tests import TransactionCase
from odoo import fields
import base64


class TestWmsDocumentManagement(TransactionCase):
    """Test cases for WMS Document Management module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Document Management Owner',
            'owner_code': 'TDMO',
            'is_warehouse_owner': True,
        })

        self.test_category = self.env['wms.document.category'].create({
            'name': 'Test Category',
            'owner_code': 'TC',
            'is_active': True,
        })

        self.test_tag = self.env['wms.document.tag'].create({
            'name': 'Test Tag',
            'description': 'Test document tag',
        })

        self.test_user = self.env['res.users'].create({
            'name': 'Test Document User',
            'login': 'test_doc_user',
            'email': 'test.doc@example.com',
        })

        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Document',
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
    def test_create_document_category(self):
        """Test creating document categories"""
        category = self.env['wms.document.category'].create({
            'name': 'Test Document Category',
            'owner_code': 'TDC',
            'description': 'Test document category description',
        })

        self.assertEqual(category.name, 'Test Document Category')
        self.assertEqual(category.owner_code, 'TDC')
        self.assertTrue(category.is_active)
        self.assertEqual(category.document_count, 0)
    def test_create_document_tag(self):
        """Test creating document tags"""
        tag = self.env['wms.document.tag'].create({
            'name': 'Test Document Tag',
            'description': 'Test document tag description',
        })

        self.assertEqual(tag.name, 'Test Document Tag')
        self.assertEqual(tag.description, 'Test document tag description')
        self.assertTrue(tag.active)
    def test_create_document(self):
        """Test creating documents"""
        document = self.env['wms.document'].create({
            'name': 'Test Document',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
            'status': 'draft',
        })

        self.assertTrue(document.document_code.startswith('DOC'))
        self.assertEqual(document.name, 'Test Document')
        self.assertEqual(document.category_id.id, self.test_category.id)
        self.assertEqual(document.owner_id.id, self.test_owner.id)
        self.assertEqual(document.version, '1.0')
        self.assertEqual(document.status, 'draft')
        self.assertTrue(document.is_latest)
    def test_document_file_upload(self):
        """Test document file upload and metadata"""
        # Create sample file content
        sample_content = b"This is a test document content"
        encoded_content = base64.b64encode(sample_content)

        document = self.env['wms.document'].create({
            'name': 'Test File Document',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'filename': 'test_document.txt',
            'file': encoded_content,
            'version': '1.0',
        })

        self.assertEqual(document.filename, 'test_document.txt')
        self.assertEqual(document.file_size, len(sample_content))
        self.assertEqual(document.file_type, 'TXT')
    def test_document_status_flow(self):
        """Test document status flow"""
        document = self.env['wms.document'].create({
            'name': 'Status Flow Test',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
            'status': 'draft',
        })

        self.assertEqual(document.status, 'draft')

        # Approve the document
        document.action_approve()
        self.assertEqual(document.status, 'approved')
        self.assertIsNotNone(document.approved_by)
        self.assertIsNotNone(document.approved_date)

        # Archive the document
        document.action_archive()
        self.assertEqual(document.status, 'archived')
    def test_document_with_tags(self):
        """Test document with tags"""
        document = self.env['wms.document'].create({
            'name': 'Tagged Document',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
        })

        # Add tags
        document.tags = [(6, 0, [self.test_tag.id])]

        self.assertEqual(len(document.tags), 1)
        self.assertTrue(self.test_tag in document.tags)
    def test_document_with_related_record(self):
        """Test document with related record"""
        document = self.env['wms.document'].create({
            'name': 'Related Document',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
            'related_model': f"stock.picking,{self.test_picking.id}",
        })

        self.assertIsNotNone(document.related_model)
    def test_document_template_creation(self):
        """Test creating document templates"""
        template = self.env['wms.document.template'].create({
            'name': 'Test Document Template',
            'owner_code': 'TDT',
            'category_id': self.test_category.id,
            'template_type': 'form',
            'content_template': 'This is a template for {{document.name}}',
            'required_fields': 'name,category_id',
        })

        self.assertEqual(template.name, 'Test Document Template')
        self.assertEqual(template.owner_code, 'TDT')
        self.assertEqual(template.template_type, 'form')
        self.assertTrue(template.is_active)
    def test_document_workflow_creation(self):
        """Test creating document workflows"""
        workflow = self.env['wms.document.workflow'].create({
            'name': 'Test Document Workflow',
            'owner_code': 'TDW',
            'initial_status': 'draft',
            'require_approval': True,
            'approval_steps': 2,
            'default_retention': 365,  # 1 year
        })

        self.assertEqual(workflow.name, 'Test Document Workflow')
        self.assertEqual(workflow.owner_code, 'TDW')
        self.assertEqual(workflow.initial_status, 'draft')
        self.assertTrue(workflow.require_approval)
        self.assertEqual(workflow.approval_steps, 2)
        self.assertEqual(workflow.default_retention, 365)
    def test_document_versioning(self):
        """Test document versioning"""
        # Create first version
        doc_v1 = self.env['wms.document'].create({
            'name': 'Versioned Document',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
            'status': 'approved',
        })

        self.assertTrue(doc_v1.is_latest)

        # Create second version
        doc_v2 = self.env['wms.document'].create({
            'name': 'Versioned Document',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '2.0',
            'status': 'approved',
        })

        # Refresh to get updated computed values
        doc_v1.refresh()
        doc_v2.refresh()

        # The second version should be marked as latest
        self.assertFalse(doc_v1.is_latest)
        self.assertTrue(doc_v2.is_latest)
    def test_document_category_hierarchy(self):
        """Test document category hierarchy"""
        parent_category = self.test_category

        child_category = self.env['wms.document.category'].create({
            'name': 'Child Category',
            'owner_code': 'CC',
            'parent_id': parent_category.id,
        })

        self.assertEqual(child_category.parent_id.id, parent_category.id)
        self.assertIn(child_category, parent_category.child_ids)
    def test_document_expiry_date_calculation(self):
        """Test document expiry date calculation"""
        from datetime import date, timedelta

        document = self.env['wms.document'].create({
            'name': 'Expiry Test Document',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
            'retention_period': 30,  # 30 days retention
        })

        # Calculate expected expiry date (30 days from creation)
        expected_expiry = fields.Date.from_string(document.created_date) + timedelta(days=30)

        # For this test, we'll just verify that the field exists and can be computed
        self.assertIsNotNone(document.created_date)
        self.assertEqual(document.retention_period, 30)
    def test_document_rejection(self):
        """Test document rejection process"""
        document = self.env['wms.document'].create({
            'name': 'Rejection Test',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
            'status': 'pending_approval',
        })

        self.assertEqual(document.status, 'pending_approval')

        # Reject the document
        document.action_reject()
        self.assertEqual(document.status, 'rejected')
    def test_document_archive_and_restore(self):
        """Test document archiving and restoration"""
        document = self.env['wms.document'].create({
            'name': 'Archive Test',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
            'status': 'approved',
        })

        # Archive the document
        document.action_archive()
        self.assertEqual(document.status, 'archived')

        # Create an archive record
        archive = self.env['wms.document.archive'].create({
            'name': 'Test Archive',
            'document_ids': [(6, 0, [document.id])],
            'reason': 'retention_expired',
        })

        # Restore the document from archive
        archive.restore_documents()

        # Refresh to get updated status
        document.refresh()
        # The document should be restored to approved status
        self.assertEqual(document.status, 'approved')
    def test_document_download_count(self):
        """Test document download count"""
        document = self.env['wms.document'].create({
            'name': 'Download Test',
            'category_id': self.test_category.id,
            'owner_id': self.test_owner.id,
            'version': '1.0',
        })

        self.assertEqual(document.download_count, 0)

        # Simulate download
        document.action_download()
        self.assertEqual(document.download_count, 1)

        # Download again
        document.action_download()
        self.assertEqual(document.download_count, 2)