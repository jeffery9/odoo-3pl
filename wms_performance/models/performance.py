from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


class WmsPerformanceIndicator(models.Model):
    """
    Performance Indicator - Key metrics for warehouse operations
    """
    _name = 'wms.performance.indicator'
    _description = 'WMS Performance Indicator'
    _order = 'category, sequence'

    name = fields.Char('Indicator Name', required=True)
    code = fields.Char('Indicator Code', required=True, copy=False)
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence', default=10)

    # Category and type
    category = fields.Selection([
        ('throughput', 'Throughput'),
        ('efficiency', 'Efficiency'),
        ('quality', 'Quality'),
        ('cost', 'Cost'),
        ('safety', 'Safety'),
        ('service', 'Customer Service'),
        ('productivity', 'Productivity'),
    ], string='Category', required=True)

    indicator_type = fields.Selection([
        ('kpi', 'KPI'),
        ('metric', 'Metric'),
        ('ratio', 'Ratio'),
        ('score', 'Score'),
    ], string='Type', default='kpi')

    # Calculation method
    calculation_method = fields.Selection([
        ('count', 'Count'),
        ('sum', 'Sum'),
        ('average', 'Average'),
        ('percentage', 'Percentage'),
        ('ratio', 'Ratio'),
        ('custom', 'Custom Formula'),
    ], string='Calculation Method', required=True)

    # Data source
    source_model = fields.Char('Source Model', help='Model name for data source')
    source_field = fields.Char('Source Field', help='Field name in source model')
    filter_domain = fields.Char('Filter Domain', help='Domain for filtering records')

    # Target and benchmark
    target_value = fields.Float('Target Value')
    benchmark_value = fields.Float('Benchmark Value')
    unit_of_measure = fields.Char('Unit of Measure', default='Each')

    # Display settings
    precision_digits = fields.Integer('Precision Digits', default=2)
    display_format = fields.Selection([
        ('number', 'Number'),
        ('percentage', 'Percentage'),
        ('time', 'Time'),
        ('currency', 'Currency'),
    ], string='Display Format', default='number')

    # Alert settings
    alert_threshold = fields.Float('Alert Threshold')
    alert_type = fields.Selection([
        ('above', 'Above Threshold'),
        ('below', 'Below Threshold'),
    ], string='Alert Type', default='above')

    # Owner restriction
    owner_id = fields.Many2one('wms.owner', 'Owner', help='Leave empty for all owners')

    @api.constrains('target_value', 'benchmark_value')
    def _check_positive_values(self):
        for indicator in self:
            if indicator.target_value < 0:
                raise ValidationError(_('Target value cannot be negative.'))
            if indicator.benchmark_value < 0:
                raise ValidationError(_('Benchmark value cannot be negative.'))


class WmsPerformanceReport(models.Model):
    """
    Performance Report - Comprehensive performance analysis
    """
    _name = 'wms.performance.report'
    _description = 'WMS Performance Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'report_date desc'

    name = fields.Char('Report Name', required=True, copy=False)
    report_code = fields.Char('Report Code', required=True, copy=False,
                              default=lambda self: _('New'))
    report_date = fields.Date('Report Date', required=True, default=fields.Date.context_today)

    # Period
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)

    # Configuration
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    report_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ], string='Report Type', required=True, default='monthly')

    # Performance categories
    throughput_performance = fields.Float('Throughput Performance (%)', digits=(10, 2))
    efficiency_performance = fields.Float('Efficiency Performance (%)', digits=(10, 2))
    quality_performance = fields.Float('Quality Performance (%)', digits=(10, 2))
    cost_performance = fields.Float('Cost Performance (%)', digits=(10, 2))
    safety_performance = fields.Float('Safety Performance (%)', digits=(10, 2))
    service_performance = fields.Float('Service Performance (%)', digits=(10, 2))

    # Overall metrics
    overall_score = fields.Float('Overall Performance Score', digits=(10, 2))
    total_indicators = fields.Integer('Total Indicators')
    indicators_above_target = fields.Integer('Indicators Above Target')
    indicators_below_target = fields.Integer('Indicators Below Target')

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('validated', 'Validated'),
        ('published', 'Published'),
    ], string='Status', default='draft', tracking=True)

    # Content
    executive_summary = fields.Html('Executive Summary')
    detailed_analysis = fields.Html('Detailed Analysis')
    recommendations = fields.Html('Recommendations')
    performance_trends = fields.Html('Performance Trends')

    # Data storage
    performance_data = fields.Text('Performance Data', help='JSON format performance data')
    charts_data = fields.Text('Charts Data', help='JSON format charts data')
    alert_summary = fields.Html('Alert Summary')

    notes = fields.Text('Notes')

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for report in self:
            if report.period_start and report.period_end and report.period_start > report.period_end:
                raise ValidationError(_('Period start date cannot be later than end date.'))

    @api.model
    def create(self, vals):
        if vals.get('report_code', _('New')) == _('New'):
            vals['report_code'] = self.env['ir.sequence'].next_by_code('wms.performance.report') or _('New')
        return super().create(vals)

    def action_generate_report(self):
        """Generate performance report"""
        for report in self:
            # Calculate performance metrics
            performance_data = report._calculate_performance_metrics()

            # Generate executive summary
            executive_summary = report._generate_executive_summary(performance_data)

            # Generate detailed analysis
            detailed_analysis = report._generate_detailed_analysis(performance_data)

            # Generate recommendations
            recommendations = report._generate_recommendations(performance_data)

            # Generate trends
            trends = report._generate_trends()

            # Generate alerts
            alerts = report._generate_alerts()

            # Update report
            report.write({
                'performance_data': json.dumps(performance_data),
                'executive_summary': executive_summary,
                'detailed_analysis': detailed_analysis,
                'recommendations': recommendations,
                'performance_trends': trends,
                'alert_summary': alerts,
                'overall_score': performance_data.get('overall_score', 0.0),
                'total_indicators': performance_data.get('total_indicators', 0),
                'indicators_above_target': performance_data.get('indicators_above_target', 0),
                'indicators_below_target': performance_data.get('indicators_below_target', 0),
                'status': 'generated'
            })

    def _calculate_performance_metrics(self):
        """Calculate all performance metrics"""
        metrics = {
            'throughput': self._calculate_throughput_metrics(),
            'efficiency': self._calculate_efficiency_metrics(),
            'quality': self._calculate_quality_metrics(),
            'cost': self._calculate_cost_metrics(),
            'safety': self._calculate_safety_metrics(),
            'service': self._calculate_service_metrics(),
        }

        # Calculate overall score (simple average for now)
        valid_scores = [v.get('score', 0) for v in metrics.values() if v.get('score') is not None]
        overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

        return {
            'metrics': metrics,
            'overall_score': overall_score,
            'total_indicators': len(valid_scores),
            'indicators_above_target': len([s for s in valid_scores if s >= 80]),  # Assuming 80% is target
            'indicators_below_target': len([s for s in valid_scores if s < 80]),
        }

    def _calculate_throughput_metrics(self):
        """Calculate throughput-related metrics"""
        # Count operations in the period
        operations = self.env['stock.picking'].search([
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('state', '=', 'done'),
            ('owner_id', '=', self.owner_id.id) if self.owner_id else ('id', '>', 0),
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id),
        ])

        total_operations = len(operations)
        inbound_ops = len(operations.filtered(lambda x: x.picking_type_id.code == 'incoming'))
        outbound_ops = len(operations.filtered(lambda x: x.picking_type_id.code == 'outgoing'))

        # Calculate throughput score based on target
        target_throughput = 1000  # Example target
        score = min((total_operations / target_throughput) * 100, 100) if target_throughput > 0 else 0

        return {
            'total_operations': total_operations,
            'inbound_operations': inbound_ops,
            'outbound_operations': outbound_ops,
            'score': score,
            'trend': 'up' if total_operations > target_throughput * 0.9 else 'down'
        }

    def _calculate_efficiency_metrics(self):
        """Calculate efficiency-related metrics"""
        # Example: Calculate pick/pack efficiency
        operations = self.env['stock.picking'].search([
            ('date_done', '>=', self.period_start),
            ('date_done', '<=', self.period_end),
            ('state', '=', 'done'),
            ('owner_id', '=', self.owner_id.id) if self.owner_id else ('id', '>', 0),
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id),
        ])

        # Calculate average processing time
        total_time = 0
        valid_ops = 0
        for op in operations:
            if op.date and op.date_done:
                duration = (op.date_done - op.date).total_seconds() / 3600  # in hours
                total_time += duration
                valid_ops += 1

        avg_processing_time = total_time / valid_ops if valid_ops > 0 else 0
        target_time = 2  # Example target in hours

        # Score based on efficiency (shorter time = higher score)
        if avg_processing_time > 0:
            score = max(0, min(100, (target_time / avg_processing_time) * 100))
        else:
            score = 100 if target_time == 0 else 0

        return {
            'avg_processing_time': avg_processing_time,
            'total_operations': len(operations),
            'score': score,
            'trend': 'up' if avg_processing_time < target_time else 'down'
        }

    def _calculate_quality_metrics(self):
        """Calculate quality-related metrics"""
        # Example: Calculate accuracy based on adjustments and errors
        adjustments = self.env['stock.inventory'].search([
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('state', '=', 'done'),
        ])

        # Assuming inventory adjustments indicate quality issues
        total_adjustments = len(adjustments)
        total_operations = self._get_total_operations()

        # Quality score = (1 - adjustments/operations) * 100
        if total_operations > 0:
            quality_rate = (1 - min(total_adjustments / total_operations, 1)) * 100
        else:
            quality_rate = 100

        return {
            'total_adjustments': total_adjustments,
            'total_operations': total_operations,
            'quality_rate': quality_rate,
            'score': quality_rate,
            'trend': 'up' if quality_rate > 95 else 'stable'
        }

    def _get_total_operations(self):
        """Get total operations for quality calculation"""
        operations = self.env['stock.picking'].search([
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('state', '=', 'done'),
            ('owner_id', '=', self.owner_id.id) if self.owner_id else ('id', '>', 0),
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id),
        ])
        return len(operations)

    def _calculate_cost_metrics(self):
        """Calculate cost-related metrics"""
        # Example: Calculate cost per operation
        total_operations = self._get_total_operations()
        # We would integrate with cost tracking modules in real implementation
        target_cost_per_op = 5.0  # Example target
        actual_cost_per_op = 4.5  # Example actual

        cost_efficiency = (target_cost_per_op / actual_cost_per_op) * 100 if actual_cost_per_op > 0 else 0
        score = min(cost_efficiency, 100)

        return {
            'cost_per_operation': actual_cost_per_op,
            'target_cost_per_op': target_cost_per_op,
            'cost_efficiency': cost_efficiency,
            'score': score,
            'trend': 'up' if actual_cost_per_op < target_cost_per_op else 'down'
        }

    def _calculate_safety_metrics(self):
        """Calculate safety-related metrics"""
        # This would connect to safety management module
        safety_incidents = self.env['wms.safety.incident'].search([
            ('incident_date', '>=', self.period_start),
            ('incident_date', '<=', self.period_end),
            ('owner_id', '=', self.owner_id.id) if self.owner_id else ('id', '>', 0),
        ]) if 'wms.safety.incident' in self.env else []

        total_incidents = len(safety_incidents)
        target_incidents = 2  # Example target

        # Safety score = (max_incidents - actual_incidents) / max_incidents * 100
        score = max(0, min(100, ((target_incidents - total_incidents) / target_incidents) * 100)) if target_incidents > 0 else 100

        return {
            'total_incidents': total_incidents,
            'target_incidents': target_incidents,
            'score': score,
            'trend': 'up' if total_incidents < target_incidents else 'down'
        }

    def _calculate_service_metrics(self):
        """Calculate service-related metrics"""
        operations = self.env['stock.picking'].search([
            ('scheduled_date', '>=', self.period_start),
            ('scheduled_date', '<=', self.period_end),
            ('state', '=', 'done'),
            ('owner_id', '=', self.owner_id.id) if self.owner_id else ('id', '>', 0),
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id),
        ])

        on_time_deliveries = 0
        total_deliveries = len(operations.filtered(lambda x: x.picking_type_id.code == 'outgoing'))

        for delivery in operations.filtered(lambda x: x.picking_type_id.code == 'outgoing'):
            if delivery.date_done and delivery.scheduled_date:
                # If delivery was on or before scheduled date
                if delivery.date_done <= delivery.scheduled_date:
                    on_time_deliveries += 1

        service_rate = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 100
        score = service_rate  # Use service rate as score directly

        return {
            'on_time_deliveries': on_time_deliveries,
            'total_deliveries': total_deliveries,
            'service_rate': service_rate,
            'score': score,
            'trend': 'up' if service_rate > 90 else 'stable'
        }

    def _generate_executive_summary(self, performance_data):
        """Generate executive summary in HTML"""
        html = f"""
        <div>
            <h4>Performance Summary</h4>
            <table class="table table-sm">
                <tr>
                    <td><strong>Overall Score:</strong></td>
                    <td>{performance_data['overall_score']:.2f}%</td>
                </tr>
                <tr>
                    <td><strong>Total Indicators:</strong></td>
                    <td>{performance_data['total_indicators']}</td>
                </tr>
                <tr>
                    <td><strong>Above Target:</strong></td>
                    <td>{performance_data['indicators_above_target']}</td>
                </tr>
                <tr>
                    <td><strong>Below Target:</strong></td>
                    <td>{performance_data['indicators_below_target']}</td>
                </tr>
            </table>
        </div>
        """
        return html

    def _generate_detailed_analysis(self, performance_data):
        """Generate detailed analysis in HTML"""
        metrics = performance_data['metrics']
        html = """
        <div>
            <h4>Detailed Metrics Analysis</h4>
        """

        for category, data in metrics.items():
            html += f"""
            <h5>{category.title()} Metrics</h5>
            <table class="table table-sm">
            """
            for key, value in data.items():
                html += f"<tr><td>{key.replace('_', ' ').title()}:</td><td>{value}</td></tr>"
            html += "</table>"

        html += "</div>"
        return html

    def _generate_recommendations(self, performance_data):
        """Generate improvement recommendations"""
        recommendations = []

        # Overall score recommendation
        overall_score = performance_data.get('overall_score', 0)
        if overall_score < 70:
            recommendations.append("Overall performance is significantly below target. Immediate action required.")
        elif overall_score < 85:
            recommendations.append("Performance needs improvement. Review processes and KPIs.")
        else:
            recommendations.append("Performance is good. Continue monitoring and gradual improvements.")

        # Check specific metrics
        metrics = performance_data.get('metrics', {})
        for category, data in metrics.items():
            score = data.get('score', 0)
            if score < 70:
                recommendations.append(f"{category.title()} performance is low ({score:.2f}%). Focus on improvements in this area.")
            elif score > 95:
                recommendations.append(f"{category.title()} performance is excellent ({score:.2f}%). Consider raising targets.")

        # Generate HTML
        html = "<div><ul>"
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        html += "</ul></div>"

        return html

    def _generate_trends(self):
        """Generate performance trends"""
        # Get previous periods to calculate trends
        prev_period_start = self.period_start - (self.period_end - self.period_start)
        prev_period_end = self.period_start - timedelta(days=1)

        # Compare with previous period (simplified)
        html = f"""
        <div>
            <h4>Trend Analysis</h4>
            <p>Period: {self.period_start} to {self.period_end}</p>
            <p>Compared to previous period: {prev_period_start} to {prev_period_end}</p>
            <p>Trend data would normally compare to previous period to identify improvements or declines.</p>
        </div>
        """
        return html

    def _generate_alerts(self):
        """Generate performance alerts"""
        performance_data = self._calculate_performance_metrics()
        alerts = []

        # Check for low performance indicators
        metrics = performance_data.get('metrics', {})
        for category, data in metrics.items():
            score = data.get('score', 0)
            if score < 70:
                alerts.append(f"⚠️ {category.title()} performance is low ({score:.2f}%)")

        # Overall score alert
        if performance_data.get('overall_score', 100) < 75:
            alerts.append(f"⚠️ Overall performance is below target ({performance_data['overall_score']:.2f}%)")

        # Generate HTML
        html = "<div><ul>"
        for alert in alerts:
            html += f'<li style="color: #d32f2f;">{alert}</li>'
        html += "</ul></div>"

        return html


class WmsOperatorPerformance(models.Model):
    """
    Operator Performance - Track individual operator performance
    """
    _name = 'wms.operator.performance'
    _description = 'WMS Operator Performance'
    _order = 'date desc, operator_id'

    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    operator_id = fields.Many2one('hr.employee', 'Operator', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)

    # Operation counts
    operations_completed = fields.Integer('Operations Completed', default=0)
    operations_assigned = fields.Integer('Operations Assigned', default=0)

    # Time metrics
    time_spent_hours = fields.Float('Time Spent (Hours)', default=0.0)
    standard_time_hours = fields.Float('Standard Time (Hours)', default=0.0)
    efficiency_rate = fields.Float('Efficiency Rate (%)', digits=(10, 2), default=100.0)

    # Quality metrics
    accuracy_rate = fields.Float('Accuracy Rate (%)', digits=(10, 2), default=100.0)
    error_count = fields.Integer('Error Count', default=0)

    # Performance scores
    productivity_score = fields.Float('Productivity Score', digits=(10, 2), default=0.0)
    quality_score = fields.Float('Quality Score', digits=(10, 2), default=0.0)
    overall_score = fields.Float('Overall Score', digits=(10, 2), default=0.0)

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('validated', 'Validated'),
    ], string='Status', default='draft')

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        # Calculate derived metrics
        if 'time_spent_hours' in vals and 'standard_time_hours' in vals:
            actual_time = vals.get('time_spent_hours', 0)
            std_time = vals.get('standard_time_hours', 0)

            if std_time > 0:
                vals['efficiency_rate'] = (std_time / actual_time * 100) if actual_time > 0 else 0
            else:
                vals['efficiency_rate'] = 100 if actual_time == 0 else 0

        # Calculate scores
        if 'operations_completed' in vals and 'error_count' in vals:
            completed = vals.get('operations_completed', 0)
            errors = vals.get('error_count', 0)

            if completed > 0:
                vals['accuracy_rate'] = ((completed - errors) / completed * 100) if completed >= errors else 0
            else:
                vals['accuracy_rate'] = 100 if errors == 0 else 0

        return super().create(vals)

    def calculate_performance_score(self):
        """Calculate overall performance score"""
        for record in self:
            # Weighted average of efficiency and quality
            score = (record.efficiency_rate * 0.6) + (record.accuracy_rate * 0.4)
            record.overall_score = score
            record.productivity_score = record.efficiency_rate
            record.quality_score = record.accuracy_rate


class WmsPerformanceWizard(models.TransientModel):
    """
    Performance Report Wizard
    """
    _name = 'wms.performance.wizard'
    _description = 'WMS Performance Report Wizard'

    period_start = fields.Date('Period Start', required=True, default=lambda self: fields.Date.to_string(fields.Date.today().replace(day=1)))
    period_end = fields.Date('Period End', required=True, default=fields.Date.today)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    report_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ], string='Report Type', required=True, default='monthly')

    def action_generate_report(self):
        """Generate performance report"""
        # Create the report
        report = self.env['wms.performance.report'].create({
            'name': f'Performance Report {self.period_start} to {self.period_end}',
            'period_start': self.period_start,
            'period_end': self.period_end,
            'owner_id': self.owner_id.id,
            'warehouse_id': self.warehouse_id.id,
            'report_type': self.report_type,
        })

        # Generate the report content
        report.action_generate_report()

        # Return the generated report
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.performance.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }