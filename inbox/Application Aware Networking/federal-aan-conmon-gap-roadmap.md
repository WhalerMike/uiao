# Federal AAN / ConMon Compliance Gap Roadmap
**As of July 1, 2026 — Internal UIAO Working Document**

---

## Executive Finding

The Federal Application-Aware Networking (AAN) series (Parts 1–13, delivered
through July 2026) provides the **evidence generation layer** for FedRAMP 20x
continuous monitoring. Two control families remain structurally absent:
**PT** (Personally Identifiable Information Processing and Transparency) and
residual **SR/PM breadth** gaps. The most urgent remaining deadline is the
BOD 26-04 VDR/VER submission on **December 7, 2026** — SR and PM governance
artifacts are in place; the SBOM telemetry evaluation pipeline wiring is pending.

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

**Current state (updated 2026-07-03):**
- Conformance Adapter: all 6 surface slots bound to AAN evidence (slots 1–6 active;
  slot-06 now covers Parts 8, 10, 12, 13 — KSI-CMT / KSI-SCR)
- OSCAL Emitter: `src/uiao/oscal/ksi_ar.py` delivers OSCAL AR with per-KSI
  `satisfied`/`not-satisfied`/`other` verdicts; accessible via `uiao oscal ksi-ar`
- Evidence-to-KSI mapping table: `ksi-mapping.yaml` covers KSI-001–016;
  KSI-011–014 confidence `high` (Part 12 VER contract); KSI-015–016 confidence `low`
  (KSI-SCR scaffolds — SBOM telemetry pipeline wiring pending)
- Part 13 PM Governance Charter (Book_13): covers PM-1/2/5/7/9/11/14/15/30;
  SCRM governance charter satisfies PM-30 (BOD 26-04 organizational evidence)

**Remaining blockers before fully automated OSCAL output:**
1. KSI-011–016 `Status: scaffold` → `active` requires evaluation-engine wiring
   (automated eval logic, not just mapping confidence — ADR-111)
2. AP (Assessment Plan) generator not yet built; `import-ap` references `#`
3. CR26 breadth gaps (CED/INR/RPL/PIY themes) still have zero local rules

---

## Sequenced Implementation Plan

### Phase 0 — Immediate (July 2026)
- [x] Parts 1–6 delivered (34 controls)
- [x] Parts 7–11 delivered (~55 controls)
- [x] Conformance Adapter surface slots 1–4 bound to AAN evidence

### Phase 1 — Completed 2026-07-03 (ahead of Class A / B+C schedule)
- [x] Part 12: SR / SBOM / VDR framework (Book_12 — BOD 26-04 tiers, Syft, Grype, OpenVEX)
- [x] Conformance Adapter SR/security slots bound (slot-05 endpoint, slot-06 security)
- [x] KSI-011–014 mapping confidence upgraded low → high (VER contract via Part 12 + slot-06)
- [ ] KSI-011–014 Status: scaffold → active (evaluation engine wiring pending — ADR-111)

### Phase 2 — September–October 2026
- [x] OSCAL Emitter extended to produce AR with KSI verdicts
      (`src/uiao/oscal/ksi_ar.py` + `uiao oscal ksi-ar` CLI, 22 tests — 2026-07-03)
- [x] Part 13: PM governance artifact templates (Book_13 — PM-1/2/5/7/9/11/14/15/30,
      SCRM charter satisfying PM-30 — 2026-07-03)
- [x] CR26 rules for SR/PM families (KSI-015 KSI-SCR-MIT + KSI-016 KSI-SCR-MON,
      scaffold confidence:low — 2026-07-03)

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
