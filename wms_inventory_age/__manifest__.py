{
    'name': 'WMS Inventory Age Analysis',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Inventory aging analysis for 3PL warehouses',
    'description': '''
        Inventory aging analysis for Third Party Logistics warehouses.
        Provides inventory age tracking and aging reports for inventory management.
    ''',
    'depends': ['base', 'stock', 'wms_owner'],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_inventory_age_views.xml',
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