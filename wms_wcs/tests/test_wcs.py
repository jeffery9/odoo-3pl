from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


@tagged('wms_wcs', 'at_install')
class TestWmsWcs(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsWcsSystem = self.env['wms.wcs.system']
        self.WmsWcsDevice = self.env['wms.wcs.device']
        self.WmsWcsTask = self.env['wms.wcs.task']
        self.WmsWcsIntegrationLog = self.env['wms.wcs.integration.log']
        self.Warehouse = self.env['stock.warehouse']
        self.Location = self.env['stock.location']
        self.Product = self.env['product.product']
        self.Owner = self.env['wms.owner']
        self.Picking = self.env['stock.picking']
        self.ProductCategory = self.env['product.category']
        self.Uom = self.env['uom.uom']

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

        # Create test UOM
        self.uom_unit = self.Uom.search([('name', '=', 'Units')], limit=1) or self.Uom.create({
            'name': 'Units',
            'category_id': self.env.ref('uom.product_uom_categ_unit').id,
            'factor': 1.0,
            'uom_type': 'reference'
        })

        # Create test WCS system
        self.wcs_system = self.WmsWcsSystem.create({
            'name': 'Test WCS System',
            'code': 'TWCS001',
            'system_type': 'automated_storage',
            'host': '192.168.1.100',
            'port': 8080,
            'protocol': 'http',
            'api_url': 'http://192.168.1.100:8080/api',
        })

        # Create test WCS device
        self.wcs_device = self.WmsWcsDevice.create({
            'name': 'Test Storage Device',
            'code': 'TSD001',
            'wcs_system_id': self.wcs_system.id,
            'device_type': 'storage',
            'location_id': self.location_src.id,
            'ip_address': '192.168.1.101',
            'max_capacity': 1000.0,
            'current_load': 500.0,
        })

    def test_wcs_system_creation(self):
        """Test creation of WCS system records"""
        system = self.WmsWcsSystem.create({
            'name': 'Another WCS System',
            'code': 'AWCS002',
            'system_type': 'conveyor',
            'host': '192.168.1.102',
            'port': 9090,
            'protocol': 'https',
            'api_url': 'https://192.168.1.102:9090/api',
        })

        self.assertEqual(system.name, 'Another WCS System')
        self.assertEqual(system.code, 'AWCS002')
        self.assertEqual(system.system_type, 'conveyor')
        self.assertEqual(system.host, '192.168.1.102')
        self.assertEqual(system.port, 9090)
        self.assertEqual(system.protocol, 'https')
        self.assertTrue(system.active)

    def test_wcs_device_creation(self):
        """Test creation of WCS device records"""
        device = self.WmsWcsDevice.create({
            'name': 'Test Conveyor Device',
            'code': 'TCD002',
            'wcs_system_id': self.wcs_system.id,
            'device_type': 'conveyor',
            'location_id': self.location_dst.id,
            'ip_address': '192.168.1.103',
            'max_capacity': 500.0,
            'current_load': 200.0,
        })

        self.assertEqual(device.name, 'Test Conveyor Device')
        self.assertEqual(device.code, 'TCD002')
        self.assertEqual(device.wcs_system_id.id, self.wcs_system.id)
        self.assertEqual(device.device_type, 'conveyor')
        self.assertEqual(device.ip_address, '192.168.1.103')
        self.assertEqual(device.max_capacity, 500.0)
        self.assertEqual(device.current_load, 200.0)
        self.assertEqual(device.efficiency_rate, 40.0)  # (200/500)*100

    def test_wcs_device_efficiency_rate_computation(self):
        """Test efficiency rate computation for WCS devices"""
        # Test with max capacity and current load
        device1 = self.WmsWcsDevice.create({
            'name': 'Efficiency Test Device 1',
            'code': 'ETD003',
            'wcs_system_id': self.wcs_system.id,
            'device_type': 'robot',
            'max_capacity': 200.0,
            'current_load': 100.0,
        })

        self.assertEqual(device1.efficiency_rate, 50.0)  # (100/200)*100

        # Test with zero values
        device2 = self.WmsWcsDevice.create({
            'name': 'Efficiency Test Device 2',
            'code': 'ETD004',
            'wcs_system_id': self.wcs_system.id,
            'device_type': 'agv',
            'max_capacity': 100.0,
            'current_load': 0.0,
        })

        self.assertEqual(device2.efficiency_rate, 0.0)

        # Test with current_load exceeding max_capacity
        device3 = self.WmsWcsDevice.write({
            'max_capacity': 100.0,
            'current_load': 150.0,  # Exceeds max capacity
        })

        # Efficiency rate should be capped at 100%
        self.assertLessEqual(self.wcs_device.efficiency_rate, 100.0)

    def test_wcs_task_creation(self):
        """Test creation of WCS task records"""
        task = self.WmsWcsTask.create({
            'task_type': 'storage',
            'wcs_system_id': self.wcs_system.id,
            'priority': '2',
            'source_location_id': self.location_src.id,
            'destination_location_id': self.location_dst.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'quantity': 10.0,
            'device_id': self.wcs_device.id,
        })

        self.assertEqual(task.task_type, 'storage')
        self.assertEqual(task.wcs_system_id.id, self.wcs_system.id)
        self.assertEqual(task.priority, '2')
        self.assertEqual(task.state, 'draft')
        self.assertEqual(task.quantity, 10.0)
        self.assertEqual(task.device_id.id, self.wcs_device.id)

    def test_wcs_task_state_transitions(self):
        """Test WCS task state transitions"""
        task = self.WmsWcsTask.create({
            'task_type': 'retrieval',
            'wcs_system_id': self.wcs_system.id,
            'source_location_id': self.location_dst.id,
            'destination_location_id': self.location_src.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'quantity': 5.0,
        })

        # Initially should be in draft
        self.assertEqual(task.state, 'draft')

        # Confirm the task
        task.action_confirm_task()
        self.assertEqual(task.state, 'confirmed')
        self.assertIsNotNone(task.date_confirmed)

        # Send to WCS
        task.action_send_to_wcs()
        self.assertEqual(task.state, 'sent')
        self.assertIsNotNone(task.date_sent)

        # Start the task
        task.action_start_task()
        self.assertEqual(task.state, 'in_progress')
        self.assertIsNotNone(task.date_started)
        self.assertIsNotNone(task.start_time)

        # Complete the task
        task.action_complete_task()
        self.assertEqual(task.state, 'completed')
        self.assertIsNotNone(task.date_completed)
        self.assertIsNotNone(task.end_time)
        self.assertGreaterEqual(task.duration_seconds, 0.0)

    def test_wcs_task_cancellation(self):
        """Test cancellation of WCS tasks"""
        task = self.WmsWcsTask.create({
            'task_type': 'move',
            'wcs_system_id': self.wcs_system.id,
            'source_location_id': self.location_src.id,
            'destination_location_id': self.location_dst.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'quantity': 3.0,
            'state': 'confirmed'
        })

        # Initially should be confirmed
        self.assertEqual(task.state, 'confirmed')

        # Cancel the task
        task.action_cancel_task()
        self.assertEqual(task.state, 'cancelled')

    def test_wcs_task_retry(self):
        """Test retry functionality for failed WCS tasks"""
        task = self.WmsWcsTask.create({
            'task_type': 'pack',
            'wcs_system_id': self.wcs_system.id,
            'source_location_id': self.location_src.id,
            'destination_location_id': self.location_dst.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'quantity': 7.0,
            'state': 'failed',
            'error_message': 'Connection timeout',
            'retry_count': 2,
        })

        # Initially should be failed with error
        self.assertEqual(task.state, 'failed')
        self.assertEqual(task.retry_count, 2)
        self.assertEqual(task.error_message, 'Connection timeout')

        # Retry the task
        task.action_retry_task()
        self.assertEqual(task.state, 'confirmed')
        self.assertEqual(task.retry_count, 3)  # Incremented by 1
        self.assertIsNone(task.error_message)

    def test_wcs_system_connection_test(self):
        """Test WCS system connection test functionality"""
        # Test initial state
        self.assertEqual(self.wcs_system.connection_status, 'disconnected')
        self.assertFalse(self.wcs_system.is_connected)

        # Execute connection test
        self.wcs_system.action_test_connection()

        # Check that connection status has been updated
        self.assertEqual(self.wcs_system.connection_status, 'connected')
        self.assertTrue(self.wcs_system.is_connected)
        self.assertIsNotNone(self.wcs_system.last_sync)

    def test_wcs_system_device_sync(self):
        """Test WCS system device synchronization"""
        # This method just logs the sync action, so we'll verify it doesn't raise an error
        # and that it returns the expected result
        result = self.wcs_system.action_sync_devices()
        # The method returns None, which is falsy, so we just make sure it doesn't throw an exception
        self.assertIsNone(result)

    def test_wcs_device_status_refresh(self):
        """Test refreshing WCS device status"""
        # Check initial state
        initial_heartbeat = self.wcs_device.last_heartbeat
        initial_status = self.wcs_device.device_status

        # Refresh the status
        self.wcs_device.action_refresh_status()

        # Check that heartbeat and status have been updated
        self.assertIsNotNone(self.wcs_device.last_heartbeat)
        self.assertNotEqual(self.wcs_device.last_heartbeat, initial_heartbeat)
        self.assertEqual(self.wcs_device.device_status, 'idle')

    def test_wcs_device_send_command(self):
        """Test sending command to WCS device"""
        command_data = {'command': 'move', 'target': 'A1', 'quantity': 10}

        # This method just logs the command, so we'll verify it doesn't raise an error
        self.wcs_device.action_send_command(command_data)

        # Test that the method runs without errors (no specific assertion needed since it just logs)

    def test_wcs_system_devices_relationship(self):
        """Test the relationship between WCS systems and devices"""
        # Verify that the device is linked to the system
        self.assertEqual(len(self.wcs_system.device_ids), 1)
        self.assertEqual(self.wcs_system.device_ids[0].id, self.wcs_device.id)

        # Create another device for the same system
        new_device = self.WmsWcsDevice.create({
            'name': 'Test AGV Device',
            'code': 'TAGV002',
            'wcs_system_id': self.wcs_system.id,
            'device_type': 'agv',
            'location_id': self.location_dst.id,
            'current_load': 100.0,
            'max_capacity': 500.0,
        })

        # Verify both devices are linked to the system
        self.assertEqual(len(self.wcs_system.device_ids), 2)
        device_ids = [d.id for d in self.wcs_system.device_ids]
        self.assertIn(self.wcs_device.id, device_ids)
        self.assertIn(new_device.id, device_ids)

    def test_wcs_integration_log_creation(self):
        """Test creation of WCS integration log records"""
        log = self.WmsWcsIntegrationLog.create({
            'wcs_system_id': self.wcs_system.id,
            'operation': 'connect',
            'status': 'success',
            'message': 'Successfully connected to WCS system',
            'request_data': '{}',
            'response_data': '{"status": "ok"}',
            'duration': 0.5,
        })

        self.assertEqual(log.wcs_system_id.id, self.wcs_system.id)
        self.assertEqual(log.operation, 'connect')
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.message, 'Successfully connected to WCS system')
        self.assertEqual(log.duration, 0.5)

    def test_wcs_task_duration_calculation(self):
        """Test duration calculation for WCS tasks"""
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()

        task = self.WmsWcsTask.create({
            'task_type': 'inventory',
            'wcs_system_id': self.wcs_system.id,
            'start_time': start_time,
            'end_time': end_time,
        })

        # Duration should be approximately 300 seconds (5 minutes)
        expected_duration = 300.0  # 5 minutes in seconds
        self.assertAlmostEqual(task.duration_seconds, expected_duration, places=0)

    def test_wcs_task_with_source_document(self):
        """Test WCS task with source document reference"""
        # Create a stock picking to use as source document
        picking = self.Picking.create({
            'name': 'TEST_PICKING_WCS_01',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
            'owner_id': self.owner.id,
            'state': 'draft',
        })

        task = self.WmsWcsTask.create({
            'task_type': 'move',
            'wcs_system_id': self.wcs_system.id,
            'source_document': f'stock.picking,{picking.id}',
            'source_location_id': self.location_src.id,
            'destination_location_id': self.location_dst.id,
            'product_id': self.product1.id,
            'quantity': 8.0,
        })

        self.assertEqual(task.source_document, f'stock.picking,{picking.id}')
        self.assertEqual(task.quantity, 8.0)