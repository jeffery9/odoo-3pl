# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Add route relationship to individual pickings
    route_id = fields.Many2one(
        'tms.route',
        string='Route',
        compute='_compute_route_id',
        store=True,
        help='Route that this picking is assigned to'
    )
    route_stop_id = fields.Many2one(
        'tms.route.stop',
        string='Route Stop',
        compute='_compute_route_stop_id',
        store=True,
        help='Specific stop on the route for this picking'
    )

    @api.depends('batch_id', 'batch_id.tms_route_ids')
    def _compute_route_id(self):
        """Compute route based on the batch's route"""
        for picking in self:
            route = False
            if picking.batch_id:
                # Get the active route for this batch if any
                active_routes = picking.batch_id.tms_route_ids.filtered(
                    lambda r: r.state in ['draft', 'confirmed', 'in_transit']
                )
                if active_routes:
                    route = active_routes[0]  # Take the first active route
            picking.route_id = route

    @api.depends('route_id', 'partner_id', 'route_id.stop_ids')
    def _compute_route_stop_id(self):
        """Compute the specific stop on the route for this picking"""
        for picking in self:
            stop = False
            if picking.route_id and picking.partner_id:
                # Find the stop in the route that has this picking
                stops = picking.route_id.stop_ids.filtered(
                    lambda s: picking.id in s.picking_ids.ids
                )
                if stops:
                    stop = stops[0]  # Take the first matching stop
            picking.route_stop_id = stop

    def action_view_route(self):
        """Action to view the route associated with this picking"""
        self.ensure_one()
        if self.route_id:
            return {
                'name': _('Route'),
                'type': 'ir.actions.act_window',
                'res_model': 'tms.route',
                'view_mode': 'form',
                'res_id': self.route_id.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Route'),
                    'message': _('This picking is not assigned to any route yet.'),
                    'type': 'info',
                    'sticky': False,
                }
            }