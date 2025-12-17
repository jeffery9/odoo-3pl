from odoo import models, fields, api
from odoo.tools import float_compare
from dateutil.relativedelta import relativedelta
import datetime


class WmsInventoryAgeReport(models.TransientModel):
    _name = 'wms.inventory.age.report'
    _description = 'WMS Inventory Age Report'

    owner_id = fields.Many2one('wms.owner', 'Owner')
    location_id = fields.Many2one('stock.location', 'Location')
    product_category_id = fields.Many2one('product.category', 'Product Category')
    date_as_of = fields.Date('Date As Of', default=fields.Date.today, required=True)
    include_zero_stock = fields.Boolean('Include Zero Stock', default=False)
    aging_periods = fields.Selection([
        ('current', 'Current (0-30 days)'),
        ('30_60', '30-60 Days'),
        ('60_90', '60-90 Days'),
        ('90_180', '90-180 Days'),
        ('180_365', '180-365 Days'),
        ('over_365', 'Over 365 Days'),
    ], 'Aging Period', help='Filter by specific aging period')
    report_lines = fields.One2many('wms.inventory.age.report.line', 'report_id', 'Report Lines', readonly=True)

    def action_generate_report(self):
        """Generate the inventory age report"""
        self.ensure_one()
        # Unlink any existing report lines
        self.report_lines.unlink()

        # Build domain for quants
        domain = [('quantity', '>', 0)]
        if self.owner_id:
            domain.append(('owner_id', '=', self.owner_id.id))
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
        if self.product_category_id:
            domain.append(('product_id.categ_id', '=', self.product_category_id.id))

        quants = self.env['stock.quant'].search(domain)

        for quant in quants:
            # Calculate the age of the inventory
            age_days = self._calculate_inventory_age(quant)

            # Determine aging period
            aging_period = self._get_aging_period(age_days)

            # Only include if aging period matches filter or no filter set
            if not self.aging_periods or self.aging_periods == aging_period:
                self.env['wms.inventory.age.report.line'].create({
                    'report_id': self.id,
                    'product_id': quant.product_id.id,
                    'location_id': quant.location_id.id,
                    'lot_id': quant.lot_id.id,
                    'quantity': quant.quantity,
                    'uom_id': quant.product_id.uom_id.id,
                    'unit_cost': quant.product_id.standard_price,
                    'total_value': quant.quantity * quant.product_id.standard_price,
                    'age_days': age_days,
                    'aging_period': aging_period,
                    'owner_id': quant.owner_id.id if quant.owner_id else False,
                    'expiry_date': quant.lot_id.expiry_date if quant.lot_id else False,
                })

        # Return action to display the report
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.inventory.age.report',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_id': self.id},
        }

    def _calculate_inventory_age(self, quant):
        """Calculate the age of inventory in days"""
        # For this example, we'll use the creation date of the quant
        # In a real implementation, this would track when inventory was received
        if quant.create_date.date() <= self.date_as_of:
            age = self.date_as_of - quant.create_date.date()
            return age.days
        else:
            # Quant was created after the report date, shouldn't happen normally
            return 0

    def _get_aging_period(self, age_days):
        """Determine the aging period based on age in days"""
        if age_days <= 30:
            return 'current'
        elif age_days <= 60:
            return '30_60'
        elif age_days <= 90:
            return '60_90'
        elif age_days <= 180:
            return '90_180'
        elif age_days <= 365:
            return '180_365'
        else:
            return 'over_365'


class WmsInventoryAgeReportLine(models.TransientModel):
    _name = 'wms.inventory.age.report.line'
    _description = 'WMS Inventory Age Report Line'

    report_id = fields.Many2one('wms.inventory.age.report', 'Report', ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product')
    location_id = fields.Many2one('stock.location', 'Location')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    quantity = fields.Float('Quantity')
    uom_id = fields.Many2one('uom.uom', 'UOM')
    unit_cost = fields.Float('Unit Cost')
    total_value = fields.Float('Total Value', compute='_compute_total_value', store=True)
    age_days = fields.Integer('Age (Days)')
    aging_period = fields.Selection([
        ('current', 'Current (0-30 days)'),
        ('30_60', '30-60 Days'),
        ('60_90', '60-90 Days'),
        ('90_180', '90-180 Days'),
        ('180_365', '180-365 Days'),
        ('over_365', 'Over 365 Days'),
    ], 'Aging Period')
    owner_id = fields.Many2one('wms.owner', 'Owner')
    expiry_date = fields.Date('Expiry Date')

    @api.depends('quantity', 'unit_cost')
    def _compute_total_value(self):
        for line in self:
            line.total_value = line.quantity * line.unit_cost



class WmsInventoryAgeAlert(models.Model):
    _name = 'wms.inventory.age.alert'
    _description = 'WMS Inventory Age Alert'
    _order = 'age_days desc'

    name = fields.Char('Alert Reference', required=True, copy=False, readonly=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial')
    owner_id = fields.Many2one('wms.owner', 'Owner')
    quantity = fields.Float('Quantity')
    age_days = fields.Integer('Age (Days)', required=True)
    alert_type = fields.Selection([
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ], 'Alert Type', required=True)
    alert_date = fields.Datetime('Alert Date', default=fields.Datetime.now)
    status = fields.Selection([
        ('open', 'Open'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ], 'Status', default='open', required=True)
    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.inventory.age.alert') or '/'
        return super().create(vals)

    def action_acknowledge(self):
        """Acknowledge the alert"""
        self.write({'status': 'acknowledged'})

    def action_resolve(self):
        """Resolve the alert"""
        self.write({'status': 'resolved'})


class WmsInventoryAgeConfig(models.Model):
    _name = 'wms.inventory.age.config'
    _description = 'WMS Inventory Age Configuration'

    name = fields.Char('Configuration Name', required=True, default='Default Configuration')
    owner_id = fields.Many2one('wms.owner', 'Owner')
    warning_age_days = fields.Integer('Warning Age (Days)', default=180, required=True,
                                     help='Inventory older than this will trigger a warning')
    critical_age_days = fields.Integer('Critical Age (Days)', default=365, required=True,
                                      help='Inventory older than this will trigger a critical alert')
    auto_create_alerts = fields.Boolean('Auto Create Alerts', default=True,
                                       help='Automatically create alerts for aged inventory')
    alert_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], 'Alert Frequency', default='weekly', required=True)

    _sql_constraints = [
        ('owner_unique', 'UNIQUE(owner_id)', 'Only one configuration per owner is allowed.'),
    ]