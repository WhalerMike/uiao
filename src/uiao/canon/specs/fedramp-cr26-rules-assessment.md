---
document_id: UIAO_207
title: "FedRAMP Consolidated Rules for 2026 — Full Rules Assessment"
version: "1.0"
status: Current
owner: "Michael Stratton"
created_at: "2026-07-01"
updated_at: "2026-07-01"
mas-scope: "in-scope"
related_adrs:
  - ADR-126
  - ADR-061
  - ADR-106
  - ADR-043
related_docs:
  - UIAO_133
  - UIAO_137
  - UIAO_132
  - UIAO_022
---

# UIAO_207 — FedRAMP Consolidated Rules for 2026: Full Rules Assessment

> **Status: CURRENT.** Fires ADR-126 (which fires ADR-061 re-evaluation trigger #1).
> Covers the full CR26 rules surface — FRR requirements, FRD definitions, and KSI
> authority upgrade — complementing UIAO_137's per-indicator KSI mapping.

## 1. Purpose and scope

FedRAMP published the **Consolidated Rules for 2026 (CR26)** on 2026-06-25, version
`2026.06.24.01`. This is the first stable, mandatory rules release under the FedRAMP
20x program. All FedRAMP stakeholders must comply by 2027-01-01; Rev5 certifications
must adopt the new rules by 2027-01-01, and FedRAMP will no longer accept new Rev5
applications after 2027-06-11.

This document:

1. **Assesses the FRR rule surface** (17 categories, 29 variants) against existing
   UIAO capabilities, recording coverage and gaps.
2. **Updates the CR26 authority provenance** — the official FedRAMP/rules JSON
   (`version 2026.06.24.01`) replaces the Palladium OSCAL snapshot as the primary
   rules authority per ADR-126 D1.
3. **Extends UIAO_137** with the official KSI source pin and notes FRR is now
   a first-class companion concern (UIAO_137 §1 explicitly deferred FRR mapping here).

**Out of scope:**
- Per-indicator KSI forward/reverse mapping (covered in UIAO_137 §3–4).
- New KSI rule authoring (downstream; tracked in FINDING-PGM-003 §4).
- CSP-side filing operations (tracked in FINDING-PGM-001 §4).
- OSCAL catalog tailoring for Low/Moderate/High baselines (fedramp-cr26 overlays).

---

## 2. Source and provenance

| Field | Value |
|---|---|
| Repository | `FedRAMP/rules` |
| File | `fedramp-consolidated-rules.json` |
| Version | `2026.06.24.01` |
| Last updated | `2026-06-24` |
| Retrieved | `2026-07-01` |
| SHA-256 | `48d1fb4c1674c15f1a966f94c9f519b246af377d2ff51845083131ad99da8c60` |
| Local path | `src/uiao/canon/compliance/reference/fedramp-cr26/official/fedramp-consolidated-rules.json` |
| Authority | **Official** — US Government (public domain, 17 U.S.C. § 105) |
| Governing ADR | ADR-126 |

The official JSON supersedes the Palladium OSCAL snapshot (`c31eb04`) as the
primary rules-text authority. The Palladium snapshot remains in place for OSCAL
catalog/profile/mapping consumption per ADR-061 D3 until FedRAMP publishes an
official OSCAL derivation.

**UIAO_137 provenance update:** The KSI indicator IDs and statements in UIAO_137
§3–4 were verified against the official JSON and are confirmed correct. The
provenance pin in UIAO_137 §2 retains the Palladium SHA for OSCAL-format lineage
and adds the official JSON version as the rules-text pin. The two sources agree on
all 46 KSI indicator IDs and their theme assignments.

---

## 3. Effective dates

| Milestone | Date | UIAO action |
|---|---|---|
| Optional adoption opens | 2026-07-04 | Official JSON vendored; UIAO_207 published |
| 20x Class B/C pipelines open | 2026-08-31 | FRR gap items tracked below must be assessed for open-pipeline readiness |
| **Mandatory for all stakeholders** | **2027-01-01** | All FRR gaps rated P1 or above must be closed |
| No new Rev5 certifications | 2027-06-11 | ConMon and VDR adapters must run CR26-mode by default for new submissions |

---

## 4. CR26 rules structure summary

The official JSON has four top-level sections:

| Section | Name | Count |
|---|---|---|
| FRD | FedRAMP Definitions | 75 defined terms |
| FRR | FedRAMP Rules | 17 categories / 29 variants (all / 20x / rev5) |
| KSI | Key Security Indicators | 10 themes / 46 indicators |
| CTL | NIST Controls | 14 families |

**Certification classes** (FRD-CCL): A (minimal), B (Low baseline), C (Moderate), D (High/enhanced).
The current deployment boundary is **GCC-Moderate (Class C)**. All FRR gap ratings below use Class C applicability.

---

## 5. FRR rules assessment

Each FRR category has an `all`, and optionally `20x` and/or `rev5` variant. The
applicable variant for UIAO's GCC-Moderate Class C posture is `all` + `20x`.
Assessment ratings: **Covered** (existing capability addresses the rule),
**Partial** (partial coverage — gap items noted), **Gap** (no substrate capability
mapped), **External** (FedRAMP or agency obligation, not CSP substrate automation).

### AFC — Addressing FedRAMP Communication

**Rating: External (CSP procedural)**

FedRAMP must maintain `@fedramp.gov`/`@gsa.gov` email infrastructure with SPF/DKIM;
CSPs must maintain a monitored `fedramp_security@<domain>` inbox. This is a
communications-hygiene requirement, not a substrate automation surface. UIAO does
not automate inbox management; CSP operators satisfy this manually. No gap item.

### AGU — Agency Use of FedRAMP Certified Cloud Services

**Rating: External (agency obligation)**

Agencies must use FedRAMP-Certified CSOs for federal information handling. UIAO's
Marketplace adapter surfaces certification status (MKT context); agency procurement
is outside substrate scope. No gap item.

### CCM — Collaborative Continuous Monitoring

**Rating: Covered**

ConMon quarterly reporting, collaborative review, and oversight-report generation
are covered by:
- `uiao.monitoring` CLI (`conmon-process`, `conmon-export-oa`, `conmon-dashboard`)
- UIAO_132 §3 (dual-track ConMon pathway)
- ADR-043 (RFC-0026 CA-7 integration)

CCM-all requires quarterly collaborative-monitoring reviews with all agency
customers; the ConMon pipeline produces the required artifacts. Open item:
automated agency-distribution of ConMon output (tracked in FINDING-PGM-001 §3.2, not a
CR26-gate blocker).

### CDS — Certification Data Sharing

**Rating: Partial**

**CDS-all**: CSO must share full Certification Data with FedRAMP and agency
customers; update data within 90 days of significant changes. The OSCAL
package pipeline (`uiao generate-all`, UIAO_022) produces the artifacts; sharing
logistics (distribution, access control) are manual today.

**CDS-rev5**: Additional data-format requirements for Rev5 submissions. UIAO's
OSCAL pipeline targets rev5 OSCAL format; no gap on content.

**Gap item G-CDS-01:** Automated distribution of updated Certification Data
packages to agency customers on change trigger is not implemented. Priority: Low
(2027-01-01 target; not a pipeline blocker). Owner: ConMon module.

### CMU — Cryptographic Module Use

**Rating: Gap**

CMU-all requires all cryptographic modules to be validated under FIPS 140-3 (or
approved transition schedule). UIAO does not currently audit cryptographic module
validation status as a substrate function. The ScubaGear adapter surfaces some
M365-layer FIPS posture, but there is no generalized CMU evaluator.

**Gap item G-CMU-01:** No substrate capability to evaluate and report cryptographic
module validation status against the FIPS 140-3 requirement. Priority: Medium
(Class C MUST for obtain/maintain as of 2026-07-04). Owner: new KSI rule or
SVC-layer adapter.

### CPO — Certification Package Overview

**Rating: Covered**

**CPO-all**: Certification Package must include all required artifacts.
**CPO-20x**: 20x-format package with KSI evidence sections.
**CPO-rev5**: Rev5-format package.

Covered by UIAO_022 (OSCAL package generation), `uiao generate-all`, and the
`ir-ssp-inject` → `ir-auditor-bundle` pipeline. The 20x KSI-evidence sections
are partially addressed (UIAO_133 D1 KSI-tagging); scaffold completeness depends
on KSI-CMT evidence binding (ADR-111).

### FRC — FedRAMP Certification

**Rating: External (process) / Partial (Class structure)**

**FRC-all**: Defines who may hold FedRAMP Certification (CSPs) and the certification
lifecycle. Process obligations (application, review, approval) are handled by
FedRAMP PMO, not by the substrate.

**FRC-20x**: Class A/B/C/D framework — Class C (Moderate) is the UIAO deployment
target. ADR-106 D4 tracks the pathway posture (traditional → modernized) and Class
C gate criteria.

**Gap item G-FRC-01:** The substrate does not yet surface a machine-readable
**Certification Class assertion** in emitted OSCAL artifacts. ADR-106 D1 specifies
KSI-theme tagging but does not include a `fedramp:certification-class: C` prop.
Priority: Low (informational, not a gate blocker). Owner: OSCAL emitter (`uiao.generators`).

### IEC — Incident Evaluation and Communication

**Rating: Partial**

IEC-all requires providers to evaluate incidents and communicate findings to all
affected parties within defined timeframes. The ConMon module surfaces incident
POA&M items (`conmon-process`). Full IEC automation — detecting an incident,
classifying it, notifying affected parties within the required window — is not
implemented as a substrate function.

**Gap item G-IEC-01:** No automated incident-evaluation-and-notification pipeline.
Incident classification, timeline tracking, and party notification are manual.
Priority: High (Class C MUST; affects authorization maintenance). Owner: future
incident-response adapter (not yet in `adapter-registry.yaml`).

### IVV — Independent Verification and Validation

**Rating: External (assessor obligation) / Partial (evidence supply)**

IVV requirements govern what independent assessors must do. The substrate's role
is to supply evidence (UIAO_138 — 3PAO evidence interface). UIAO_138 covers the
evidence-package side; IVV assessment activities are assessor-side obligations.

**Gap item G-IVV-01:** UIAO_138 (Draft) must reach Current status before the
2026-08-31 Class B/C pipeline open. Owner: UIAO_138 governance-review track.

### MAS — Minimum Assessment Scope

**Rating: Covered**

ADR-106 D2 implements the MAS inclusion test at canon-component granularity
(`mas-scope` frontmatter field on every canon component). RFC-0005's two-prong
test (federal information + CIA impact) is applied per component; classification
is carried in canon.

### MKT — Marketplace Listing

**Rating: External (FedRAMP/CSP procedural)**

Marketplace listing and status maintenance are procedural CSP obligations with
FedRAMP. The substrate does not automate marketplace interactions. No gap item.

### REC — FedRAMP Recognition of Independent Assessment Services

**Rating: External (FedRAMP/assessor obligation)**

FedRAMP Recognition requirements govern the assessor registry. Not a CSP/substrate
concern. No gap item.

### SCG — Secure Configuration Guide

**Rating: Covered**

CSPs must maintain and publish a Secure Configuration Guide covering all
configurable options and recommended settings. The ScubaGear adapter surfaces
baseline configuration posture; the `adapter-run-scuba` pipeline produces the
SCuBA-aligned configuration evidence that feeds SCG artifacts. Manual SCG
document authoring (narrative guide) is a CSP-side documentation obligation.

### SCN — Significant Change Notification

**Rating: Partial**

SCN-all requires providers to notify FedRAMP and all agency customers of
significant changes (Adaptive, Transformative, Certification-Class) within
defined timeframes. The substrate detects drift (`substrate drift`), but does not
currently automate significant-change classification or notification delivery.

**Gap item G-SCN-01:** No automated significant-change classification against the
CR26 taxonomy (Adaptive / Transformative / Certification-Class). Priority: Medium
(Class C MUST for maintain). Owner: drift engine + change-notification adapter
(ADR-111 companion).

### SDR — Security Decision Record

**Rating: Partial**

**SDR-all**: CSPs must maintain a Security Decision Record documenting accepted
vulnerabilities, significant changes, and related risk-acceptance decisions.
**SDR-20x**: Machine-readable SDR in the 20x package format.
**SDR-rev5**: SDR in POAM/SSP narrative format.

The POA&M pipeline (`conmon-process`, `poam_rules.py`) produces structured
decision records for vulnerabilities. A machine-readable SDR as a discrete OSCAL
artifact distinct from the POAM is not yet emitted.

**Gap item G-SDR-01:** No dedicated SDR emitter producing the CR26 SDR artifact
as specified in CPO/SDR-20x. Currently embedded in POAM. Priority: Medium
(required for Class C 20x package). Owner: `uiao.generators` (new SDR command).

### VDR — Vulnerability Detection and Response

**Rating: Covered**

**VDR-all**: Systematically detect vulnerabilities using scanning, threat
intelligence, bug bounties, incident response, and automated control testing.
**VDR-20x Class C**: Verify/validate machine-based resources at least every **3
days**.
**VDR-rev5 Class C**: Verify/validate at least every **month**.

Covered by:
- ADR-043 (RFC-0026 CA-7, VDR integration)
- UIAO_132 §3 (VDR pathway — Pathway 1 modernized, Pathway 2 traditional)
- `conmon-process` pipeline and POA&M rules

The 3-day Class C cadence for 20x is a tighter cycle than the monthly Rev5
requirement. The ConMon pipeline supports configurable cadences; the 3-day cycle
must be validated as a supported configuration.

**Gap item G-VDR-01:** The 3-day machine-verification cadence for Class C 20x has
not been explicitly validated in the ConMon scheduler. Priority: Medium (Class C
MUST; mandatory 2026-12-07 per CISA BOD 26-04). Owner: ConMon module cadence
configuration.

### VER — Vulnerability Evaluation and Reporting

**Rating: Covered**

**VER-all**: Evaluate and report vulnerability status to all affected parties.
**VER-20x / VER-rev5**: Variant-specific reporting formats and timeframes.

Covered by the ConMon pipeline (`conmon-export-oa`, `conmon-dashboard`), the
POAM structure, and VDR/VER integration per ADR-043 / UIAO_132. No additional
gap items beyond G-VDR-01.

---

## 6. FRR gap summary

| Gap ID | FRR | Description | Priority | 2027-01-01 gate? | Owner |
|---|---|---|---|---|---|
| G-CMU-01 | CMU | No FIPS 140-3 module validation evaluator | Medium | Yes | SVC adapter / new KSI rule |
| G-CDS-01 | CDS | No automated Certification Data distribution | Low | No | ConMon module |
| G-FRC-01 | FRC | No machine-readable Certification Class prop in OSCAL | Low | No | `uiao.generators` |
| G-IEC-01 | IEC | No automated incident evaluation/notification pipeline | High | Yes | New IR adapter |
| G-IVV-01 | IVV | UIAO_138 (evidence interface) still Draft | Medium | Yes (pre-Aug 31) | UIAO_138 review |
| G-SCN-01 | SCN | No automated significant-change classification/notification | Medium | Yes | Drift engine + notification adapter |
| G-SDR-01 | SDR | No dedicated SDR artifact emitter (CR26 20x format) | Medium | Yes | `uiao.generators` |
| G-VDR-01 | VDR | 3-day Class C cadence not validated in ConMon scheduler | Medium | Yes (pre-Dec 7) | ConMon module |

**Coverage summary:** 9 of 17 FRR categories fully covered, 5 partial, 3 external/CSP-procedural.
6 gap items are 2027-01-01-gate blockers.

---

## 7. KSI surface summary (delegate to UIAO_137)

KSI forward/reverse mapping is maintained in UIAO_137 (current version 0.2,
updated 2026-06-18). Key metrics:

- **14 local KSI rules** (KSI-001 through KSI-014) covering **21 of 46** CR26
  KSI indicators (~46%).
- **Themes with zero local rules**: CED (1), INR (3), PIY (5), RPL (4), SCR (2)
  = 15 indicators.
- **Themes with partial local rules**: CNA (2/8), MLA (2/5), SVC (4/8)
  = 10 indicators.
- **Themes fully covered**: IAM (6/6 via KSI-001…009), CMT (4/4 via KSI-011…014
  scaffolds — not yet evaluable).

The official JSON (`version 2026.06.24.01`) confirms all 46 KSI indicator IDs and
their NIST SP 800-53 control anchors. The UIAO_137 §3 forward-mapping table
remains valid against the official JSON; no indicator was renamed or restructured
between the Palladium Public Preview snapshot and the official launch.

**UIAO_137 provenance pin update (v0.2 → v0.3):** The KSI catalog source is now
dual-pinned:

| Pin type | Source | Identifier |
|---|---|---|
| Rules text (primary, ADR-126 D1) | `FedRAMP/rules` JSON | version `2026.06.24.01` |
| OSCAL catalog (secondary, ADR-061) | Palladium snapshot | SHA `c31eb04c082d6d578a26a00de9a482707ab7a00c` |

---

## 8. FRD definitions coverage

The 75 CR26 defined terms are grouped into 10 tags:

| Tag | Count | UIAO relevance |
|---|---|---|
| Stakeholder | 12 | Provider, Agency, Assessor, Advisor — referenced in FRR rules |
| Certification | 15 | Certification Class, Package, Data — referenced in CPO/FRC/CDS |
| Vulnerability | 10 | Accepted/Ongoing/Overdue Vulnerability — referenced in VDR/VER |
| Assessment | 8 | Artifact, Assessor, Evidence — referenced in IVV/SDR |
| Incident | 6 | Incident, Impact, Affected Parties — referenced in IEC |
| Significant Changes | 7 | Adaptive/Transformative/Certification-Class — referenced in SCN |
| Information Resource | 5 | Machine/Human-Based — referenced in MAS/VDR |
| Accounts | 4 | User/Non-User accounts — referenced in IAM KSI |
| Customer Effect | 3 | Customer data, Customer-affecting — referenced in VDR/IEC |
| (untagged) | 5 | General-purpose terms |

UIAO emitters and adapters that produce OSCAL props citing FRR or KSI rules
must use the CR26 vocabulary exactly as defined in FRD. Notably:
- "Accepted Vulnerability" (FRD-ACV) is a term of art with a specific
  non-mitigation/non-remediation meaning — not to be confused with "acknowledged."
- "Adaptive Change" (FRD-ADP) has a narrower scope than "minor change" in prior
  FedRAMP guidance.
- "Assessor" (FRD-ASR) replaces "Third-Party Assessment Organization (3PAO)" as
  the official term.

---

## 9. CTL controls surface

The `CTL` section maps 14 NIST SP 800-53 control families to CR26 context. The
controls present in this section are the SP 800-53 controls that directly anchor
KSI indicator statements. This is not the full Rev5 Moderate baseline — it is the
CR26-selected evidence surface.

Families present: AC, AU, CA, CM, CP, IA, IR, MA, PS, RA, SA, SC, SI, SR.

The `fedramp-cr26-catalog` conformance adapter (ADR-061 D3) uses this CTL section
for DRIFT-PROVENANCE validation — if a control ID cited in a local KSI rule's
`Mappings.NIST_800-53` field does not resolve in the CTL section, the adapter
emits a drift finding.

---

## 10. References

- [ADR-126](../adr/adr-126-fedramp-cr26-official-rules-adoption.md) — governing ADR for this assessment
- [ADR-061](../adr/adr-061-fedramp-cr26-catalog-vendoring.md) — vendoring policy (amended by ADR-126)
- [ADR-106](../adr/adr-106-fedramp-20x-integration.md) — FedRAMP 20x integration
- [ADR-043](../adr/adr-043-fedramp-rfc-0026-ca7-integration.md) — RFC-0026 CA-7 integration
- [UIAO_137](./fedramp-cr26-ksi-mapping.md) — per-indicator KSI forward/reverse mapping
- [UIAO_133](./fedramp-20x-integration.md) — FedRAMP 20x integration spec
- [UIAO_132](./fedramp-rfc-0026-ca7-integration.md) — RFC-0026 CA-7 pathway spec
- [UIAO_022](./fedramp-oscal-package-spec.md) — OSCAL package generation spec
- [UIAO_138](./fedramp-3pao-evidence-interface.md) — 3PAO evidence interface
- Official JSON: `src/uiao/canon/compliance/reference/fedramp-cr26/official/fedramp-consolidated-rules.json`
- FedRAMP announcement: `https://www.fedramp.gov/2026-06-25-propelling-change-fedramp-launches-consolidated-rules-for-2026/`
