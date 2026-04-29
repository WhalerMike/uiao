# Governance and Provenance
Id: DOM_GOV
PlaneId: PLN_GOV

## Description
Baselines, provenance, and governance substrate.

## Source State
- Manual CA/MFA/PIM policy management
- Email/ticket-based governance
- Manual device config review

## Target State
- Entra ID Identity Baselines (UIAO_BL_001, BL_002)
- Endpoint Compliance Baselines (UIAO_BL_007, BL_008)
- Governance Substrate with SHA-256-linked provenance chain
- Automated drift detection and remediation orchestration

## Key Transformations
- Identity Baselines -> Canonical OSCAL baselines with drift detection
- Endpoint Compliance Baselines -> Intune governance
- Governance Substrate -> Provenance chain and evidence generation

## Dependencies
- LC_POLICY
- DOM_ID_DIR
- DOM_DEVICE

## Detailed Design
_To be elaborated in Phase 2 design sessions._
