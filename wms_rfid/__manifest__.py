{
    'name': 'WMS RFID Integration',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'RFID Integration for 3PL warehouses',
    'description': '''
        RFID Integration Module

        Integrate RFID technology for warehouse operations with:
        - RFID tag management
        - RFID reader configuration
        - Transaction logging and tracking
        - RFID-based inventory processes
        - Real-time tracking and monitoring
        - Security and access control features
    ''',
    'depends': [
        'base',
        'stock',
        'hr',
        'wms_owner',
        'wms_value_added',  # For RFID tracking of value-added services
        'wms_wave_auto',    # For RFID in wave operations
        'wms_packing_rule', # For RFID in packing operations
        'maintenance',      # For equipment tracking
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/rfid_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}