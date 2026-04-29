# Access and Conditional Policy
Id: DOM_ACCESS
PlaneId: PLN_ACCESS

## Description
Conditional Access, Zero Trust enforcement, and policy overlay.

## Source State
- Static firewall rules
- GPO security filtering
- One-time authentication decisions

## Target State
- Conditional Access policies with device compliance requirements
- Policy Overlay with continuous evaluation
- Named locations and risk-based controls

## Key Transformations
- Security Filtering -> Conditional Access
- Policy Overlay -> Continuous enforcement layer
- AD Sites & Subnets -> Named Locations + Conditional Access

## Dependencies
- DOM_ID_DIR
- DOM_DEVICE
- DOM_NETWORK
- LC_POLICY

## Detailed Design
_To be elaborated in Phase 2 design sessions._
