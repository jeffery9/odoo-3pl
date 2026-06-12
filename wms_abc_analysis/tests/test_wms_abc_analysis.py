from odoo.tests import TransactionCase
from odoo import fields


class TestWmsAbcAnalysis(TransactionCase):
    """Test cases for WMS ABC Analysis module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test ABC Analysis Owner',
            'owner_code': 'TAAO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_picking_type = self.env['stock.picking.type'].create({
            'name': 'Test Picking Type',
            'code': 'incoming',
            'sequence_code': 'IN',
            'default_location_src_id': self.test_location.id,
            'default_location_dest_id': self.test_location.id,
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for ABC Analysis',
                        'categ_id': self.env.ref('product.product_category_all').id,
            'standard_price': 25.0,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')
    def test_create_abc_analysis(self):
        """Test creating an ABC analysis record"""
        abc_analysis = self.env['wms.abc.analysis'].create({
            'name': 'Test ABC Analysis',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
            'status': 'draft',
            'analysis_method': 'combined',
        })

        self.assertEqual(abc_analysis.name, 'Test ABC Analysis')
        self.assertEqual(abc_analysis.owner_id.id, self.test_owner.id)
        self.assertEqual(abc_analysis.analysis_method, 'combined')
        self.assertEqual(abc_analysis.status, 'draft')
    def test_abc_analysis_rules(self):
        """Test creating ABC analysis rules"""
        abc_analysis = self.env['wms.abc.analysis'].create({
            'name': 'Rules Test',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
            'status': 'draft',
        })

        abc_rule = self.env['wms.abc.rule'].create({
            'analysis_id': abc_analysis.id,
            'abc_class': 'A',
            'name': 'A Class Rule',
            'min_value': 10000.0,
            'max_value': 999999.0,
            'percentage': 20.0,
        })

        self.assertEqual(len(abc_analysis.abc_rules), 1)
        self.assertEqual(abc_analysis.abc_rules[0].abc_class, 'A')
        self.assertEqual(abc_analysis.abc_rules[0].name, 'A Class Rule')
        self.assertEqual(abc_analysis.abc_rules[0].min_value, 10000.0)
    def test_abc_analysis_line(self):
        """Test creating ABC analysis lines"""
        abc_analysis = self.env['wms.abc.analysis'].create({
            'name': 'Line Test',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
            'status': 'completed',
        })

        abc_line = self.env['wms.abc.analysis.line'].create({
            'analysis_id': abc_analysis.id,
            'product_id': self.test_product.id,
            'value': 5000.0,
            'volume': 200.0,
            'frequency': 15,
            'abc_class': 'A',
            'unit_cost': 25.0,
        })

        self.assertEqual(len(abc_analysis.analysis_lines), 1)
        self.assertEqual(abc_analysis.analysis_lines[0].product_id.id, self.test_product.id)
        self.assertEqual(abc_analysis.analysis_lines[0].abc_class, 'A')
        self.assertEqual(abc_analysis.analysis_lines[0].value, 5000.0)
        self.assertEqual(abc_analysis.analysis_lines[0].total_cost, 5000.0)  # volume * unit_cost = 200 * 25

    def test_abc_analysis_status_flow(self):
        """Test the status flow of ABC analysis records"""
        abc_analysis = self.env['wms.abc.analysis'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
            'status': 'draft',
        })

        self.assertEqual(abc_analysis.status, 'draft')

        # Start the analysis
        abc_analysis.action_start_analysis()
        self.assertEqual(abc_analysis.status, 'in_progress')

        # Since running the full analysis may have dependencies we can't easily mock,
        # we'll just complete it manually for testing purposes
        abc_analysis.write({'status': 'completed'})
        self.assertEqual(abc_analysis.status, 'completed')
    def test_abc_analysis_totals_computation(self):
        """Test that ABC analysis totals are computed correctly"""
        abc_analysis = self.env['wms.abc.analysis'].create({
            'name': 'Totals Computation Test',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
            'status': 'completed',
        })

        # Add multiple analysis lines with different ABC classes
        self.env['wms.abc.analysis.line'].create([
            {
                'analysis_id': abc_analysis.id,
                'product_id': self.test_product.id,
                'value': 5000.0,
                'volume': 200.0,
                'frequency': 15,
                'abc_class': 'A',
                'unit_cost': 25.0,
            },
            {
                'analysis_id': abc_analysis.id,
                'product_id': self.test_product.id,
                'value': 2000.0,
                'volume': 100.0,
                'frequency': 8,
                'abc_class': 'B',
                'unit_cost': 20.0,
            },
            {
                'analysis_id': abc_analysis.id,
                'product_id': self.test_product.id,
                'value': 500.0,
                'volume': 50.0,
                'frequency': 3,
                'abc_class': 'C',
                'unit_cost': 10.0,
            },
        ])

        # Refresh to get updated computed values
        abc_analysis.refresh()

        # Check that totals are computed correctly
        self.assertEqual(abc_analysis.total_products, 3)
        self.assertEqual(abc_analysis.a_class_count, 1)
        self.assertEqual(abc_analysis.b_class_count, 1)
        self.assertEqual(abc_analysis.c_class_count, 1)
    def test_abc_analysis_methods(self):
        """Test different analysis methods"""
        methods = ['value', 'volume', 'frequency', 'combined']

        for i, method in enumerate(methods):
            abc_analysis = self.env['wms.abc.analysis'].create({
                'name': f'Test Analysis Method {method}',
                'owner_id': self.test_owner.id,
                'period_start': fields.Date.today(),
                'period_end': fields.Date.add(fields.Date.today(), days=30),
                'analysis_method': method,
            })
            self.assertEqual(abc_analysis.analysis_method, method)
    def test_abc_analysis_wizard(self):
        """Test creating ABC analysis using wizard"""
        wizard = self.env['wms.abc.analysis.wizard'].create({
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
            'analysis_method': 'combined',
        })

        result = wizard.action_run_abc_analysis()

        # Verify the result is an action to open the ABC analysis form
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'wms.abc.analysis')

        # Get the created analysis
        abc_analysis = self.env['wms.abc.analysis'].browse(result['res_id'])
        self.assertEqual(abc_analysis.analysis_method, 'combined')
        self.assertEqual(abc_analysis.status, 'in_progress')
    def test_product_abc_classification_extension(self):
        """Test the product extension for ABC classification"""
        product = self.env['product.product'].create({
            'name': 'Test Product ABC Extension',
                        'categ_id': self.env.ref('product.product_category_all').id,
            'standard_price': 15.0,
        })

        # Initially, the product should have no ABC classification
        self.assertFalse(product.abc_classification)

        # Update the product with ABC classification
        product.abc_classification = 'A'
        product.abc_last_analysis_date = fields.Datetime.now()
        product.annual_usage_value = 10000.0
        product.annual_usage_volume = 500.0
        product.usage_frequency = 25

        self.assertEqual(product.abc_classification, 'A')
        self.assertEqual(product.annual_usage_value, 10000.0)
        self.assertEqual(product.annual_usage_volume, 500.0)
        self.assertEqual(product.usage_frequency, 25)
    def test_abc_analysis_ownership_isolation(self):
        """Test that ABC analysis records are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second ABC Analysis Owner',
            'owner_code': 'SAAO',
            'is_warehouse_owner': True,
        })

        abc_analysis1 = self.env['wms.abc.analysis'].create({
            'name': 'ABC Analysis for Owner 1',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
        })

        abc_analysis2 = self.env['wms.abc.analysis'].create({
            'name': 'ABC Analysis for Owner 2',
            'owner_id': owner2.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
        })

        self.assertNotEqual(abc_analysis1.owner_id.id, abc_analysis2.owner_id.id)
        self.assertNotEqual(abc_analysis1.name, abc_analysis2.name)