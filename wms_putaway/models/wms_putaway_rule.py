from odoo import models, fields, api


class WmsPutawayRule(models.Model):
    _name = 'wms.putaway.rule'
    _description = 'WMS Putaway Rule'

    name = fields.Char('Rule Name', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner',
                               domain=[('is_warehouse_owner', '=', True)])
    product_id = fields.Many2one('product.product', 'Product')
    product_category_id = fields.Many2one('product.category', 'Product Category')
    abc_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')
    ], 'ABC Category')
    location_in_id = fields.Many2one('stock.location', 'Apply In', required=True)
    location_out_id = fields.Many2one('stock.location', 'Put Into', required=True)
    max_capacity = fields.Float('Max Capacity')
    priority = fields.Integer('Priority', default=10)
    active = fields.Boolean('Active', default=True)
    storage_category_id = fields.Many2one(
        'stock.storage.category', 'Storage Category', check_company=True,
        help="Native Odoo 18 storage category for enhanced putaway logic"
    )
    def _get_putaway_strategy(self, product, quantity, location, package=None, from_move_id=None, lot=None):
        """Enhanced to include native Odoo storage categories with 3PL-specific logic and lot tracking"""

        # First try to find a specific rule for the owner with storage category
        if self.env.context.get('current_owner_id'):
            owner_id = self.env.context.get('current_owner_id')
            domain = [
                ('owner_id', '=', owner_id),
                '|',
                ('product_id', '=', product.id),
                ('product_category_id', '=', product.categ_id.id),
                ('location_in_id', 'child_of', location.id),
                ('active', '=', True)
            ]
            rules = self.search(domain, order='priority desc')
            for rule in rules:
                # Check if the destination location has storage category restrictions
                if rule.storage_category_id:
                    # Use native Odoo logic to check storage category compatibility
                    if self._is_storage_category_compatible(
                        rule.location_out_id, product, quantity, package, rule.storage_category_id
                    ):
                        # Additional check for lot compatibility if lot is provided
                        if lot and rule._check_lot_compatibility(lot, rule.location_out_id):
                            return rule.location_out_id
                        elif not lot:
                            return rule.location_out_id
                else:
                    # Use original logic for backward compatibility
                    if self._location_has_capacity(rule.location_out_id, product, quantity, rule.max_capacity):
                        # Additional check for lot compatibility if lot is provided
                        if lot and rule._check_lot_compatibility(lot, rule.location_out_id):
                            return rule.location_out_id
                        elif not lot:
                            return rule.location_out_id

        # Then try general rules with storage categories
        domain = [
            ('owner_id', '=', False),
            '|',
            ('product_id', '=', product.id),
            ('product_category_id', '=', product.categ_id.id),
            ('location_in_id', 'child_of', location.id),
            ('active', '=', True)
        ]
        rules = self.search(domain, order='priority desc')
        for rule in rules:
            if rule.storage_category_id:
                if self._is_storage_category_compatible(
                    rule.location_out_id, product, quantity, package, rule.storage_category_id
                ):
                    # Additional check for lot compatibility if lot is provided
                    if lot and rule._check_lot_compatibility(lot, rule.location_out_id):
                        return rule.location_out_id
                    elif not lot:
                        return rule.location_out_id
            else:
                if self._location_has_capacity(rule.location_out_id, product, quantity, rule.max_capacity):
                    # Additional check for lot compatibility if lot is provided
                    if lot and rule._check_lot_compatibility(lot, rule.location_out_id):
                        return rule.location_out_id
                    elif not lot:
                        return rule.location_out_id

        return False
    def _check_lot_compatibility(self, lot, location):
        """Check if a specific lot is compatible with this location considering 3PL requirements"""
        # Check if lot belongs to the same owner as the location (if owner is specified)
        if self.owner_id and lot.owner_id and self.owner_id != lot.owner_id:
            return False

        # Check other lot compatibility rules
        # For example, expiry date checking
        if lot.expiry_date and lot.expiry_date < fields.Datetime.now():
            return False

        # Check if location can accommodate this specific lot
        return True
    def _is_storage_category_compatible(self, location, product, quantity, package, storage_category):
        """Check if location with storage category can accept the product/package"""
        # Check max weight if applicable
        if storage_category.max_weight > 0:
            forecast_weight = location._get_weight(self.env.context.get('exclude_sml_ids', set()))[location]['forecast_weight']
            product_weight = product.weight
            if package and package.package_type_id:
                # For packages, get total weight of packages in location
                package_smls = self.env['stock.move.line'].search([
                    ('result_package_id', '=', package.id),
                    ('state', 'not in', ['done', 'cancel'])
                ])
                total_weight = forecast_weight + sum(
                    sml.quantity_product_uom * sml.product_id.weight for sml in package_smls
                )
            else:
                total_weight = forecast_weight + (product.weight * quantity)

            if total_weight > storage_category.max_weight:
                return False

        # Check product/package capacity if set
        if package and storage_category.package_capacity_ids:
            package_capacity = storage_category.package_capacity_ids.filtered(
                lambda pc: pc.package_type_id == package.package_type_id
            )
            if package_capacity:
                current_count = len(location.quant_ids.filtered(
                    lambda q: q.package_id and q.package_id.package_type_id == package.package_type_id
                ))
                if current_count >= package_capacity.quantity:
                    return False
        elif storage_category.product_capacity_ids:
            product_capacity = storage_category.product_capacity_ids.filtered(
                lambda pc: pc.product_id == product
            )
            if product_capacity:
                current_qty = sum(location.quant_ids.filtered(
                    lambda q: q.product_id == product
                ).mapped('quantity'))
                if current_qty >= product_capacity.quantity:
                    return False

        # Check product mixing policy
        if storage_category.allow_new_product == 'empty':
            if location.quant_ids.filtered(lambda q: q.quantity > 0):
                return False
        elif storage_category.allow_new_product == 'same':
            existing_products = location.quant_ids.filtered(lambda q: q.quantity > 0).mapped('product_id')
            if existing_products and product not in existing_products:
                return False

        return True
    def _location_has_capacity(self, location, product, quantity, max_capacity):
        """Check if location has capacity based on custom max_capacity field"""
        if max_capacity and max_capacity > 0:
            # Check current capacity usage for this location
            current_quants = self.env['stock.quant'].search([
                ('location_id', '=', location.id),
                ('product_id', '!=', product.id)  # Different from the product we're checking
            ])
            current_count = sum(quant.quantity for quant in current_quants)
            return (current_count + 1) <= max_capacity  # Simplified capacity check
        return True