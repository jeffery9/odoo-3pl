{
    'name': 'WMS EIQ Analysis',
    'version': '18.0.1.0.0',
    'category': 'Warehouse Management',
    'summary': 'EIQ Analysis - Entry-Item-Quantity Analysis for 3PL warehouses',
    'description': '''
        EIQ Analysis Module - Entry-Item-Quantity Analysis

        Perform Entry-Item-Quantity analysis for:
        - Warehouse layout optimization
        - Picking path design
        - Storage location allocation strategies
        - Operation process improvement
        - ABC analysis integration
    ''',
    'depends': [
        'base',
        'stock',
        'wms_owner',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/eiq_analysis_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}