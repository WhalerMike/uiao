# Device Identity and Compliance
Id: DOM_DEVICE
PlaneId: PLN_DEVICE

## Description
Device identity, configuration, and compliance baselines.

## Source State
- Domain-joined Windows clients
- GPO-based configuration and loopback processing
- On-prem servers without cloud projection

## Target State
- Entra ID-joined or hybrid-joined devices
- Intune configuration profiles and compliance policies
- Azure Arc-enabled servers with managed identities
- Device posture integrated into Conditional Access

## Key Transformations
- Computer Objects -> Entra ID Device Identity + Arc
- GPO -> Intune Configuration Profiles + Compliance Policies
- GPO Loopback -> Device-Targeted Policy
- GPO Admin Scoping -> Intune Scope Tags

## Dependencies
- LC_DEVICE
- LC_POLICY
- DOM_ID_DIR

## Detailed Design
_To be elaborated in Phase 2 design sessions._
