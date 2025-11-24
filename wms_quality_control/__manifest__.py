{
    'name': 'WMS Quality Control',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Quality control for 3PL warehouses',
    'description': '''
        Quality control for Third Party Logistics warehouses.
        Provides quality inspection, testing, and compliance tracking.
    ''',
    'depends': ['base', 'stock', 'wms_owner'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_quality_control_views.xml',
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