{
    "name": "WMS Finance Integration",
    "summary": "Integrate warehouse operations with financial systems and accounting",
    "description": """
        Advanced finance integration system for 3PL warehouses including:
        - Automated financial posting for warehouse transactions
        - Cost allocation and tracking for storage and handling
        - Revenue recognition for warehouse services
        - Financial reporting and analytics
        - Integration with accounting systems
        - Cost center management
        - Financial compliance and audit trails
        - Multi-currency support
    """,
    "version": "17.0.1.0.0",
    "category": "Accounting/Accounting",
    "depends": [
        "base",
        "stock",
        "account",
        "sale",
        "purchase",
        "wms_owner",
        "wms_billing"
    ],
    "data": [
        "data/sequence_data.xml",
        "security/ir.model.access.csv",
        "views/finance_integration_views.xml",
        "views/menu_views.xml"
    ],
    "demo": [
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}