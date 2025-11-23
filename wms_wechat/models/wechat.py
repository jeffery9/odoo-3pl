from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import requests
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WmsWechatApp(models.Model):
    """
    WeChat App - Configuration for WeChat Mini Program integration
    """
    _name = 'wms.wechat.app'
    _description = 'WMS WeChat App'
    _order = 'name'

    name = fields.Char('App Name', required=True)
    app_id = fields.Char('App ID', required=True, help='WeChat Mini Program App ID')
    app_secret = fields.Char('App Secret', required=True, help='WeChat Mini Program App Secret')
    description = fields.Text('Description')

    # App configuration
    active = fields.Boolean('Active', default=True)
    app_type = fields.Selection([
        ('mini_program', 'Mini Program'),
        ('official_account', 'Official Account'),
        ('work_wechat', 'Work WeChat'),
    ], string='App Type', default='mini_program')

    # API configuration
    access_token = fields.Char('Access Token', readonly=True)
    token_expires = fields.Datetime('Token Expires', readonly=True)
    api_base_url = fields.Char('API Base URL', default='https://api.weixin.qq.com')

    # Business configuration
    warehouse_ids = fields.Many2many('stock.warehouse', string='Allowed Warehouses')
    default_warehouse_id = fields.Many2one('stock.warehouse', 'Default Warehouse')
    enable_inventory_check = fields.Boolean('Enable Inventory Check', default=True)
    enable_location_search = fields.Boolean('Enable Location Search', default=True)
    enable_picking_notifications = fields.Boolean('Enable Picking Notifications', default=True)

    # User management
    user_sync_enabled = fields.Boolean('User Synchronization Enabled', default=True)
    auto_create_users = fields.Boolean('Auto Create Users', default=True)

    # Integration settings
    webhook_url = fields.Char('Webhook URL', help='URL for receiving WeChat server callbacks')
    enable_webhook = fields.Boolean('Enable Webhook', default=False)

    # Status
    last_sync = fields.Datetime('Last Sync')
    connection_status = fields.Selection([
        ('disconnected', 'Disconnected'),
        ('connecting', 'Connecting'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ], string='Connection Status', default='disconnected', readonly=True)

    notes = fields.Text('Notes')

    def get_access_token(self):
        """Get access token from WeChat API"""
        for app in self:
            if app.token_expires and app.token_expires > fields.Datetime.now():
                # Token is still valid
                return app.access_token
            else:
                # Request new token
                url = f"{app.api_base_url}/cgi-bin/token"
                params = {
                    'grant_type': 'client_credential',
                    'appid': app.app_id,
                    'secret': app.app_secret,
                }

                try:
                    response = requests.get(url, params=params)
                    result = response.json()
                    if 'access_token' in result:
                        app.write({
                            'access_token': result['access_token'],
                            'token_expires': fields.Datetime.now() + timedelta(seconds=result.get('expires_in', 7200) - 300),  # 5 min buffer
                            'connection_status': 'connected',
                        })
                        return result['access_token']
                    else:
                        app.write({'connection_status': 'error'})
                        return None
                except Exception as e:
                    app.write({
                        'connection_status': 'error',
                        'notes': f'Error getting access token: {str(e)}'
                    })
                    return None

    def action_test_connection(self):
        """Test connection to WeChat API"""
        for app in self:
            token = app.get_access_token()
            if token:
                app.write({
                    'connection_status': 'connected',
                    'last_sync': fields.Datetime.now(),
                })
            else:
                app.write({'connection_status': 'error'})

    def process_webhook_data(self, message_data):
        """Process incoming webhook data from WeChat"""
        self.ensure_one()
        wechat_message_model = self.env['wms.wechat.message'].sudo()

        # Create and process the incoming message
        incoming_message = wechat_message_model.create({
            'name': message_data.get('MsgId', f'IN_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}'),
            'message_type': message_data.get('MsgType', 'text'),
            'sender_openid': message_data.get('FromUserName', ''),
            'receiver_openid': message_data.get('ToUserName', ''),
            'content': message_data.get('Content', ''),
            'timestamp': datetime.fromtimestamp(message_data.get('CreateTime', datetime.now().timestamp())) if message_data.get('CreateTime') else fields.Datetime.now(),
            'direction': 'in',
            'status': 'pending',
            'app_id': self.id,
        })

        # Process the message based on its content/type
        incoming_message._route_message()

        return incoming_message


class WmsWechatUser(models.Model):
    """
    WeChat User - Users registered through WeChat integration
    """
    _name = 'wms.wechat.user'
    _description = 'WMS WeChat User'
    _order = 'name'

    openid = fields.Char('OpenID', required=True, copy=False)
    unionid = fields.Char('UnionID', copy=False, help='Union ID across WeChat ecosystem')
    name = fields.Char('User Name', required=True)
    nickname = fields.Char('Nickname')
    avatar_url = fields.Char('Avatar URL')
    gender = fields.Selection([
        ('0', 'Unknown'),
        ('1', 'Male'),
        ('2', 'Female'),
    ], string='Gender', default='0')
    city = fields.Char('City')
    province = fields.Char('Province')
    country = fields.Char('Country')

    # User information
    active = fields.Boolean('Active', default=True)
    user_type = fields.Selection([
        ('employee', 'Employee'),
        ('customer', 'Customer'),
        ('partner', 'Partner'),
        ('visitor', 'Visitor'),
    ], string='User Type', default='visitor')

    # Odoo user association
    odoo_user_id = fields.Many2one('res.users', 'Odoo User', help='Associated Odoo user account')
    employee_id = fields.Many2one('hr.employee', 'Employee')

    # Permissions
    allowed_warehouse_ids = fields.Many2many('stock.warehouse', string='Allowed Warehouses')

    # WeChat app association
    app_id = fields.Many2one('wms.wechat.app', 'WeChat App', required=True)
    subscribe = fields.Boolean('Subscribed', default=True)
    subscribe_time = fields.Datetime('Subscribe Time')
    unsubscribe_time = fields.Datetime('Unsubscribe Time')

    # Last activity
    last_login = fields.Datetime('Last Login')
    last_activity = fields.Datetime('Last Activity')

    notes = fields.Text('Notes')

    _sql_constraints = [
        ('openid_unique', 'unique(openid)', 'OpenID must be unique!'),
    ]

    def sync_user_info(self, user_data):
        """Sync user information from WeChat"""
        for user in self:
            update_vals = {
                'nickname': user_data.get('nickname'),
                'avatar_url': user_data.get('headimgurl'),
                'gender': user_data.get('sex', '0'),
                'city': user_data.get('city'),
                'province': user_data.get('province'),
                'country': user_data.get('country'),
                'subscribe': user_data.get('subscribe', True),
            }
            if user_data.get('subscribe') and not user.subscribe_time:
                update_vals['subscribe_time'] = fields.Datetime.now()
            elif not user_data.get('subscribe') and not user.unsubscribe_time:
                update_vals['unsubscribe_time'] = fields.Datetime.now()

            user.write(update_vals)

    def action_login(self):
        """Handle user login through WeChat"""
        for user in self:
            user.write({
                'last_login': fields.Datetime.now(),
                'last_activity': fields.Datetime.now(),
            })


class WmsWechatMessage(models.Model):
    """
    WeChat Message - Messages sent to or received from WeChat
    """
    _name = 'wms.wechat.message'
    _description = 'WMS WeChat Message'
    _order = 'timestamp desc'

    name = fields.Char('Message ID', required=True, copy=False)
    message_type = fields.Selection([
        ('text', 'Text'),
        ('image', 'Image'),
        ('voice', 'Voice'),
        ('video', 'Video'),
        ('location', 'Location'),
        ('link', 'Link'),
        ('event', 'Event'),
    ], string='Message Type', required=True)

    # Sender and receiver
    sender_openid = fields.Char('Sender OpenID', required=True)
    receiver_openid = fields.Char('Receiver OpenID')
    app_id = fields.Many2one('wms.wechat.app', 'WeChat App', required=True)

    # Message content
    content = fields.Text('Content')
    media_id = fields.Char('Media ID', help='ID of media file if message contains media')
    timestamp = fields.Datetime('Timestamp', default=fields.Datetime.now)

    # Message direction
    direction = fields.Selection([
        ('in', 'Incoming'),
        ('out', 'Outgoing'),
    ], string='Direction', required=True, default='in')

    # Related to business objects
    related_model = fields.Char('Related Model')
    related_id = fields.Integer('Related ID')
    operation = fields.Char('Operation', help='Business operation associated with the message')

    # Response tracking
    is_read = fields.Boolean('Is Read', default=False)
    is_processed = fields.Boolean('Is Processed', default=False)
    response_id = fields.Many2one('wms.wechat.message', 'Response Message')

    # Status and results
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')

    error_message = fields.Text('Error Message')

    notes = fields.Text('Notes')

    def send_message(self, openid, content, message_type='text'):
        """Send message to WeChat user"""
        for app in self.app_id:
            access_token = app.get_access_token()
            if not access_token:
                return False

            url = f"{app.api_base_url}/cgi-bin/message/custom/send"
            data = {
                'touser': openid,
                'msgtype': message_type,
                'text': {'content': content}
            }

            if message_type == 'text':
                data['text'] = {'content': content}
            else:
                # For other message types, we would format differently
                pass

            try:
                response = requests.post(url, json=data)
                result = response.json()
                if result.get('errcode') == 0:
                    self.write({
                        'status': 'sent',
                        'name': result.get('msgid', self.name),  # Use returned message ID if available
                    })
                    return True
                else:
                    self.write({
                        'status': 'failed',
                        'error_message': result.get('errmsg', 'Unknown error')
                    })
                    return False
            except Exception as e:
                self.write({
                    'status': 'failed',
                    'error_message': str(e)
                })
                return False

    def mark_as_read(self):
        """Mark message as read"""
        self.write({'is_read': True})

    def mark_as_processed(self):
        """Mark message as processed"""
        self.write({'is_processed': True})

    def process_incoming_message(self, message_data):
        """Process an incoming message from WeChat"""
        for message in self:
            # Create the incoming message record
            incoming_message = self.create({
                'name': message_data.get('MsgId', f'IN_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}'),
                'message_type': message_data.get('MsgType', 'text'),
                'sender_openid': message_data.get('FromUserName'),
                'receiver_openid': message_data.get('ToUserName'),
                'app_id': message.app_id.id,
                'content': message_data.get('Content', ''),
                'timestamp': datetime.fromtimestamp(message_data.get('CreateTime', datetime.now().timestamp())),
                'direction': 'in',
                'status': 'pending',
            })

            # Process the message based on its content/type
            incoming_message._route_message()

            return incoming_message

    def _route_message(self):
        """Route the incoming message to the appropriate handler based on content and message type"""
        for message in self:
            message_type = message.message_type
            content = message.content.lower().strip() if message.content else ""

            if message_type == 'text':
                # Handle text-based commands
                if content.startswith('inventory') or 'inventory' in content:
                    message._handle_inventory_request()
                elif content.startswith('location') or 'location' in content:
                    message._handle_location_request()
                elif content.startswith('picking') or 'picking' in content:
                    message._handle_picking_request()
                elif content.startswith('help') or content == '?' or 'help' in content:
                    message._handle_help_request()
                else:
                    # Default response for unrecognized commands
                    message._handle_unrecognized_request()
            elif message_type == 'location':
                message._handle_location_message()
            elif message_type == 'image':
                message._handle_image_message()
            elif message_type == 'event':
                message._handle_event_message()
            else:
                # For other message types, try to handle as text
                message._handle_unrecognized_request()

            # Mark as processed
            message.mark_as_processed()

    def _handle_location_message(self):
        """Handle location messages (when user shares their location)"""
        response_content = "Thank you for sharing your location. Our system can use location data for navigation and task assignment."

        # Send response back to user
        response_message = self.env['wms.wechat.message'].create({
            'name': f'RESP_{self.id}',
            'message_type': 'text',
            'sender_openid': self.app_id.app_id,
            'receiver_openid': self.sender_openid,
            'app_id': self.app_id.id,
            'content': response_content,
            'direction': 'out',
        })
        response_message.send_message(self.sender_openid, response_content)

    def _handle_image_message(self):
        """Handle image messages (for example, for quality checks or reporting)"""
        response_content = "Image received. In a full implementation, this could be used for quality inspection or damage reporting."

        # Send response back to user
        response_message = self.env['wms.wechat.message'].create({
            'name': f'RESP_{self.id}',
            'message_type': 'text',
            'sender_openid': self.app_id.app_id,
            'receiver_openid': self.sender_openid,
            'app_id': self.app_id.id,
            'content': response_content,
            'direction': 'out',
        })
        response_message.send_message(self.sender_openid, response_content)

    def _handle_event_message(self):
        """Handle event messages (such as subscribe/unsubscribe)"""
        # Process based on event type
        event_type = self.content  # In real implementation, event type would be in a separate field
        if 'subscribe' in event_type.lower():
            self._handle_subscribe_event()
        elif 'unsubscribe' in event_type.lower():
            self._handle_unsubscribe_event()
        else:
            # Default event handling
            self._handle_unrecognized_request()

    def _handle_subscribe_event(self):
        """Handle user subscription event"""
        # Find or create the user
        user = self.env['wms.wechat.user'].search([('openid', '=', self.sender_openid)], limit=1)
        if not user and self.app_id.auto_create_users:
            user = self.env['wms.wechat.user'].create({
                'openid': self.sender_openid,
                'name': f'WeChat User {self.sender_openid[-6:]}',
                'app_id': self.app_id.id,
                'subscribe': True,
                'subscribe_time': fields.Datetime.now(),
            })

        response_content = "Welcome! You've successfully subscribed to warehouse services. Type 'help' for available commands."

        # Send welcome message back to user
        response_message = self.env['wms.wechat.message'].create({
            'name': f'RESP_{self.id}',
            'message_type': 'text',
            'sender_openid': self.app_id.app_id,
            'receiver_openid': self.sender_openid,
            'app_id': self.app_id.id,
            'content': response_content,
            'direction': 'out',
        })
        response_message.send_message(self.sender_openid, response_content)

    def _handle_unsubscribe_event(self):
        """Handle user unsubscription event"""
        # Update user subscription status
        user = self.env['wms.wechat.user'].search([('openid', '=', self.sender_openid)], limit=1)
        if user:
            user.write({
                'subscribe': False,
                'unsubscribe_time': fields.Datetime.now(),
            })

        _logger.info(f"User unsubscribed: {self.sender_openid}")

    def _handle_inventory_request(self):
        """Handle inventory-related requests"""
        # Find the associated WeChat user
        user = self.env['wms.wechat.user'].search([('openid', '=', self.sender_openid)], limit=1)
        if not user:
            # Auto-create user if enabled in app settings
            app = self.app_id
            if app.auto_create_users:
                user = self.env['wms.wechat.user'].create({
                    'openid': self.sender_openid,
                    'name': f'WeChat User {self.sender_openid[-6:]}',  # Use last 6 chars as name
                    'app_id': app.id,
                })

        if user:
            # Create an inventory check request
            inventory_check = self.env['wms.wechat.inventory.check'].create({
                'check_type': 'location_check',
                'operator_id': user.id,
                'warehouse_id': user.allowed_warehouse_ids[0].id if user.allowed_warehouse_ids else user.app_id.default_warehouse_id.id,
                'app_id': self.app_id.id,
            })

            # Send a response back to the user
            response_message = self.env['wms.wechat.message'].create({
                'name': f'RESP_{self.id}',
                'message_type': 'text',
                'sender_openid': self.app_id.app_id,
                'receiver_openid': self.sender_openid,
                'app_id': self.app_id.id,
                'content': f'Inventory check initiated: {inventory_check.name}. Please scan items to verify quantities.',
                'direction': 'out',
            })
            response_message.send_message(self.sender_openid, f'Inventory check initiated: {inventory_check.name}. Please scan items to verify quantities.')

    def _handle_location_request(self):
        """Handle location-related requests"""
        response_content = "Please specify which location you're looking for. Example: 'location A01' or 'find location for product ABC123'"

        # Send response back to user
        response_message = self.env['wms.wechat.message'].create({
            'name': f'RESP_{self.id}',
            'message_type': 'text',
            'sender_openid': self.app_id.app_id,
            'receiver_openid': self.sender_openid,
            'app_id': self.app_id.id,
            'content': response_content,
            'direction': 'out',
        })
        response_message.send_message(self.sender_openid, response_content)

    def _handle_picking_request(self):
        """Handle picking-related requests"""
        response_content = "Picking information: You can view your assigned picking tasks in the app. Would you like me to list them?"

        # Send response back to user
        response_message = self.env['wms.wechat.message'].create({
            'name': f'RESP_{self.id}',
            'message_type': 'text',
            'sender_openid': self.app_id.app_id,
            'receiver_openid': self.sender_openid,
            'app_id': self.app_id.id,
            'content': response_content,
            'direction': 'out',
        })
        response_message.send_message(self.sender_openid, response_content)

    def _handle_help_request(self):
        """Handle help requests"""
        help_text = """
        Available commands:
        - inventory: Start an inventory check
        - location [item]: Find location for an item
        - picking: Check picking tasks
        - help or ?: Show this help message
        """

        # Send response back to user
        response_message = self.env['wms.wechat.message'].create({
            'name': f'RESP_{self.id}',
            'message_type': 'text',
            'sender_openid': self.app_id.app_id,
            'receiver_openid': self.sender_openid,
            'app_id': self.app_id.id,
            'content': help_text,
            'direction': 'out',
        })
        response_message.send_message(self.sender_openid, help_text)

    def _handle_unrecognized_request(self):
        """Handle unrecognized requests"""
        default_response = "I didn't understand that command. Type 'help' for available commands."

        # Send response back to user
        response_message = self.env['wms.wechat.message'].create({
            'name': f'RESP_{self.id}',
            'message_type': 'text',
            'sender_openid': self.app_id.app_id,
            'receiver_openid': self.sender_openid,
            'app_id': self.app_id.id,
            'content': default_response,
            'direction': 'out',
        })
        response_message.send_message(self.sender_openid, default_response)


class WmsWechatInventoryCheck(models.Model):
    """
    WeChat Inventory Check - Inventory checks initiated through WeChat
    """
    _name = 'wms.wechat.inventory.check'
    _description = 'WMS WeChat Inventory Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_created desc'

    name = fields.Char('Check Reference', required=True, copy=False,
                       default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True)

    # Check information
    date_created = fields.Datetime('Date Created', default=fields.Datetime.now)
    date_started = fields.Datetime('Date Started')
    date_completed = fields.Datetime('Date Completed')
    check_type = fields.Selection([
        ('cycle_count', 'Cycle Count'),
        ('full_inventory', 'Full Inventory'),
        ('location_check', 'Location Check'),
        ('product_check', 'Product Check'),
    ], string='Check Type', required=True)

    # Operator and location
    operator_id = fields.Many2one('wms.wechat.user', 'Operator', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    product_id = fields.Many2one('product.product', 'Product')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')

    # Warehouse and app
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    app_id = fields.Many2one('wms.wechat.app', 'WeChat App', required=True)

    # Results
    items_checked = fields.Integer('Items Checked', readonly=True)
    discrepancies_found = fields.Integer('Discrepancies Found', readonly=True)
    accuracy_rate = fields.Float('Accuracy Rate (%)', readonly=True)

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.wechat.inventory.check') or _('New')
        return super().create(vals)

    def action_start_check(self):
        """Start the inventory check"""
        for check in self:
            check.write({
                'state': 'in_progress',
                'date_started': fields.Datetime.now(),
            })

    def action_complete_check(self, results_data=None):
        """Complete the inventory check"""
        for check in self:
            # Process results if provided
            if results_data:
                check.items_checked = results_data.get('items_checked', 0)
                check.discrepancies_found = results_data.get('discrepancies_found', 0)
                total_items = results_data.get('items_checked', 1)
                if total_items > 0:
                    check.accuracy_rate = ((total_items - check.discrepancies_found) / total_items) * 100
                else:
                    check.accuracy_rate = 100.0

            check.write({
                'state': 'completed',
                'date_completed': fields.Datetime.now(),
            })

    def action_cancel_check(self):
        """Cancel the inventory check"""
        for check in self:
            check.write({'state': 'cancelled'})


class WmsWechatPickingNotification(models.Model):
    """
    WeChat Picking Notification - Notifications sent to WeChat users about picking tasks
    """
    _name = 'wms.wechat.picking.notification'
    _description = 'WMS WeChat Picking Notification'
    _order = 'date_created desc'

    name = fields.Char('Notification Reference', required=True, copy=False)
    notification_type = fields.Selection([
        ('new_picking', 'New Picking Task'),
        ('picking_updated', 'Picking Updated'),
        ('picking_completed', 'Picking Completed'),
        ('location_assigned', 'Location Assigned'),
        ('urgent_picking', 'Urgent Picking'),
    ], string='Notification Type', required=True)

    # Related picking
    stock_picking_id = fields.Many2one('stock.picking', 'Stock Picking', required=True)

    # Recipients
    recipient_user_id = fields.Many2one('wms.wechat.user', 'Recipient', required=True)
    app_id = fields.Many2one('wms.wechat.app', 'WeChat App', required=True)

    # Notification details
    date_created = fields.Datetime('Date Created', default=fields.Datetime.now)
    date_sent = fields.Datetime('Date Sent')
    date_read = fields.Datetime('Date Read')

    # Content
    title = fields.Char('Title', required=True)
    message = fields.Text('Message', required=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')

    # Status
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')

    # Results
    response_data = fields.Text('Response Data')
    error_message = fields.Text('Error Message')

    def send_notification(self):
        """Send notification to WeChat user"""
        for notification in self:
            # Create a WeChat message
            message = self.env['wms.wechat.message'].create({
                'name': f'NOTIFY_{notification.id}',
                'message_type': 'text',
                'sender_openid': notification.app_id.app_id,
                'receiver_openid': notification.recipient_user_id.openid,
                'app_id': notification.app_id.id,
                'content': f"{notification.title}\n{notification.message}",
                'direction': 'out',
            })

            # Send the message through WeChat API
            if message.send_message(notification.recipient_user_id.openid, f"{notification.title}\n{notification.message}"):
                notification.write({
                    'status': 'sent',
                    'date_sent': fields.Datetime.now(),
                })
            else:
                notification.write({
                    'status': 'failed',
                    'error_message': message.error_message,
                })

    def mark_as_read(self):
        """Mark notification as read"""
        for notification in self:
            notification.write({
                'status': 'read',
                'date_read': fields.Datetime.now(),
            })