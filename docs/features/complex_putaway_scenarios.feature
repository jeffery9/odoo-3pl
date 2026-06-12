# language: en
Feature: Complex Putaway Scenarios and Optimization (wms_putaway)
    As a 3PL warehouse operations manager
    I want to handle complex putaway scenarios involving capacity, compatibility, and dynamic rules
    So that my warehouse space is used efficiently without violating safety or customer constraints.

    Background:
        Given the Odoo WMS system is running with "wms_putaway" and "wms_eiq_analysis" modules installed
        And I have configured a location zone "Zone-A1" with 100 kg max capacity
        And a rule that ABC Category A products must go to "Zone-Express"

    Scenario: Prevent Overloading of Putaway Zones
        When the system attempts to put away a 50kg shipment into Zone-A1 which currently has 60kg used
        And then another 50kg shipment for the same zone is selected by the algorithm
        Then the second shipment should be blocked or diverted to an overflow area
        Because it would exceed the configured `max_capacity` of 100 kg

    Scenario: Dynamic Putaway Recalculation based on EIQ Analysis
        Given product "P-XYZ" is currently categorized as ABC Category B (Medium Turnover)
        When the "wms_eiq_analysis" cron job updates "P-XYZ" to ABC Category A (High Turnover) due to recent sales
        And a new inbound order for "P-XYZ" arrives
        Then the putaway algorithm must prioritize "Zone-Express" over standard zones
        Even if no specific owner rule overrides this

    Scenario: Handle Partial Putaway due to Inventory Mismatch
        Given an inbound order has 10 units of product X and the suggested location can only fit 7 units
        When I confirm the putaway in the RF device
        Then the system should record 7 units as "Putaway" and 3 units as "Pending/Overflow"
        And the remaining 3 units should be assigned to a secondary suggested location or kept in staging

    Scenario: Conflict between "ABC Category" and "Specific Customer Storage" Rules
        Given customer "Customer-Gold" has a mandatory rule to store all items in "Premium Zone"
        And the incoming item is ABC Category C (Low Turnover) which normally goes to "Remote Storage"
        When the putaway strategy is calculated
        Then the system should select "Premium Zone" for the item
        Because Owner-Specific Rule Priority > General ABC Priority

    Scenario: Suggest Consolidation for Small Quantity Items
        Given a pending putaway task for 1 unit of Product A and another task for 2 units of Product A
        And both items are compatible
        When I initiate a consolidation batch
        Then the system should combine these into a single move for 3 units to a larger location
        To minimize the number of open locations and improve picking efficiency later
