from odoo import models, fields, api


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    # Add 3PL-specific fields to procurement group
    owner_id = fields.Many2one(
        'wms.owner',
        string='3PL Owner',
        help='Owner for this procurement group in multi-owner scenarios'
    )
    def _get_rule(self, product_id, location_id, values):
        """Enhanced rule selection with 3PL-specific filtering"""
        # First try to get the original rule
        rule = super()._get_rule(product_id, location_id, values)

        # Apply 3PL-specific filtering if owner is specified in values
        owner_id = values.get('owner_id')
        if owner_id:
            # Search for rules that match the specific owner
            domain = self._get_rule_domain(location_id, values)
            domain.append(('owner_id', '=', owner_id))

            location = location_id
            # Get the location hierarchy, starting from location_id up to its root location.
            locations = location_id
            while locations[-1].location_id:
                locations |= locations[-1].location_id

            # Updated search with 3PL-specific filters
            rule = self.env['stock.rule'].search([
                ('location_dest_id', 'in', locations.ids),
                ('action', '!=', 'push'),
                ('owner_id', '=', owner_id),
                ('active', '=', True),
                '|', ('company_id', '=', False), ('company_id', 'child_of', values.get('company_id', self.env.company).id)
            ], order='route_sequence, sequence', limit=1)

        return rule
    def _get_rule_domain(self, locations, values):
        """Enhanced rule domain with 3PL-specific filters"""
        domain = super()._get_rule_domain(locations, values)

        # Add 3PL-specific filters from values if they exist
        owner_id = values.get('owner_id')
        if owner_id:
            domain = ['&', ('owner_id', '=', owner_id)] + domain

        return domain