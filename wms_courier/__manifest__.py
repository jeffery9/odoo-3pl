{
    'name': 'WMS Courier Integration',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Courier Integration for 3PL warehouses',
    'description': '''
        Courier Integration Module

        Integrate with courier companies for shipping with:
        - Courier company management
        - Shipping service definitions
        - Shipment order tracking
        - API integration capabilities
        - Label printing and tracking
        - Cost calculation and reporting
    ''',
    'depends': [
        'base',
        'stock',
        'sale',
        'wms_owner',
        'wms_value_added',  # For shipping value-added service results
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/courier_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}