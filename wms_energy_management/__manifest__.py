{
    "name": "WMS Energy Management",
    "summary": "Track and optimize energy consumption in 3PL warehouses",
    "description": """
        Advanced energy management system for 3PL warehouses including:
        - Energy consumption monitoring and tracking
        - Equipment energy usage analysis
        - Carbon footprint calculation
        - Energy cost allocation and reporting
        - Peak demand management
        - Energy efficiency optimization
        - Renewable energy integration
        - Energy analytics and dashboards
    """,
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "depends": [
        "base",
        "stock",
        "hr",
        "wms_owner"
    ],
    "data": [
        "data/sequence_data.xml",
        "security/ir.model.access.csv",
        "views/energy_management_views.xml",
        "views/menu_views.xml"
    ],
    "demo": [
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}