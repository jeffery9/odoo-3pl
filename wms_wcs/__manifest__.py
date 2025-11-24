{
    'name': 'WMS WCS Integration',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'WCS Integration for 3PL warehouses',
    'description': '''
        WCS (Warehouse Control System) Integration Module

        Integrate with warehouse control systems for automation with:
        - WCS system management
        - Device and equipment control
        - Task management and scheduling
        - Real-time monitoring and feedback
        - Integration logging and tracking
        - Status monitoring and alerts
    ''',
    'depends': [
        'base',
        'stock',
        'wms_owner',
        'wms_value_added',    # For WCS automation of value-added services
        'wms_wave_auto',      # For WCS coordination with wave operations
        'wms_location_usage', # For WCS optimization based on location usage
        'wms_rfid',           # For WCS coordination with RFID tracking
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wcs_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}