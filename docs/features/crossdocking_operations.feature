# language: en
Feature: Cross-docking Operations (wms_crossdock)
    As a logistics coordinator
    I want to identify opportunities for direct transfer of goods
    So that we reduce handling costs and speed up delivery times.

    Background:
        Given the Odoo WMS system is running with "wms_crossdock" module installed
        And I am logged in as an Operations Manager

    Scenario: Automatic detection of cross-docking opportunities
        When an inbound shipment arrives for a product that is also urgently needed by an outbound customer
        Then the system should flag this SKU as a potential cross-dock candidate
        And suggest linking the inbound receipt to the outbound delivery

    Scenario: Partial cross-docking execution
        Given an inbound order has 100 units but only 50 are needed for immediate cross-dock
        When I execute the partial transfer
        Then 50 units should be moved directly to a staging zone or outbound vehicle
        And the remaining 50 should remain in standard storage inventory

    Scenario: Cross-dock performance monitoring
        Given several cross-dock operations have been completed this month
        When I open the Cross-dock Analytics Dashboard
        Then I should see metrics such as "Direct Transfer Ratio", "Avg. Processing Time", and "Cost Savings"
        And a list of customers who benefited most from faster delivery
