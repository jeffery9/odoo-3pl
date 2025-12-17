from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


@tagged('wms_rfid', 'at_install')
class TestWmsRfid(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsRfidTag = self.env['wms.rfid.tag']
        self.WmsRfidReader = self.env['wms.rfid.reader']
        self.WmsRfidTransaction = self.env['wms.rfid.transaction']
        self.WmsRfidInventory = self.env['wms.rfid.inventory']
        self.Warehouse = self.env['stock.warehouse']
        self.Location = self.env['stock.location']
        self.Product = self.env['product.product']
        self.Owner = self.env['wms.owner']
        self.Picking = self.env['stock.picking']
        self.ProductCategory = self.env['product.category']
        self.Employee = self.env['hr.employee']
        self.MaintenanceEquipment = self.env['maintenance.equipment']
        self.Uom = self.env['uom.uom']
        self.StockLot = self.env['stock.lot']

        # Create a test warehouse
        self.warehouse = self.Warehouse.create({
            'name': 'Test Warehouse',
            'code': 'TST'
        })

        # Create test locations
        self.location_src = self.Location.create({
            'name': 'Test Source Location',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id
        })

        self.location_dst = self.Location.create({
            'name': 'Test Destination Location',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id
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

        # Create test employee
        self.employee = self.Employee.create({
            'name': 'Test Employee',
            'work_location': 'Test Location'
        })

        # Create test equipment
        self.equipment = self.MaintenanceEquipment.create({
            'name': 'Test Equipment',
            'category_id': self.env.ref('maintenance.equipment_category_1').id if self.env.ref('maintenance.equipment_category_1', False) else False,
        })

        # Create test UOM
        self.uom_unit = self.Uom.search([('name', '=', 'Units')], limit=1) or self.Uom.create({
            'name': 'Units',
            'category_id': self.env.ref('uom.product_uom_categ_unit').id,
            'factor': 1.0,
            'uom_type': 'reference'
        })

        # Create test lot
        self.lot = self.StockLot.create({
            'name': 'TESTLOT001',
            'product_id': self.product1.id,
            'company_id': self.env.company.id,
        })

        # Create test RFID tag
        self.rfid_tag = self.WmsRfidTag.create({
            'name': 'TEST_TAG_001',
            'tag_type': 'product',
            'product_id': self.product1.id,
            'rfid_uid': '123456789ABC',
            'capacity': 100.0,
            'current_load': 50.0,
        })

        # Create test RFID reader
        self.rfid_reader = self.WmsRfidReader.create({
            'name': 'Test RFID Reader',
            'code': 'TRR001',
            'reader_type': 'fixed',
            'location_id': self.location_src.id,
            'warehouse_id': self.warehouse.id,
            'ip_address': '192.168.1.100',
            'port': 8080,
            'antenna_count': 4,
            'read_range': 2.0,
            'frequency': 915.0,
        })

    def test_rfid_tag_creation(self):
        """Test creation of RFID tag records"""
        tag = self.WmsRfidTag.create({
            'name': 'TEST_TAG_002',
            'tag_type': 'location',
            'location_id': self.location_dst.id,
            'rfid_uid': 'ABC987654321',
            'capacity': 200.0,
            'current_load': 75.0,
            'security_level': 'high',
        })

        self.assertEqual(tag.name, 'TEST_TAG_002')
        self.assertEqual(tag.tag_type, 'location')
        self.assertEqual(tag.location_id.id, self.location_dst.id)
        self.assertEqual(tag.rfid_uid, 'ABC987654321')
        self.assertEqual(tag.capacity, 200.0)
        self.assertEqual(tag.current_load, 75.0)
        self.assertEqual(tag.utilization_rate, 37.5)  # (75/200)*100
        self.assertTrue(tag.active)

    def test_rfid_tag_utilization_rate_computation(self):
        """Test utilization rate computation for RFID tags"""
        # Test with capacity and current load
        tag1 = self.WmsRfidTag.create({
            'name': 'UTIL_TAG_001',
            'tag_type': 'container',
            'capacity': 150.0,
            'current_load': 75.0,
        })

        self.assertEqual(tag1.utilization_rate, 50.0)  # (75/150)*100

        # Test with zero capacity (should result in 0% utilization)
        tag2 = self.WmsRfidTag.create({
            'name': 'UTIL_TAG_002',
            'tag_type': 'pallet',
            'capacity': 0.0,
            'current_load': 50.0,
        })

        self.assertEqual(tag2.utilization_rate, 0.0)

        # Test with current_load exceeding capacity
        tag3 = self.WmsRfidTag.create({
            'name': 'UTIL_TAG_003',
            'tag_type': 'container',
            'capacity': 50.0,
            'current_load': 75.0,
        })

        # Utilization rate should be capped at 100%
        self.assertEqual(tag3.utilization_rate, 100.0)

    def test_rfid_tag_status_transitions(self):
        """Test RFID tag status transitions"""
        tag = self.WmsRfidTag.create({
            'name': 'TRANSITION_TAG_001',
            'tag_type': 'product',
            'product_id': self.product1.id,
        })

        # Initially should be available and active
        self.assertEqual(tag.status, 'available')
        self.assertTrue(tag.active)

        # Activate the tag
        tag.action_activate_tag()
        self.assertEqual(tag.status, 'in_use')
        self.assertTrue(tag.active)
        self.assertIsNotNone(tag.date_activated)

        # Report as lost
        tag.action_report_lost()
        self.assertEqual(tag.status, 'lost')

        # Report as damaged
        tag.action_report_damaged()
        self.assertEqual(tag.status, 'damaged')

        # Deactivate the tag
        tag.action_deactivate_tag()
        self.assertFalse(tag.active)
        self.assertEqual(tag.status, 'retired')
        self.assertIsNotNone(tag.date_deactivated)

    def test_rfid_reader_creation(self):
        """Test creation of RFID reader records"""
        reader = self.WmsRfidReader.create({
            'name': 'Second RFID Reader',
            'code': 'SRR002',
            'reader_type': 'handheld',
            'location_id': self.location_dst.id,
            'warehouse_id': self.warehouse.id,
            'ip_address': '192.168.1.101',
            'port': 8081,
            'protocol': 'tcp',
            'antenna_count': 1,
            'read_range': 1.5,
            'power_level': 27.0,
            'frequency': 866.0,
            'supported_standards': 'ISO 18000-6C, EPC Class 1 Gen 2',
            'auto_scan_enabled': True,
            'scan_interval': 60,
        })

        self.assertEqual(reader.name, 'Second RFID Reader')
        self.assertEqual(reader.code, 'SRR002')
        self.assertEqual(reader.reader_type, 'handheld')
        self.assertEqual(reader.location_id.id, self.location_dst.id)
        self.assertEqual(reader.warehouse_id.id, self.warehouse.id)
        self.assertEqual(reader.ip_address, '192.168.1.101')
        self.assertEqual(reader.port, 8081)
        self.assertEqual(reader.protocol, 'tcp')
        self.assertEqual(reader.antenna_count, 1)
        self.assertEqual(reader.read_range, 1.5)
        self.assertTrue(reader.auto_scan_enabled)
        self.assertEqual(reader.scan_interval, 60)

    def test_rfid_reader_connection(self):
        """Test RFID reader connection functionality"""
        # Test initial state
        self.assertEqual(self.rfid_reader.status, 'offline')
        self.assertFalse(self.rfid_reader.is_connected)

        # Connect the reader
        self.rfid_reader.action_connect_reader()
        self.assertEqual(self.rfid_reader.status, 'online')
        self.assertTrue(self.rfid_reader.is_connected)
        self.assertIsNotNone(self.rfid_reader.last_connection)

        # Disconnect the reader
        self.rfid_reader.action_disconnect_reader()
        self.assertEqual(self.rfid_reader.status, 'offline')
        self.assertFalse(self.rfid_reader.is_connected)

    def test_rfid_reader_scan(self):
        """Test RFID reader scan functionality"""
        # This method just logs the scan, so we'll verify it doesn't raise an error
        result = self.rfid_reader.action_scan_tags()
        # The method returns None, which is falsy, so we just make sure it doesn't throw an exception
        self.assertIsNone(result)

    def test_rfid_transaction_creation(self):
        """Test creation of RFID transaction records"""
        transaction = self.WmsRfidTransaction.create({
            'transaction_type': 'read',
            'tag_id': self.rfid_tag.id,
            'reader_id': self.rfid_reader.id,
            'rfid_uid': '123456789ABC',
            'timestamp': datetime.now(),
            'source_location_id': self.location_src.id,
            'destination_location_id': self.location_dst.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'quantity': 10.0,
            'lot_id': self.lot.id,
            'operator_id': self.employee.id,
            'equipment_id': self.equipment.id,
        })

        self.assertEqual(transaction.transaction_type, 'read')
        self.assertEqual(transaction.tag_id.id, self.rfid_tag.id)
        self.assertEqual(transaction.reader_id.id, self.rfid_reader.id)
        self.assertEqual(transaction.rfid_uid, '123456789ABC')
        self.assertEqual(transaction.source_location_id.id, self.location_src.id)
        self.assertEqual(transaction.destination_location_id.id, self.location_dst.id)
        self.assertEqual(transaction.product_id.id, self.product1.id)
        self.assertEqual(transaction.quantity, 10.0)
        self.assertEqual(transaction.operator_id.id, self.employee.id)
        self.assertEqual(transaction.equipment_id.id, self.equipment.id)
        self.assertEqual(transaction.status, 'completed')

    def test_rfid_transaction_verification(self):
        """Test RFID transaction verification"""
        transaction = self.WmsRfidTransaction.create({
            'transaction_type': 'move',
            'tag_id': self.rfid_tag.id,
            'reader_id': self.rfid_reader.id,
            'source_location_id': self.location_src.id,
            'destination_location_id': self.location_dst.id,
            'product_id': self.product1.id,
            'quantity': 5.0,
            'status': 'completed',
        })

        # Initially should not be verified
        self.assertFalse(transaction.is_verified)
        self.assertEqual(transaction.status, 'completed')

        # Verify the transaction
        transaction.action_verify_transaction()
        self.assertTrue(transaction.is_verified)
        self.assertEqual(transaction.status, 'verified')

    def test_rfid_transaction_error_marking(self):
        """Test marking RFID transactions with errors"""
        transaction = self.WmsRfidTransaction.create({
            'transaction_type': 'location_change',
            'tag_id': self.rfid_tag.id,
            'reader_id': self.rfid_reader.id,
            'product_id': self.product1.id,
            'quantity': 3.0,
            'status': 'completed',
        })

        # Initially should be completed without errors
        self.assertEqual(transaction.status, 'completed')
        self.assertIsNone(transaction.error_message)

        # Mark with error
        transaction.action_mark_error('Connection timeout')
        self.assertEqual(transaction.status, 'error')
        self.assertEqual(transaction.error_message, 'Connection timeout')

    def test_rfid_inventory_creation(self):
        """Test creation of RFID inventory records"""
        inventory = self.WmsRfidInventory.create({
            'location_id': self.location_src.id,
            'warehouse_id': self.warehouse.id,
            'operator_id': self.employee.id,
            'reader_ids': [(6, 0, [self.rfid_reader.id])],
            'include_sublocations': True,
            'count_zero': False,
            'owner_id': self.owner.id,
        })

        self.assertEqual(inventory.state, 'draft')
        self.assertEqual(inventory.location_id.id, self.location_src.id)
        self.assertEqual(inventory.warehouse_id.id, self.warehouse.id)
        self.assertEqual(inventory.operator_id.id, self.employee.id)
        self.assertIn(self.rfid_reader.id, [r.id for r in inventory.reader_ids])
        self.assertTrue(inventory.include_sublocations)
        self.assertFalse(inventory.count_zero)
        self.assertEqual(inventory.owner_id.id, self.owner.id)

    def test_rfid_inventory_state_transitions(self):
        """Test RFID inventory state transitions"""
        inventory = self.WmsRfidInventory.create({
            'location_id': self.location_src.id,
            'warehouse_id': self.warehouse.id,
            'operator_id': self.employee.id,
        })

        # Initially should be in draft
        self.assertEqual(inventory.state, 'draft')

        # Start the inventory
        inventory.action_start_inventory()
        self.assertEqual(inventory.state, 'in_progress')
        self.assertIsNotNone(inventory.date_start)

        # Complete the inventory
        inventory.action_complete_inventory()
        self.assertEqual(inventory.state, 'completed')
        self.assertIsNotNone(inventory.date_end)

        # Create another inventory and cancel it
        inventory2 = self.WmsRfidInventory.create({
            'location_id': self.location_dst.id,
            'warehouse_id': self.warehouse.id,
        })

        inventory2.action_cancel_inventory()
        self.assertEqual(inventory2.state, 'cancelled')

    def test_rfid_inventory_report_generation(self):
        """Test RFID inventory report generation"""
        inventory = self.WmsRfidInventory.create({
            'location_id': self.location_src.id,
            'warehouse_id': self.warehouse.id,
        })

        # Generate report should return an action dictionary
        action = inventory.action_generate_report()
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'wms.rfid.transaction')
        self.assertEqual(action['view_mode'], 'list,form')
        self.assertIn('TEST_TAG_001', str(action.get('domain', [])))

    def test_rfid_tag_onchange_functionality(self):
        """Test onchange functionality for RFID tags"""
        # Create a tag with product type and associated product
        tag = self.WmsRfidTag.new({
            'name': 'ONCHANGE_TAG_001',
            'tag_type': 'product',
            'product_id': self.product1.id,
            'location_id': self.location_src.id,
            'employee_id': self.employee.id,
        })

        # Initially all should be set
        self.assertEqual(tag.tag_type, 'product')
        self.assertEqual(tag.product_id.id, self.product1.id)
        self.assertEqual(tag.location_id.id, self.location_src.id)
        self.assertEqual(tag.employee_id.id, self.employee.id)

        # Change tag type to location and check onchange effect
        tag.tag_type = 'location'
        tag._onchange_tag_type()

        # Product should be cleared but location and employee should remain
        self.assertNotEqual(tag.product_id.id, self.product1.id)  # Should be falsy now
        self.assertEqual(tag.location_id.id, self.location_src.id)  # Should remain
        self.assertEqual(tag.employee_id.id, self.employee.id)  # Should remain

    def test_rfid_transaction_source_document(self):
        """Test RFID transaction with source document reference"""
        # Create a stock picking to use as source document
        picking = self.Picking.create({
            'name': 'TEST_PICKING_RFID_01',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
            'owner_id': self.owner.id,
            'state': 'draft',
        })

        transaction = self.WmsRfidTransaction.create({
            'transaction_type': 'outbound',
            'tag_id': self.rfid_tag.id,
            'reader_id': self.rfid_reader.id,
            'source_document': f'stock.picking,{picking.id}',
            'product_id': self.product1.id,
            'quantity': 8.0,
        })

        self.assertEqual(transaction.source_document, f'stock.picking,{picking.id}')
        self.assertEqual(transaction.quantity, 8.0)

    def test_rfid_inventory_results_calculation(self):
        """Test RFID inventory results calculation"""
        inventory = self.WmsRfidInventory.create({
            'location_id': self.location_src.id,
            'warehouse_id': self.warehouse.id,
        })

        # Initially should have default values
        self.assertEqual(inventory.items_counted, 0)
        self.assertEqual(inventory.discrepancies_found, 0)
        self.assertEqual(inventory.accuracy_rate, 0.0)

        # Call the calculation method
        inventory._calculate_results()

        # After calculation, should still be default values (as method is currently dummy)
        self.assertEqual(inventory.items_counted, 0)
        self.assertEqual(inventory.discrepancies_found, 0)
        self.assertEqual(inventory.accuracy_rate, 100.0)  # Method sets this to 100.0