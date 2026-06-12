@using BDD.Background[WMSOwnerContext]
Feature: WMS Owner Management
    As an administrator
    I want to manage multi-owner profiles and permissions
    So that the correct data isolation and access controls are enforced across all 3PL operations

    Scenario: Successfully create a new owner profile with restricted roles
        Given the system is running in development mode
        When I navigate to Owner Management and click 'Create'
        And I fill out the form with Owner Name "TestOwner" and Role "Limited Inventory View"
        And I save the owner record
        Then the new owner should be visible in the system user list with restricted permissions

    Scenario: Attempt to create an owner without proper role
        Given the system is running in development mode
        When I navigate to Owner Management and click 'Create'
        And I fill out the form with Owner Name "TestOwner" and Role "InvalidRole"
        And I save the owner record
        Then a validation error should be shown indicating invalid role

    Scenario: Verify permission inheritance for owners
        Given the system is running in development mode
        When an owner logs in with role "Limited Inventory View"
        And they attempt to access a restricted area
        Then they should be denied access and receive a permission error message