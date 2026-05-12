---
deliverable_id: Spec2-D6.1
title: "Federal HRIT Integration Runbook"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 6
status: Draft
version: 0.2
owner: Identity Architecture
created: 2026-05-05
updated: 2026-05-12
canonical_adrs:
  - ADR-003   # HR-system-agnostic by construction
  - ADR-051   # SAML trust anchor
  - ADR-052   # PIV / USAccess
  - ADR-053   # OPM Azure APIM
  - ADR-054   # Single-ATO reciprocity
canonical_docs:
  - UIAO_007
  - UIAO_129
  - UIAO_130
  - UIAO_136
  - UIAO_140
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.3
  - Spec2-D1.4
  - Spec2-D3.1
  - Spec2-D3.2
  - Spec2-D3.4
  - Spec2-D3.5
  - Spec2-D5.4
sibling_deliverables: []
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D6.1: Federal HRIT Integration Runbook

> **Status (v0.2, 2026-05-12):** Federal-civilian-specific instance of
> the Spec 2 HR-agnostic provisioning architecture. Names the
> canonical federal HR / personnel / credential systems and maps each
> to the Spec2-D3.1 inbound provisioning pipeline. Companion to the
> generic Spec2-D5.4 HR System Onboarding Playbook. Since v0.1 the
> customer-facing companion artifacts — the Federal HRIT Productization
> whitepaper, the OPM HRIT reference deployment case study, the
> A.9 NIST + FICAM cross-walk §4.1 NIST SP 800-63A subsection, and
> the `hrit-record-inventory` Python interface stub — have landed in
> canon. See §12 Revision history.

## 1. Purpose, Scope, and Reference

The generic Spec 2 architecture (Spec2-D3.1) is HR-system-agnostic by
design — Workday, Oracle HCM, SAP SuccessFactors, or any other HR
source plugs into the canonical schema (Spec2-D1.1) via per-source
adapters. This deliverable makes that architecture **concrete for
federal-civilian deployments** by enumerating the federal HR /
personnel / credential systems that any federal-agency customer of
the platform will need to integrate, and pointing each at its place
in the provisioning pipeline.

Reference instance: the OPM Federal HRIT Modernization Solicitation
24322626R0007 (Amendment 4) platform. The same runbook applies to
any subsequent federal-civilian deployment of the Spec 2 architecture.

### 1.1 Scope

In scope:

- **Federal HR systems of record** — the systems that author the HR
  attribute stream that the Spec2-D3.1 middleware consumes.
- **Federal personnel systems** — adjacent systems that participate
  in the HR-driven provisioning flow but are not themselves the HR
  source of record.
- **Federal credential / identity-proofing systems** — particularly
  USAccess (PIV credential issuance) which terminates the
  workforce-identity trust anchor introduced by ADR-052.
- **Federal hiring & lifecycle systems** — USA Staffing, USA
  Performance, eOPF, EHRI — that exchange data with the HR system
  of record at hire / mover / leaver events.

Out of scope:

- Customer-facing identity flows (citizen / business / beneficiary).
  Those land in the Customer Identity canon block (UIAO_141 /
  UIAO_142 / ADR-055) once that block is on main, not here.
- State-level HR systems (state agency hires).
- DoD-specific HR systems beyond DCPDS (covered in this runbook
  because DoD civilians are HRIT-platform consumers under the
  reference instance's scope).

## 2. Federal HR / Personnel Systems Matrix

The systems below are the canonical federal HR / personnel /
credential authorities a federal-civilian deployment of Spec 2
will integrate. Each row maps the system to its role in the
Spec2-D3.1 pipeline and cites the legal-basis frame governing
its data exchange.

| System | Operator | Role in pipeline | Legal frame | Spec2-D3.1 binding |
|---|---|---|---|---|
| **NFC EmpowHR / FPPS** | USDA National Finance Center | HR system of record for many civilian agencies (USDA, DOJ, DOC, DHS components, Treasury OCC, SSA, …) | 5 U.S.C. §552a (Privacy Act); SORN OPM/GOVT-1 | Inbound source — per-source adapter conforms to D1.1 canonical schema |
| **Treasury HR Connect** | Department of the Treasury | HR system of record for Treasury bureaus | 5 U.S.C. §552a; Treasury-issued SORNs | Inbound source — per-source adapter |
| **DCPDS** | Defense Civilian Personnel Advisory Service (DCPAS / DoD) | HR system of record for DoD civilian employees | 5 U.S.C. §552a; DoD-issued SORN; 10 U.S.C. §1593 | Inbound source — per-source adapter |
| **DOI IBC HR** | Interior Business Center (Department of Interior) | HR / payroll provider for several smaller civilian agencies | 5 U.S.C. §552a | Inbound source — per-source adapter |
| **USA Staffing** | OPM | Hire request / vacancy / announcement / new-hire data; SOAP RPI to HR systems | 5 U.S.C. §3301 et seq. | Spec2-D2.1 (Joiner) trigger source; Req #66 in HRIT solicitation |
| **GRB Platform** | OPM | Federal benefits enrollment (FEHB, FEGLI, FSAFEDS, retirement) | 5 U.S.C. §8901 et seq. | Spec2-D2.x consumer of HR attributes; downstream of provisioning |
| **USAJobs (OPM)** | OPM | Federal job applicant identity (pre-hire) | 5 U.S.C. §3301 | Pre-hire window source (Spec2-D2.7) |
| **eOPF** | OPM (centralized digital personnel folder) | Long-term personnel record retention; downstream of HR system events | 5 U.S.C. §552a; 5 C.F.R. part 293 | Downstream consumer of provisioning events; Federal Records Act archive |
| **EHRI** | OPM | Government-wide HR / payroll / training data warehouse for analytics and policy | 5 U.S.C. §3301; OPM SORN GOVT-7 | Downstream consumer; Privacy Act routine-use disclosures |
| **USAccess** | GSA Managed Service | PIV credential issuance under HSPD-12 / FIPS 201-3 | HSPD-12; FIPS 201-3; OMB M-22-09 | **Trust-anchor binding** (UIAO_129 binding #4) — workforce-identity credential issuance terminates here per ADR-052 |
| **OPM eAuthentication / OPM Entra** | OPM | Federal-IdP for HRIT-platform consumers | OMB M-19-17; OMB M-22-09; HRIT Solicitation 24322626R0007 §5.1.1 #3 | Federation IdP — consuming agencies authenticate via SAML 2.0 (per ADR-051) to OPM Entra |
| **Microsoft Entra Government Cloud** | Microsoft / OPM-tenant-operated | The IAM target of the provisioning pipeline | OMB M-22-09; FedRAMP Moderate / High | **IAM binding** (UIAO_129 binding #3) — receives SCIM 2.0 inbound provisioning from middleware |

Notation:

- *"Inbound source"* → the system feeds the Spec2-D3.1 middleware.
- *"Per-source adapter"* → the adapter conforms input to the
  canonical Spec2-D1.1 HR attribute schema before it enters the
  middleware.
- *"Downstream consumer"* → the system reads provisioning events
  emitted by the middleware (often via EHRI feeds or OPM-operated
  data exchanges).

## 3. Per-system integration patterns

For every system in §2, integration follows one of three patterns:

### 3.1 Pattern A — Native HR adapter (NFC EmpowHR / Treasury HR Connect / DCPDS / DOI IBC)

The HR system is the **source of truth** per Spec2-D3.6. The
integration pattern:

1. Per-source adapter consumes the HR system's published change-data
   feed (SOAP, REST, or batch file per system).
2. Adapter normalizes records to the Spec2-D1.1 canonical schema.
3. Spec2-D3.2 middleware computes the OrgPath (Spec2-D3.5), generates
   the UPN, and constructs the SCIM 2.0 payload.
4. Microsoft Graph `bulkUpload` endpoint applies the payload to OPM
   Entra (Spec2-D3.4 attribute mapping).
5. Spec2-D2.x JML workflows operate on the resulting Entra records.

Each per-source adapter is a candidate for its own activation ADR
(modeled on ADR-035) when the engagement requires it.

### 3.2 Pattern B — OPM-operated lifecycle service (USA Staffing / GRB / EHRI / eOPF)

These services are operated by OPM, exchange data with the HR
system of record on lifecycle events, and either trigger or consume
Spec2-D3.1 provisioning events:

- **USA Staffing → HR system of record**: Request Processing
  Interconnection (RPI, SOAP per HRIT Req #66) sends new-hire data
  upstream into the HR system, which then triggers Spec2-D2.1.
- **GRB Platform**: consumes HR attributes downstream for benefits
  enrollment workflows; reads from Entra (post-provisioning) or from
  the HR system directly.
- **EHRI**: government-wide data warehouse; ingests HR / payroll /
  training data via the Guide to Human Resources Reporting (GHRR)
  feeds; downstream consumer.
- **eOPF**: long-term personnel record archive; ingests SF-50 events,
  benefits documentation, onboarding records via the eOPF ICDs (per
  HRIT Solicitation Q&A #146).

These are integration points, not provisioning sources — the
runbook's job is to ensure the HR-system → Entra path is in place
*before* OPM lifecycle services are wired, since they all depend
on the canonical attribute set already existing in Entra.

### 3.3 Pattern C — Trust-anchor / federation (USAccess / OPM Entra)

These systems terminate the **trust-anchor** and **federation**
bindings of UIAO_129 §2:

- **USAccess** (PIV credential issuance) is the conformance authority
  for the federal-personnel trust-anchor binding, observed via the
  `piv-usaccess` adapter slot reserved in ADR-052. PIV certificates
  chain to the Federal Common Policy CA G2.
- **OPM Entra** is the federation IdP for the entire HRIT platform
  per the solicitation's §5.1.1 #3 mandate; consuming agencies
  authenticate via SAML 2.0 assertions (per ADR-051) carrying
  PIV-bound subject attributes.

Together they implement the **federal-personnel authentication
chain**: PIV credential at USAccess → SAML assertion to OPM Entra →
SAML-asserted Application Identity binding (per UIAO_129 §2 #4).

## 4. Provisioning lifecycle alignment

The federal HRIT systems integrate with each step of the Spec2-D2.x
JML lifecycle as follows:

| JML phase | Federal system contribution |
|---|---|
| **Joiner (D2.1)** | USA Staffing RPI provides new-hire data upstream; HR system of record (NFC / HR Connect / DCPDS) provisions the canonical record; Spec2-D3.1 pipeline writes to OPM Entra; PIV credential issuance scheduled at USAccess |
| **Pre-hire (D2.7)** | USAJobs identity claim; HR system pre-hire window record; Spec2-D2.7 inactive-user provisioning |
| **Mover (D2.2)** | HR system of record emits attribute deltas (department, manager, location, worker-type); Spec2-D3.1 pipeline applies SCIM PATCH; OrgPath recomputed; downstream group / policy / device-tag re-evaluation |
| **Leaver (D2.3)** | HR system of record terminates the canonical record; Spec2-D3.1 deactivates Entra account; PIV revoked at USAccess; eOPF receives final record set; EHRI ingests separation event |
| **Rehire (D2.4)** | HR system reactivates record; Spec2-D2.4 PATCH on existing externalId; PIV may be re-issued or re-bound at USAccess |
| **Conversion (D2.5)** | Worker-type change (e.g., temporary → permanent, civilian → military reservist); HR system emits atomic update; Entra worker-type attribute updated |

## 5. Federal-specific compliance frame

Every per-system integration above must satisfy the federal
compliance frame the HRIT platform operates under:

- **FedRAMP Moderate** authorization on every component (per
  HRIT solicitation §5.1.1 #1)
- **Privacy Act of 1974 (5 U.S.C. §552a)** — every HR-attribute
  exchange between agencies is governed by a System of Records
  Notice (SORN) routine use; the runbook's per-system entries
  cite the controlling SORN
- **Computer Matching and Privacy Protection Act of 1988
  (CMPPA)** — applicable when matching programs span agencies
- **OMB M-22-09 (Federal Zero Trust Strategy)** — phishing-resistant
  MFA (PIV/CAC) and identity-as-keystone posture
- **OMB M-25-21** — referenced in HRIT Req #5; SCIM provisioning
  near-real-time / 15-minute SLA
- **NIST SP 800-53 Rev 5** Moderate-impact controls
- **NIST SP 800-63-3** identity assurance levels (IAL/AAL/FAL)
- **HSPD-12 / FIPS 201-3** for PIV credential lifecycle

## 6. Single-ATO reciprocity (ADR-054 / UIAO_140)

This runbook's deployments operate under the single-ATO reciprocity
model formalized by ADR-054 / UIAO_140: **one** OPM ATO covers all
consuming agencies under documented reciprocity acceptance. Each
consuming agency files a Reciprocity Record acknowledging the
controlling SSP and ATO; per-agency ATOs are not produced.

The federal HR systems in §2 are not themselves authorized under
the HRIT platform's ATO — they are external authorities whose data
the HRIT platform consumes. Each integration point requires an
authorized inter-agency data exchange agreement (ISA / IAA / MOU)
documented in the platform's authorization boundary.

## 7. Operator commands

Federal-specific operator commands extending the generic Spec 2
operator surface:

```bash
uiao app provision --name <fqdn> --hrit-source nfc-empowhr
uiao kyc trust-anchor verify --identifier <piv-cert-fingerprint> --authority usaccess
uiao app onboard-federal --tenant <agency-code> --hrit-source treasury-hr-connect
```

Each command honors the existing UIAO operator semantics: returns
exit 0 on success; non-zero drift-class code on failure; emits
signed events to the evidence graph (UIAO_113).

## 8. Failure modes and handling

| Failure | Detection | Remediation |
|---|---|---|
| HR system of record unavailable during Joiner | per-source adapter health check fails | Hold record in `Proposed` state; retry per agency-specific SLA |
| PIV credential not yet issued at USAccess for new hire | DRIFT-IDENTITY at first cert-required action | Out-of-band PIV-issuance ticket via USAccess; retry after cert chain valid |
| OPM Entra federation token expired | DRIFT-AUTHZ at next agency-tenant action | Refresh OPM-Entra federation; re-issue SAML assertion |
| Inter-agency MOU expired | DRIFT-AUTHZ on attribute-exchange run | Suspend exchange; route to legal review for renewal |
| SORN routine use citation no longer valid | DRIFT-AUTHZ on next exchange | Suspend exchange; agency Privacy Officer issues amended SORN; legal review |
| EHRI ingestion behind on lifecycle events | DRIFT-PROVENANCE on EHRI feed audit | Trigger backfill; notify OPM EHRI team |

## 9. Evidence outputs

Each federal-HRIT engagement produces:

1. Signed events in the evidence graph for each per-system
   integration step, lifecycle event, and reciprocity record.
2. A per-tenant federal-HRIT integration evidence bundle referenced
   from UIAO_113.
3. A drift-scan baseline that subsequent runs compare against;
   federal-HRIT drift findings are first-class peers to existing
   workforce-identity findings.
4. A provenance record naming the per-system adapter version, the
   canonical schema version (Spec2-D1.1), and the controlling SSP /
   ATO version per UIAO_140.

## 10. Deferred follow-ups

- **Per-HRIT-system adapter activation ADRs** — one per row of §2
  (twelve candidates) when an engagement requires the integration.
  Expected first activations: NFC EmpowHR (largest civilian HR
  population) and OPM Entra federation (foundational).
- **EHRI / eOPF data feed integration runbooks** — separate
  deliverable; the EHRI / eOPF surfaces have their own ICDs and
  deserve dedicated specs.
- **DoD Common Access Card (CAC)** equivalent of the USAccess /
  PIV runbook — DoD civilians under DCPDS use CAC issued via DEERS
  / RAPIDS rather than USAccess. Worth a sibling Spec2-D6.2.
- **State-level HR integration** — state-civilian HR exchange is
  out of scope here; lands under a future Spec2-D6.x once a state
  engagement materializes.

## 11. Cross-references

- Spec2-D1.1, Spec2-D1.3, Spec2-D1.4 — canonical HR attribute schema
  and HR-to-Entra / HR-to-AD attribute mapping matrices
- Spec2-D3.1 — API-driven inbound provisioning architecture (the
  reference architecture this runbook concretizes)
- Spec2-D3.2, Spec2-D3.4, Spec2-D3.5, Spec2-D3.6 — middleware,
  attribute mapping engine, OrgPath population, writeback policy
- Spec2-D5.4 — generic HR System Onboarding Playbook (this runbook
  is the federal-civilian-specific instance)
- UIAO_007 — OrgTree Modernization (AD-to-Entra)
- UIAO_129 — Application Identity Model (binding model this runbook
  realizes per system)
- UIAO_130 — Application Identity Onboarding Runbook
- UIAO_136 — Priority 1 Transformation Project Plans
- UIAO_140 — Single-ATO Reciprocity Model (authorization frame)
- ADR-003 — HR-system-agnostic doctrine
- ADR-051 — SAML trust anchor (federation context for OPM Entra)
- ADR-052 — PIV / USAccess (workforce credential authority)
- ADR-053 — OPM Azure APIM (gateway pattern)
- ADR-054 — Single-ATO reciprocity model

### Customer-doc companions (added in v0.2)

- [`docs/customer-documents/whitepapers/federal-hrit-productization.qmd`](../../../../docs/customer-documents/whitepapers/federal-hrit-productization.qmd) — customer-facing whitepaper covering the federal HRIT mandate landscape, the 9-system federal HR ecosystem, the three integration patterns, and federal mandate alignment
- [`docs/customer-documents/case-studies/reference-deployment-opm-hrit-to-entra.qmd`](../../../../docs/customer-documents/case-studies/reference-deployment-opm-hrit-to-entra.qmd) — synthetic end-to-end case study exercising this runbook against a federal civilian agency archetype (companion to the AD reference deployment)
- [`docs/customer-documents/compliance/federal-mandates/nist-icam-crosswalk.qmd`](../../../../docs/customer-documents/compliance/federal-mandates/nist-icam-crosswalk.qmd) §4.1 — A.9 NIST + FICAM Cross-Walk extension covering NIST SP 800-63A (enrollment + identity proofing) and how this runbook consumes the proofing event
- [`src/uiao/adapters/modernization/hrit/inventory.py`](../../adapters/modernization/hrit/inventory.py) — phase-tagged HRRecordInventory interface stub (`extract_hrit_record_inventory`) consuming Spec2-D1.1 canonical-schema records; emits `DRIFT-IDENTITY` for OrgPath-unresolvable records; live federal-HR-system adapter implementations deferred

## 12. Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1 | 2026-05-05 | Identity Architecture | Initial federal-civilian-specific instance of the Spec 2 HR-agnostic provisioning architecture. Named the canonical federal HR / personnel / credential systems (§2 12-row matrix); mapped each to its role in the Spec2-D3.1 pipeline; codified the three federal integration patterns (Pattern A native HR adapter / Pattern B OPM lifecycle service / Pattern C trust anchor / federation); aligned to the lifecycle workflows in Spec2-D2.1–D2.5. |
| 0.2 | 2026-05-12 | Identity Architecture | Customer-doc surface landed: Federal HRIT Productization whitepaper (PR #437), OPM HRIT → Entra ID reference deployment case study (PR #451), A.9 NIST + FICAM cross-walk §4.1 NIST SP 800-63A extension (PR #453). Python interface-stub adapter landed under `src/uiao/adapters/modernization/hrit/` with phase-tagged `HRRecordInventory` artifact + 24 tests (PR #449). Status callout + canon `version` / `updated` bumped; §11 Cross-references extended with the customer-doc companions. No substantive changes to §§1–10 — the operational runbook is unchanged; v0.2 captures the customer-facing and code-stub surfaces that now reference it. |
