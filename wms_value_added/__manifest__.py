{
    'name': 'WMS Value Added Services',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'Value Added Services for 3PL warehouses',
    'description': '''
        Value Added Services Module

        Manage value added services performed on products in the warehouse with:
        - Service definitions and pricing
        - Operation tracking and scheduling
        - Quality control and compliance checks
        - Performance metrics and reporting
        - Resource planning and allocation
    ''',
    'depends': [
        'base',
        'stock',
        'hr',
        'wms_owner',
        'wms_quality_control',  # For quality checks
        'mrp',  # For BOM and manufacturing operations
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/value_added_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}