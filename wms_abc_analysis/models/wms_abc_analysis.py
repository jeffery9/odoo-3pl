from odoo import models, fields, api


class WmsAbcAnalysis(models.Model):
    _name = 'wms.abc.analysis'
    _description = 'WMS ABC Analysis'
    _order = 'analysis_date desc'

    name = fields.Char('Analysis Reference', required=True, copy=False, readonly=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    analysis_date = fields.Datetime('Analysis Date', required=True, default=fields.Datetime.now)
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ], 'Status', default='draft', required=True)
    total_products = fields.Integer('Total Products Analyzed', compute='_compute_totals', store=True)
    a_class_count = fields.Integer('A Class Products', compute='_compute_totals', store=True)
    b_class_count = fields.Integer('B Class Products', compute='_compute_totals', store=True)
    c_class_count = fields.Integer('C Class Products', compute='_compute_totals', store=True)
    notes = fields.Text('Notes')
    analysis_method = fields.Selection([
        ('value', 'Value Based'),
        ('volume', 'Volume Based'),
        ('frequency', 'Frequency Based'),
        ('combined', 'Combined'),
    ], 'Analysis Method', default='combined', required=True)
    abc_rules = fields.One2many('wms.abc.rule', 'analysis_id', 'ABC Rules')
    analysis_lines = fields.One2many('wms.abc.analysis.line', 'analysis_id', 'Analysis Lines')

    @api.model_create_multi
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.abc.analysis') or '/'
        return super().create(vals)

    @api.depends('analysis_lines', 'analysis_lines.abc_class', 'analysis_lines.product_id')
    def _compute_totals(self):
        for record in self:
            record.total_products = len(record.analysis_lines)
            record.a_class_count = len(record.analysis_lines.filtered(lambda l: l.abc_class == 'A'))
            record.b_class_count = len(record.analysis_lines.filtered(lambda l: l.abc_class == 'B'))
            record.c_class_count = len(record.analysis_lines.filtered(lambda l: l.abc_class == 'C'))
    def action_start_analysis(self):
        """Start the ABC analysis process"""
        self.write({
            'status': 'in_progress',
            'analysis_date': fields.Datetime.now()
        })
    def action_run_analysis(self):
        """Run the ABC analysis"""
        for analysis in self:
            # Clear existing analysis lines
            analysis.analysis_lines.unlink()

            # Get products for this owner
            products = self.env['product.product'].search([
                ('type', '=', 'product'),
                ('categ_id', '!=', False),
            ])

            # Calculate metrics for each product
            for product in products:
                # Calculate product metrics (value, volume, frequency)
                value = self._calculate_product_value(product, analysis.period_start, analysis.period_end)
                volume = self._calculate_product_volume(product, analysis.period_start, analysis.period_end)
                frequency = self._calculate_product_frequency(product, analysis.period_start, analysis.period_end)

                # Determine ABC class based on the analysis method
                abc_class = self._determine_abc_class(product, analysis, value, volume, frequency)

                # Create analysis line
                self.env['wms.abc.analysis.line'].create({
                    'analysis_id': analysis.id,
                    'product_id': product.id,
                    'value': value,
                    'volume': volume,
                    'frequency': frequency,
                    'abc_class': abc_class,
                    'unit_cost': product.standard_price,
                })

        self.write({'status': 'completed'})
    def _calculate_product_value(self, product, start_date, end_date):
        """Calculate the value of product movement during the period"""
        # This is a simplified calculation - in a real implementation,
        # this would look at actual stock movements
        moves = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('picking_id.owner_id', '=', self.owner_id.id),
        ])
        total_value = 0.0
        for move in moves:
            total_value += move.value  # This is the accounting value of the move
        return total_value
    def _calculate_product_volume(self, product, start_date, end_date):
        """Calculate the volume of product movement during the period"""
        moves = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('picking_id.owner_id', '=', self.owner_id.id),
        ])
        total_volume = sum(moves.mapped('product_uom_qty'))
        return total_volume
    def _calculate_product_frequency(self, product, start_date, end_date):
        """Calculate the frequency of product movement during the period"""
        moves = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('picking_id.owner_id', '=', self.owner_id.id),
        ])
        return len(moves)
    def _determine_abc_class(self, product, analysis, value, volume, frequency):
        """Determine the ABC class based on rules"""
        # Default rules if no custom rules defined
        a_rules = analysis.abc_rules.filtered(lambda r: r.abc_class == 'A')
        b_rules = analysis.abc_rules.filtered(lambda r: r.abc_class == 'B')
        c_rules = analysis.abc_rules.filtered(lambda r: r.abc_class == 'C')

        # Use default thresholds if no custom rules
        if not a_rules:
            a_rules = self.env['wms.abc.rule'].search([('default_rules', '=', True), ('abc_class', '=', 'A')], limit=1)
        if not b_rules:
            b_rules = self.env['wms.abc.rule'].search([('default_rules', '=', True), ('abc_class', '=', 'B')], limit=1)
        if not c_rules:
            c_rules = self.env['wms.abc.rule'].search([('default_rules', '=', True), ('abc_class', '=', 'C')], limit=1)

        # Determine class based on method
        if analysis.analysis_method == 'value':
            # A class: top 20% by value
            # B class: next 30% by value
            # C class: remaining 50% by value
            return self._classify_by_value(product, analysis, value)
        elif analysis.analysis_method == 'volume':
            # A class: top 20% by volume
            # B class: next 30% by volume
            # C class: remaining 50% by volume
            return self._classify_by_volume(product, analysis, volume)
        elif analysis.analysis_method == 'frequency':
            # A class: top 20% by frequency
            # B class: next 30% by frequency
            # C class: remaining 50% by frequency
            return self._classify_by_frequency(product, analysis, frequency)
        else:  # combined
            # Use combined approach
            return self._classify_combined(product, analysis, value, volume, frequency)
    def _classify_by_value(self, product, analysis, value):
        """Classify product by value"""
        # This would need to compare against other products' values
        # For now, return 'C' as default
        return 'C'

    def _classify_by_volume(self, product, analysis, volume):
        """Classify product by volume"""
        # This would need to compare against other products' volumes
        # For now, return 'C' as default
        return 'C'

    def _classify_by_frequency(self, product, analysis, frequency):
        """Classify product by frequency"""
        # This would need to compare against other products' frequencies
        # For now, return 'C' as default
        return 'C'

    def _classify_combined(self, product, analysis, value, volume, frequency):
        """Classify product by combined metrics"""
        # This would use a weighted combination of all factors
        # For now, return 'C' as default
        return 'C'

    def action_archive_analysis(self):
        """Archive the analysis record"""
        self.write({'status': 'archived'})
    def action_generate_report(self):
        """Generate ABC analysis report"""
        self.ensure_one()
        return self.env.ref('wms_abc_analysis.action_report_abc_analysis').report_action(self)


class WmsAbcRule(models.Model):
    _name = 'wms.abc.rule'
    _description = 'WMS ABC Rule'

    analysis_id = fields.Many2one('wms.abc.analysis', 'Analysis', ondelete='cascade')
    abc_class = fields.Selection([
        ('A', 'A Class'),
        ('B', 'B Class'),
        ('C', 'C Class'),
    ], 'ABC Class', required=True)
    name = fields.Char('Rule Name', required=True)
    description = fields.Text('Description')
    min_value = fields.Float('Minimum Value', help='Minimum value threshold')
    max_value = fields.Float('Maximum Value', help='Maximum value threshold')
    min_volume = fields.Float('Minimum Volume', help='Minimum volume threshold')
    max_volume = fields.Float('Maximum Volume', help='Maximum volume threshold')
    min_frequency = fields.Float('Minimum Frequency', help='Minimum frequency threshold')
    max_frequency = fields.Float('Maximum Frequency', help='Maximum frequency threshold')
    percentage = fields.Float('Percentage', help='Percentage of products in this class', digits=(3, 2))
    default_rules = fields.Boolean('Default Rules', default=False)
    owner_id = fields.Many2one('wms.owner', 'Owner', related='analysis_id.owner_id', store=True)


class WmsAbcAnalysisLine(models.Model):
    _name = 'wms.abc.analysis.line'
    _description = 'WMS ABC Analysis Line'

    analysis_id = fields.Many2one('wms.abc.analysis', 'Analysis', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    value = fields.Float('Value', help='Total value of product during period')
    volume = fields.Float('Volume', help='Total quantity moved during period')
    frequency = fields.Integer('Frequency', help='Number of movements during period')
    abc_class = fields.Selection([
        ('A', 'A Class'),
        ('B', 'B Class'),
        ('C', 'C Class'),
    ], 'ABC Class', required=True)
    unit_cost = fields.Float('Unit Cost')
    total_cost = fields.Float('Total Cost', compute='_compute_total_cost', store=True)
    notes = fields.Text('Notes')
    owner_id = fields.Many2one('wms.owner', 'Owner', related='analysis_id.owner_id', store=True)

    @api.depends('volume', 'unit_cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.volume * line.unit_cost


class WmsAbcAnalysisWizard(models.TransientModel):
    _name = 'wms.abc.analysis.wizard'
    _description = 'WMS ABC Analysis Wizard'

    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    period_start = fields.Date('Period Start', required=True, default=fields.Date.today)
    period_end = fields.Date('Period End', required=True, default=fields.Date.today)
    analysis_method = fields.Selection([
        ('value', 'Value Based'),
        ('volume', 'Volume Based'),
        ('frequency', 'Frequency Based'),
        ('combined', 'Combined'),
    ], 'Analysis Method', default='combined', required=True)
    notes = fields.Text('Notes')
    def action_run_abc_analysis(self):
        """Run ABC analysis with specified parameters"""
        self.ensure_one()

        # Create the analysis record
        analysis = self.env['wms.abc.analysis'].create({
            'owner_id': self.owner_id.id,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'analysis_method': self.analysis_method,
            'notes': self.notes,
            'status': 'draft',
        })

        # Run the analysis
        analysis.action_start_analysis()
        analysis.action_run_analysis()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.abc.analysis',
            'res_id': analysis.id,
            'view_mode': 'form',
            'target': 'current',
        }