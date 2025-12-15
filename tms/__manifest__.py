{
    'name': '3PL Transportation Management System',
    'version': '1.0',
    'category': 'Operations/Transportation',
    'sequence': 10,
    'summary': 'Transportation Management System for 3PL operations',
    'description': """
        Transportation Management System (TMS) module for managing
        multi-stop delivery routes, fleet operations, and delivery tracking.

        Features:
        - Route planning and optimization
        - Multi-stop delivery management
        - Fleet and driver assignment
        - Delivery status tracking
        - Proof of delivery capture
        - Integration with Odoo's stock_fleet module
    """,
    'depends': [
        'stock',
        'stock_fleet',
        'fleet',
        'sale',
        'contacts',
        'base_geolocalize',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/route_area_views.xml',
        'views/tms_route_views.xml',
        'views/tms_route_stop_views.xml',
        'views/stock_picking_batch_views.xml',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
        'views/tms_menu.xml',
        'wizard/tms_route_stop_adjust_wizard_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}