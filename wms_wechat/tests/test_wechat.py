from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json
import mock


@tagged('wms_wechat', 'at_install')
class TestWmsWechat(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.WmsWechatApp = self.env['wms.wechat.app']
        self.WmsWechatUser = self.env['wms.wechat.user']
        self.WmsWechatMessage = self.env['wms.wechat.message']
        self.WmsWechatInventoryCheck = self.env['wms.wechat.inventory.check']
        self.WmsWechatPickingNotification = self.env['wms.wechat.picking.notification']
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

        # Create test WeChat app
        self.wechat_app = self.WmsWechatApp.create({
            'name': 'Test WeChat Mini App',
            'app_id': 'wxc123456789abcdef',
            'app_secret': 'test_secret_key_123456',
            'app_type': 'mini_program',
            'enable_inventory_check': True,
            'enable_location_search': True,
            'enable_picking_notifications': True,
            'auto_create_users': True,
            'default_warehouse_id': self.warehouse.id,
        })

        # Create test WeChat user
        self.wechat_user = self.WmsWechatUser.create({
            'openid': 'o123456789abcdef1234567890',
            'name': 'Test WeChat User',
            'nickname': 'TestUser',
            'app_id': self.wechat_app.id,
            'subscribe': True,
            'subscribe_time': datetime.now(),
            'allowed_warehouse_ids': [(6, 0, [self.warehouse.id])],
        })

    def test_wechat_app_creation(self):
        """Test creation of WeChat app records"""
        app = self.WmsWechatApp.create({
            'name': 'Another WeChat App',
            'app_id': 'wxc987654321fedcba',
            'app_secret': 'another_test_secret',
            'app_type': 'official_account',
            'enable_inventory_check': False,
            'enable_location_search': True,
            'user_sync_enabled': True,
            'auto_create_users': False,
            'default_warehouse_id': self.warehouse.id,
        })

        self.assertEqual(app.name, 'Another WeChat App')
        self.assertEqual(app.app_id, 'wxc987654321fedcba')
        self.assertEqual(app.app_type, 'official_account')
        self.assertFalse(app.enable_inventory_check)
        self.assertTrue(app.enable_location_search)
        self.assertTrue(app.active)

    def test_wechat_user_creation(self):
        """Test creation of WeChat user records"""
        user = self.WmsWechatUser.create({
            'openid': 'o987654321fedcba9876543210',
            'name': 'Second WeChat User',
            'nickname': 'SecondUser',
            'unionid': 'u123456789abcdef',
            'avatar_url': 'https://example.com/avatar.jpg',
            'gender': '1',
            'city': 'Test City',
            'province': 'Test Province',
            'country': 'Test Country',
            'user_type': 'employee',
            'app_id': self.wechat_app.id,
            'subscribe': True,
            'subscribe_time': datetime.now(),
            'allowed_warehouse_ids': [(6, 0, [self.warehouse.id])],
        })

        self.assertEqual(user.name, 'Second WeChat User')
        self.assertEqual(user.nickname, 'SecondUser')
        self.assertEqual(user.openid, 'o987654321fedcba9876543210')
        self.assertEqual(user.unionid, 'u123456789abcdef')
        self.assertEqual(user.user_type, 'employee')
        self.assertTrue(user.subscribe)
        self.assertIn(self.warehouse.id, [w.id for w in user.allowed_warehouse_ids])

    def test_wechat_user_sync_info(self):
        """Test WeChat user info synchronization"""
        user_data = {
            'nickname': 'Updated Nickname',
            'headimgurl': 'https://example.com/updated_avatar.jpg',
            'sex': '2',
            'city': 'Updated City',
            'province': 'Updated Province',
            'country': 'Updated Country',
            'subscribe': True,
        }

        # Update user info
        self.wechat_user.sync_user_info(user_data)

        self.assertEqual(self.wechat_user.nickname, 'Updated Nickname')
        self.assertEqual(self.wechat_user.avatar_url, 'https://example.com/updated_avatar.jpg')
        self.assertEqual(self.wechat_user.gender, '2')
        self.assertEqual(self.wechat_user.city, 'Updated City')
        self.assertTrue(self.wechat_user.subscribe)

    def test_wechat_user_login(self):
        """Test WeChat user login functionality"""
        initial_last_login = self.wechat_user.last_login
        initial_last_activity = self.wechat_user.last_activity

        # Perform login action
        self.wechat_user.action_login()

        # Check that login and activity timestamps have been updated
        self.assertIsNotNone(self.wechat_user.last_login)
        self.assertIsNotNone(self.wechat_user.last_activity)
        self.assertGreaterEqual(self.wechat_user.last_login, initial_last_login or datetime.min)
        self.assertGreaterEqual(self.wechat_user.last_activity, initial_last_activity or datetime.min)

    def test_wechat_message_creation(self):
        """Test creation of WeChat message records"""
        message = self.WmsWechatMessage.create({
            'name': 'TEST_MSG_001',
            'message_type': 'text',
            'sender_openid': 'o123456789abcdef1234567890',
            'receiver_openid': 'wxc123456789abcdef',
            'app_id': self.wechat_app.id,
            'content': 'Hello from WeChat user!',
            'timestamp': datetime.now(),
            'direction': 'in',
            'status': 'pending',
        })

        self.assertEqual(message.name, 'TEST_MSG_001')
        self.assertEqual(message.message_type, 'text')
        self.assertEqual(message.sender_openid, 'o123456789abcdef1234567890')
        self.assertEqual(message.receiver_openid, 'wxc123456789abcdef')
        self.assertEqual(message.direction, 'in')
        self.assertEqual(message.status, 'pending')
        self.assertEqual(message.content, 'Hello from WeChat user!')

    def test_wechat_message_status_transitions(self):
        """Test WeChat message status transitions"""
        message = self.WmsWechatMessage.create({
            'name': 'TEST_MSG_002',
            'message_type': 'text',
            'sender_openid': 'o123456789abcdef1234567890',
            'receiver_openid': 'wxc123456789abcdef',
            'app_id': self.wechat_app.id,
            'content': 'Test message',
            'direction': 'out',
            'status': 'pending',
        })

        # Initially should be pending
        self.assertEqual(message.status, 'pending')
        self.assertFalse(message.is_read)
        self.assertFalse(message.is_processed)

        # Mark as read
        message.mark_as_read()
        self.assertTrue(message.is_read)

        # Mark as processed
        message.mark_as_processed()
        self.assertTrue(message.is_processed)

    def test_wechat_inventory_check_creation(self):
        """Test creation of WeChat inventory check records"""
        inventory_check = self.WmsWechatInventoryCheck.create({
            'check_type': 'location_check',
            'operator_id': self.wechat_user.id,
            'warehouse_id': self.warehouse.id,
            'app_id': self.wechat_app.id,
            'location_id': self.location_src.id,
            'product_id': self.product1.id,
        })

        self.assertEqual(inventory_check.check_type, 'location_check')
        self.assertEqual(inventory_check.operator_id.id, self.wechat_user.id)
        self.assertEqual(inventory_check.warehouse_id.id, self.warehouse.id)
        self.assertEqual(inventory_check.app_id.id, self.wechat_app.id)
        self.assertEqual(inventory_check.state, 'draft')
        self.assertEqual(inventory_check.location_id.id, self.location_src.id)
        self.assertEqual(inventory_check.product_id.id, self.product1.id)

    def test_wechat_inventory_check_state_transitions(self):
        """Test WeChat inventory check state transitions"""
        inventory_check = self.WmsWechatInventoryCheck.create({
            'check_type': 'cycle_count',
            'operator_id': self.wechat_user.id,
            'warehouse_id': self.warehouse.id,
            'app_id': self.wechat_app.id,
        })

        # Initially should be in draft
        self.assertEqual(inventory_check.state, 'draft')

        # Start the check
        inventory_check.action_start_check()
        self.assertEqual(inventory_check.state, 'in_progress')
        self.assertIsNotNone(inventory_check.date_started)

        # Complete the check
        inventory_check.action_complete_check({
            'items_checked': 10,
            'discrepancies_found': 1,
        })
        self.assertEqual(inventory_check.state, 'completed')
        self.assertIsNotNone(inventory_check.date_completed)
        self.assertEqual(inventory_check.items_checked, 10)
        self.assertEqual(inventory_check.discrepancies_found, 1)
        self.assertAlmostEqual(inventory_check.accuracy_rate, 90.0)  # (10-1)/10 * 100

        # Create another check and cancel it
        inventory_check2 = self.WmsWechatInventoryCheck.create({
            'check_type': 'full_inventory',
            'operator_id': self.wechat_user.id,
            'warehouse_id': self.warehouse.id,
            'app_id': self.wechat_app.id,
        })

        inventory_check2.action_cancel_check()
        self.assertEqual(inventory_check2.state, 'cancelled')

    def test_wechat_picking_notification_creation(self):
        """Test creation of WeChat picking notification records"""
        # Create a test picking
        picking = self.Picking.create({
            'name': 'TEST_PICKING_WECHAT_01',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
            'owner_id': self.owner.id,
        })

        notification = self.WmsWechatPickingNotification.create({
            'notification_type': 'new_picking',
            'stock_picking_id': picking.id,
            'recipient_user_id': self.wechat_user.id,
            'app_id': self.wechat_app.id,
            'title': 'New Picking Task',
            'message': f'You have a new picking task: {picking.name}',
            'priority': 'normal',
        })

        self.assertEqual(notification.notification_type, 'new_picking')
        self.assertEqual(notification.stock_picking_id.id, picking.id)
        self.assertEqual(notification.recipient_user_id.id, self.wechat_user.id)
        self.assertEqual(notification.app_id.id, self.wechat_app.id)
        self.assertEqual(notification.title, 'New Picking Task')
        self.assertIn(picking.name, notification.message)
        self.assertEqual(notification.priority, 'normal')
        self.assertEqual(notification.status, 'pending')

    def test_wechat_picking_notification_status_transitions(self):
        """Test WeChat picking notification status transitions"""
        # Create a test picking
        picking = self.Picking.create({
            'name': 'TEST_PICKING_WECHAT_02',
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dst.id,
        })

        notification = self.WmsWechatPickingNotification.create({
            'notification_type': 'urgent_picking',
            'stock_picking_id': picking.id,
            'recipient_user_id': self.wechat_user.id,
            'app_id': self.wechat_app.id,
            'title': 'Urgent Picking Task',
            'message': f'Urgent: {picking.name}',
            'priority': 'urgent',
        })

        # Initially should be pending
        self.assertEqual(notification.status, 'pending')

        # Mark as read
        notification.mark_as_read()
        self.assertEqual(notification.status, 'read')
        self.assertIsNotNone(notification.date_read)

    @mock.patch('requests.get')
    def test_wechat_app_connection_test(self, mock_get):
        """Test WeChat app connection functionality"""
        # Mock the API response
        mock_get.return_value.json.return_value = {
            'access_token': 'test_access_token',
            'expires_in': 7200
        }

        # Test initial state
        self.assertEqual(self.wechat_app.connection_status, 'disconnected')

        # Test connection
        self.wechat_app.action_test_connection()

        # Verify that the token was updated and connection was successful
        self.assertEqual(self.wechat_app.connection_status, 'connected')
        self.assertIsNotNone(self.wechat_app.last_sync)

    def test_wechat_app_get_access_token(self):
        """Test getting access token from WeChat API"""
        # This test would require mocking the API call in a real scenario
        # For now, we'll test the method directly with a mock
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'access_token': 'mocked_token',
                'expires_in': 7200
            }

            token = self.wechat_app.get_access_token()
            self.assertEqual(token, 'mocked_token')

    def test_wechat_message_routing(self):
        """Test routing of WeChat messages based on content"""
        # Create a test message with inventory command
        message = self.WmsWechatMessage.create({
            'name': 'TEST_ROUTE_MSG_001',
            'message_type': 'text',
            'sender_openid': self.wechat_user.openid,
            'receiver_openid': self.wechat_app.app_id,
            'app_id': self.wechat_app.id,
            'content': 'inventory check',
            'direction': 'in',
            'status': 'pending',
        })

        # The routing happens through _route_message which should trigger
        # the appropriate handler based on content
        message._route_message()

        # Check that message was processed
        self.assertTrue(message.is_processed)

    def test_wechat_message_help_request(self):
        """Test handling of help requests in WeChat messages"""
        # Create a message with help command
        message = self.WmsWechatMessage.create({
            'name': 'TEST_HELP_MSG_001',
            'message_type': 'text',
            'sender_openid': self.wechat_user.openid,
            'receiver_openid': self.wechat_app.app_id,
            'app_id': self.wechat_app.id,
            'content': 'help',
            'direction': 'in',
            'status': 'pending',
        })

        # This should trigger the help handler
        message._route_message()

        # A response message should have been created
        response_messages = self.WmsWechatMessage.search([
            ('name', 'like', f'RESP_{message.id}')
        ])
        self.assertTrue(len(response_messages) > 0)

    def test_wechat_message_inventory_request(self):
        """Test handling of inventory requests in WeChat messages"""
        # Create a message with inventory command
        message = self.WmsWechatMessage.create({
            'name': 'TEST_INV_MSG_001',
            'message_type': 'text',
            'sender_openid': self.wechat_user.openid,
            'receiver_openid': self.wechat_app.app_id,
            'app_id': self.wechat_app.id,
            'content': 'inventory',
            'direction': 'in',
            'status': 'pending',
        })

        # This should trigger the inventory handler and create an inventory check
        message._route_message()

        # Check if an inventory check was created
        inventory_checks = self.WmsWechatInventoryCheck.search([
            ('operator_id', '=', self.wechat_user.id)
        ])
        self.assertTrue(len(inventory_checks) > 0)

    def test_wechat_user_unique_openid_constraint(self):
        """Test that OpenID must be unique for WeChat users"""
        # Create first user
        user1 = self.WmsWechatUser.create({
            'openid': 'o_unique_test_001',
            'name': 'Test User 1',
            'app_id': self.wechat_app.id,
        })

        # Attempt to create second user with same OpenID should fail
        with self.assertRaises(ValidationError):
            self.WmsWechatUser.create({
                'openid': 'o_unique_test_001',  # Same OpenID as user1
                'name': 'Test User 2',
                'app_id': self.wechat_app.id,
            })

    def test_process_webhook_data(self):
        """Test processing of webhook data from WeChat"""
        # Sample webhook message data
        message_data = {
            'ToUserName': self.wechat_app.app_id,
            'FromUserName': self.wechat_user.openid,
            'CreateTime': int(datetime.now().timestamp()),
            'MsgType': 'text',
            'Content': 'inventory request',
            'MsgId': '123456789'
        }

        # Process the webhook data
        incoming_message = self.wechat_app.process_webhook_data(message_data)

        # Verify the incoming message was created
        self.assertEqual(incoming_message.message_type, 'text')
        self.assertEqual(incoming_message.sender_openid, self.wechat_user.openid)
        self.assertEqual(incoming_message.content, 'inventory request')
        self.assertEqual(incoming_message.direction, 'in')
        self.assertTrue(incoming_message.is_processed)