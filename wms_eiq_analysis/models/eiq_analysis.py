from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


class WmsEiqAnalysis(models.Model):
    """
    EIQ Analysis - Entry-Item-Quantity Analysis
    Analyze statistical relationships between entry, item, and quantity for warehouse planning and optimization
    """
    _name = 'wms.eiq.analysis'
    _description = 'WMS EIQ Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'analysis_date desc'

    name = fields.Char('Analysis Name', required=True, copy=False)
    analysis_date = fields.Date('Analysis Date', required=True, default=fields.Date.context_today)
    period_start = fields.Date('Analysis Period Start', required=True)
    period_end = fields.Date('Analysis Period End', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')

    # Analysis dimensions
    analysis_type = fields.Selection([
        ('inbound', 'Inbound EIQ Analysis'),
        ('outbound', 'Outbound EIQ Analysis'),
        ('internal', 'Internal Operation EIQ Analysis'),
        ('combined', 'Combined EIQ Analysis'),
    ], string='Analysis Type', required=True, default='outbound')

    # Statistical information
    total_orders = fields.Integer('Total Orders', readonly=True)
    total_items = fields.Integer('Total Items', readonly=True)
    total_quantity = fields.Float('Total Quantity', readonly=True)

    # EIQ Core Indicators
    entries = fields.Integer('Total Entries (Orders)', readonly=True)  # E - Entry (Orders)
    items = fields.Integer('Total Items (SKUs)', readonly=True)   # I - Item (SKUs)
    quantity = fields.Float('Total Quantity', readonly=True)   # Q - Quantity
    eoq = fields.Float('Average Items per Order (Items/Order)', readonly=True, digits=(10, 2))  # I/E
    qoe = fields.Float('Average Quantity per Order (Quantity/Order)', readonly=True, digits=(10, 2))  # Q/E
    qoi = fields.Float('Average Quantity per Item (Quantity/Item)', readonly=True, digits=(10, 2))  # Q/I

    # Order Analysis
    max_items_per_order = fields.Integer('Max Items per Order', readonly=True)
    min_items_per_order = fields.Integer('Min Items per Order', readonly=True)
    avg_items_per_order = fields.Float('Average Items per Order', readonly=True, digits=(10, 2))

    # Item Analysis
    max_orders_per_item = fields.Integer('Max Orders per Item', readonly=True)
    min_orders_per_item = fields.Integer('Min Orders per Item', readonly=True)
    avg_orders_per_item = fields.Float('Average Orders per Item', readonly=True, digits=(10, 2))

    # Detailed Statistics (JSON Storage)
    detailed_stats = fields.Text('Detailed Statistics', readonly=True, help='Detailed statistical information in JSON format')

    # Analysis Results
    analysis_results = fields.Html('Analysis Results', readonly=True)
    recommendations = fields.Html('Optimization Recommendations', readonly=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('validated', 'Validated'),
    ], string='Status', default='draft', tracking=True)

    # Calculation Parameters
    calculation_method = fields.Selection([
        ('simple', 'Simple Statistics'),
        ('weighted', 'Weighted Statistics'),
        ('advanced', 'Advanced Analysis'),
    ], string='Calculation Method', default='simple')

    notes = fields.Text('Notes')

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for analysis in self:
            if analysis.period_start and analysis.period_end and analysis.period_start > analysis.period_end:
                raise ValidationError(_('Analysis period start date cannot be later than end date.'))

    def action_generate_analysis(self):
        """Generate EIQ analysis"""
        for analysis in self:
            # Execute EIQ analysis calculation
            stats = analysis._calculate_eiq_stats()

            # Update analysis results
            analysis.write({
                'total_orders': stats.get('total_orders', 0),
                'total_items': stats.get('total_items', 0),
                'total_quantity': stats.get('total_quantity', 0.0),

                'entries': stats.get('entries', 0),  # E - Order count
                'items': stats.get('items', 0),      # I - Item count
                'quantity': stats.get('quantity', 0.0),  # Q - Quantity

                'eoq': stats.get('eoq', 0.0),  # I/E - Average items per order
                'qoe': stats.get('qoe', 0.0),  # Q/E - Average quantity per order
                'qoi': stats.get('qoi', 0.0),  # Q/I - Average quantity per item

                'max_items_per_order': stats.get('max_items_per_order', 0),
                'min_items_per_order': stats.get('min_items_per_order', 0),
                'avg_items_per_order': stats.get('avg_items_per_order', 0.0),

                'max_orders_per_item': stats.get('max_orders_per_item', 0),
                'min_orders_per_item': stats.get('min_orders_per_item', 0),
                'avg_orders_per_item': stats.get('avg_orders_per_item', 0.0),

                'detailed_stats': json.dumps(stats.get('detailed_stats', {})),
                'analysis_results': analysis._format_analysis_results(stats),
                'recommendations': analysis._generate_recommendations(stats),
                'state': 'generated'
            })

    def _calculate_eiq_stats(self):
        """Calculate EIQ statistics"""
        self.ensure_one()

        # Get relevant data based on analysis type
        operations = self._get_operations_for_analysis()

        if not operations:
            return {
                'total_orders': 0,
                'total_items': 0,
                'total_quantity': 0.0,
                'entries': 0,
                'items': 0,
                'quantity': 0.0,
                'eoq': 0.0,
                'qoe': 0.0,
                'qoi': 0.0,
                'detailed_stats': {}
            }

        # Count orders, items, quantities
        orders = {}
        items = {}
        total_qty = 0.0

        for operation in operations:
            order_id = operation.id
            orders[order_id] = {
                'items': set(),
                'quantity': 0.0
            }

            # Get product lines in operation
            if hasattr(operation, 'move_line_ids'):
                moves = operation.move_line_ids
            elif hasattr(operation, 'move_ids'):
                moves = operation.move_ids
            else:
                continue

            for move in moves:
                product_id = move.product_id.id
                qty = move.qty_done or move.product_uom_qty

                # Count order-level information
                orders[order_id]['items'].add(product_id)
                orders[order_id]['quantity'] += qty
                total_qty += qty

                # Count item-level information
                if product_id not in items:
                    items[product_id] = {
                        'orders': set(),
                        'quantity': 0.0,
                        'total_qty': 0.0
                    }
                items[product_id]['orders'].add(order_id)
                items[product_id]['quantity'] += qty
                items[product_id]['total_qty'] += qty

        # Calculate statistics
        total_orders = len(orders)
        total_items = len(items)
        total_quantity = total_qty

        # EIQ Core Indicators
        entries = total_orders  # E - Order count
        e_items = total_items   # I - Item count
        e_quantity = total_quantity  # Q - Total Quantity

        # Calculate ratios
        eoq = (e_items / entries) if entries > 0 else 0.0  # I/E - Average items per order
        qoe = (e_quantity / entries) if entries > 0 else 0.0  # Q/E - Average quantity per order
        qoi = (e_quantity / e_items) if e_items > 0 else 0.0  # Q/I - Average quantity per item

        # Order Analysis
        items_per_order = [len(order['items']) for order in orders.values()] if orders else [0]
        max_items_per_order = max(items_per_order) if items_per_order else 0
        min_items_per_order = min(items_per_order) if items_per_order else 0
        avg_items_per_order = sum(items_per_order) / len(items_per_order) if items_per_order else 0.0

        # Item Analysis
        orders_per_item = [len(item['orders']) for item in items.values()] if items else [0]
        max_orders_per_item = max(orders_per_item) if orders_per_item else 0
        min_orders_per_item = min(orders_per_item) if orders_per_item else 0
        avg_orders_per_item = sum(orders_per_item) / len(orders_per_item) if orders_per_item else 0.0

        # Detailed Statistics
        detailed_stats = {
            'orders': {
                'count': total_orders,
                'items_distribution': self._calculate_distribution(items_per_order),
                'quantity_distribution': [order['quantity'] for order in orders.values()]
            },
            'items': {
                'count': total_items,
                'orders_distribution': self._calculate_distribution(orders_per_item),
                'quantity_distribution': [item['total_qty'] for item in items.values()]
            },
            'items_per_order_analysis': self._analyze_items_per_order(orders),
            'orders_per_item_analysis': self._analyze_orders_per_item(items),
            'abc_analysis': self._calculate_abc_analysis(items)
        }

        return {
            'total_orders': total_orders,
            'total_items': total_items,
            'total_quantity': total_quantity,
            'entries': entries,
            'items': e_items,
            'quantity': e_quantity,
            'eoq': eoq,
            'qoe': qoe,
            'qoi': qoi,
            'max_items_per_order': max_items_per_order,
            'min_items_per_order': min_items_per_order,
            'avg_items_per_order': avg_items_per_order,
            'max_orders_per_item': max_orders_per_item,
            'min_orders_per_item': min_orders_per_item,
            'avg_orders_per_item': avg_orders_per_item,
            'detailed_stats': detailed_stats
        }

    def _get_operations_for_analysis(self):
        """根据分析类型获取相关的操作数据"""
        domain = [
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('state', '=', 'done'),  # 只分析已完成的操作
        ]

        if self.owner_id:
            if 'owner_id' in self.env['stock.picking']._fields:
                domain.append(('owner_id', '=', self.owner_id.id))

        if self.warehouse_id:
            domain.append(('picking_type_id.warehouse_id', '=', self.warehouse_id.id))

        operations = []

        if self.analysis_type in ['inbound', 'combined']:
            # 入库操作 - receipt pickings
            inbound_domain = domain + [('picking_type_id.code', '=', 'incoming')]
            inbound_ops = self.env['stock.picking'].search(inbound_domain)
            operations += inbound_ops.ids

        if self.analysis_type in ['outbound', 'combined']:
            # 出库操作 - delivery pickings
            outbound_domain = domain + [('picking_type_id.code', '=', 'outgoing')]
            outbound_ops = self.env['stock.picking'].search(outbound_domain)
            operations += outbound_ops.ids

        if self.analysis_type in ['internal', 'combined']:
            # 库内操作 - internal transfers
            internal_domain = domain + [('picking_type_id.code', '=', 'internal')]
            internal_ops = self.env['stock.picking'].search(internal_domain)
            operations += internal_ops.ids

        # 去除重复ID并获取记录
        unique_ops = list(set(operations))
        return self.env['stock.picking'].browse(unique_ops)

    def _calculate_distribution(self, values):
        """计算数值分布"""
        if not values:
            return {'min': 0, 'max': 0, 'avg': 0, 'total': 0}

        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'total': sum(values),
            'count': len(values)
        }

    def _analyze_items_per_order(self, orders):
        """分析每订单品项数"""
        if not orders:
            return {}

        item_counts = [len(order['items']) for order in orders.values()]
        if not item_counts:
            return {}

        return {
            'single_item_orders': len([c for c in item_counts if c == 1]),
            'multi_item_orders': len([c for c in item_counts if c > 1]),
            'high_complexity_orders': len([c for c in item_counts if c > 10]),  # 超过10个品项的订单
            'distribution': self._get_frequency_distribution(item_counts)
        }

    def _analyze_orders_per_item(self, items):
        """分析每品项订单数"""
        if not items:
            return {}

        order_counts = [len(item['orders']) for item in items.values()]
        if not order_counts:
            return {}

        return {
            'low_frequency_items': len([c for c in order_counts if c <= 2]),  # 2个订单以内的品项
            'high_frequency_items': len([c for c in order_counts if c > 10]),  # 10个订单以上的品项
            'distribution': self._get_frequency_distribution(order_counts)
        }

    def _get_frequency_distribution(self, values):
        """获取频次分布"""
        from collections import Counter
        counter = Counter(values)
        return dict(counter.most_common(10))  # 返回前10个最常见的值

    def _calculate_abc_analysis(self, items):
        """基于EIQ数据计算ABC分析"""
        if not items:
            return []

        # 按总数量排序
        sorted_items = sorted(
            items.items(),
            key=lambda x: x[1]['total_qty'],
            reverse=True
        )

        total_qty = sum(item[1]['total_qty'] for item in sorted_items)
        if total_qty == 0:
            return []

        abc_analysis = []
        cumulative_qty = 0
        cumulative_percent = 0

        for i, (item_id, item_data) in enumerate(sorted_items):
            product = self.env['product.product'].browse(item_id)
            item_qty = item_data['total_qty']
            item_percent = (item_qty / total_qty) * 100
            cumulative_qty += item_qty
            cumulative_percent = (cumulative_qty / total_qty) * 100

            # ABC分类
            if cumulative_percent <= 70:
                category = 'A'
            elif cumulative_percent <= 90:
                category = 'B'
            else:
                category = 'C'

            abc_analysis.append({
                'rank': i + 1,
                'product_id': item_id,
                'product_name': product.display_name,
                'quantity': item_qty,
                'percent': round(item_percent, 2),
                'cumulative_percent': round(cumulative_percent, 2),
                'category': category
            })

        return abc_analysis

    def _format_analysis_results(self, stats):
        """Format analysis results to HTML"""
        html = """
        <div>
            <h4>EIQ Analysis Core Indicators</h4>
            <table class="table table-sm">
                <tr>
                    <td><strong>Total Orders (E):</strong></td>
                    <td>{entries}</td>
                </tr>
                <tr>
                    <td><strong>Total Items (I):</strong></td>
                    <td>{items}</td>
                </tr>
                <tr>
                    <td><strong>Total Quantity (Q):</strong></td>
                    <td>{quantity}</td>
                </tr>
                <tr>
                    <td><strong>Average Items per Order (I/E):</strong></td>
                    <td>{eoq}</td>
                </tr>
                <tr>
                    <td><strong>Average Quantity per Order (Q/E):</strong></td>
                    <td>{qoe}</td>
                </tr>
                <tr>
                    <td><strong>Average Quantity per Item (Q/I):</strong></td>
                    <td>{qoi}</td>
                </tr>
            </table>

            <h4>Order Analysis</h4>
            <table class="table table-sm">
                <tr>
                    <td><strong>Min Items per Order:</strong></td>
                    <td>{min_items_per_order}</td>
                </tr>
                <tr>
                    <td><strong>Max Items per Order:</strong></td>
                    <td>{max_items_per_order}</td>
                </tr>
                <tr>
                    <td><strong>Average Items per Order:</strong></td>
                    <td>{avg_items_per_order}</td>
                </tr>
            </table>

            <h4>Item Analysis</h4>
            <table class="table table-sm">
                <tr>
                    <td><strong>Min Orders per Item:</strong></td>
                    <td>{min_orders_per_item}</td>
                </tr>
                <tr>
                    <td><strong>Max Orders per Item:</strong></td>
                    <td>{max_orders_per_item}</td>
                </tr>
                <tr>
                    <td><strong>Average Orders per Item:</strong></td>
                    <td>{avg_orders_per_item}</td>
                </tr>
            </table>
        </div>
        """.format(
            entries=stats.get('entries', 0),
            items=stats.get('items', 0),
            quantity=round(stats.get('quantity', 0.0), 2),
            eoq=round(stats.get('eoq', 0.0), 2),
            qoe=round(stats.get('qoe', 0.0), 2),
            qoi=round(stats.get('qoi', 0.0), 2),
            min_items_per_order=stats.get('min_items_per_order', 0),
            max_items_per_order=stats.get('max_items_per_order', 0),
            avg_items_per_order=round(stats.get('avg_items_per_order', 0.0), 2),
            min_orders_per_item=stats.get('min_orders_per_item', 0),
            max_orders_per_item=stats.get('max_orders_per_item', 0),
            avg_orders_per_item=round(stats.get('avg_orders_per_item', 0.0), 2),
        )

        return html

    def _generate_recommendations(self, stats):
        """Generate optimization recommendations"""
        recommendations = []

        # Analyze average items per order
        avg_items = stats.get('avg_items_per_order', 0)
        if avg_items < 1.5:
            recommendations.append("Average items per order is low ({}), suggest optimizing picking routes and considering order consolidation.".format(round(avg_items, 2)))
        elif avg_items > 10:
            recommendations.append("Average items per order is high ({}), suggest zone picking or batch picking.".format(round(avg_items, 2)))

        # Analyze average orders per item
        avg_orders = stats.get('avg_orders_per_item', 0)
        if avg_orders > 20:
            recommendations.append("Some items have very high order frequency, suggest placing them in prime storage locations.")
        elif avg_orders < 2:
            recommendations.append("Some items have very low order frequency, consider storing them in distant locations or optimizing inventory.")

        # Analyze EIQ ratio
        eoq = stats.get('eoq', 0)
        if eoq > 5:
            recommendations.append("I/E ratio is high ({}), indicating orders contain many items, suitable for single-order picking.".format(round(eoq, 2)))
        elif eoq < 2:
            recommendations.append("I/E ratio is low ({}), indicating orders contain few items, consider batch picking.".format(round(eoq, 2)))

        # ABC analysis recommendations
        abc_analysis = stats.get('detailed_stats', {}).get('abc_analysis', [])
        if abc_analysis:
            a_items = [item for item in abc_analysis if item['category'] == 'A']
            if len(a_items) > 0:
                recommendations.append("A-class items ({} items) have high frequency, suggest placing them in the most convenient locations.".format(len(a_items)))

        if not recommendations:
            recommendations.append("Current EIQ analysis shows reasonable operation mode, recommend continuous monitoring.")

        # Generate HTML
        html = '<div><ul>'
        for rec in recommendations:
            html += '<li>{}</li>'.format(rec)
        html += '</ul></div>'

        return html


class WmsEiqAnalysisReport(models.TransientModel):
    """
    EIQ Analysis Report Wizard
    """
    _name = 'wms.eiq.analysis.report'
    _description = 'WMS EIQ Analysis Report Wizard'

    period_start = fields.Date('Analysis Period Start', required=True, default=lambda self: fields.Date.to_string(fields.Date.today().replace(day=1)))
    period_end = fields.Date('Analysis Period End', required=True, default=fields.Date.today)
    owner_id = fields.Many2one('wms.owner', 'Owner')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    analysis_type = fields.Selection([
        ('inbound', 'Inbound EIQ Analysis'),
        ('outbound', 'Outbound EIQ Analysis'),
        ('internal', 'Internal Operation EIQ Analysis'),
        ('combined', 'Combined EIQ Analysis'),
    ], string='Analysis Type', required=True, default='outbound')
    calculation_method = fields.Selection([
        ('simple', 'Simple Statistics'),
        ('weighted', 'Weighted Statistics'),
        ('advanced', 'Advanced Analysis'),
    ], string='Calculation Method', default='simple')

    def action_generate_report(self):
        """Generate EIQ analysis report"""
        # Create analysis record
        analysis = self.env['wms.eiq.analysis'].create({
            'name': 'EIQ Analysis {} to {}'.format(self.period_start, self.period_end),
            'period_start': self.period_start,
            'period_end': self.period_end,
            'owner_id': self.owner_id.id,
            'warehouse_id': self.warehouse_id.id,
            'analysis_type': self.analysis_type,
            'calculation_method': self.calculation_method,
        })

        # Generate analysis
        analysis.action_generate_analysis()

        # Return analysis record
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.eiq.analysis',
            'res_id': analysis.id,
            'view_mode': 'form',
            'target': 'current',
        }