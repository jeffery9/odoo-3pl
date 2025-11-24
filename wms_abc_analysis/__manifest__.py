{
    'name': 'WMS ABC Analysis',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'ABC analysis for 3PL warehouses',
    'description': '''
        ABC analysis for Third Party Logistics warehouses.
        Provides ABC classification based on usage value and frequency.
    ''',
    'depends': ['base', 'stock', 'wms_owner', 'wms_putaway'],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/wms_abc_analysis_views.xml',
        'views/stock_product_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}