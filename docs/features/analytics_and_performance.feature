# language: en
Feature: Warehouse Analytics and Performance (wms_performance, wms_location_usage, wms_inventory_age)
    As a 3PL WMS administrator
    I want to track operator productivity, location utilization, and inventory aging
    So that I can identify bottlenecks, optimize space, and generate performance reports for stakeholders.

    Background:
        Given the Odoo WMS system is running with all analytics modules installed
        And several days of operational data (pickings, putaways, etc.) exist in the system

    Scenario: Monitor operator daily performance metrics
        When I open the Operator Performance Dashboard
        Then I should see real-time metrics for each employee, such as "Picks per Hour" and "Putaway Efficiency"
        And I should be able to compare individual performance against team averages

    Scenario: Analyze location utilization and space efficiency
        Given the warehouse is experiencing congestion in Zone A
        When I open the Location Usage Analysis tool
        Then the system should visualize capacity usage across all zones
        And it should highlight "Overloaded" locations that have exceeded their configured max_capacity thresholds

    Scenario: Track inventory aging to prevent obsolescence
        Given stock has been sitting in the warehouse for an extended period
        When I run the Inventory Aging Analysis report
        Then the system should categorize stock by days held (e.g., 0-30, 31-60, 60+ days)
        And it should alert me to any "A-Category" items that have unexpectedly aged into "C-Category" status
