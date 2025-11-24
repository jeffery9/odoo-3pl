{
    "name": "WMS Labor Management",
    "summary": "Track and manage labor activities, productivity, and costs in 3PL warehouses",
    "description": """
        Advanced labor management system for 3PL warehouses including:
        - Employee time tracking and attendance
        - Task assignment and work order management
        - Productivity metrics and performance tracking
        - Labor cost allocation and reporting
        - Skill-based task assignment
        - Break and shift management
        - Overtime and premium pay tracking
        - Labor analytics and dashboards
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
        "views/labor_management_views.xml",
        "views/menu_views.xml"
    ],
    "demo": [
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3"
}