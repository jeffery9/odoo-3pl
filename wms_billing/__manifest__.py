{
    'name': 'WMS Billing Management',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'Billing management for 3PL warehouses',
    'description': '''
        Billing management for Third Party Logistics warehouses.
        Provides automated billing, invoice generation, and payment tracking.
    ''',
    'depends': ['base', 'stock', 'account', 'wms_owner', 'wms_quality_control'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/wms_billing_rule_views.xml',
        'views/wms_billing_record_views.xml',
        'views/wms_invoice_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}