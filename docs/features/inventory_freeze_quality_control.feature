# language: en
Feature: Inventory Freeze and Quality Control (wms_inventory_freeze, wms_quality_control)
    As a warehouse quality inspector
    I want to freeze inventory for specific reasons without physically moving it
    So that the system prevents its use in pending operations until the issue is resolved.

    Background:
        Given the Odoo WMS system is running with "wms_inventory_freeze" module installed
        And there are available stock quants in the system

    Scenario: Freeze inventory due to quality issues
        When an operator identifies a damaged batch of goods
        Then I should be able to apply a "Frozen" status to those specific stock quants
        And the system must mark these items as unavailable for picking or putaway immediately
        And an audit trail must record the reason (e.g., damage, pending inspection)

    Scenario: Release frozen inventory after resolution
        Given a batch of items has been previously "Frozen" for quality checks
        When the QC team confirms the goods are now safe to use
        Then I should be able to transition the status from "Frozen" back to "Available"
        And the system should make these items immediately visible in standard inventory queries

    Scenario: View frozen inventory analytics
        Given multiple owners have a mix of available and frozen stock
        When I open the Inventory Analytics Dashboard
        Then I should see a breakdown of "Frozen vs Available" quantities by owner
        And a list of top reasons for freezing (e.g., Damage, Discrepancy, QC Hold)
