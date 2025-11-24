{
    'name': 'WMS RF Container Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'RF container management for 3PL warehouses',
    'description': '''
        RF container management for Third Party Logistics warehouses.
        Provides barcode/RFID scanning capabilities for container tracking.
    ''',
    'depends': ['base', 'stock', 'wms_owner'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_container_views.xml',
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