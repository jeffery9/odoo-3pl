@using BDD.Background[WMSWaveContext]
Feature: Wave Picking Management
    As a warehouse supervisor
    I want to group multiple pending pick orders into optimized waves
    So that picking routes are consolidated and picked efficiently

Scenario: Successful creation of a mixed-priority pickup wave
    Given there are 5 open picking orders: 2 High Priority (expiring soon), 3 Medium Priority (standard)
    When I select the "End-of-Day Prep" wave template
    And I run the wave generation logic
    Then the system should assign a single optimized pick path that visits all 5 required locations, prioritizing high-priority items first.