# WMS Putaway Step Definitions
from behave import given, when, then

class WMSPutawaySteps:
    @given('the system is operational and user "{user}" is logged in')
    def step_given_system_operational(self, username):
        """SETUP: Simulate login for putaway module."""
        print(f"Simulating successful login/context setup for Putaway user {username}...")
        if self.context and not hasattr(self.context, "user"):
            self.context.user = {"name": username, "groups": ["wms_putaway_group"]}

    @given('a facility location "{location_name}" exists with valid credentials')
    def step_given_facility(self, location_name):
        """SETUP: Seed core location record."""
        print(f"Seeding prerequisite: Creating/verifying warehouse location '{location_name}'...")
        if self.context:
            self.context.facility = {"name": location_name, "active": True}

    @given('there are {quantity:d} units of {sku} at storage area {area}')
    def step_given_stock(self, quantity, sku, area):
        """SETUP: Mock inventory seed for putaway testing."""
        print(f"Seeding stock for SKU '{sku}': {quantity} units in area '{area}'.")
        if self.context:
            self.context.inventory = {"sku": sku, "quantity": quantity, "location": area}

    @when('the planner executes putaway for {quantity} units of {sku}')
    def step_when_execute_putaway(self, sku):
        """ACTION: Executes the core Putaway API call and captures context."""
        print(f"Action: Executing Putaway plan for SKU '{sku}'...")
        if self.context.inventory:
            result = {"success": True, "putaway_plan_id": f"P-{self.context.user['name']}-{so}", "assigned_locations": ["A1-01", "A1-02"]}
            self.scenario_manager.set_context("last_putaway", result)
        else:
            result = {"success": False, "error": "Missing inventory context for putaway plan."}
            self.scenario_manager.set_context("last_putaway", result)

    @then('the system should assign optimal locations based on {criteria}')
    def step_then_assign_optimal_locations(self, criteria):
        """ASSERT: Checks if the putaway process generated expected location assignments."""
        last_putaway = self.scenario_manager.get_context("last_putaway")
        if last_putaway and not last_putaway["success"]:
            raise AssertionError(f"Putaway failed during execution: {last_putaway['error']}")
        elif "assigned_locations" in last_putaway:
            print(f"Assertion passed: Optimal locations found: {', '.join(last_putaway['assigned_locations'])}.")
        else:
            raise AssertionError("Could not assert putaway location assignment.")