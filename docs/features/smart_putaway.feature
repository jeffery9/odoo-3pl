# language: en
Feature: Smart Putaway Rules (wms_putaway)
    As a warehouse manager
    I want to automate the assignment of storage locations based on intelligent rules
    So that goods are stored in the most efficient and safe places.

    Background:
        Given the Odoo WMS system is running with "wms_putaway" module installed
        And I am logged in as a Warehouse Administrator

    Scenario: Automatic putaway based on ABC classification
        When an inbound move for an "A-Category" (High Turnover) product is confirmed
        Then the system should automatically suggest a location near the dispatch area
        And the suggestion must respect the specific owner's allocated zones

    Scenario: Capacity-constrained putaway
        Given the primary suggested zone has reached 90% of its max capacity
        When I attempt to confirm the full quantity in that zone
        Then the system should trigger a "Partial Putaway" or suggest an overflow location
        And I should be warned about the capacity limit

    Scenario: Manual override for special handling
        Given a putaway rule has auto-assigned a location for a hazardous item
        When I manually select a different "Hazardous Storage" zone
        Then the system should validate that the new location supports the specific cargo type
        And update the move line accordingly
