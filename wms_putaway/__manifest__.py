{
    'name': 'WMS Putaway Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Enhanced putaway rules for 3PL warehouses',
    'description': '''
        Enhanced putaway rules for Third Party Logistics warehouses.
        Provides advanced putaway strategies based on owner, ABC classification, and capacity.
    ''',
    'depends': ['base', 'stock', 'wms_owner'],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_putaway_rule_views.xml',
        'views/wms_storage_area_views.xml',
        'views/wms_cargo_type_views.xml',
        'views/wms_workzone_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}