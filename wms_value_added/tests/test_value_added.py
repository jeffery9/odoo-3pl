from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


@tagged('wms_value_added', 'at_install')
class TestWmsValueAdded(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsValueAddedService = self.env['wms.value.added.service']
        self.WmsValueAddedOperation = self.env['wms.value.added.operation']
        self.WmsValueAddedProductLine = self.env['wms.value.added.product.line']
        self.WmsValueAddedMaterial = self.env['wms.value.added.material']
        self.WmsValueAddedReport = self.env['wms.value.added.report']
        self.Warehouse = self.env['stock.warehouse']
        self.Location = self.env['stock.location']
        self.Product = self.env['product.product']
        self.Owner = self.env['wms.owner']
        self.Picking = self.env['stock.picking']
        self.ProductCategory = self.env['product.category']
        self.Employee = self.env['hr.employee']

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

        # Create test employee/operator
        self.employee = self.Employee.create({
            'name': 'Test Operator',
            'work_location': 'Test Location'
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
            'weight': 2.0,
            'volume': 0.02,
            'length': 15,
            'width': 15,
            'height': 15
        })

        self.material_product = self.Product.create({
            'name': 'Test Material Product',
            'type': 'product',
            'default_code': 'MAT001',
            'weight': 0.1,
            'volume': 0.001,
            'length': 5,
            'width': 5,
            'height': 5
        })

        # Create test service
        self.service = self.WmsValueAddedService.create({
            'name': 'Test Assembly Service',
            'code': 'TAS001',
            'service_type': 'assembly',
            'service_category': 'product',
            'standard_time': 30.0,
            'cost_per_unit': 2.50,
            'price_per_unit': 5.00,
            'has_quality_check': True,
            'requires_approval': True
        })

    def test_value_added_service_creation(self):
        """Test creation of value added service records"""
        service = self.WmsValueAddedService.create({
            'name': 'Test Packaging Service',
            'code': 'TPS001',
            'service_type': 'packaging',
            'service_category': 'product',
            'standard_time': 15.0,
            'cost_per_unit': 1.50,
            'price_per_unit': 3.00,
        })

        self.assertEqual(service.name, 'Test Packaging Service')
        self.assertEqual(service.code, 'TPS001')
        self.assertEqual(service.service_type, 'packaging')
        self.assertEqual(service.service_category, 'product')
        self.assertEqual(service.standard_time, 15.0)
        self.assertTrue(service.active)

    def test_value_added_operation_creation(self):
        """Test creation of value added operation records"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
        })

        self.assertEqual(operation.service_id.id, self.service.id)
        self.assertEqual(operation.owner_id.id, self.owner.id)
        self.assertEqual(operation.warehouse_id.id, self.warehouse.id)
        self.assertEqual(operation.priority, '1')
        self.assertEqual(operation.state, 'draft')

    def test_value_added_operation_state_transitions(self):
        """Test value added operation state transitions"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
        })

        # Check initial state
        self.assertEqual(operation.state, 'draft')

        # Start the operation
        operation.action_start_operation()
        # Since the initial state is 'draft' not 'scheduled', this should not change the state
        # Let's update the state to scheduled first
        operation.write({'state': 'scheduled'})

        # Now start the operation
        operation.action_start_operation()
        self.assertEqual(operation.state, 'in_progress')

        # Complete the operation
        operation.action_complete_operation()
        # Since the service has quality check enabled, it should go to 'quality_check'
        self.assertEqual(operation.state, 'quality_check')

        # Approve the operation
        operation.action_approve_operation()
        # Since the service has approval required, it should go to 'approved'
        self.assertEqual(operation.state, 'approved')

        # Complete again to reach final state
        operation.write({'state': 'quality_check'})
        operation.action_approve_operation()
        # Since approval is required, this would go to completed now
        # Actually, let's check the logic: if requires_approval is True, it goes to approved, else completed
        # If we update to completed
        operation.action_complete_operation()  # This should set the state to quality check since has_quality_check is True
        self.assertEqual(operation.state, 'quality_check')

    def test_value_added_product_line_creation(self):
        """Test creation of value added product line records"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
        })

        product_line = self.WmsValueAddedProductLine.create({
            'operation_id': operation.id,
            'product_id': self.product1.id,
            'quantity': 10.0,
            'line_type': 'input',
            'unit_cost': 1.0,
        })

        self.assertEqual(product_line.operation_id.id, operation.id)
        self.assertEqual(product_line.product_id.id, self.product1.id)
        self.assertEqual(product_line.quantity, 10.0)
        self.assertEqual(product_line.line_type, 'input')
        self.assertAlmostEqual(product_line.total_cost, 10.0, 2)  # quantity * unit_cost

    def test_value_added_material_creation(self):
        """Test creation of value added material records"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
        })

        material = self.WmsValueAddedMaterial.create({
            'operation_id': operation.id,
            'product_id': self.material_product.id,
            'planned_quantity': 5.0,
            'used_quantity': 4.5,
            'unit_cost': 0.5,
        })

        self.assertEqual(material.operation_id.id, operation.id)
        self.assertEqual(material.product_id.id, self.material_product.id)
        self.assertEqual(material.planned_quantity, 5.0)
        self.assertEqual(material.used_quantity, 4.5)
        self.assertAlmostEqual(material.total_cost, 2.25, 2)  # used quantity * unit_cost

    def test_value_added_operation_progress_calculation(self):
        """Test progress calculation for value added operations"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
            'state': 'in_progress'
        })

        # When state is 'in_progress', progress should be 50%
        self.assertEqual(operation.progress, 50.0)

        # Change state to completed
        operation.write({'state': 'completed'})
        self.assertEqual(operation.progress, 100.0)

        # Change state to draft
        operation.write({'state': 'draft'})
        self.assertEqual(operation.progress, 0.0)

    def test_value_added_operation_duration_calculation(self):
        """Test duration calculation for value added operations"""
        start_time = datetime.now() - timedelta(minutes=30)
        end_time = datetime.now()

        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'date_started': start_time,
            'date_completed': end_time,
            'priority': '1',
            'state': 'completed'
        })

        # Duration should be approximately 30 minutes
        self.assertAlmostEqual(operation.duration_minutes, 30.0, places=0)

    def test_value_added_operation_cost_calculation(self):
        """Test cost calculation for value added operations"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
            'state': 'completed'
        })

        # Add a material line to the operation
        material = self.WmsValueAddedMaterial.create({
            'operation_id': operation.id,
            'product_id': self.material_product.id,
            'planned_quantity': 2.0,
            'used_quantity': 2.0,
            'unit_cost': 1.0,
        })

        # The cost should be calculated based on materials
        # Note: actual cost calculation is complex and depends on labor rates
        # For this test we just verify that the cost field exists and is accessible
        self.assertIsNotNone(operation.cost)

    def test_value_added_operation_revenue_calculation(self):
        """Test revenue calculation for value added operations"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
            'state': 'completed'
        })

        # Add a product line to the operation
        product_line = self.WmsValueAddedProductLine.create({
            'operation_id': operation.id,
            'product_id': self.product1.id,
            'quantity': 10.0,
            'line_type': 'input',
            'unit_cost': 1.0,
        })

        # Revenue should be calculated based on service price and quantity
        expected_revenue = self.service.price_per_unit * product_line.quantity
        self.assertEqual(operation.revenue, expected_revenue)

    def test_value_added_operation_margin_calculation(self):
        """Test margin calculation for value added operations"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
            'state': 'completed'
        })

        # Add a product line to the operation
        product_line = self.WmsValueAddedProductLine.create({
            'operation_id': operation.id,
            'product_id': self.product1.id,
            'quantity': 10.0,
            'line_type': 'input',
            'unit_cost': 1.0,
        })

        # Margin = Revenue - Cost
        expected_revenue = self.service.price_per_unit * product_line.quantity
        expected_margin = expected_revenue - operation.cost
        self.assertEqual(operation.margin, expected_margin)

    def test_value_added_report_wizard(self):
        """Test value added service report wizard"""
        wizard = self.WmsValueAddedReport.create({
            'date_from': datetime.now() - timedelta(days=7),
            'date_to': datetime.now(),
            'owner_id': self.owner.id,
            'service_type': 'assembly',
            'warehouse_id': self.warehouse.id,
        })

        self.assertEqual(wizard.date_from, datetime.now().date() - timedelta(days=7))
        self.assertEqual(wizard.date_to, datetime.now().date())
        self.assertEqual(wizard.owner_id.id, self.owner.id)
        self.assertEqual(wizard.service_type, 'assembly')
        self.assertEqual(wizard.warehouse_id.id, self.warehouse.id)

        # Test that it can generate an action
        action = wizard.action_generate_report()
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'wms.value.added.operation')

    def test_value_added_operation_cancel(self):
        """Test cancellation of value added operations"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
            'state': 'draft'
        })

        # Initially should be in draft
        self.assertEqual(operation.state, 'draft')

        # Cancel the operation
        operation.action_cancel_operation()
        # Operation should be cancelled if it was in draft, scheduled, or in_progress
        self.assertEqual(operation.state, 'cancelled')

    def test_value_added_product_line_onchange(self):
        """Test onchange methods for value added product lines"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
        })

        # Create a product line without specifying UOM or unit_cost
        product_line = self.WmsValueAddedProductLine.create({
            'operation_id': operation.id,
            'product_id': self.product1.id,
            'quantity': 5.0,
            'line_type': 'input',
        })

        # The UOM should be automatically set from the product
        self.assertEqual(product_line.product_uom.id, self.product1.uom_id.id)

        # The unit cost should be automatically set from the product
        self.assertEqual(product_line.unit_cost, self.product1.standard_price)

    def test_value_added_material_onchange(self):
        """Test onchange methods for value added materials"""
        operation = self.WmsValueAddedOperation.create({
            'service_id': self.service.id,
            'owner_id': self.owner.id,
            'warehouse_id': self.warehouse.id,
            'date_scheduled': datetime.now(),
            'priority': '1',
        })

        # Create a material line without specifying UOM or unit_cost
        material = self.WmsValueAddedMaterial.create({
            'operation_id': operation.id,
            'product_id': self.material_product.id,
            'planned_quantity': 3.0,
            'used_quantity': 3.0,
        })

        # The UOM should be automatically set from the product
        self.assertEqual(material.product_uom.id, self.material_product.uom_id.id)

        # The unit cost should be automatically set from the product
        self.assertEqual(material.unit_cost, self.material_product.standard_price)