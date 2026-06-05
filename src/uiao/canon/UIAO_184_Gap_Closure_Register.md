---
document_id: UIAO_184
title: "Gap Closure Register — The Gap That Remains"
version: "1.0"
status: Current
classification: OPERATIONAL
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-05"
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
---

# Gap Closure Register — The Gap That Remains

> **Purpose.** This register is the machine-readable backing for the gap table in [`Book_15_CPT_23`](../../../docs/customer-documents/orgpath-narrative/Book_15_CPT_23.qmd) ("The Gap That Remains"). The narrative chapter argues that *naming the gaps in the governance record is itself a governance act*. This register operationalizes that argument: it turns the chapter's four named gaps into tracked workstreams with owning artifacts, closure criteria, and sequencing, so the gap table is regenerated from data rather than hand-asserted. Each closed item is a PR that flips a row here and cites the artifact that closed it.

## How to read this register

Each of the four gaps named in Chapter 23 maps to a **workstream** (A–D). For each workstream this register records: current state, the canonical artifact(s) that govern the work, the closure criterion, and dependencies. Status values: **Open** (no closure work landed), **In progress** (some closure work landed), **Closed** (criterion met).

## The four gaps (mirrors Book 15 / Chapter 23)

| # | Gap (Ch 23 wording) | Workstream | Status | Governing artifact |
|---|---|---|---|---|
| 1 | Four NIST 800-53 control families have no UIAO corpus coverage | A | In progress | `compliance-mapping.qmd §7`; [UIAO_185](UIAO_185_System_Security_Plan_Template.md) §4/§5 |
| 2 | Eighty-seven controls require new or amended documents | A | In progress | `compliance-mapping.qmd §7`; [UIAO_185](UIAO_185_System_Security_Plan_Template.md) / [UIAO_186](UIAO_186_Incident_Response_Plan.md) |
| 3 | Three planned PowerShell modules have specs but no implementation | B | In progress | [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md); UIAO_181/182/183 |
| 4 | OrgPath drift detection engine only partially implemented | C | In progress | [ADR-084](adr/adr-084-phase5-consumer-architecture.md); UIAO_163 |

> **Note on gaps 1 and the "four families."** Of the four uncovered families — **AT** (Awareness & Training), **MP** (Media Protection), **PE** (Physical & Environmental), **PS** (Personnel Security) — MP and PE are substantially **inherited** from the GCC-Moderate SaaS infrastructure and close via *inheritance declarations* in the SSP, not new programs. Only **AT** and **PS** are genuine documentation gaps requiring dedicated program docs. The headline count of "four" is accurate; the closure work is two programs plus two inheritance statements. This distinction is surfaced here so the SSP states it explicitly.

## Workstream A — Compliance documentation (Gaps 1 & 2)

The roadmap already exists in [`compliance-mapping.qmd §7`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd); this workstream **executes and formalizes** it rather than designing anew.

| Item | Closure criterion | Status |
|---|---|---|
| SSP Template (`PL-2`) — maps all 323 Moderate controls; states MP/PE inheritance | Authored, registered with a `UIAO_NNN` id | **Closed** — [UIAO_185](UIAO_185_System_Security_Plan_Template.md) |
| Incident Response Plan (`IR-1`…`IR-8`) | Authored, registered | **Closed** — [UIAO_186](UIAO_186_Incident_Response_Plan.md) |
| POA&M Template (`CA-5`) — auto-generatable from assessment output | Authored, registered | Open |
| Security Awareness & Training Program (`AT-1`…`AT-4`) — closes the **AT** family | Authored, registered | Open |
| Supply Chain Risk Management Plan (`SR-1`…`SR-12`) | Authored, registered | Open |
| Continuous Monitoring Strategy (`CA-7`) | Authored, registered | Open |
| Privacy Impact Assessment (PT family) | Authored, registered | Open |
| **Personnel Security Program (`PS-1`…`PS-9`) — closes the PS family** | Authored, registered | Open |
| 15 document amendments (`compliance-mapping.qmd §7.2`) | Each amendment merged | Open |

> The Personnel Security program is added here because `compliance-mapping.qmd §7` under-specifies it relative to the AT program, yet PS is one of the four named uncovered families. It is sequenced in Phase 3 alongside the PIA.

**Closure criterion for Gaps 1 & 2:** every new document above authored and registered in `document-registry.yaml`; the residual ~87-control count recomputed to zero genuine doc gaps. New compliance docs receive `UIAO_NNN` allocations as authored (not pre-allocated, to avoid registering paths that do not yet resolve and tripping the substrate walker's `DRIFT-PROVENANCE` check).

## Workstream B — PowerShell modules (Gap 3)

Governance scaffolding **landed**; implementation is the remaining work, in the dependency order fixed by [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md).

| Item | Closure criterion | Status |
|---|---|---|
| ADR-094 — toolchain doctrine, build order, signing/OSCAL contract | Merged | **Closed** |
| [UIAO_182](UIAO_182_UIAOImportAdapters_Module_Specification.md) — UIAOImportAdapters spec | Authored, registered | **Closed** (spec) |
| [UIAO_181](UIAO_181_UIAOIdentityAssessment_Module_Specification.md) — UIAOIdentityAssessment spec | Authored, registered | **Closed** (spec) |
| [UIAO_183](UIAO_183_UIAOPlanGenerators_Module_Specification.md) — UIAOPlanGenerators spec | Authored, registered | **Closed** (spec) |
| Implement UIAOImportAdapters (producer) | `.psd1`+`.psm1`+Pester under `tools/powershell/`, signed | Open |
| Implement UIAOIdentityAssessment (producer) | `.psd1`+`.psm1`+Pester under `tools/powershell/`, signed | Open |
| Implement UIAOPlanGenerators (consumer) — **highest value** | OrgPath-dependency-graph derivation, signed | Open |

**Closure criterion for Gap 3:** all three modules implemented, signed, Pester-tested, with output round-tripping the IR/OSCAL pipeline. The phrase "specifications but not implementations" in Ch 23 flips to "implemented" only when all three ship.

## Workstream C — OrgPath drift engine (Gap 4)

The plan is [ADR-084](adr/adr-084-phase5-consumer-architecture.md)'s Phase 5 sequence plus two classifier-level sub-gaps. The engine is substantially built (`src/uiao/governance/drift_engine.py`); DRIFT-SCHEMA / DRIFT-SEMANTIC / DRIFT-AUTHZ are complete.

| Item | Closure criterion | Status |
|---|---|---|
| `DRIFT-PROVENANCE` in-memory classifier (`classify_provenance_drift`) | Implemented in `src/uiao/governance/drift.py` with tests | **Closed** |
| Per-facet `DRIFT-IDENTITY` validation (Codebook membership) | Reintroduced post ADR-084 phases 1–5 | Open |
| ADR-084 consumer rebuilds (phases 1–5) | Each consumer module rebuilt (Model C) | Open |
| DriftEngine Model C orchestrator integration (phase 6) | Wired to rebuilt consumers | In progress |

**Closure criterion for Gap 4:** `DRIFT-PROVENANCE` and per-facet `DRIFT-IDENTITY` both detecting; ADR-084 phases 1–6 complete. Ch 23's "only partially implemented" flips to "implemented."

> **Landed in the same change that created this register:** `classify_provenance_drift` now exists in `src/uiao/governance/drift.py`, wired into the composite `classify_drift` between DRIFT-AUTHZ and DRIFT-SEMANTIC, covering envelope-completeness, integrity-seal, and citation-drift detection. This is the first row this register closes.

## Workstream D — Close the loop (the governance act)

This register **is** Workstream D. Closing the loop means:

1. Every closure is a PR that flips a status cell in this register and cites the closing artifact.
2. The Book 15 / Chapter 23 gap table is treated as **derived** from this register — when a workstream reaches Closed, the chapter row is updated to match, not the other way around.
3. `updated_at` in this register's frontmatter advances on every status change, giving the gap state an auditable timeline.

## Sequencing across workstreams

```
A.Phase1 (SSP/IR) ───► A.Phase2 (POA&M/AT/SR) ───► A.Phase3 (ConMon/PIA/PS)
B.1 scaffolding ✓ ───► B.2 Import → Identity → PlanGenerators
C.1 DRIFT-PROVENANCE ✓        C.2 DRIFT-IDENTITY ◄── blocked on ADR-084 ph1-5
D register ✓ ◄── all workstreams report status into this register
```

A.Phase1, B.2 (producers), and C.2's prerequisites have no cross-workstream blockers and can proceed in parallel. B.2's consumer (UIAOPlanGenerators) waits on its two producers per ADR-094.

## Change log

| Date | Change |
|---|---|
| 2026-06-05 | Register created (v1.0). Workstream B scaffolding (ADR-094 + UIAO_181/182/183) and Workstream C.1 (`DRIFT-PROVENANCE` classifier) landed and marked Closed. |
| 2026-06-05 | Workstream A Phase 1: SSP Template (UIAO_185) and Incident Response Plan (UIAO_186) authored and registered. Gaps 1 & 2 advanced to In progress. |

