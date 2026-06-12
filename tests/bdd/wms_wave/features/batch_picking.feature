# -------------------------------------------------- #
# wms_wave Module Scaffolding
# Focused on batch picking and wave generation features.
# -------------------------------------------------- #

# /tests/bdd/wms_wave/features/batch_picking.feature
@wms_owner @p0 @functional @smoke
Feature: Wave Picking Management
  Background: System Setup
    Given the system is operational and user 'picker_supervisor' is logged in
    And an open wave 'WVE-456' has been created for picking orders

  Scenario: Successfully generating a pick list from pending orders
    Given there are 20 pending picking orders awaiting grouping
    When the supervisor runs the batch assignment process for WVE-456
    Then the system must generate 3 optimized pick lists, and update order statuses to 'Picking Assigned'

  Scenario: Handling cancelled or incomplete picks during wave processing
    Given pick list PL-789 is partially completed by staff member X
    When supervisor marks PL-789 as incomplete due to item shortage
    Then the system must revert the picking orders in PL-789 to 'Awaiting Picking' status