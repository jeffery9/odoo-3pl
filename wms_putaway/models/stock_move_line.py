from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Add 3PL-specific fields to stock move lines
    owner_id = fields.Many2one(
        'wms.owner',
        string='3PL Owner',
        help='Owner of the goods for multi-owner scenarios',
        compute='_compute_owner_id',
        store=True,
        readonly=False
    )
    cargo_type_id = fields.Many2one(
        'wms.cargo.type',
        string='Cargo Type',
        help='Cargo type for this line',
        compute='_compute_cargo_type',
        store=True,
        readonly=False
    )
    workzone_id = fields.Many2one(
        'wms.workzone',
        string='Work Zone',
        help='Work zone this line belongs to',
        compute='_compute_workzone',
        store=True,
        readonly=False
    )
    abc_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')
    ], 'ABC Category', help='ABC classification for the move line')

    # Lot/Serial related computed fields
    lot_expiry_date = fields.Datetime(
        'Lot Expiry Date',
        compute='_compute_lot_expiry_date',
        readonly=True,
        store=False
    )
    lot_product_qty = fields.Float('Lot Quantity', related='lot_id.product_qty', readonly=True)
    lot_ref = fields.Char('Lot Internal Reference', related='lot_id.ref', readonly=True)
    lot_note = fields.Html('Lot Description', related='lot_id.note', readonly=True)
    def _compute_lot_expiry_date(self):
        """Safely compute lot expiry date, handling cases where expiry_date field doesn't exist"""
        for line in self:
            if line.lot_id and hasattr(line.lot_id, 'expiry_date'):
                line.lot_expiry_date = line.lot_id.expiry_date
            else:
                line.lot_expiry_date = False

    @api.depends('move_id.owner_id')
    def _compute_owner_id(self):
        """Compute owner from the parent move"""
        for line in self:
            if line.move_id.owner_id:
                line.owner_id = line.move_id.owner_id
            elif not line.owner_id:
                # If no owner is set on the move, try to get from other sources
                line.owner_id = line.picking_id.owner_id if hasattr(line.picking_id, 'owner_id') else False

    @api.depends('move_id.cargo_type_id')
    def _compute_cargo_type(self):
        """Compute cargo type from the parent move"""
        for line in self:
            if line.move_id.cargo_type_id:
                line.cargo_type_id = line.move_id.cargo_type_id

    @api.depends('move_id.workzone_id')
    def _compute_workzone(self):
        """Compute work zone from the parent move"""
        for line in self:
            if line.move_id.workzone_id:
                line.workzone_id = line.move_id.workzone_id

    def _action_done(self):
        """Override to ensure proper lot handling for 3PL operations"""
        # Call the original action_done to handle quantity and location updates
        result = super()._action_done()

        # After the move is done, ensure lot information is properly updated
        for line in self:
            if line.lot_id:
                # Update lot location if needed
                if line.location_dest_id:
                    line.lot_id.location_id = line.location_dest_id

        return result
    def _create_and_assign_production_lot(self):
        """Override to handle 3PL-specific lot creation"""
        # Call the original method to create the lot
        result = super()._create_and_assign_production_lot()

        # Add 3PL-specific handling for the created lots
        for line in self:
            if line.lot_id and line.owner_id:
                # Potentially add owner-specific lot properties or notes
                # This could be enhanced further based on 3PL requirements
                pass

        return result