# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TmsRouteStopAdjustWizard(models.TransientModel):
    _name = 'tms.route.stop.adjust.wizard'
    _description = 'TMS Route Stop Adjustment Wizard'

    stop_id = fields.Many2one(
        'tms.route.stop',
        string='Route Stop',
        required=True
    )
    adjustment_reason = fields.Selection([
        ('traffic', 'Traffic Conditions'),
        ('weather', 'Weather Conditions'),
        ('customer', 'Customer Request'),
        ('vehicle', 'Vehicle Issue'),
        ('other', 'Other Reason')
    ], string='Adjustment Reason', required=True)
    new_sequence = fields.Integer(
        string='New Sequence'
    )
    new_time_window_start = fields.Datetime(
        string='New Time Window Start'
    )
    new_time_window_end = fields.Datetime(
        string='New Time Window End'
    )

    @api.model
    def default_get(self, fields):
        res = super(TmsRouteStopAdjustWizard, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'tms.route.stop':
            res['stop_id'] = self.env.context.get('active_id')
        return res

    def action_adjust_stop(self):
        self.ensure_one()
        if self.stop_id:
            self.stop_id.with_context(
                default_reason=self.adjustment_reason,
                default_sequence=self.new_sequence,
                default_time_window_start=self.new_time_window_start,
                default_time_window_end=self.new_time_window_end
            ).action_adjust_stop()
        return {'type': 'ir.actions.act_window_close'}