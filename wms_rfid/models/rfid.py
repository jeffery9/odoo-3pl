from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class WmsRfidTag(models.Model):
    """
    RFID Tag - RFID tags used in the warehouse
    """
    _name = 'wms.rfid.tag'
    _description = 'WMS RFID Tag'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Tag ID', required=True, copy=False)
    description = fields.Text('Description')

    # Tag information
    tag_type = fields.Selection([
        ('product', 'Product Tag'),
        ('location', 'Location Tag'),
        ('pallet', 'Pallet Tag'),
        ('container', 'Container Tag'),
        ('employee', 'Employee Tag'),
        ('equipment', 'Equipment Tag'),
    ], string='Tag Type', required=True)

    # Tag status
    active = fields.Boolean('Active', default=True)
    status = fields.Selection([
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('retired', 'Retired'),
    ], string='Status', default='available')

    # Associated information
    product_id = fields.Many2one('product.product', 'Product', help='Product associated with this tag')
    location_id = fields.Many2one('stock.location', 'Location', help='Location associated with this tag')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', help='Lot or serial number associated with this tag')
    employee_id = fields.Many2one('hr.employee', 'Employee', help='Employee associated with this tag')
    equipment_id = fields.Many2one('maintenance.equipment', 'Equipment', help='Equipment associated with this tag')

    # Tag properties
    capacity = fields.Float('Capacity (KG)', help='Maximum capacity for container/pallet tags')
    current_load = fields.Float('Current Load (KG)', help='Current load for container/pallet tags')
    utilization_rate = fields.Float('Utilization Rate (%)', compute='_compute_utilization_rate')

    # RFID specific data
    rfid_uid = fields.Char('RFID UID', help='Unique identifier from RFID reader')
    rfid_data = fields.Text('RFID Data', help='Raw data stored on RFID tag')
    security_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Security Level', default='medium')

    # Lifecycle
    date_activated = fields.Datetime('Date Activated')
    date_deactivated = fields.Datetime('Date Deactivated')
    last_scanned = fields.Datetime('Last Scanned')

    # Traceability
    owner_id = fields.Many2one('wms.owner', 'Owner', help='Owner of the tagged item')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help='Warehouse where tag is used')

    notes = fields.Text('Notes')

    @api.depends('current_load', 'capacity')
    def _compute_utilization_rate(self):
        for tag in self:
            if tag.capacity and tag.current_load:
                tag.utilization_rate = min((tag.current_load / tag.capacity) * 100, 100.0)
            else:
                tag.utilization_rate = 0.0

    @api.onchange('tag_type')
    def _onchange_tag_type(self):
        # Clear associated fields when tag type changes
        if self.tag_type != 'product':
            self.product_id = False
        if self.tag_type != 'location':
            self.location_id = False
        if self.tag_type != 'employee':
            self.employee_id = False
        if self.tag_type != 'equipment':
            self.equipment_id = False

    def action_activate_tag(self):
        """Activate the RFID tag"""
        for tag in self:
            tag.write({
                'active': True,
                'status': 'in_use',
                'date_activated': fields.Datetime.now(),
            })

    def action_deactivate_tag(self):
        """Deactivate the RFID tag"""
        for tag in self:
            tag.write({
                'active': False,
                'status': 'retired',
                'date_deactivated': fields.Datetime.now(),
            })

    def action_report_lost(self):
        """Report the RFID tag as lost"""
        for tag in self:
            tag.write({
                'status': 'lost',
            })

    def action_report_damaged(self):
        """Report the RFID tag as damaged"""
        for tag in self:
            tag.write({
                'status': 'damaged',
            })


class WmsRfidReader(models.Model):
    """
    RFID Reader - RFID readers installed in the warehouse
    """
    _name = 'wms.rfid.reader'
    _description = 'WMS RFID Reader'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Reader Name', required=True)
    code = fields.Char('Reader Code', required=True, copy=False)
    description = fields.Text('Description')

    # Reader information
    active = fields.Boolean('Active', default=True)
    reader_type = fields.Selection([
        ('fixed', 'Fixed Reader'),
        ('mobile', 'Mobile Reader'),
        ('handheld', 'Handheld Reader'),
        ('portal', 'Portal Reader'),
        ('embedded', 'Embedded Reader'),
    ], string='Reader Type', required=True)

    # Location and configuration
    location_id = fields.Many2one('stock.location', 'Installation Location')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    ip_address = fields.Char('IP Address')
    port = fields.Integer('Port Number')
    protocol = fields.Selection([
        ('tcp', 'TCP/IP'),
        ('udp', 'UDP'),
        ('serial', 'Serial'),
        ('usb', 'USB'),
    ], string='Communication Protocol', default='tcp')

    # Technical specifications
    antenna_count = fields.Integer('Number of Antennas', default=1)
    read_range = fields.Float('Read Range (Meters)')
    power_level = fields.Float('Power Level (dBm)')
    last_connection = fields.Datetime('Last Connection')
    is_connected = fields.Boolean('Connected', readonly=True)

    # Status
    status = fields.Selection([
        ('offline', 'Offline'),
        ('online', 'Online'),
        ('maintenance', 'Maintenance'),
        ('error', 'Error'),
    ], string='Status', default='offline', readonly=True)

    # RFID technology
    frequency = fields.Float('Frequency (MHz)')
    supported_standards = fields.Char('Supported Standards', help='e.g., ISO 18000-6C, EPC Class 1 Gen 2')

    # Integration
    integration_enabled = fields.Boolean('Integration Enabled', default=True)
    auto_scan_enabled = fields.Boolean('Auto Scan Enabled', default=False)
    scan_interval = fields.Integer('Auto Scan Interval (seconds)', default=30)

    # Traceability
    installation_date = fields.Date('Installation Date')
    last_maintenance = fields.Date('Last Maintenance Date')
    next_maintenance = fields.Date('Next Maintenance Date')

    notes = fields.Text('Notes')

    def action_connect_reader(self):
        """Connect to the RFID reader"""
        for reader in self:
            # This would implement the actual connection to the RFID reader
            # For now, we'll just update the status
            reader.write({
                'status': 'online',
                'is_connected': True,
                'last_connection': fields.Datetime.now(),
            })

    def action_disconnect_reader(self):
        """Disconnect from the RFID reader"""
        for reader in self:
            reader.write({
                'status': 'offline',
                'is_connected': False,
            })

    def action_scan_tags(self):
        """Initiate a scan for RFID tags"""
        for reader in self:
            # This would trigger the RFID reader to scan for tags
            # In a real implementation, this would call the RFID reader API
            _logger.info(f"Scanning for tags with reader: {reader.name}")


class WmsRfidTransaction(models.Model):
    """
    RFID Transaction - Log of RFID scans and transactions
    """
    _name = 'wms.rfid.transaction'
    _description = 'WMS RFID Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'timestamp desc'

    name = fields.Char('Transaction ID', required=True, copy=False,
                       default=lambda self: _('New'))
    transaction_type = fields.Selection([
        ('read', 'Read'),
        ('write', 'Write'),
        ('location_change', 'Location Change'),
        ('inventory_check', 'Inventory Check'),
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('move', 'Move'),
        ('count', 'Count'),
    ], string='Transaction Type', required=True)

    # RFID information
    tag_id = fields.Many2one('wms.rfid.tag', 'RFID Tag', required=True)
    reader_id = fields.Many2one('wms.rfid.reader', 'RFID Reader', required=True)
    rfid_uid = fields.Char('RFID UID', help='Unique identifier from RFID scan')
    timestamp = fields.Datetime('Timestamp', default=fields.Datetime.now, required=True)

    # Transaction details
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    destination_location_id = fields.Many2one('stock.location', 'Destination Location')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    quantity = fields.Float('Quantity')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')

    # Related documents
    source_document = fields.Reference([
        ('stock.picking', 'Stock Picking'),
        ('stock.move', 'Stock Move'),
        ('stock.quant', 'Stock Quant'),
        ('stock.inventory', 'Inventory'),
        ('sale.order', 'Sale Order'),
        ('purchase.order', 'Purchase Order'),
    ], string='Source Document')

    # Operator and equipment
    operator_id = fields.Many2one('hr.employee', 'Operator')
    equipment_id = fields.Many2one('maintenance.equipment', 'Equipment Used')

    # Status and verification
    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('error', 'Error'),
    ], string='Status', default='completed')

    verification_code = fields.Char('Verification Code', help='Code to verify the transaction')
    is_verified = fields.Boolean('Verified', default=False)

    # Additional data
    raw_data = fields.Text('Raw RFID Data')
    processed_data = fields.Text('Processed Data')
    error_message = fields.Text('Error Message')

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.rfid.transaction') or _('New')
        return super().create(vals)

    def action_verify_transaction(self):
        """Verify the RFID transaction"""
        for transaction in self:
            transaction.write({
                'is_verified': True,
                'status': 'verified',
            })

    def action_mark_error(self, error_msg):
        """Mark the transaction as having an error"""
        for transaction in self:
            transaction.write({
                'status': 'error',
                'error_message': error_msg,
            })


class WmsRfidInventory(models.Model):
    """
    RFID Inventory - Inventory counts performed using RFID
    """
    _name = 'wms.rfid.inventory'
    _description = 'WMS RFID Inventory'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char('Inventory Reference', required=True, copy=False,
                       default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True)

    # Inventory details
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now)
    date_end = fields.Datetime('End Date')
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    reader_ids = fields.Many2many('wms.rfid.reader', string='RFID Readers Used')

    # Operator and equipment
    operator_id = fields.Many2one('hr.employee', 'Operator')
    equipment_used = fields.Many2many('maintenance.equipment', string='Equipment Used')

    # Configuration
    include_sublocations = fields.Boolean('Include Sub-locations', default=True)
    count_zero = fields.Boolean('Count Zero Quantity Items', default=True)
    exclude_products = fields.Boolean('Exclude Specific Products', default=False)
    excluded_product_ids = fields.Many2many('product.product', string='Excluded Products')

    # Results
    items_counted = fields.Integer('Items Counted', readonly=True)
    discrepancies_found = fields.Integer('Discrepancies Found', readonly=True)
    accuracy_rate = fields.Float('Accuracy Rate (%)', readonly=True)
    variance_value = fields.Float('Variance Value', readonly=True, digits='Product Price')

    # Traceability
    owner_id = fields.Many2one('wms.owner', 'Owner')
    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.rfid.inventory') or _('New')
        return super().create(vals)

    def action_start_inventory(self):
        """Start the RFID inventory"""
        for inventory in self:
            inventory.write({
                'state': 'in_progress',
                'date_start': fields.Datetime.now(),
            })

    def action_complete_inventory(self):
        """Complete the RFID inventory"""
        for inventory in self:
            inventory.write({
                'state': 'completed',
                'date_end': fields.Datetime.now(),
            })
            # Calculate inventory results
            inventory._calculate_results()

    def action_cancel_inventory(self):
        """Cancel the RFID inventory"""
        for inventory in self:
            inventory.write({'state': 'cancelled'})

    def _calculate_results(self):
        """Calculate inventory results"""
        for inventory in self:
            # This would calculate actual results based on RFID scanned data
            # For now, we'll set dummy values
            inventory.items_counted = 0  # Would be calculated from RFID transactions
            inventory.discrepancies_found = 0  # Would be calculated from comparison
            inventory.accuracy_rate = 100.0  # Would be calculated from accuracy

    def action_generate_report(self):
        """Generate inventory report"""
        for inventory in self:
            # Return an action to view the inventory results
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'wms.rfid.transaction',
                'view_mode': 'list,form',
                'domain': [('tag_id.location_id', '=', inventory.location_id.id)],
                'context': {
                    'search_default_date_from': inventory.date_start,
                    'search_default_date_to': inventory.date_end or fields.Datetime.now(),
                },
                'target': 'current',
                'name': f'RFID Inventory Results: {inventory.name}'
            }
            return action