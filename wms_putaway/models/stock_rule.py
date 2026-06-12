from odoo import models, fields


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # Add 3PL-specific fields to enhance stock rules
    owner_id = fields.Many2one(
        'wms.owner',
        string='3PL Owner',
        help='Specific owner this rule applies to in multi-owner scenarios'
    )
    cargo_type_id = fields.Many2one(
        'wms.cargo.type',
        string='Cargo Type',
        help='Cargo type restriction for this rule'
    )
    workzone_id = fields.Many2one(
        'wms.workzone',
        string='Work Zone',
        help='Work zone this rule applies to'
    )
    storage_category_id = fields.Many2one(
        'stock.storage.category',
        string='Storage Category',
        help='Restrict rule based on storage category'
    )
    abc_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')
    ], 'ABC Category', help='ABC classification for the rule')
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        """Extend the stock move values to include 3PL-specific fields"""
        move_values = super()._get_stock_move_values(
            product_id, product_qty, product_uom, location_dest_id, name,
            origin, company_id, values
        )

        # Add 3PL-specific values from the rule if available
        if self.owner_id:
            move_values['owner_id'] = self.owner_id.id
        if self.cargo_type_id:
            move_values['cargo_type_id'] = self.cargo_type_id.id
        if self.workzone_id:
            move_values['workzone_id'] = self.workzone_id.id

        return move_values