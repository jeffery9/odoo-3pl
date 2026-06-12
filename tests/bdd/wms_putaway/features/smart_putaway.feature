@using BDD.Background[WMSPutawayContext]
Feature: Smart Putaway Logic and Allocation Rules
    As a warehouse manager
    I want the system to automatically calculate and assign optimal putaway locations based on product characteristics (ABC class, dimensions)
    So that picking efficiency is maximized and inventory utilization is optimized

Scenario: Successful smart putaway for high-demand 'A' class items
    Given an incoming shipment of 10 units of SKU "ITEM-A-123" with ABC Class 'A'
    When I initiate the putaway process
    And the system assigns the optimal location (e.g., Aisle 01, Shelf B)
    Then the inventory record for SKU "ITEM-A-123" should show a reserved quantity at that specific location