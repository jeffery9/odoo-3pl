# -------------------------------------------------- #
# wms_putaway Module Scaffolding
# This directory is dedicated to BDD features and steps for intelligent putaway logic.
# -------------------------------------------------- #

# /tests/bdd/wms_putaway/features/putaway_rules.feature
@wms_owner @p0 @functional @smoke
Feature: Putaway Rule Enforcement
  Background: System Setup
    Given the system is operational and user 'warehouse_planner' is logged in
    And a facility location 'WH-A' exists with valid credentials

  Scenario: Successfully assigning inventory to optimal storage area based on ABC class
    Given SKU-123 (ABC Class) requires putaway
    When the planner executes putaway for 5 units of SKU-123
    Then the system must assign stock location L1, adhering to the Putaway Policy X

  Scenario: Failure when designated storage area is full
    Given a storage area 'A5' has reached capacity (99%)
    When the planner attempts putaway for 10 units into A5
    Then the system should block the action and suggest an alternative location