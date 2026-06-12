# language: en
Feature: Packing Verification and Outbound Handover (wms_packing_check, wms_handover)
    As an outbound supervisor
    I want to ensure all picked items are packed correctly and verified before dispatch
    So that we prevent shipping errors and maintain accountability with carriers.

    Background:
        Given the Odoo WMS system is running with "wms_packing_check" and "wms_handover" modules installed
        And there are outbound pickings ready for packing in zone A

    Scenario: Execute mandatory packing verification step
        When an operator moves a picked order to the packing area
        Then the system should require them to perform a "Verification Scan" on each SKU
        And the operation should be blocked if any item is missing or has the wrong quantity

    Scenario: Handle packing exceptions and rework
        Given a discrepancy is detected during the verification scan
        When I record the exception details (e.g., wrong color, damaged box) in the RF device
        Then the system should update the order status to "Needs Rework"
        And it should route the task back to the picking zone or to a secondary QC flow

    Scenario: Manage outbound handover with carriers
        Given all orders for the day have passed packing verification and are staged at the dock
        When the carrier driver arrives and presents their manifest
        Then I should use the "Handover" feature to confirm receipt of the packages
        And the system must generate a digital signature and timestamp for the outbound log
