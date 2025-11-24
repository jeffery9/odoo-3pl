{
    'name': 'WMS Wave Auto',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Automated Wave Generation for 3PL warehouses',
    'description': '''
        Automated Wave Generation Module

        Generate picking waves automatically based on various criteria with:
        - Rule-based wave generation
        - Priority management
        - Time slot optimization
        - Resource allocation
        - Performance tracking
    ''',
    'depends': [
        'base',
        'stock',
        'wms_owner',
        'wms_location_usage',  # For location optimization in wave planning
        'wms_eiq_analysis',    # For EIQ analysis to optimize wave generation
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wave_auto_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}