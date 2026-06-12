# language: en
Feature: Labor Management (wms_labor_management)
    As a warehouse operations manager
    I want to track and analyze employee labor efficiency across all WMS activities
    So that I can optimize workforce allocation and improve operational productivity.

    Background:
        Given the Odoo WMS system is running with "wms_labor_management" module installed
        And I am logged in as a Warehouse Supervisor

    Scenario: Track operator activity by task type
        When an operator completes inbound receipt, putaway, or picking tasks throughout the day
        Then the system should automatically record the time spent on each activity type
        And calculate metrics such as "Units Per Hour" and "Tasks Completed per Shift"

    Scenario: Monitor labor utilization across shifts
        Given multiple operators are working across different shifts (morning/night)
        When I view the Labor Utilization Dashboard
        Then I should see peak activity periods, idle time analysis, and overtime warnings
        And recommendations for optimal shift scheduling based on order volume forecasts

    Scenario: Generate labor performance reports
        Given a month of operational data has been collected
        When I trigger "Generate Labor Reports" for the team
        Then the system should produce individual performance summaries with rankings
        And highlight top performers and operators needing additional training
