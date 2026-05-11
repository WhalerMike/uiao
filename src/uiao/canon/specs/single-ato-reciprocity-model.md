---
document_id: UIAO_140
title: "UIAO Single-ATO Reciprocity Model"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-04"
updated_at: "2026-05-04"
boundary: "GCC-Moderate"
---

# UIAO Single-ATO Reciprocity Model

## 1. Overview

This spec defines the **single-tenant-of-record / multi-tenant-of-consumption**
authorization model: one System Security Plan (SSP), one Authority to Operate
(ATO), N consuming agencies under reciprocity. It is the canon counterpart to
the per-system ATO model that UIAO has assumed by default and must coexist
with.

Established under ADR-054. Authoritative for any UIAO deployment where a
federal authorizing official issues a single ATO that covers consumption by
multiple agencies. The reference instance is the OPM Federal HRIT
Modernization platform (Solicitation 24322626R0007), where one OPM ATO covers
all ~24 consuming CFO-Act agencies.

This spec is consumed by UIAO_112 (Multi-Tenant Isolation), UIAO_113
(Evidence Graph), UIAO_120 (Zero-Trust Integration Layer), and the OSCAL
generation pipeline (`uiao.oscal`).

## 2. Roles

| Role | Definition | Example (HRIT reference) |
|---|---|---|
| **System Operator** | Entity that operates the platform and authors the SSP. | HRIT prime contractor |
| **Authorizing Official (AO)** | Federal official empowered to issue the controlling ATO. | OPM Authorizing Officials, finalized by OPM CIO |
| **Consuming Agency** | Federal agency that consumes the platform under the controlling ATO via reciprocity. | Any of ~24 CFO-Act agencies onboarded to HRIT |
| **Continuous Monitor** | Function that evaluates posture against the controlling SSP on the cadence required by the AO. | UIAO ConMon pipeline (UIAO_111 / CONMON.md) |

## 3. Artifacts

The model produces and maintains the following artifacts in the evidence
graph (UIAO_113):

| Artifact | Owner | Cardinality | OSCAL representation |
|---|---|---|---|
| **System Security Plan (SSP)** | System Operator | One per platform | `system-security-plan` |
| **Authority to Operate (ATO)** | Authorizing Official | One per platform | Authorization decision linked from the SSP |
| **POA&M** | System Operator | One per platform | `plan-of-action-and-milestones` |
| **Continuous Monitoring evidence** | Continuous Monitor | Continuous stream | `assessment-results` |
| **Reciprocity Record** | Consuming Agency | One per consuming agency | `assessment-results` (back-matter resource) |

**Key invariant:** there is no per-agency SSP, no per-agency POA&M, no
per-agency ATO decision. The single SSP enumerates the configuration latitude
that consuming agencies have; everything else is fixed by canon.

## 4. Lifecycle

Five states, all transitions logged to the evidence graph (UIAO_113):

1. **Authorization** — System Operator submits draft SSP within 30 days of
   the qualifying contractual event (e.g., contract award), final SSP within
   45 days. AO reviews; ATO decision is signed and linked to the SSP.
2. **Reciprocity** — Each Consuming Agency files a Reciprocity Record
   acknowledging the controlling SSP and ATO. The record is signed by the
   agency's CIO (or delegate) and includes the agency's
   configuration-latitude elections.
3. **Continuous Monitoring** — Continuous Monitor produces evidence against
   the single SSP on the AO-mandated cadence. Per-tenant evidence views are
   derivative and tenant-scoped; the primary evidence stream is platform-
   wide.
4. **Reauthorization** — At least 30 days before ATO expiration, an updated
   SSP package is submitted. The AO renews, modifies, or denies the ATO.
   Reciprocity Records carry forward unless the agency withdraws.
5. **Termination** — Either the AO revokes the ATO or all Consuming Agencies
   withdraw. The platform exits production; evidence retention follows the
   FedRAMP ConMon Playbook §7 retention contract.

Each transition requires a signed event in the evidence graph. State
transitions for the controlling SSP/ATO and for each Reciprocity Record are
independently signed.

## 5. Drift Classes

Existing UIAO drift classes apply, with these tenant-scoped semantics:

| Class | Trigger in the reciprocity context | Severity |
|---|---|---|
| `DRIFT-SCHEMA` | Reciprocity Record missing required fields, or a tenant configuration in use that is not enumerated in the SSP's latitude table | P2 |
| `DRIFT-AUTHZ` | Tenant configuration in use that the SSP explicitly forbids; per-agency ATO record found where only reciprocity is permitted | P1 |
| `DRIFT-PROVENANCE` | Continuous-monitoring evidence missing the platform-scope grouping key, or tenant-scoped event missing the agency grouping key | P3 |
| `DRIFT-IDENTITY` | Tenant principal presenting an identity not recognized under the controlling SSP's IdP federation contract | P1 |
| `DRIFT-SEMANTIC` | SSP-declared baseline value differs from observed runtime value across tenants | P2 |

## 6. Evidence Graph Mapping

Each reciprocity event emits a structured node in the evidence graph
(UIAO_113):

```
ato-decision (controlling)
  ├── reciprocity-record (agency-1)
  ├── reciprocity-record (agency-2)
  ├── ...
  └── reciprocity-record (agency-N)
```

Continuous-monitoring evidence attaches to the controlling `ato-decision`,
not to individual reciprocity records — the single ATO is the singular root
of authority.

Required fields on a `reciprocity-record` event:
- `agency_id` (canonical agency code)
- `ssp_version` and `ato_decision_id` being acknowledged
- `acknowledged_by` (CIO or delegate, with PIV-anchored signature)
- `acknowledged_at` (ISO-8601)
- `configuration_latitude` (tenant-specific elections within the SSP's
  declared latitude table)

## 7. OSCAL Output Profile

Default outputs from the OSCAL generation pipeline under this model:

| Artifact | Emitted by default? | Notes |
|---|---|---|
| `system-security-plan` (controlling) | Yes | One per platform |
| `plan-of-action-and-milestones` (controlling) | Yes | One per platform |
| `assessment-results` (continuous monitoring) | Yes | Single platform-scope stream |
| `assessment-results` (reciprocity records) | Yes | One back-matter resource per consuming agency |
| `system-security-plan` (per agency) | **No** | Disabled by default; opt-in flag for non-reciprocity deployments |

A future ADR may introduce a non-default emission of per-agency SSPs for
deployments outside the reciprocity model.

## 8. Cross-References

- UIAO_112 — Multi-Tenant Isolation (consumes the reciprocity model when
  tenants share an authorizing official)
- UIAO_113 — Evidence Graph (event schema for reciprocity records)
- UIAO_120 — Zero-Trust Integration Layer (consumer)
- UIAO_111 — Continuous Monitoring (operates against the controlling SSP)
- ADR-043 — FedRAMP RFC-0026 pathway alignment (defines the BIR pathway
  under which this ATO model operates)
- ADR-051 — SAML trust anchor (federation context for reciprocity-bound
  identities)
- ADR-052 — PIV / USAccess (federal personnel authentication context)
- ADR-053 — OPM Azure APIM (gateway authority context for HRIT reference
  instance)
- ADR-054 — Single-ATO Reciprocity (the ADR that authorized this spec)
