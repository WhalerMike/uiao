# Network and Name Resolution
Id: DOM_NETWORK
PlaneId: PLN_NETWORK

## Description
DNS, named locations, and hybrid network constructs.

## Source State
- AD-integrated DNS
- On-prem-only name resolution
- AD Sites and Subnets

## Target State
- Azure DNS / Hybrid DNS
- Named locations feeding Conditional Access
- Hybrid DNS orchestration

## Key Transformations
- DNS (AD-Integrated) -> Azure DNS / Hybrid DNS
- AD Sites & Subnets -> Named Locations + Conditional Access

## Dependencies
- DOM_ACCESS

## Detailed Design
_To be elaborated in Phase 2 design sessions._
