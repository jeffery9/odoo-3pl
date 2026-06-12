# language: en
Feature: Value-Added Services Management (wms_value_added)
    As a 3PL service coordinator
    I want to manage value-added services for customers
    So that we can offer additional processing options beyond standard warehousing.

    Background:
        Given the Odoo WMS system is running with "wms_value_added" module installed
        And I am logged in as a Warehouse Operator

    Scenario: Create and execute a value-added service order
        When I create a new service request for an existing inbound shipment
        And I select "Quality Inspection" and "Label Replacement" as the services
        Then the system should generate a service order linked to the original stock receipt
        And operators can complete each sub-service step in sequence

    Scenario: Configure custom value-added service types
        Given multiple customers need different packaging requirements
        When I define a new "Custom Packaging" service type in configuration
        Then this service should appear as an available option for future orders
        And it should reference the correct labor and material cost rules

    Scenario: Track VAS completion and billing
        Given several value-added services have been completed this week
        When I open the VAS Analytics Dashboard
        Then I should see metrics such as "Service Completion Rate", "Avg. Processing Time per Service", and "Revenue by Service Type"
