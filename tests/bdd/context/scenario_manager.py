# Shared Context Manager for all BDD Scenarios

# File Path: tests/bdd/context/scenario_manager.py

class ScenarioManager:
    """Manages state (user, records) across a single Gherkin scenario run."""
    def __init__(self):
        # State variables initialized at the start of each scenario
        self.current_user = None
        self.facility_location = None
        self.manifest_records = {} # {Manifest ID: {status, created_by}}
        self.active_orders = {}    # {SO-ID: [items]}
    def set_user(self, user):
        """Sets the authenticated user for the current scenario."""
        self.current_user = user

    def set_facility(self, location):
        """Records the active facility location context."""
        self.facility_location = location

    # Utility methods to simulate database/API interactions for state persistence
    def create_record(self, model, data):
        """Simulates creation of a record and returns its unique ID."""
        # In real life: this would call Odoo's ORM or API client directly.
        print(f"[MockDB] Created {model} record with data: {data}. Returning fake ID.")
        return f"REC-{hash(str(data)) % 1000}"

    def get_stock_status(self, sku):
        """Returns mock stock level for a given SKU."""
        if "XYZ" in sku: return {"available": 10}
        if "ABC" in sku: return {"available": 5}
        return {"available": None}

    # Add methods for tracking manifests, orders, etc. as needed by specific modules.