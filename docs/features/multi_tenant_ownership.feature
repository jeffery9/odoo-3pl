# language: en
Feature: Multi-Tenant Warehouse Ownership (wms_owner)
    As a 3PL warehouse manager
    I want to manage multiple warehouse owners with strict data isolation
    So that each client's inventory and billing information remains private.

    Background:
        Given the Odoo WMS system is running with "wms_owner" module installed
        And I am logged in as an Administrator

    Scenario: Register a new 3PL warehouse owner
        When I create a new partner marked as "Warehouse Owner"
        And I generate an automated unique "Owner Code" for them
        Then the system should enable specific billing fields (e.g., storage fee rate)
        And the system must apply data isolation rules restricting this owner's view to their own data

    Scenario: Assign inventory to a specific owner
        Given a warehouse owner exists with code "OWNER_A"
        When I create an inbound stock receipt for products assigned to "OWNER_A"
        Then the stock quants must be linked to "OWNER_A"
        And "OWNER_B" users should not be able to see this inventory

    Scenario: View owner-specific KPIs
        Given a warehouse owner has completed several operations today
        When I open the Owner Dashboard for that owner
        Then I should see inbound, outbound, and storage volumes specific to them
