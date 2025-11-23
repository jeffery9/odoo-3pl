{
    'name': 'WMS RF Blind Receive',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'RF blind receiving for 3PL warehouses',
    'description': '''
        RF blind receiving for Third Party Logistics warehouses.
        Provides blind receiving capabilities with RF scanning for verification.
    ''',
    'depends': ['base', 'stock', 'wms_owner', 'wms_quality_control'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_blind_receive_views.xml',
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