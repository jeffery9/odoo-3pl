{
    'name': 'WMS WeChat Integration',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'WeChat Integration for 3PL warehouses',
    'description': '''
        WeChat Integration Module

        Integrate with WeChat Mini Programs for warehouse operations with:
        - WeChat app configuration and management
        - User registration and authentication
        - Inventory checking through mobile app
        - Picking notifications and updates
        - Location search and navigation
        - Real-time communication with warehouse staff
    ''',
    'depends': [
        'base',
        'stock',
        'hr',
        'wms_owner',
        'wms_value_added',    # For WeChat interface for value-added services
        'wms_wave_auto',      # For WeChat notifications about wave operations
        'wms_packing_rule',   # For WeChat in packing operations
        'wms_rfid',           # For WeChat integration with RFID operations
        'wms_courier',        # For WeChat notifications about shipping
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wechat_views.xml',
    ],
    'controllers': [
        'controllers',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}