from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


class WmsWaveRule(models.Model):
    """
    Auto Wave Rule Configuration (extension of base wave rule)
    Configure rules and conditions for automatic wave generation
    """
    _inherit = 'wms.wave.rule'  # Inherit from the base wave rule model

    # Time-based conditions (extending the base model)
    time_trigger_type = fields.Selection([
        ('fixed_time', 'Fixed Time'),
        ('interval', 'Time Interval'),
        ('rolling_window', 'Rolling Window'),
    ], string='Time Trigger Method', default='fixed_time')
    fixed_time = fields.Float('Fixed Time (hours)')  # 24-hour format, e.g., 9.5 means 9:30
    time_interval = fields.Integer('Time Interval (minutes)')
    rolling_window_minutes = fields.Integer('Rolling Window (minutes)')

    # Quantity-based conditions (extending the base model)
    min_orders = fields.Integer('Minimum Orders', default=1)
    max_orders = fields.Integer('Maximum Orders')
    min_volume = fields.Float('Minimum Volume (m³)')
    max_volume = fields.Float('Maximum Volume (m³)')
    min_weight = fields.Float('Minimum Weight (kg)')
    max_weight = fields.Float('Maximum Weight (kg)')

    # Order attribute restrictions
    warehouse_ids = fields.Many2many('stock.warehouse', string='Applicable Warehouses')
    picking_type_ids = fields.Many2many('stock.picking.type', string='Applicable Operation Types')
    priority_filter = fields.Selection([
        ('high_only', 'High Priority Only'),
        ('normal_only', 'Normal Priority Only'),
        ('low_only', 'Low Priority Only'),
        ('mixed', 'Mixed Priority'),
    ], string='Priority Filter', default='mixed')
    carrier_filter_ids = fields.Many2many('delivery.carrier', string='Carrier Filter')
    delivery_date_filter = fields.Boolean('Filter by Delivery Date')

    # Wave rules
    wave_strategy = fields.Selection([
        ('fifo', 'First In First Out'),
        ('lifo', 'Last In First Out'),
        ('priority', 'Priority First'),
        ('delivery_date', 'Delivery Date First'),
        ('volume_weight', 'Volume Weight Optimization'),
        ('location_proximity', 'Location Proximity Optimization'),
    ], string='Wave Strategy', default='priority')

    # Other configurations
    auto_confirm = fields.Boolean('Auto Confirm after Generation', default=True)
    auto_assign = fields.Boolean('Auto Assign to Operator')
    max_wave_size = fields.Integer('Maximum Wave Size', help='Maximum number of pickings allowed in a single wave')
    enable_batching = fields.Boolean('Enable Grouping Optimization')
    batching_strategy = fields.Selection([
        ('single_zone', 'Single Zone'),
        ('multi_zone', 'Multi Zone'),
        ('wave_splitting', 'Wave Splitting'),
    ], string='Grouping Strategy', default='single_zone')

    # Status and execution
    last_execution = fields.Datetime('Last Execution Time')
    execution_count = fields.Integer('Execution Count', default=0)
    notes = fields.Text('Notes')

    @api.constrains('min_orders', 'max_orders')
    def _check_order_limits(self):
        for rule in self:
            if rule.min_orders > rule.max_orders > 0:
                raise ValidationError(_('Minimum orders cannot be greater than maximum orders.'))

    def action_execute_rule(self):
        """Manually execute rule to create wave"""
        for rule in self:
            wave_picking_ids = self._get_pickings_for_wave(rule)
            if wave_picking_ids:
                if len(wave_picking_ids) >= rule.min_orders:
                    self._create_wave_from_pickings(rule, wave_picking_ids)

    def _get_pickings_for_wave(self, rule):
        """Get suitable pickings based on the rule"""
        domain = [
            ('state', 'in', ['assigned', 'waiting']),  # assigned or waiting state
            ('picking_type_id.code', '=', 'outgoing'),  # outgoing operations
        ]

        # Filter by warehouse
        if rule.warehouse_ids:
            domain.append(('picking_type_id.warehouse_id', 'in', rule.warehouse_ids.ids))

        # Filter by operation type
        if rule.picking_type_ids:
            domain.append(('picking_type_id', 'in', rule.picking_type_ids.ids))

        # Filter by priority
        if rule.priority_filter == 'high_only':
            domain.append(('priority', '=', '1'))
        elif rule.priority_filter == 'normal_only':
            domain.append(('priority', '=', '0'))
        elif rule.priority_filter == 'low_only':
            domain.append(('priority', '=', '0'))

        # Filter by carrier
        if rule.carrier_filter_ids:
            domain.append(('carrier_id', 'in', rule.carrier_filter_ids.ids))

        # Get pickings
        pickings = self.env['stock.picking'].search(domain)

        # Further filter by volume and weight limits
        filtered_pickings = self._filter_by_volume_weight(pickings, rule)

        # Sort by strategy
        sorted_pickings = self._sort_pickings_by_strategy(filtered_pickings, rule)

        # Limit quantity
        if rule.max_orders and len(sorted_pickings) > rule.max_orders:
            sorted_pickings = sorted_pickings[:rule.max_orders]

        return sorted_pickings

    def _filter_by_volume_weight(self, pickings, rule):
        """Filter pickings by volume and weight limits"""
        filtered = []
        current_volume = 0.0
        current_weight = 0.0

        for picking in pickings:
            # Calculate volume and weight of the current picking
            volume = sum(move.product_id.volume * move.product_uom_qty for move in picking.move_ids)
            weight = sum(move.product_id.weight * move.product_uom_qty for move in picking.move_ids)

            # Check if volume limit is exceeded
            if rule.max_volume and current_volume + volume > rule.max_volume:
                continue

            # Check if weight limit is exceeded
            if rule.max_weight and current_weight + weight > rule.max_weight:
                continue

            # Check if minimum limits are met (if there are minimum limits)
            if (rule.min_volume and volume < rule.min_volume) or \
               (rule.min_weight and weight < rule.min_weight):
                continue

            filtered.append(picking)
            current_volume += volume
            current_weight += weight

            # Stop if maximum order count limit is reached
            if rule.max_orders and len(filtered) >= rule.max_orders:
                break

        return filtered

    def _sort_pickings_by_strategy(self, pickings, rule):
        """Sort pickings by wave strategy"""
        if rule.wave_strategy == 'fifo':
            return sorted(pickings, key=lambda p: p.create_date)
        elif rule.wave_strategy == 'lifo':
            return sorted(pickings, key=lambda p: p.create_date, reverse=True)
        elif rule.wave_strategy == 'priority':
            priority_map = {'1': 3, '0': 2, '2': 4, '3': 5}  # Emergency priority is highest
            return sorted(pickings, key=lambda p: priority_map.get(p.priority, 0), reverse=True)
        elif rule.wave_strategy == 'delivery_date':
            return sorted(pickings, key=lambda p: (p.scheduled_date or fields.Datetime.now()))
        elif rule.wave_strategy == 'volume_weight':
            return sorted(pickings, key=lambda p: (p.volume or 0) + (p.weight or 0), reverse=True)
        elif rule.wave_strategy == 'location_proximity':
            # This requires a more complex algorithm to calculate location distance
            # Simplified implementation: sort by source location of first move
            return sorted(pickings, key=lambda p: p.move_ids[:1].location_id.name or '')
        else:
            return pickings

    def _create_wave_from_pickings(self, rule, pickings):
        """Create wave from pickings"""
        wave_name = f"Auto-Wave-{fields.Date.today()}-{rule.code}"

        # Create picking batch
        picking_batch = self.env['stock.picking.batch'].create({
            'name': wave_name,
            'picking_ids': [(6, 0, [p.id for p in pickings])],
        })

        # Auto confirm if set after generation
        if rule.auto_confirm:
            picking_batch.action_confirm()

        # Update rule execution statistics
        rule.write({
            'last_execution': fields.Datetime.now(),
            'execution_count': rule.execution_count + 1,
        })

        return picking_batch


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # 添加与自动波次相关的字段
    auto_wave_candidate = fields.Boolean('自动波次候选', default=False,
                                        help='标记此拣货单是否适合自动波次生成')
    wave_suitability_score = fields.Float('波次适配度评分', readonly=True,
                                         help='此拣货单被选入波次的评分')
    auto_wave_rule_id = fields.Many2one('wms.wave.rule', '自动波次规则',
                                       help='用于生成此拣货单的规则')

    # Fields related to auto wave
    auto_wave_candidate_en = fields.Boolean('Auto Wave Candidate', default=False,
                                        help='Mark if this picking is suitable for auto wave generation')
    wave_suitability_score_en = fields.Float('Wave Suitability Score', readonly=True,
                                         help='Score for this picking being selected into a wave')
    auto_wave_rule_id_en = fields.Many2one('wms.wave.rule', 'Auto Wave Rule',
                                       help='Rule used to generate this picking batch')