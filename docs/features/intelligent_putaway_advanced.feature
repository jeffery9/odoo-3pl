# language: en
Feature: Advanced Intelligent Putaway and Rule Engine (wms_putaway)
    As a 3PL warehouse system architect
    I want to define complex priority logic for putaway rules
    So that the most critical business constraints (like safety or owner contracts) are respected over efficiency.

    Background:
        Given the Odoo WMS system is running with "wms_putaway" and "wms_eiq_analysis" modules installed
        And Putaway Rules are configured as follows:
            | Rule Name         | Criteria            | Priority | Target Zone       | ABC Category |
            | Safety Hazard     | Cargo=Flammable     | 100      | Hazardous Storage | None         |
            | Premium Customer  | Owner=Client_X      | 50       | VIP Secure Zone   | Any          |
            | High Turnover     | ABC=A               | 20       | Fast-Pick Zone    | A            |
            | General Rule      | Default             | 1        | Standard Storage  | Any          |

    Scenario: Resolve conflicts between Safety and ABC Efficiency
        When an inbound order for a "Flammable" product (ABC Category A) arrives from Client Y
        Then the system must prioritize the "Safety Hazard" rule (Priority 100)
        And ignore the "High Turnover" suggestion, ensuring the item goes to "Hazardous Storage"

    Scenario: Apply Owner-Specific Overrides for Premium Clients
        Given an inbound order is for "Client_X" (a premium owner with specific rules)
        And the product is ABC Category C (Low Turnover)
        Then the system must prioritize the "Premium Customer" rule (Priority 50) over the General Rule
        And assign the item to "VIP Secure Zone" regardless of its turnover rate

    Scenario: Dynamic Putaway Strategy Adjustment based on EIQ Data
        Given product P-100 is currently in ABC Category B with a putaway strategy for "Standard Storage"
        And the "wms_eiq_analysis" module updates P-100 to ABC Category A due to seasonal demand
        When I process the next inbound move for P-100
        Then the system should automatically apply the "High Turnover" logic (Priority 20)
        And suggest a location in "Fast-Pick Zone" near the dispatch area

    Scenario: Putaway Consolidation for Compatible Items
        Given an operator is moving two different products to the same storage zone
        And both products are compatible and have small quantities
        Then the system should suggest placing them in the same bin (if capacity allows) or adjacent bins
        To optimize space utilization and reduce the number of unique SKUs per location

    Scenario: Enforce Owner-Specific Capacity Constraints
        Given the "VIP Secure Zone" assigned to Client_X has a max_capacity defined in its putaway rule
        When I attempt to place items in the VIP zone that exceeds this max_capacity
        Then the system must block the putaway action and suggest an overflow location
        And notify the warehouse manager of the capacity breach for that specific owner's rule
