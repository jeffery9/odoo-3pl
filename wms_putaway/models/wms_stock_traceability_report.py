from odoo import models, fields, api
from odoo.tools import format_datetime
from markupsafe import Markup
from collections import defaultdict
import json


class WmsStockTraceabilityReport(models.TransientModel):
    _name = 'wms.stock.traceability.report'
    _description = '3PL Traceability Report'
    _inherit = 'stock.traceability.report'  # Now inheriting from Odoo's native traceability report

    # 3PL-specific fields
    owner_id = fields.Many2one('wms.owner', 'Owner')
    abc_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')
    ], 'ABC Category')
    def get_lines(self, line_id=False, **kw):
        """Override native method to include 3PL-specific data"""
        # Call the parent method to get the standard Odoo traceability data
        lines = super().get_lines(line_id, **kw)

        # Add 3PL-specific enrichments
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        rec_id = kw and kw['model_id'] or context.get('active_id')

        # If we're filtering by owner, apply our custom filter
        if self.owner_id:
            filtered_lines = []
            for line in lines:
                # Get the actual move line to check owner
                if line.get('model') == 'stock.move.line':
                    move_line = self.env['stock.move.line'].browse(line.get('model_id'))
                    if move_line.owner_id == self.owner_id:
                        filtered_lines.append(line)
                    elif not move_line.owner_id and self.owner_id:
                        # Additional check for moves related to pickings
                        if move_line.picking_id and hasattr(move_line.picking_id, 'owner_id') and move_line.picking_id.owner_id == self.owner_id:
                            filtered_lines.append(line)
                else:
                    filtered_lines.append(line)
            lines = filtered_lines

        return lines
    def _make_dict_move(self, level, parent_id, move_line, unfoldable=False):
        """Override to include 3PL-specific data in the traceability report"""
        # Call the parent method to get the standard data
        result = super()._make_dict_move(level, parent_id, move_line, unfoldable)

        # Add 3PL-specific information to the result
        for data in result:
            data['owner_name'] = move_line.owner_id.name if move_line.owner_id else ''
            data['cargo_type'] = move_line.cargo_type_id.name if move_line.cargo_type_id else ''
            data['workzone'] = move_line.workzone_id.name if move_line.workzone_id else ''
            data['abc_category'] = move_line.abc_category or ''

        return result
    def _final_vals_to_lines(self, final_vals, level):
        """Override to include 3PL-specific columns in the final output"""
        # Call the parent method to get the standard data
        lines = super()._final_vals_to_lines(final_vals, level)

        # Add 3PL-specific columns to each line
        for line in lines:
            # Find the corresponding move_line to get 3PL data
            if line.get('model') == 'stock.move.line':
                move_line = self.env['stock.move.line'].browse(line.get('model_id'))
                line['owner_name'] = move_line.owner_id.name if move_line.owner_id else ''
                line['cargo_type'] = move_line.cargo_type_id.name if move_line.cargo_type_id else ''
                line['workzone'] = move_line.workzone_id.name if move_line.workzone_id else ''
                line['abc_category'] = move_line.abc_category or ''

                # Update columns to include 3PL-specific information
                if len(line['columns']) >= 7:  # Make sure we have enough columns
                    # Add 3PL-specific columns after the existing ones
                    line['columns'].append(line.get('owner_name', ''))
                    line['columns'].append(line.get('cargo_type', ''))
                    line['columns'].append(line.get('workzone', ''))
                    line['columns'].append(line.get('abc_category', ''))

        return lines
    def _lines(self, line_id=False, model_id=False, model=False, level=0, move_lines=None, **kw):
        """Override to include 3PL-specific filtering"""
        # Call the parent method to get the standard lines
        final_vals = super()._lines(line_id, model_id, model, level, move_lines, **kw)

        # Apply 3PL-specific filtering if needed
        if self.owner_id:
            filtered_vals = []
            for val in final_vals:
                # Get the actual move line to check owner
                if val.get('model') == 'stock.move.line':
                    move_line = self.env['stock.move.line'].browse(val.get('model_id'))
                    if move_line.owner_id == self.owner_id:
                        filtered_vals.append(val)
                    elif not move_line.owner_id and self.owner_id:
                        # Check if the picking has the owner
                        if move_line.picking_id and hasattr(move_line.picking_id, 'owner_id') and move_line.picking_id.owner_id == self.owner_id:
                            filtered_vals.append(val)
                else:
                    filtered_vals.append(val)
            final_vals = filtered_vals

        return final_vals