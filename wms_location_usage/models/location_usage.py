from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


class WmsLocationUsage(models.Model):
    """
    Location Usage Analysis - Location Usage Analysis
    Analyze the usage and efficiency of warehouse locations
    """
    _name = 'wms.location.usage'
    _description = 'WMS Location Usage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'usage_rate desc'

    name = fields.Char('Analysis Name', required=True, copy=False)
    analysis_date = fields.Date('Analysis Date', required=True, default=fields.Date.context_today)
    period_start = fields.Date('Analysis Period Start', required=True)
    period_end = fields.Date('Analysis Period End', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)

    # Analysis scope
    analysis_type = fields.Selection([
        ('all', 'All Locations'),
        ('occupied', 'Occupied Locations'),
        ('empty', 'Empty Locations'),
        ('by_zone', 'By Zone Statistics'),
        ('by_category', 'By Category Statistics'),
    ], string='Analysis Type', required=True, default='all')

    # Statistical Summary
    total_locations = fields.Integer('Total Locations', readonly=True)
    occupied_locations = fields.Integer('Occupied Locations', readonly=True)
    empty_locations = fields.Integer('Empty Locations', readonly=True)
    usage_rate = fields.Float('Average Occupancy Rate (%)', readonly=True, digits=(10, 2))

    # Space Utilization
    total_capacity = fields.Float('Total Capacity', readonly=True, help='Total volume or total quantity capacity')
    used_capacity = fields.Float('Used Capacity', readonly=True, help='Used volume or quantity')
    capacity_usage_rate = fields.Float('Capacity Utilization (%)', readonly=True, digits=(10, 2))

    # Location Classification Statistics
    high_usage_locations = fields.Integer('High Occupancy Locations (>80%)', readonly=True)
    low_usage_locations = fields.Integer('Low Occupancy Locations (<20%)', readonly=True)
    unused_locations = fields.Integer('Unused Locations', readonly=True)

    # Dynamic Analysis
    turnover_rate = fields.Float('Turnover Rate', readonly=True, digits=(10, 2), help='Inventory turnover frequency')
    avg_residence_time = fields.Float('Average Residence Time (Days)', readonly=True, digits=(10, 2))

    # Analysis Results
    detailed_analysis = fields.Text('Detailed Analysis', readonly=True, help='Detailed analysis data in JSON format')
    recommendations = fields.Html('Optimization Recommendations', readonly=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('validated', 'Validated'),
    ], string='Status', default='draft', tracking=True)

    # Statistical Information
    stats_by_category = fields.Text('Statistics by Category', readonly=True)
    stats_by_zone = fields.Text('Statistics by Zone', readonly=True)
    usage_trend = fields.Text('Usage Trend', readonly=True)

    notes = fields.Text('Notes')

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for analysis in self:
            if analysis.period_start and analysis.period_end and analysis.period_start > analysis.period_end:
                raise ValidationError(_('Analysis period start date cannot be later than end date.'))

    def action_generate_analysis(self):
        """Generate location usage analysis"""
        for analysis in self:
            # Execute location usage analysis calculation
            stats = analysis._calculate_location_usage_stats()

            # Update analysis results
            analysis.write({
                'total_locations': stats.get('total_locations', 0),
                'occupied_locations': stats.get('occupied_locations', 0),
                'empty_locations': stats.get('empty_locations', 0),
                'usage_rate': stats.get('usage_rate', 0.0),
                'total_capacity': stats.get('total_capacity', 0.0),
                'used_capacity': stats.get('used_capacity', 0.0),
                'capacity_usage_rate': stats.get('capacity_usage_rate', 0.0),
                'high_usage_locations': stats.get('high_usage_locations', 0),
                'low_usage_locations': stats.get('low_usage_locations', 0),
                'unused_locations': stats.get('unused_locations', 0),
                'turnover_rate': stats.get('turnover_rate', 0.0),
                'avg_residence_time': stats.get('avg_residence_time', 0.0),
                'detailed_analysis': json.dumps(stats.get('detailed_analysis', {})),
                'recommendations': analysis._generate_recommendations(stats),
                'stats_by_category': json.dumps(stats.get('stats_by_category', {})),
                'stats_by_zone': json.dumps(stats.get('stats_by_zone', {})),
                'usage_trend': json.dumps(stats.get('usage_trend', {})),
                'state': 'generated'
            })

    def _calculate_location_usage_stats(self):
        """Calculate location usage statistics"""
        self.ensure_one()

        # Get all locations in specified warehouse
        location_domain = [
            ('location_id', 'child_of', self.warehouse_id.lot_stock_id.id),
            ('usage', '=', 'internal'),  # Only count internal locations
        ]
        locations = self.env['stock.location'].search(location_domain)

        total_locations = len(locations)
        occupied_locations = 0
        empty_locations = 0
        total_capacity = 0.0
        used_capacity = 0.0

        # Calculate occupation status for each location
        location_details = []
        for location in locations:
            # Get inventory in the location
            quants = self.env['stock.quant'].search([
                ('location_id', '=', location.id),
                ('quantity', '>', 0),
            ])

            location_occupied = len(quants) > 0
            location_volume = 0.0
            location_weight = 0.0

            for quant in quants:
                if quant.owner_id and quant.owner_id.id == self.owner_id.id:
                    # Calculate volume and weight
                    product = quant.product_id
                    quant_volume = product.volume * quant.quantity
                    quant_weight = product.weight * quant.quantity

                    location_volume += quant_volume
                    location_weight += quant_weight
                    used_capacity += quant_volume

            # Add location capacity
            if location.volume_per_location:
                total_capacity += location.volume_per_location
            else:
                # If location doesn't have volume capacity set, estimate based on goods occupied
                total_capacity += location_volume * 1.5  # Estimated capacity, can be adjusted based on configuration

            # Count occupation status
            if location_occupied:
                occupied_locations += 1
            else:
                empty_locations += 1

            location_details.append({
                'location_id': location.id,
                'location_name': location.display_name,
                'is_occupied': location_occupied,
                'occupied_volume': location_volume,
                'occupied_weight': location_weight,
                'capacity': location.volume_per_location or location_volume * 1.5,
                'usage_rate': (location_volume / (location.volume_per_location or (location_volume * 1.5))) * 100 if (location.volume_per_location or (location_volume * 1.5)) > 0 else 0
            })

        # Calculate overall occupancy rate
        usage_rate = (occupied_locations / total_locations * 100) if total_locations > 0 else 0.0
        capacity_usage_rate = (used_capacity / total_capacity * 100) if total_capacity > 0 else 0.0

        # Analyze high and low occupancy locations
        high_usage_locations = len([loc for loc in location_details if loc['usage_rate'] > 80])
        low_usage_locations = len([loc for loc in location_details if loc['usage_rate'] < 20])
        unused_locations = empty_locations

        # Calculate turnover rate (simplified calculation)
        turnover_rate = self._calculate_turnover_rate()
        avg_residence_time = self._calculate_avg_residence_time()

        # Statistics by zone and category
        stats_by_zone = self._calculate_stats_by_zone(locations)
        stats_by_category = self._calculate_stats_by_category(locations)

        # Usage trend analysis
        usage_trend = self._calculate_usage_trend()

        return {
            'total_locations': total_locations,
            'occupied_locations': occupied_locations,
            'empty_locations': empty_locations,
            'usage_rate': usage_rate,
            'total_capacity': total_capacity,
            'used_capacity': used_capacity,
            'capacity_usage_rate': capacity_usage_rate,
            'high_usage_locations': high_usage_locations,
            'low_usage_locations': low_usage_locations,
            'unused_locations': unused_locations,
            'turnover_rate': turnover_rate,
            'avg_residence_time': avg_residence_time,
            'detailed_analysis': {
                'location_details': location_details,
                'top_occupied': sorted(location_details, key=lambda x: x['usage_rate'], reverse=True)[:10],
                'top_empty': [loc for loc in location_details if not loc['is_occupied']][:10]
            },
            'stats_by_zone': stats_by_zone,
            'stats_by_category': stats_by_category,
            'usage_trend': usage_trend
        }

    def _calculate_turnover_rate(self):
        """Calculate inventory turnover rate (simplified version)"""
        # Calculate the frequency of inbound and outbound operations during the specified period
        domain = [
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('state', '=', 'done'),
        ]

        if hasattr(self.env['stock.move'], 'owner_id'):
            domain.append(('owner_id', '=', self.owner_id.id))

        moves = self.env['stock.move'].search(domain)
        # Simplified calculation: turnover rate = outbound quantity / average inventory
        # More complex logic is needed here, returning an estimated value for now
        return 12.0  # Assume 12 turnovers per year

    def _calculate_avg_residence_time(self):
        """Calculate average residence time (simplified version)"""
        # Estimate average residence time by querying the creation time of inventory records
        quants = self.env['stock.quant'].search([
            ('location_id', 'child_of', self.warehouse_id.lot_stock_id.id),
            ('owner_id', '=', self.owner_id.id),
            ('quantity', '>', 0),
        ])

        total_days = 0
        count = 0
        for quant in quants:
            if quant.create_date:
                days = (fields.Datetime.now() - quant.create_date).days
                total_days += days
                count += 1

        return (total_days / count) if count > 0 else 0.0

    def _calculate_stats_by_zone(self, locations):
        """Statistics by zone"""
        stats = {}
        for location in locations:
            zone = location.location_id.name if location.location_id else 'Unknown Zone'
            if zone not in stats:
                stats[zone] = {
                    'total': 0,
                    'occupied': 0,
                    'empty': 0,
                    'usage_rate': 0.0
                }

            stats[zone]['total'] += 1
            quants = self.env['stock.quant'].search([('location_id', '=', location.id), ('quantity', '>', 0)])
            if quants:
                stats[zone]['occupied'] += 1
            else:
                stats[zone]['empty'] += 1

        # Calculate usage rate
        for zone, data in stats.items():
            data['usage_rate'] = (data['occupied'] / data['total'] * 100) if data['total'] > 0 else 0.0

        return stats

    def _calculate_stats_by_category(self, locations):
        """Statistics by location category"""
        stats = {}
        for location in locations:
            category = location.chief_worker.name if hasattr(location, 'chief_worker') and location.chief_worker else 'General Location'
            if category not in stats:
                stats[category] = {
                    'total': 0,
                    'occupied': 0,
                    'empty': 0,
                    'usage_rate': 0.0
                }

            stats[category]['total'] += 1
            quants = self.env['stock.quant'].search([('location_id', '=', location.id), ('quantity', '>', 0)])
            if quants:
                stats[category]['occupied'] += 1
            else:
                stats[category]['empty'] += 1

        # Calculate usage rate
        for category, data in stats.items():
            data['usage_rate'] = (data['occupied'] / data['total'] * 100) if data['total'] > 0 else 0.0

        return stats

    def _calculate_usage_trend(self):
        """Calculate usage trend"""
        # Simplified implementation: analyze location usage trend by month
        trends = []
        current_date = self.period_start
        while current_date <= self.period_end:
            # Calculate location usage for current date
            quants = self.env['stock.quant'].search([
                ('create_date', '<=', current_date),
                ('quantity', '>', 0),
                ('location_id', 'child_of', self.warehouse_id.lot_stock_id.id),
                ('owner_id', '=', self.owner_id.id),
            ])

            trends.append({
                'date': current_date,
                'occupied_locations': len(quants),
                'total_quantity': sum(quant.quantity for quant in quants)
            })

            current_date += timedelta(days=7)  # Weekly statistics, can be adjusted as needed

        return trends

    def _generate_recommendations(self, stats):
        """Generate optimization recommendations"""
        recommendations = []

        # Recommendations based on occupancy rate
        usage_rate = stats.get('usage_rate', 0)
        if usage_rate < 50:
            recommendations.append("Location occupancy rate is low ({}%), suggest optimizing product storage strategy to improve space utilization.".format(round(usage_rate, 2)))
        elif usage_rate > 90:
            recommendations.append("Location occupancy rate is very high ({}%), there may be storage pressure, suggest expanding capacity or optimizing layout.".format(round(usage_rate, 2)))

        # Recommendations based on high occupancy locations
        high_usage = stats.get('high_usage_locations', 0)
        if high_usage > 0:
            recommendations.append("Found {} high occupancy locations (>80%), suggest placing fast-turnover items here.".format(high_usage))

        # Recommendations based on low occupancy locations
        low_usage = stats.get('low_usage_locations', 0)
        if low_usage > 0:
            recommendations.append("Found {} low occupancy locations (<20%), consider reassigning or using for other purposes.".format(low_usage))

        # Recommendations based on empty locations
        empty_count = stats.get('empty_locations', 0)
        total_count = stats.get('total_locations', 1)
        empty_rate = (empty_count / total_count) * 100 if total_count > 0 else 0
        if empty_rate > 30:
            recommendations.append("Empty location ratio is high ({}%), suggest checking product layout rationality.".format(round(empty_rate, 2)))

        # Recommendations based on capacity utilization
        capacity_rate = stats.get('capacity_usage_rate', 0)
        if capacity_rate < 60:
            recommendations.append("Capacity utilization is low ({}%), products may not be fully utilizing location space.".format(round(capacity_rate, 2)))
        elif capacity_rate > 95:
            recommendations.append("Capacity utilization is very high ({}%), there may be risk of over-stacking.".format(round(capacity_rate, 2)))

        if not recommendations:
            recommendations.append("Current location usage is good, recommend maintaining and monitoring regularly.")

        # Generate HTML
        html = '<div><ul>'
        for rec in recommendations:
            html += '<li>{}</li>'.format(rec)
        html += '</ul></div>'

        return html


class WmsLocationUtilization(models.Model):
    """
    Location Utilization Details - Location Utilization Details
    """
    _name = 'wms.location.utilization'
    _description = 'WMS Location Utilization Details'
    _order = 'usage_rate desc'

    analysis_id = fields.Many2one('wms.location.usage', 'Location Usage Analysis', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    location_name = fields.Char('Location Name', related='location_id.name', store=True)
    zone_name = fields.Char('Zone', compute='_compute_zone', store=True)

    # Occupation Status
    is_occupied = fields.Boolean('Is Occupied')
    capacity = fields.Float('Location Capacity')
    used_volume = fields.Float('Used Volume')
    used_weight = fields.Float('Used Weight')

    # Utilization Rate
    usage_rate = fields.Float('Usage Rate (%)', digits=(10, 2))
    turnover_frequency = fields.Float('Turnover Frequency', digits=(10, 2))

    # Area Efficiency
    area_utilization = fields.Float('Area Utilization (%)', digits=(10, 2))

    # Owner Related
    owner_id = fields.Many2one('wms.owner', 'Owner')

    # Item Information
    product_count = fields.Integer('Product Count')
    total_quantity = fields.Float('Total Quantity')

    # Time Information
    first_used_date = fields.Date('First Used Date')
    last_used_date = fields.Date('Last Used Date')

    # Efficiency Category
    efficiency_category = fields.Selection([
        ('high', 'High Efficiency (>80%)'),
        ('medium', 'Medium Efficiency (20%-80%)'),
        ('low', 'Low Efficiency (<20%)'),
        ('unused', 'Unused'),
    ], string='Efficiency Category', compute='_compute_efficiency_category', store=True)

    @api.depends('usage_rate')
    def _compute_efficiency_category(self):
        for record in self:
            if record.usage_rate is None or record.usage_rate == 0:
                record.efficiency_category = 'unused'
            elif record.usage_rate > 80:
                record.efficiency_category = 'high'
            elif record.usage_rate < 20:
                record.efficiency_category = 'low'
            else:
                record.efficiency_category = 'medium'

    @api.depends('location_id')
    def _compute_zone(self):
        for record in self:
            # Simplification: use parent location as zone
            zone = record.location_id.location_id
            record.zone_name = zone.name if zone else 'Unknown Zone'


class WmsLocationUsageReport(models.TransientModel):
    """
    Location Usage Report Wizard
    """
    _name = 'wms.location.usage.report'
    _description = 'WMS Location Usage Report Wizard'

    period_start = fields.Date('Analysis Period Start', required=True, default=lambda self: fields.Date.to_string(fields.Date.today().replace(day=1)))
    period_end = fields.Date('Analysis Period End', required=True, default=fields.Date.today)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    analysis_type = fields.Selection([
        ('all', 'All Locations'),
        ('occupied', 'Occupied Locations'),
        ('empty', 'Empty Locations'),
        ('by_zone', 'By Zone Statistics'),
        ('by_category', 'By Category Statistics'),
    ], string='Analysis Type', required=True, default='all')

    def action_generate_report(self):
        """Generate location usage report"""
        # Create analysis record
        analysis = self.env['wms.location.usage'].create({
            'name': 'Location Usage Analysis {} to {} {}'.format(
                self.period_start,
                self.period_end,
                self.owner_id.name or 'All Owners'
            ),
            'period_start': self.period_start,
            'period_end': self.period_end,
            'owner_id': self.owner_id.id,
            'warehouse_id': self.warehouse_id.id,
            'analysis_type': self.analysis_type,
        })

        # Generate analysis
        analysis.action_generate_analysis()

        # Return analysis record
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.location.usage',
            'res_id': analysis.id,
            'view_mode': 'form',
            'target': 'current',
        }