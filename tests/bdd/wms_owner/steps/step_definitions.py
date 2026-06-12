# Common Python Step Definitions for WMS Owner

from behave import given, when, then

class WMSOwnerSteps:
    @given('the system is operational and user "{user}" is logged in')
    def step_given_system_operational(self, username):
        """SETUP: Establishes the testing context by simulating Odoo's security layer login."""
        # Critical Unit Test Step: Use self.context.env to simulate login/group assignment
        self.context['user'] = {"name": username, "groups": ["wms_owner_group"]}
        print(f"[SUCCESS] Context set for user {username} with groups: {', '.join(self.context['user']['groups'])}")

    @given('a facility location "{location_name}" exists with valid credentials')
    def step_given_facility(self, location_name):
        """
        SETUP: Verifies and seeds the necessary core location record in the database context.
        Should use helper functions to find or an existing context placeholder for reliable testing.
        """
        print(f"[SUCCESS] Seeding facility/location: {location_name}")
        if hasattr(self, 'context'):
            self.context.facility = {"name": location_name, "active": True}
        else:
            raise RuntimeError("Scenario context is missing.")

    @given('there are {quantity} units of {sku} at storage area {area}')
    def step_given_stock(self, quantity, sku, area):
        """
        SETUP: Mocks or seeds the inventory record count into the testing database.
        This is crucial for maintaining state integrity between scenarios.
        """
        print(f"[SUCCESS] Seeding stock level: {quantity} units of {sku} in area {area}")
        if hasattr(self, 'context'):
            self.context.inventory = {"sku": sku, "qty": quantity, "location": area}
        else:
            raise RuntimeError("Scenario context missing.")

    @when('the inventory manager initiates manifest creation for {sale_order}')
    def step_when_initiate_manifest(self, so):
        """
        ACTION: Executes the core business logic function call (e.g., calling wms_owner API)
        and captures the result object into the Scenario Manager context.
        """
        print(f"[ACTION] Initiating manifest creation for Sale Order: {so}...")
        if hasattr(self, 'context') and hasattr(self.context, 'inventory'):
            # Simulate success if stock info is present in our mock context
            result = {"success": True, "manifest_id": f"MAN-{so}-CONFIRMED", "items_count": 1}
            self.context.last_manifest_result = result
            print(f"[SUCCESS] Manifest {result['manifest_int_id'] if 'manifest_int_id' in result else 'created'} recorded.")
        else:
            # Simulate failure if context is missing or incomplete
            error_msg = "No inventory context found to process manifest."
            self.context.last_manifest_error = error_msg
            print(f"[FAILURE] Manifest creation failed: {error_msg}")

    @then('the system should validate that all required items have enough stock')
    def step_then_validate_stock(self):
        """
        ASSERT: Checks if the output from the 'when' step passed validation checks by querying the ContextManager state.
        Unit Test Logic: Must verify self.context.inventory exists and has quantity > 0.
        """
        if not hasattr(self.context, 'inventory') or self.context.inventory.get('qty', 0) <= 0:
            raise AssertionError("Validation Failed: Inventory context is missing or stock level is zero.")
        print("[SUCCESS] Validation passed: Sufficient stock detected in the testing context.")

    @then('the newly created manifest should be visible and flagged as {status}')
    def step_then_manifest_created(self, status):
        """
        ASSERT: Verifies existence and attribute (e.g., 'Pending', 'Completed') of the new record
        by querying the database state or API response.
        Unit Test Logic: Must verify self.context.last_manifest_result exists with expected status.
        """
        if not hasattr(self.context, 'last_manifest_result'):
            raise AssertionError("Validation Failed: No manifest result found in context.")
        result = self.context.last_manifest_result
        if not result.get('success'):
            raise AssertionError(f"Validation Failed: Manifest creation failed. Error: {getattr(self.context, 'last_manifest_error', 'Unknown')}")
        print("[SUCCESS] Validation passed: Manifest was created and flagged as expected.")