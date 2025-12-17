from odoo import models, fields, api
from datetime import datetime, timedelta


class WmsWaveRule(models.Model):
    _name = 'wms.wave.rule'
    _description = 'WMS Wave Generation Rule'

    name = fields.Char('Rule Name', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    trigger_type = fields.Selection([
        ('time', 'Time Based'),
        ('order_count', 'Order Count'),
        ('order_volume', 'Order Volume'),
        ('order_weight', 'Order Weight'),
        ('order_value', 'Order Value'),
        ('priority', 'Priority Based')
    ], 'Trigger Type', required=True)
    trigger_value = fields.Float('Trigger Value')
    time_period = fields.Selection([
        ('15min', '15 minutes'),
        ('30min', '30 minutes'),
        ('1hour', '1 hour'),
        ('2hours', '2 hours'),
        ('4hours', '4 hours'),
        ('8hours', '8 hours'),
        ('12hours', '12 hours'),
        ('day', 'Day'),
        ('week', 'Week')
    ], 'Time Period', default='day')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], 'Priority')
    max_orders_per_wave = fields.Integer('Max Orders per Wave', default=50)
    max_volume_per_wave = fields.Float('Max Volume per Wave (CBM)')
    max_weight_per_wave = fields.Float('Max Weight per Wave (KG)')
    max_pickers = fields.Integer('Max Pickers per Wave', default=5)
    active = fields.Boolean('Active', default=True)

    # Fields for auto wave functionality (base fields that may be extended)
    sequence = fields.Integer('Sequence', default=10)
    code = fields.Char('Rule Code')
    wave_strategy = fields.Selection([
        ('fifo', 'First In First Out'),
        ('lifo', 'Last In First Out'),
        ('priority', 'Priority First'),
        ('delivery_date', 'Delivery Date First'),
        ('volume_weight', 'Volume Weight Optimization'),
        ('location_proximity', 'Location Proximity Optimization'),
    ], string='Wave Strategy')
    last_execution = fields.Datetime('Last Execution Time')
    execution_count = fields.Integer('Execution Count', default=0)
    notes = fields.Text('Notes')

    @api.model
    def _cron_generate_waves(self):
        """Scheduled action to automatically generate waves based on rules"""
        rules = self.search([('active', '=', True)])
        for rule in rules:
            rule._generate_wave()

    def _generate_wave(self):
        """Generate wave based on rule configuration"""
        # Get pickings that match the rule criteria
        domain = [
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id),
            ('state', '=', 'assigned'),
            ('batch_id', '=', False),  # Not already in a batch
        ]

        # Add priority filter if specified
        if self.priority:
            domain.append(('priority', '=', self.priority))

        # Get pickings based on trigger type
        if self.trigger_type == 'time':
            # Filter by time period
            if self.time_period == '15min':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(minutes=15)))
            elif self.time_period == '30min':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(minutes=30)))
            elif self.time_period == '1hour':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(hours=1)))
            elif self.time_period == '2hours':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(hours=2)))
            elif self.time_period == '4hours':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(hours=4)))
            elif self.time_period == '8hours':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(hours=8)))
            elif self.time_period == '12hours':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(hours=12)))
            elif self.time_period == 'day':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(days=1)))
            elif self.time_period == 'week':
                domain.append(('scheduled_date', '<=', fields.Datetime.now() + timedelta(weeks=1)))

        pickings = self.env['stock.picking'].search(domain, limit=self.max_orders_per_wave)

        if pickings:
            # Create batch with wave characteristics
            batch = self.env['stock.picking.batch'].create({
                'name': f'WAVE-{fields.Date.today()}-{self.id}',
                'picking_ids': [(6, 0, pickings.ids)],
                'batch_type': 'wave',
                'priority': self.priority,
            })

            return batch
        return False

    def generate_wave_manually(self):
        """Generate wave manually from action button"""
        self.ensure_one()
        return self._generate_wave()

    def action_execute_rule(self):
        """Manually execute rule to create wave - stub method for base model"""
        # This method is implemented in the auto wave extension
        return True

    def toggle_active(self):
        """Toggle the active state of the rule"""
        self.active = not self.active
        return True