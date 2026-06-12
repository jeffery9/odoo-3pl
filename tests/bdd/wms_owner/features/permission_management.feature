@using BDD.Background[WMSOwnerContext]
Feature: Owner Permission and Role Management
    As an administrator
    I want to assign granular permissions and roles to specific owners
    So that data access is strictly isolated based on job requirements

Scenario: Revoke inventory viewing permission for a specific warehouse owner
    Given the system has 'Warehouse A' setup with active users
    When I select the "Team Alpha" owner profile
    And I navigate to Permission Settings
    And I uncheck the "View Inventory Levels" checkbox
    And I save the changes
    Then all reports generated for "Team Alpha" should no longer show inventory levels