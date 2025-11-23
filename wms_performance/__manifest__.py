{
    'name': 'WMS Performance Management',
    'version': '1.0',
    'category': 'Warehouse Management',
    'summary': 'Performance Management for 3PL warehouses',
    'description': '''
        Performance Management Module

        Track and analyze warehouse performance with:
        - Key Performance Indicators (KPIs)
        - Performance reports and analysis
        - Operator productivity tracking
        - Efficiency and quality metrics
        - Trend analysis and recommendations
    ''',
    'depends': [
        'base',
        'stock',
        'hr',
        'wms_owner',
        'wms_value_added',      # For performance metrics on value-added services
        'wms_wave_auto',        # For performance metrics on wave operations
        'wms_packing_rule',     # For performance metrics on packing rules
        'wms_courier',          # For performance metrics on shipping
        'wms_wcs',              # For performance metrics on WCS operations
        'wms_rfid',             # For performance metrics on RFID operations
        'wms_location_usage',   # For location performance metrics
        'wms_eiq_analysis',     # For EIQ-based performance insights
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/performance_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}