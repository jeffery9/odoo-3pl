# Unit Test Implementation Plan for WMS Owner Module

## Goal
To implement functional unit and integration tests within `wms_owner/steps/step_definitions.py` that correctly simulate Odoo's service layer calls, group checks, and record creation (OWNER module context).

## Current State (Goal Achieved)
-   **Feature Blueprint:** BDD features defined in `create_owner.feature` and `permission_management.feature` are complete and define the required end-to-end behavior.
-   **Boilerplate Steps:** The basic structure for setup, action, and assertion steps exist in `step_definitions.py`.

## Implementation Roadmap (Next Phase)

### 🎯 Task: Implement Core Service Logic Unit Tests (Targeting wms_owner/steps/step_definitions.py)

1.  **Dependency Identification:** We must assume access to Odoo's ORM context (`self.context.env`).
2.  **Priority Target 1: User Permission Check (Isolation Test)**
    *   **Function/Method:** Create a private method `_check_user_permissions(self, required_group)` inside `WMSOwnerSteps`.
    *   **Logic:** This function must simulate checking if the currently logged-in user (`self.context['user']['groups']`) contains the `required_group` using mock Odoo group/record rules (e.g., `env('res.partner').search([('group', '=', required_group)])`).
    *   **Unit Test Output:** Should raise a specific `PermissionError` if validation fails, allowing the step definition to fail gracefully and report "Unauthorized."

3.  **Priority Target 2: Resource Creation (Integration Test)**
    *   **Function/Method:** Enhance the logging in `step_given_facility` to not just print, but to mock the successful creation of a record using `self.context.env['wms.location'].create({...})`. This tests service contract execution.

4.  **Next Step (After completion): Putaway Unit Tests.** Apply the same pattern to the `wms_putaway` module's step definitions.