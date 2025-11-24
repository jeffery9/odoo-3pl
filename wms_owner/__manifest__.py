{
    'name': 'WMS Owner Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Multi-owner management for 3PL warehouses',
    'description': """
        Multi-owner management for Third Party Logistics warehouses.
        Provides enhanced owner management, billing rules, and data isolation.
    """,
    'depends': ['base', 'stock', 'account'],
    'data': [
        'security/wms_owner_security.xml',
        'security/ir.model.access.csv',
        'views/wms_owner_views.xml',
        'views/wms_billing_rule_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}