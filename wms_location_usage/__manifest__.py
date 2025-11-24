{
    'name': 'WMS Location Usage Analysis',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'Location Usage Analysis for 3PL warehouses',
    'description': '''
        Location Usage Analysis Module

        Analyze the usage of warehouse locations, including:
        - Location occupancy statistics
        - Space utilization analysis
        - Location efficiency evaluation
        - Usage trend analysis
        - Optimization recommendations and reports
    ''',
    'depends': [
        'base',
        'stock',
        'wms_owner',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/location_usage_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}