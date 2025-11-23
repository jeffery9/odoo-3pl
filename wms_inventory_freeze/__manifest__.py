{
    'name': 'WMS Inventory Freeze',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'Inventory freeze management for 3PL warehouses',
    'description': '''
        Inventory freeze management for Third Party Logistics warehouses.
        Provides inventory freezing capabilities for quality control and investigations.
    ''',
    'depends': ['base', 'stock', 'wms_owner', 'wms_quality_control'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_inventory_freeze_views.xml',
        'views/stock_quant_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}