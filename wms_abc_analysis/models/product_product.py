from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    abc_classification = fields.Selection([
        ('A', 'A Class'),
        ('B', 'B Class'),
        ('C', 'C Class'),
    ], 'ABC Classification', help='ABC classification based on usage value and frequency')
    abc_last_analysis_date = fields.Datetime('Last ABC Analysis Date')
    annual_usage_value = fields.Float('Annual Usage Value', help='Total value of product usage in the last year')
    annual_usage_volume = fields.Float('Annual Usage Volume', help='Total quantity of product usage in the last year')
    usage_frequency = fields.Integer('Usage Frequency', help='Number of times product was used in the last year')
    def action_run_abc_analysis(self):
        """Run ABC analysis for this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wms.abc.analysis.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_product_ids': [(6, 0, self.ids)]}
        }