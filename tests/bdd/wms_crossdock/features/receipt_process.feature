# -------------------------------------------------- #
# wms_crossdock Module Scaffolding
# Focuses on receiving and staging operations.
# -------------------------------------------------- #

# /tests/bdd/wms_crossdock/features/receipt_process.feature
@wms_owner @p0 @functional @smoke
Feature: Cross-Docking Operations Management
  Background: System Setup
    Given the system is operational and user 'receiving_clerk' is logged in
    And a receiving document (ASN) for shipment 789 was successfully loaded

  Scenario: Completing cross-dock receipt of inbound goods
    When the clerk scans the pallet barcode P-789 against the ASN
    Then the system must validate that all expected items were received and update inventory status to 'Quarantine'

  Scenario: Handling exceptions during cross-dock receipt (Shortage)
    Given the ASN expects 50 units of SKU-DEF
    When the clerk scans only 45 units of SKU-DEF, marking 5 as Shortage
    Then the system must create a formal discrepancy report and suspend further processing until resolved