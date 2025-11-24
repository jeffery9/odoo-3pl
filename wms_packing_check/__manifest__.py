{
    'name': 'WMS Packing Check',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Packing check management for 3PL warehouses',
    'description': '''
        Packing check management for Third Party Logistics warehouses.
        Provides packing verification and quality control capabilities.
    ''',
    'depends': ['base', 'stock', 'wms_owner', 'wms_quality_control'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_packing_check_views.xml',
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