# language: en
Feature: Wave Picking Management (wms_wave, wms_wave_auto)
    As a warehouse planner
    I want to group outbound orders into waves for optimized picking operations
    So that we can maximize labor efficiency and meet shipping deadlines.

    Background:
        Given the Odoo WMS system is running with "wms_wave" module installed
        And there are multiple pending outbound deliveries in the system

    Scenario: Auto-generate wave from pending orders
        When I trigger the "Auto Wave Generation" cron or action
        Then the system should group orders by logic (e.g., carrier, zone, owner)
        And create a new "Stock Picking Batch" (Wave) containing the relevant moves

    Scenario: Optimize picking path within a wave
        Given a multi-order wave has been created for the same zone
        When I generate picking tasks from this wave
        Then the system should suggest a sequence of locations that minimizes walking distance
        And combine identical products across different orders into single pick lines

    Scenario: Collaborative picking in a wave
        Given a large wave is assigned to the "Zone A" group
        When three operators start working on this wave simultaneously
        Then each operator should see their specific subset of tasks without conflicts
        And the wave status should update to reflect overall progress in real-time
