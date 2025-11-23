{
    'name': 'WMS Handover Management',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'Handover management for 3PL warehouses',
    'description': '''
        Handover management for Third Party Logistics warehouses.
        Provides handover tracking and sign-off capabilities.
    ''',
    'depends': ['base', 'stock', 'wms_owner', 'wms_quality_control'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_handover_views.xml',
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