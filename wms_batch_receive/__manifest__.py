{
    'name': 'WMS Batch Receive',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'Batch receiving for 3PL warehouses',
    'description': '''
        Batch receiving for Third Party Logistics warehouses.
        Provides batch receiving capabilities for multiple orders simultaneously.
    ''',
    'depends': ['base', 'stock', 'wms_owner', 'wms_quality_control'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_batch_receive_views.xml',
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