{
    "name": "WMS Document Management",
    "summary": "Manage documents, files, and records in 3PL warehouses",
    "description": """
        Advanced document management system for 3PL warehouses including:
        - Document upload and storage with versioning
        - Document categorization and tagging
        - Document search and retrieval
        - Document approval workflows
        - Document retention and archival
        - Document access control and permissions
        - Integration with warehouse operations
        - Document analytics and reporting
    """,
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "depends": [
        "base",
        "stock",
        "document",
        "wms_owner",
        "wms_quality_control",
        "wms_returns_management"
    ],
    "data": [
        "data/sequence_data.xml",
        "security/ir.model.access.csv",
        "views/document_management_views.xml",
        "views/menu_views.xml"
    ],
    "demo": [
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}