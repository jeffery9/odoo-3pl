# language: en
Feature: Billing and Settlement (wms_billing)
    As a financial accountant or 3PL manager
    I want to automatically calculate and bill customers based on predefined rules
    So that the warehouse generates revenue accurately and transparently.

    Background:
        Given the Odoo WMS system is running with "wms_billing" module installed
        And billing rules have been configured for various owners and operations

    Scenario: Automatic billing record generation upon operation completion
        When a stock move (e.g., inbound handling or outbound packing) is confirmed as done
        Then the system should automatically create a "WMS Billing Record" in Odoo
        And this record must be linked to the specific owner and the operation type

    Scenario: Apply complex billing rules (Volume/Weight based)
        Given a billing rule configured for "Storage" based on volume (per cubic meter)
        When I query the storage billing report for Owner A over 30 days
        Then the system should sum up the daily volume of inventory and multiply it by the agreed rate
        And apply any "Minimum Charge" constraints if the calculated amount is too low

    Scenario: Generate periodic customer invoices
        Given a monthly settlement cycle has passed for multiple owners
        When I trigger the "Generate Invoices" batch process
        Then the system should compile all billing records per owner into an Odoo Invoice (account.move)
        And send the billing details to the respective customers for confirmation
