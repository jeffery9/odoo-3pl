{
    'name': 'WMS Crossdock Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Crossdock management for 3PL warehouses',
    'description': '''
        Crossdock management for Third Party Logistics warehouses.
        Provides intelligent matching of inbound and outbound orders.
    ''',
    'depends': ['base', 'stock', 'wms_owner'],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_crossdock_operation_views.xml',
        'views/wms_crossdock_match_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}