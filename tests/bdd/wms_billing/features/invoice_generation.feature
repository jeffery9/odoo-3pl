# -------------------------------------------------- #
# wms_billing Module Scaffolding
# Focuses on invoicing, financial linkage, and billing rules.
# -------------------------------------------------- #

# /tests/bdd/wms_billing/features/invoice_generation.feature
@wms_owner @p0 @functional @smoke
Feature: Billing and Invoice Management
  Background: System Setup
    Given the system is operational and user 'accountant' is logged in
    And a confirmed shipment invoice FI-2026-1 is available for billing

  Scenario: Successful generation of an invoice from validated shipments
    When the accountant initiates the bulk invoicing process for all pending manifests
    Then the system must generate Invoice FI-2026-A, and update related manifest statuses to 'Billed'

  Scenario: Handling partial shipment/partial bill scenario
    Given a single manifest has 5 items shipped, but only 3 are invoiced
    When the accountant partially invoices the manifest for 3 units
    Then the invoice should reflect the partial amount, and remaining goods must be marked as 'Pending Billing'