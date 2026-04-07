---
title: "Appendix B-03: Multi-Cloud Identity Matrix"
appendix: "B-03"
family: "Truth Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-007", "ADR-008"]
---

# Appendix B-03: Multi-Cloud Identity Matrix

## Purpose

This appendix defines the Multi-Cloud Identity Matrix — the canonical mapping of identity constructs across the cloud platforms integrated by UIAO. It provides the authoritative reference for how identity anchors from different cloud providers are normalized into Canonical Identity Records in the Truth Fabric.

## Scope

Applies to all cloud platform adapters integrated with UIAO. The matrix covers the primary identity constructs used by each supported cloud provider and maps them to canonical UIAO identity types.

## Identity Matrix

The following matrix maps cloud-specific identity constructs to UIAO canonical identity types. Each mapping includes the local identifier format, verification method, and trust level.

### Person Identities

| Cloud Provider | Local Identity Construct | Local ID Format | Canonical Type | Default Trust Level |
|---|---|---|---|---|
| Microsoft Azure / Entra ID | User Principal Name (UPN) | user@domain.com | `person` | HIGH (AAD-verified) |
| Microsoft Azure / Entra ID | Object ID | UUID | `person` | HIGH |
| AWS IAM | IAM User ARN | arn:aws:iam::account:user/name | `person` | MEDIUM (no identity proofing) |
| AWS IAM | SSO User ID | UUID | `person` | HIGH (SSO-verified) |
| Google Cloud | Google Account Email | user@domain.com | `person` | HIGH (Google-verified) |
| Google Cloud | Cloud Identity UID | numeric string | `person` | HIGH |
| On-premises AD | sAMAccountName | DOMAIN\username | `person` | MEDIUM |
| On-premises AD | objectGUID | UUID | `person` | HIGH |

### Service Identities

| Cloud Provider | Local Identity Construct | Local ID Format | Canonical Type | Default Trust Level |
|---|---|---|---|---|
| Azure | Service Principal / App ID | UUID | `service` | HIGH (AAD-registered) |
| Azure | Managed Identity | UUID | `service` | HIGH (platform-managed) |
| AWS | IAM Role ARN | arn:aws:iam::account:role/name | `service` | MEDIUM |
| AWS | Service Account | ARN string | `service` | MEDIUM |
| GCP | Service Account Email | name@project.iam.gserviceaccount.com | `service` | HIGH |

### Device Identities

| Cloud Provider | Local Identity Construct | Local ID Format | Canonical Type | Default Trust Level |
|---|---|---|---|---|
| Azure | Device ID (Entra ID joined) | UUID | `device` | HIGH (MDM-enrolled) |
| Azure | Intune Device ID | UUID | `device` | HIGH |
| AWS | EC2 Instance ID | i-xxxxxxxxxxxxxxxxx | `device` | MEDIUM |
| GCP | Compute Instance Resource ID | URL format | `device` | MEDIUM |
| On-premises | Active Directory Computer Account | DOMAIN\computername$ | `device` | MEDIUM |

## Trust Level Definitions

| Trust Level | Meaning |
|---|---|
| HIGH | Identity has been verified through a strong authentication mechanism (MFA, PKI, platform-managed). May be used without additional corroboration. |
| MEDIUM | Identity is known to the source system but has not been independently verified. SHOULD be corroborated by a second adapter before use in compliance attestations. |
| LOW | Identity has been asserted but not verified by any mechanism. MUST be corroborated before use. |

## Cross-Cloud Identity Correlation

When the same real-world person or service has identities in multiple cloud platforms, the Truth Fabric can create cross-cloud anchor bindings in the Canonical Identity Record. Cross-cloud correlation requires:
- At least two HIGH-trust anchors pointing to the same real-world subject, OR
- One HIGH-trust anchor plus Governance Plane authorization of the correlation

Cross-cloud correlation records are stored in the CIR's `anchors` array with a `correlation_basis` field documenting how the correlation was established.

## Dependencies

- **ADR-007:** Multi-cloud adapter model decision record
- **ADR-008:** Zero-trust identity anchoring decision record
- **Appendix B-02:** Identity anchoring protocol
