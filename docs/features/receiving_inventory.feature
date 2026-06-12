# language: en
Feature: Receiving Inventory (wms_rf_container, wms_batch_receive)
    As a warehouse operator using RF scanners
    I want to efficiently receive goods into the system
    So that inventory levels are updated accurately and immediately.

    Background:
        Given the Odoo WMS system is running with "wms_rf_container" module installed
        And I am logged in as an RF Operator

    Scenario: Receive goods by scanning a container
        When I scan a unique QR/Bar code on a shipping container
        Then the system should open the corresponding inbound order
        And I should be able to confirm individual lines with quantities

    Scenario: Perform blind receive without documents
        Given an incoming shipment is expected but without pre-printed labels
        When I use the "Blind Receive" function on the RF device
        And I manually enter the product SKU and quantity
        Then the system should create a provisional stock receipt linked to the correct owner

    Scenario: Batch receive multiple units of the same item
        Given I have scanned 5 identical SKUs in a row
        When I confirm the batch operation
        Then the total quantity for that SKU should be summed up correctly
        And no separate pickings should be created for each unit
