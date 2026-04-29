# HR-Driven Provisioning
Id: DOM_HR_PROV
PlaneId: PLN_IDENTITY

## Description
HR-agnostic provisioning architecture for human identities.

## Source State
- On-prem HR -> MIM -> AD
- Manual account creation
- Ticket-driven lifecycle changes

## Target State
- Cloud HR connector (Workday or Oracle) -> Entra ID
- API-driven inbound provisioning
- Joiner-Mover-Leaver workflows in Entra ID Governance
- Attribute writeback to HR where required

## Key Transformations
- On-prem HR -> MIM -> AD -> Entra Connect Sync -> Entra ID
- Cloud HR Connector -> Entra ID (Workday/Oracle)
- API-driven inbound provisioning for non-standard HR sources

## Dependencies
- LC_HUMAN
- DOM_ID_DIR

## Detailed Design
_To be elaborated in Phase 2 design sessions._
