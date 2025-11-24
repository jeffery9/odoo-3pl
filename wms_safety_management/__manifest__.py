{
    "name": "WMS Safety Management",
    "summary": "Track and manage safety incidents, training, and compliance in 3PL warehouses",
    "description": """
        Advanced safety management system for 3PL warehouses including:
        - Safety incident tracking and reporting
        - Safety training and certification management
        - Safety inspection and audit management
        - Personal protective equipment (PPE) tracking
        - Safety compliance monitoring
        - Risk assessment and mitigation
        - Safety performance metrics
        - Safety analytics and dashboards
    """,
    "version": "18.0.1.0.0",
    "category": "Human Resources/Human Resources",
    "depends": [
        "base",
        "hr",
        "stock",
        "hr_attendance",
        "wms_owner"
    ],
    "data": [
        "data/sequence_data.xml",
        "security/ir.model.access.csv",
        "views/safety_management_views.xml",
        "views/menu_views.xml"
    ],
    "demo": [
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}