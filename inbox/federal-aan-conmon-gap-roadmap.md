# Federal AAN / ConMon Compliance Gap Roadmap
**As of July 1, 2026 — Internal UIAO Working Document**

---

## Executive Finding

The Federal Application-Aware Networking (AAN) series (Parts 1–6, and Parts 7–11
in production) provides the **evidence generation layer** for FedRAMP 20x
continuous monitoring. It does not close every required NIST SP 800-53 control
family. Three families are structurally absent: **PM** (Program Management),
**PT** (Personally Identifiable Information Processing and Transparency), and
**SR** (Supply Chain Risk Management). SR is the most urgent due to the
BOD 26-04 VDR/VER deadline of **December 7, 2026**.

The Conformance Adapter / OSCAL Emitter framework provides the
**evidence governance layer** — tracking which evidence closes which control,
generating machine-readable KSI packages, and feeding the automated ConMon gate.
Without it, the AAN evidence exists but cannot be transmitted in the format
FedRAMP 20x evaluators ingest.

---

## Hard Deadlines

| Date | Event | Impact |
|------|--------|--------|
| **Aug 3, 2026** | FedRAMP 20x Class A opens | First submission window for new authorizations |
| **Aug 31, 2026** | Class B + C opens | GCC Moderate systems can begin |
| **Dec 7, 2026** | BOD 26-04 VDR/VER deadline | SBOM + vendor disclosure required; KSI-011–014 become evaluable |
| **Jan 1, 2027** | FedRAMP 20x mandatory | All new authorizations must use 20x; legacy Rev 5 path closes |
| **Jun 11, 2027** | New Rev 5 certs cease | No new legacy authorizations after this date |

---

## AAN Series Control Closure (Parts 1–11)

### Parts 1–6 (Production, 34 Controls)

| Part | Topic | Controls Closed |
|------|-------|-----------------|
| Part 1 | InfoBlox DDI (IPAM/DNS/DHCP/PKI) | 16 |
| Part 2 | SD-WAN, SASE, UC (Teams Phone, Amazon Connect) | 7 |
| Part 3 | Entra ID, ZTNA, Active Governance | 12 |
| Part 4 | SQL Server Authentication Modernization | (depth on IA family) |
| Part 5 | SQL Server Implementation Runbook | (procedural evidence) |
| Part 6 | Database Architecture / Network Physics | (depth on SC/SI families) |
| **Total** | | **34 distinct controls** |

### Parts 7–11 (In Production, ~55 Additional Controls)

| Part | Topic | Target Controls |
|------|-------|-----------------|
| Part 7 | Privileged Access Management (Entra PIM + PAW) | AC-5, AC-6(×7), AC-11/12, IA-11 |
| Part 8 | Vulnerability Management (Defender VM + KEV) | RA-5(×3), SI-2(×2), SI-5, CM-7(×2) |
| Part 9 | Data Protection (Purview + Key Vault CMK) | MP-2–5, SC-12/13/17/28, AU-10 |
| Part 10 | SIEM / XDR / Detection Engineering (Sentinel) | AU-6(×3), AU-7/8/11, SI-4(×4), IR-4/6/8 |
| Part 11 | Business Continuity / Contingency Planning | CP-2(×3), CP-3/4(×2), CP-6/7(×3), CP-8(×2) |

---

## Identified Gaps — Control Families Not Yet Covered

### Priority 1: SR — Supply Chain Risk Management (BOD 26-04 Gate)

The BOD 26-04 VDR/VER requirement activates on **December 7, 2026**.
KSI-011 through KSI-014 are currently `Status: scaffold` — non-evaluable
because the required SBOM + vendor disclosure evidence contract does not yet
exist. These controls cannot be closed by network architecture documents alone;
they require an SBOM generation pipeline and a VDR/VER submission process.

**Gap controls:** SR-1, SR-2, SR-3, SR-5, SR-6, SR-8, SR-10, SR-11

**Recommended approach:**
- Part 12: Supply Chain Risk Management — SBOM generation (Syft/Trivy),
  VDR format (CycloneDX or SPDX), VER submission process, vendor disclosure
  matrix. Must produce machine-readable artifacts the Conformance Adapter can
  reference before December 7, 2026.

### Priority 2: PM — Program Management

PM controls require organizational artifacts (security program plan, POA&M
process, authorization boundary documentation, metrics reporting). These are
governance documents, not technical implementations. They are a pre-condition
for the Authorization Package.

**Gap controls:** PM-1, PM-2, PM-5, PM-7, PM-9, PM-11, PM-14, PM-15, PM-30

**Recommended approach:**
- Part 13: Program Management Artifacts — boundary document template, security
  program plan outline, POA&M tracker template, metrics dashboard structure.
  Format as fillable DOCX templates since these are org-specific.

### Priority 3: PT — PII Processing and Transparency

PT controls are required for any system that processes PII. In the federal
GCC Moderate context this includes citizen-facing portals (N8NN, contact center)
and any HR/workforce system.

**Gap controls:** PT-1, PT-2, PT-3, PT-4, PT-5, PT-7

**Recommended approach:**
- Part 14: PII Processing and Transparency — privacy threshold analysis template,
  consent notice patterns, PII data flow mapping integrated with Purview
  sensitivity labels from Part 9.

### Priority 4: CR26 Breadth Gaps (FedRAMP 20x KSI Rules)

CR26 currently has rules for 21 of 46 controls (46%). Five themes have zero
rules: CED, INR, RPL, SCR, PIY. These map to the same PM/PT/SR gap areas.

**Recommended approach:**
- CR26 rules for CED/INR/RPL/SCR/PIY should be drafted as ADR-0xx (placeholder)
  after SR and PM artifacts are completed, so the rules reference real evidence.

---

## Conformance Adapter / OSCAL Emitter Gap

The AAN series generates evidence. The Conformance Adapter framework is the
governance layer that maps evidence → control → KSI and produces the OSCAL
AP/AR/POAM artifact bundle FedRAMP 20x evaluators ingest.

**Current state:**
- Conformance Adapter: schema defined, 4 of 6 surface slots in progress
- OSCAL Emitter: `Status: scaffold` — produces partial AP, no AR or POAM yet
- Evidence-to-KSI mapping table: partially authored in `KSI-*.qmd` files

**Blockers before OSCAL output is evaluable:**
1. All 6 surface slots must have at least one bound rule per KSI they contribute to
2. KSI-011–014 require SR artifacts (VDR/VER) before they can have bound rules
3. The OSCAL Emitter must be extended to produce AR (Assessment Results) with
   `satisfied`/`not-satisfied` status per KSI, not just AP (Plan)

---

## Sequenced Implementation Plan

### Phase 0 — Immediate (July 2026)
- [x] Parts 1–6 delivered (34 controls)
- [ ] Parts 7–11 delivered (est. July 2026, ~55 controls)
- [ ] Conformance Adapter surface slots 1–4 bound to AAN evidence

### Phase 1 — August 2026 (Class A / B+C opens)
- [ ] Part 12: SR / SBOM / VDR framework
- [ ] Conformance Adapter SR slot bound to Part 12 artifacts
- [ ] KSI-011–014 status upgraded from scaffold to active

### Phase 2 — September–October 2026
- [ ] OSCAL Emitter extended to produce AR with KSI verdicts
- [ ] Part 13: PM governance artifact templates
- [ ] CR26 rules for SR/PM families

### Phase 3 — November 2026 (BOD 26-04 runway)
- [ ] Part 14: PT / PII processing templates
- [ ] First complete OSCAL AP+AR+POAM bundle generated
- [ ] Pre-submission package review against FedRAMP 20x KSI checklist

### Phase 4 — December 2026 (pre-mandatory)
- [ ] BOD 26-04 VDR/VER submission (Dec 7)
- [ ] Authorization package submitted (Class B+C window)
- [ ] CR26 breadth gaps (CED/INR/RPL/SCR/PIY) filled

---

## Technology Recommendations by Gap

| Gap Area | Recommended Technology / Approach |
|----------|----------------------------------|
| SBOM generation | Syft (Anchore) or Trivy — integrated into CI/CD pipeline |
| VDR format | CycloneDX 1.6 (XML or JSON) — CISA-preferred |
| VER submission | CISA VEX Portal or email per BOD 26-04 guidance |
| OSCAL AP/AR | `trestle` (IBM) or custom Python emitter against OSCAL 1.1 schema |
| PII mapping | Purview Data Map + sensitivity label lineage (extends Part 9) |
| PM metrics | Sentinel workbook for AU/CA/PM KPI dashboard |

---

*This document is an internal UIAO working artifact. It does not constitute an
authorization package or official assessment. All control closure claims are
advisory pending formal ATO review.*
