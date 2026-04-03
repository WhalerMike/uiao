---
title: "UIAO FIMF Adapter Registry and Federated Truth Fabric"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO FIMF Adapter Registry and Federated Truth Fabric

**Version 1.0**

---

## Purpose

This document establishes the FIMF (Federated Identity Management Framework) adapter registry for UIAO and defines the pointer-first, claims-not-copies architecture that preserves truth and prevents data bloat across federal, state, and local jurisdictions.

---

## Core Architectural Principle

**Store the minimal canonical claim and immutable provenance; otherwise store a secure pointer and fetch signed assertions on demand.** Raw authoritative records remain at source.

---

## Adapter Registry (Priority Order)

| Adapter | Connects To | Claim Type | Transport | Confidence |
| :------ | :---------- | :--------- | :-------- | :--------- |
| Mainframe (z/OS Connect / MQ) | Legacy mainframes | Mapped from COBOL records | z/OS Connect, MQ, batch | High |
| SSA SSN | Social Security systems | `ssn:identity` | Mutual TLS API, signed XML/JSON | High |
| State DMV (MD MVA) | State DMV systems | `dmv:license` | State API, batch, MQ bridge | High |
| IRS / ITIN | IRS taxpayer identity | `itin:identity` | Mutual TLS API, secure file transfer | High |
| DHS / USCIS Immigration | Immigration status | `immigration:status` | Mutual TLS API, secure MQ | High |
| DoS Passport | Passport records | `passport:identity` | API or batch, signed assertions | High |
| DoD / Military ID | DoD identity stores | `military:id` | Secure DoD gateway, mutual TLS | High |
| State Vital Records | Birth/death registries | `vital:event` | Secure API, event feed | High |
| OPM / HRIS | Federal HR systems | `agency:employee` | HR API, SFTP, SCIM | High |
| Payments / Treasury | Payment systems | `payment:status` | Secure API, batch | High |
| PKI / Certificate Authority | PIV, certificates | `credential:cert` | OCSP, CRL, PKI APIs | High |
| IdP / SSO (SAML/OIDC) | Identity providers | Signed assertions with xALs | SAML, OIDC/OAuth | Varies |
| CMDB / Asset Management | Agency CMDBs | `asset:endpoint` | REST API, telemetry bus | Medium-High |
| Agency Case Management | Program case systems | `case:status` | REST API, event bus | Medium |
| IoT / Telemetry | Sensors, endpoints | Aggregated pointers | MQTT, time-series DB | Low-Medium |
| Consent Management | Consent registries | `consent:token` | API, signed tokens | High |
| Purpose Token Issuer | Legal/policy authority | `purpose:token` | OAuth2/JWT issuance | High |
| Adjudication Workflow | Human review systems | `adjudication:task` | Task API, case queue | Human-in-loop |
| Audit / SIEM | Security logs | `audit:event` | Syslog, SIEM APIs | High |

---

## What UIAO Stores vs Points To

| Pattern | UIAO Behavior | Rationale |
| :------ | :------------ | :-------- |
| Authoritative fact, low latency | Store canonical claim + provenance; keep pointer to source | Fast reads with provenance |
| Rare or sensitive fact | Do not store; return pointer + signed assertion on demand | Minimizes risk and legal exposure |
| High-volume telemetry | Store aggregates and pointers; raw telemetry in time-series stores | Prevents graph bloat |
| Temporary session data | Cache ephemeral claims with strict TTL | Improves UX without creating truth copies |
| Emergency offline needs | Store encrypted snapshot with legal justification and short retention | Operational necessity with governance |

---

## Canonical Claim Structure

Every adapter must emit:

- **Canonical Claim**: claim_id, claim_type, hashed_identifier, value (minimal), confidence_score, recency_ts
- **Provenance Record**: source_authority, source_record_id, signed_digest, signature_ts, adapter_version, legal_basis
- **Pointer/Locator**: source_endpoint_uri, access_method (API/batch), access_token_policy
- **Access Audit**: requester_id, purpose_token, response_minimization, audit_ts

---

## Adapter Onboarding Checklist

- [ ] Signed MOU and legal basis for sharing
- [ ] Federation Practice Statement published
- [ ] Schema mapping to canonical claim
- [ ] Signed assertion format and key exchange
- [ ] Transport and ATO (mutual TLS, FIPS/NIST controls)
- [ ] Provenance fields validated on ingest
- [ ] Confidence scoring rules defined
- [ ] TTL and retention policy set
- [ ] Acceptance tests: signature validation, provenance completeness, purpose token enforcement, performance SLA

---

## Anti-Bloat Controls

- **Claims not copies** enforced by adapter onboarding checklist
- **Pointer-first default**; caching only with explicit SLA and TTL
- **Provenance mandatory** for every claim
- **Human adjudication gate** for conflicts or confidence below threshold
- **Pruning jobs** scheduled for stale derived artifacts
- **Separate telemetry from truth**: high-volume data stays in time-series stores

---

## Confidence Scoring Rules

| Level | Criteria | Allowed Actions |
| :---- | :------- | :-------------- |
| High | Signed real-time API from authoritative source, recency <30 days | Automated decisions; cache minimal claim |
| Medium | Batch extract with checksum, recency <180 days | Human review for critical decisions |
| Low | Probabilistic match, scanned docs, partial identifiers | Never automated; route to adjudication |

---

## FIMF Governance Structure

- **Federated Council**: Executive approvals, trust agreements, dispute resolution
- **FIMF Working Group**: Technical standards, adapter certification, metadata registry
- **Privacy Board**: Independent review of purpose tokens, minimization, and audits

---

## KPIs

- Claim Duplication Factor (target: <=1.5)
- Provenance Completeness (target: 100%)
- Adjudication Volume (target: trending down)
- Shadow DB Count (target: quarterly reduction)
- Cache TTL Compliance (target: 100%)
- False Automation Rate (target: below agreed threshold)

---

## Adapter Layer Implementation Artifacts

The following artifacts in `uiao-core` provide the concrete implementation of the adapter contract described in this document:

| Artifact | Path | Purpose |
| :------ | :--- | :------ |
| BaseAdapter ABC | `adapters/base_adapter.py` | Abstract base class defining the ten adapter responsibility domains |
| Adapter Registry | `adapters/__init__.py` | In-process registry for adapter discovery and instantiation |
| Adapter Contract | `docs/adapters/adapter-contract.md` | Human-readable, governance-aligned adapter contract specification |
| Canonical Definition | `docs/adapters/canonical-definition-of-a-uiao-adapter.md` | Full-length definition of a UIAO adapter with all ten domains |
| Diagram Set | `docs/adapters/adapter-responsibilities-diagram-set.md` | ASCII diagrams covering architecture, responsibilities, and lifecycle |

Vendor-specific adapters (e.g., `uiao-adapter-entra`, `uiao-adapter-infoblox`) live in separate repositories and must conform to the `BaseAdapter` contract.

---

*End of UIAO FIMF Adapter Registry v1.1*
