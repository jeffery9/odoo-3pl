{
    'name': 'WMS Packing Rule',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'Packing Rules for 3PL warehouses',
    'description': '''
        Packing Rules Module

        Define and manage packing rules with:
        - Box size optimization
        - Product compatibility rules
        - Weight and dimension constraints
        - Automated packing suggestions
        - Multi-parcel optimization
    ''',
    'depends': [
        'base',
        'stock',
        'wms_owner',
        'wms_value_added',  # For handling value-added services in packing
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/packing_rule_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}