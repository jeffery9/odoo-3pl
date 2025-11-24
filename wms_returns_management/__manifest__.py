{
    "name": "WMS Returns Management",
    "summary": "Manage return merchandise authorization (RMA) and returns processing for 3PL warehouses",
    "description": """
        Advanced returns management system for 3PL warehouses including:
        - Return Merchandise Authorization (RMA) processing
        - Return reason tracking and categorization
        - Refund and credit management
        - Returns inventory management
        - Returns quality control and disposition
        - Customer return communication
        - Returns analytics and reporting
    """,
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "depends": [
        "base",
        "stock",
        "sale",
        "purchase",
        "wms_owner",
        "wms_quality_control"
    ],
    "data": [
        "data/sequence_data.xml",
        "security/ir.model.access.csv",
        "views/returns_management_views.xml",
        "views/menu_views.xml"
    ],
    "demo": [
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}