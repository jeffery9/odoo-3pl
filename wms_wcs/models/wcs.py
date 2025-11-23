from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import requests
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WmsWcsSystem(models.Model):
    """
    WCS System - Warehouse Control System integration
    """
    _name = 'wms.wcs.system'
    _description = 'WMS WCS System'
    _order = 'name'

    name = fields.Char('System Name', required=True)
    code = fields.Char('System Code', required=True, copy=False)
    description = fields.Text('Description')

    # System information
    active = fields.Boolean('Active', default=True)
    system_type = fields.Selection([
        ('automated_storage', 'Automated Storage System'),
        ('conveyor', 'Conveyor System'),
        ('agv', 'Automated Guided Vehicle'),
        ('robotic_arm', 'Robotic Arm System'),
        ('sorter', 'Sorting System'),
        ('warehouse_automation', 'Warehouse Automation'),
    ], string='System Type', required=True)

    # Connection configuration
    host = fields.Char('Host', help='WCS system host address')
    port = fields.Integer('Port', help='WCS system port')
    protocol = fields.Selection([
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
        ('tcp', 'TCP'),
        ('modbus', 'Modbus'),
        ('opc_ua', 'OPC-UA'),
    ], string='Protocol', default='http')
    username = fields.Char('Username')
    password = fields.Char('Password')

    # API configuration
    api_url = fields.Char('API URL')
    api_key = fields.Char('API Key')
    is_connected = fields.Boolean('Connected', readonly=True)

    # Status and monitoring
    last_sync = fields.Datetime('Last Sync')
    connection_status = fields.Selection([
        ('disconnected', 'Disconnected'),
        ('connecting', 'Connecting'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ], string='Connection Status', default='disconnected', readonly=True)

    # WCS devices
    device_ids = fields.One2many('wms.wcs.device', 'wcs_system_id', 'Devices')

    notes = fields.Text('Notes')

    def action_test_connection(self):
        """Test connection to the WCS system"""
        for system in self:
            try:
                # This would implement the actual connection test to the WCS system
                # For now, we'll just update the status
                system.write({
                    'connection_status': 'connected',
                    'is_connected': True,
                    'last_sync': fields.Datetime.now(),
                })
            except Exception as e:
                system.write({
                    'connection_status': 'error',
                    'is_connected': False,
                })

    def action_sync_devices(self):
        """Synchronize devices with the WCS system"""
        for system in self:
            # This would sync devices from the WCS system
            # For now, we'll just log the action
            _logger.info(f"Syncing devices for WCS system: {system.name}")


class WmsWcsDevice(models.Model):
    """
    WCS Device - Individual devices managed by the WCS system
    """
    _name = 'wms.wcs.device'
    _description = 'WMS WCS Device'
    _order = 'name'

    name = fields.Char('Device Name', required=True)
    code = fields.Char('Device Code', required=True, copy=False)
    description = fields.Text('Description')

    # Device information
    wcs_system_id = fields.Many2one('wms.wcs.system', 'WCS System', required=True)
    device_type = fields.Selection([
        ('storage', 'Storage Device'),
        ('conveyor', 'Conveyor'),
        ('robot', 'Robot'),
        ('agv', 'AGV'),
        ('sorter', 'Sorter'),
        ('scanner', 'Scanner'),
        ('printer', 'Printer'),
        ('light', 'Light Indicator'),
        ('scale', 'Scale'),
    ], string='Device Type', required=True)

    # Location and configuration
    location_id = fields.Many2one('stock.location', 'Stock Location', help='Physical location of the device')
    is_active = fields.Boolean('Active', default=True)
    device_status = fields.Selection([
        ('offline', 'Offline'),
        ('idle', 'Idle'),
        ('working', 'Working'),
        ('maintenance', 'Maintenance'),
        ('error', 'Error'),
    ], string='Status', default='offline', readonly=True)

    # Technical specifications
    ip_address = fields.Char('IP Address')
    max_capacity = fields.Float('Max Capacity')
    current_load = fields.Float('Current Load')
    efficiency_rate = fields.Float('Efficiency Rate (%)', compute='_compute_efficiency_rate')

    # Connection details
    last_heartbeat = fields.Datetime('Last Heartbeat')
    last_command = fields.Datetime('Last Command Executed')
    command_queue_size = fields.Integer('Command Queue Size', default=0)

    notes = fields.Text('Notes')

    @api.depends('current_load', 'max_capacity')
    def _compute_efficiency_rate(self):
        for device in self:
            if device.max_capacity and device.current_load:
                device.efficiency_rate = min((device.current_load / device.max_capacity) * 100, 100.0)
            else:
                device.efficiency_rate = 0.0

    def action_send_command(self, command_data):
        """Send command to the WCS device"""
        for device in self:
            # This would send the actual command to the device
            # For now, we'll just log the action
            _logger.info(f"Sending command to device {device.name}: {command_data}")

    def action_refresh_status(self):
        """Refresh the device status from WCS system"""
        for device in self:
            # This would refresh status from the WCS system
            # For now, we'll just update the heartbeat
            device.write({
                'last_heartbeat': fields.Datetime.now(),
                'device_status': 'idle',  # Simulate status update
            })


class WmsWcsTask(models.Model):
    """
    WCS Task - Tasks sent to the WCS system for execution
    """
    _name = 'wms.wcs.task'
    _description = 'WMS WCS Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, date_created'

    name = fields.Char('Task Reference', required=True, copy=False,
                       default=lambda self: _('New'))
    task_type = fields.Selection([
        ('storage', 'Storage Task'),
        ('retrieval', 'Retrieval Task'),
        ('move', 'Move Task'),
        ('sort', 'Sort Task'),
        ('pack', 'Pack Task'),
        ('label', 'Label Task'),
        ('inventory', 'Inventory Task'),
        ('maintenance', 'Maintenance Task'),
    ], string='Task Type', required=True)

    # Task information
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('sent', 'Sent to WCS'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ], string='State', default='draft', tracking=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1')

    date_created = fields.Datetime('Date Created', default=fields.Datetime.now)
    date_confirmed = fields.Datetime('Date Confirmed')
    date_sent = fields.Datetime('Date Sent to WCS')
    date_started = fields.Datetime('Date Started')
    date_completed = fields.Datetime('Date Completed')

    # WCS integration
    wcs_system_id = fields.Many2one('wms.wcs.system', 'WCS System', required=True)
    device_id = fields.Many2one('wms.wcs.device', 'Assigned Device')
    task_data = fields.Text('Task Data', help='JSON data for the WCS task')

    # Source and destination
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    destination_location_id = fields.Many2one('stock.location', 'Destination Location')

    # Product information
    product_id = fields.Many2one('product.product', 'Product')
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    quantity = fields.Float('Quantity')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')

    # Related documents
    source_document = fields.Reference([
        ('stock.picking', 'Stock Picking'),
        ('stock.move', 'Stock Move'),
        ('stock.quant', 'Stock Quant'),
        ('sale.order', 'Sale Order'),
        ('purchase.order', 'Purchase Order'),
    ], string='Source Document')

    # Execution details
    start_time = fields.Datetime('Start Time')
    end_time = fields.Datetime('End Time')
    duration_seconds = fields.Float('Duration (seconds)', compute='_compute_duration')
    success_rate = fields.Float('Success Rate (%)')

    # Integration feedback
    wcs_response = fields.Text('WCS Response')
    error_message = fields.Text('Error Message')
    retry_count = fields.Integer('Retry Count', default=0)

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.wcs.task') or _('New')
        return super().create(vals)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for task in self:
            if task.start_time and task.end_time:
                duration = (task.end_time - task.start_time).total_seconds()
                task.duration_seconds = duration
            else:
                task.duration_seconds = 0.0

    def action_confirm_task(self):
        """Confirm the task and prepare for sending to WCS"""
        for task in self:
            if task.state == 'draft':
                task.write({
                    'state': 'confirmed',
                    'date_confirmed': fields.Datetime.now(),
                })

    def action_send_to_wcs(self):
        """Send the task to the WCS system"""
        for task in self:
            if task.state == 'confirmed':
                # Here we would send the task to the WCS system
                # For now, we'll just update the state
                task.write({
                    'state': 'sent',
                    'date_sent': fields.Datetime.now(),
                })

    def action_start_task(self):
        """Mark the task as started by the WCS system"""
        for task in self:
            if task.state == 'sent':
                task.write({
                    'state': 'in_progress',
                    'date_started': fields.Datetime.now(),
                    'start_time': fields.Datetime.now(),
                })

    def action_complete_task(self):
        """Mark the task as completed by the WCS system"""
        for task in self:
            if task.state == 'in_progress':
                task.write({
                    'state': 'completed',
                    'date_completed': fields.Datetime.now(),
                    'end_time': fields.Datetime.now(),
                })

    def action_cancel_task(self):
        """Cancel the WCS task"""
        for task in self:
            if task.state in ['draft', 'confirmed', 'sent']:
                task.write({'state': 'cancelled'})

    def action_retry_task(self):
        """Retry the failed task"""
        for task in self:
            if task.state == 'failed':
                task.write({
                    'state': 'confirmed',
                    'retry_count': task.retry_count + 1,
                    'error_message': False,
                })


class WmsWcsIntegrationLog(models.Model):
    """
    WCS Integration Log - Log of all interactions with WCS system
    """
    _name = 'wms.wcs.integration.log'
    _description = 'WMS WCS Integration Log'
    _order = 'timestamp desc'

    timestamp = fields.Datetime('Timestamp', default=fields.Datetime.now, required=True)
    wcs_system_id = fields.Many2one('wms.wcs.system', 'WCS System')
    operation = fields.Selection([
        ('connect', 'Connect'),
        ('disconnect', 'Disconnect'),
        ('send_task', 'Send Task'),
        ('receive_response', 'Receive Response'),
        ('heartbeat', 'Heartbeat'),
        ('sync', 'Synchronize'),
        ('error', 'Error'),
    ], string='Operation', required=True)

    status = fields.Selection([
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string='Status', required=True)

    message = fields.Text('Message')
    request_data = fields.Text('Request Data')
    response_data = fields.Text('Response Data')
    duration = fields.Float('Duration (seconds)')

    # Related to specific entities
    task_id = fields.Many2one('wms.wcs.task', 'Task')
    device_id = fields.Many2one('wms.wcs.device', 'Device')