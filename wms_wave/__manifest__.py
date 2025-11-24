{
    'name': 'WMS Wave Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Wave picking management for 3PL warehouses',
    'description': '''
        Wave picking management for Third Party Logistics warehouses.
        Provides automated wave generation, optimization, and multi-user picking.
    ''',
    'depends': ['base', 'stock', 'stock_picking_batch', 'wms_owner'],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_wave_rule_views.xml',
        'views/wms_picking_batch_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}