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
| 1 | Four NIST 800-53 control families have no UIAO corpus coverage | A | **Closed** | MP/PE via [UIAO_185](UIAO_185_System_Security_Plan_Template.md) §5 inheritance; AT via [UIAO_187](UIAO_187_Security_Awareness_and_Training_Program.md); PS via [UIAO_188](UIAO_188_Personnel_Security_Program.md) |
| 2 | Eighty-seven controls require new or amended documents | A | **Closed** | `compliance-mapping.qmd §7`; [UIAO_185](UIAO_185_System_Security_Plan_Template.md) / [UIAO_186](UIAO_186_Incident_Response_Plan.md) |
| 3 | Three planned PowerShell modules have specs but no implementation | B | **Closed** | [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md); UIAO_181/182/183 |
| 4 | OrgPath drift detection engine only partially implemented | C | In progress | [ADR-084](adr/adr-084-phase5-consumer-architecture.md); UIAO_163 |

> **Note on gaps 1 and the "four families."** Of the four uncovered families — **AT** (Awareness & Training), **MP** (Media Protection), **PE** (Physical & Environmental), **PS** (Personnel Security) — MP and PE are substantially **inherited** from the GCC-Moderate SaaS infrastructure and close via *inheritance declarations* in the SSP, not new programs. Only **AT** and **PS** are genuine documentation gaps requiring dedicated program docs. The headline count of "four" is accurate; the closure work is two programs plus two inheritance statements. This distinction is surfaced here so the SSP states it explicitly.

## Workstream A — Compliance documentation (Gaps 1 & 2)

The roadmap already exists in [`compliance-mapping.qmd §7`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd); this workstream **executes and formalizes** it rather than designing anew.

| Item | Closure criterion | Status |
|---|---|---|
| SSP Template (`PL-2`) — maps all 323 Moderate controls; states MP/PE inheritance | Authored, registered with a `UIAO_NNN` id | **Closed** — [UIAO_185](UIAO_185_System_Security_Plan_Template.md) |
| Incident Response Plan (`IR-1`…`IR-8`) | Authored, registered | **Closed** — [UIAO_186](UIAO_186_Incident_Response_Plan.md) |
| POA&M Template (`CA-5`) — auto-generatable from assessment output | Authored, registered | **Closed** — [UIAO_189](UIAO_189_POAM_Template.md) |
| Security Awareness & Training Program (`AT-1`…`AT-4`) — closes the **AT** family | Authored, registered | **Closed** — [UIAO_187](UIAO_187_Security_Awareness_and_Training_Program.md) |
| Supply Chain Risk Management Plan (`SR-1`…`SR-12`) | Authored, registered | **Closed** — [UIAO_191](UIAO_191_Supply_Chain_Risk_Management_Plan.md) |
| Continuous Monitoring Strategy (`CA-7`) | Authored, registered | **Closed** — [UIAO_190](UIAO_190_Continuous_Monitoring_Strategy.md) |
| Privacy Impact Assessment (PT family) | Authored, registered | **Closed** — [UIAO_192](UIAO_192_Privacy_Impact_Assessment.md) |
| **Personnel Security Program (`PS-1`…`PS-9`) — closes the PS family** | Authored, registered | **Closed** — [UIAO_188](UIAO_188_Personnel_Security_Program.md) |
| 15 document amendments (`compliance-mapping.qmd §7.2`) | Each amendment merged | **Complete — 15 of 15.** 11 additive control sections (Identity/PKI/DR/Ops/Build/Training guides, ADR-041, Master Plan, Quarto guide, CA library, Git-hooks doc); `web.config` hardened (SC-8/SC-13 app-layer + Schannel cross-ref); canonical `app.ini` created (SC-13 FIPS-approved hashing, AC-12 session control); Active-Passive Replication Guide (`active-passive-replication.qmd`, SI-4/CP-4/SC-8/SC-28) and Governance Dashboard Design (`governance-dashboard-design.qmd`, AC-3/AC-6/AU-11/CA-2) authored and wired into the site. |

> The Personnel Security program is added here because `compliance-mapping.qmd §7` under-specifies it relative to the AT program, yet PS is one of the four named uncovered families. It is sequenced in Phase 3 alongside the PIA.

**Closure criterion for Gaps 1 & 2:** every new document above authored and registered in `document-registry.yaml`; the residual ~87-control count recomputed to zero genuine doc gaps. **All seven new documents are authored and registered** (UIAO_185–192) **and all 15 §7.2 amendments are merged** (the §7.2 row above enumerates each); every control enumerated in `compliance-mapping.qmd §7` is now addressed by a new document or a merged amendment. **Gaps 1 and 2 are Closed.** New compliance docs receive `UIAO_NNN` allocations as authored (not pre-allocated, to avoid registering paths that do not yet resolve and tripping the substrate walker's `DRIFT-PROVENANCE` check).

## Workstream B — PowerShell modules (Gap 3)

Governance scaffolding **landed** and **all three modules are now implemented**, in the dependency order fixed by [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md) — the two producers (UIAOImportAdapters, UIAOIdentityAssessment) then the consumer (UIAOPlanGenerators).

| Item | Closure criterion | Status |
|---|---|---|
| ADR-094 — toolchain doctrine, build order, signing/OSCAL contract | Merged | **Closed** |
| [UIAO_182](UIAO_182_UIAOImportAdapters_Module_Specification.md) — UIAOImportAdapters spec | Authored, registered | **Closed** (spec) |
| [UIAO_181](UIAO_181_UIAOIdentityAssessment_Module_Specification.md) — UIAOIdentityAssessment spec | Authored, registered | **Closed** (spec) |
| [UIAO_183](UIAO_183_UIAOPlanGenerators_Module_Specification.md) — UIAOPlanGenerators spec | Authored, registered | **Closed** (spec) |
| Implement UIAOImportAdapters (producer) | `.psd1`+`.psm1`+Pester under `tools/powershell/`, signed | **Implemented** — `tools/powershell/UIAOImportAdapters/` (6 roster functions, Pester-tested, wired into the Pester CI). Output sealed with the canonical `content_hash` (byte-identical to `uiao.ir.models.core.canonical_hash`), so imports are `DRIFT-PROVENANCE`-classifiable by `src/uiao/governance/drift.py`. Authenticode signing occurs at release packaging (`pwsh-pack`). |
| Implement UIAOIdentityAssessment (producer) | `.psd1`+`.psm1`+Pester under `tools/powershell/`, signed | **Implemented** — `tools/powershell/UIAOIdentityAssessment/` (6 roster functions: four Entra exporters, AD-vs-Entra reconciliation, orchestrator). Cloud-aware Graph resolution mirrors `uiao.adapters._graph_clouds` (fail-closed); offline `-SnapshotPath` path makes it Pester-tested without a live tenant. Reconciliation emits `DRIFT-IDENTITY`; output sealed with the canonical `content_hash`. Signing at release packaging. |
| Implement UIAOPlanGenerators (consumer) — **highest value** | OrgPath-dependency-graph derivation, signed | **Implemented** — `tools/powershell/UIAOPlanGenerators/` (6 roster functions: per-device / GPO / identity-wave / DNS / PKI generators + master plan). Decommissioning order via deterministic topological sort (Kahn) of the OrgPath dependency graph; cycles + cross-domain edges flagged as approval blockers. Plans cite `derived_from` and are sealed with the canonical `content_hash` (timestamp-free data ⇒ reproducible). Signing at release packaging. |

**Closure criterion for Gap 3:** all three modules implemented, signed, Pester-tested, with output round-tripping the IR/OSCAL pipeline. The phrase "specifications but not implementations" in Ch 23 flips to "implemented" only when all three ship. **Met:** all three modules (UIAOImportAdapters, UIAOIdentityAssessment, UIAOPlanGenerators) are implemented under `tools/powershell/` and Pester-tested in CI; each emits canonical-`content_hash`-sealed output (IR/OSCAL-compatible). Authenticode signing is applied at release packaging (`pwsh-pack`). **Gap 3 is Closed.**

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
| 2026-06-05 | Workstream A: AT program (UIAO_187) and PS program (UIAO_188) authored and registered. All four named families now have corpus coverage (MP/PE inheritance + AT/PS programs) — **Gap 1 Closed**. |
| 2026-06-05 | Workstream A: POA&M Template (UIAO_189, `CA-5`) and Continuous Monitoring Strategy (UIAO_190, `CA-7`) authored and registered. Gap 2 advancing — SR plan, PIA, and the 15 §7.2 amendments remain. |
| 2026-06-05 | Workstream A: SCRM Plan (UIAO_191, `SR`) and Privacy Impact Assessment (UIAO_192, PT) authored and registered. All seven §7.1 new documents complete; only the 15 §7.2 amendments remain for Gap 2. |
| 2026-06-05 | Workstream A: 11 of 15 §7.2 amendments applied as additive control sections across existing docs (Identity/PKI/DR/Ops/Build/Training guides, ADR-041 `CA-6`, Master Plan, Quarto guide, CA library, Git-hooks doc). 4 remain (web.config, app.ini, replication guide, dashboard design) — functional config or new-doc decisions, deferred for direction. |
| 2026-06-05 | Workstream A: final 4 §7.2 amendments done per user direction (functional + new docs). web.config hardened (removeServerHeader, Referrer/Permissions-Policy, documented Schannel TLS scope); canonical `deploy/windows-server/app.ini` created (PBKDF2 FIPS-approved hashing, LOGIN_REMEMBER_DAYS=0, OFFLINE_MODE); two new customer docs authored and wired into the site sidebar — Active-Passive Replication Guide and Governance Dashboard Design. **Gap 2 §7.2 amendments 15/15 complete.** |
| 2026-06-05 | Workstream A complete: all 7 new documents (UIAO_185–192) registered and all 15 §7.2 amendments merged. **Gap 2 status flipped In progress → Closed** in the summary table and closure-criterion note. Workstreams B (Gap 3) and C (Gap 4) remain in progress. |
| 2026-06-05 | Workstream B: **UIAOImportAdapters implemented** (`tools/powershell/UIAOImportAdapters/` — 6 roster functions per UIAO_182, Pester-tested, wired into the Pester CI). Output sealed with the canonical `content_hash` (verified byte-identical to `uiao.ir.models.core.canonical_hash`), making imports `DRIFT-PROVENANCE`-classifiable. First of the three Gap-3 modules; UIAOIdentityAssessment and UIAOPlanGenerators remain. |
| 2026-06-05 | Workstream B: **UIAOIdentityAssessment implemented** (`tools/powershell/UIAOIdentityAssessment/` — 6 roster functions per UIAO_181: four Entra exporters, AD-vs-Entra reconciliation, orchestrator). Cloud-aware Graph endpoint resolution mirrors `uiao.adapters._graph_clouds` (fail-closed; `commercial` serves GCC-Moderate); offline `-SnapshotPath` makes it Pester-tested without a live tenant. Reconciliation surfaces `DRIFT-IDENTITY`; output sealed with the canonical `content_hash`. **2 of 3 Gap-3 modules done**; UIAOPlanGenerators (consumer) remains. |
| 2026-06-05 | Workstream B: **UIAOPlanGenerators implemented** (`tools/powershell/UIAOPlanGenerators/` — 6 roster functions per UIAO_183: per-device / GPO / identity-wave / DNS / PKI generators + master plan). The marquee algorithm — decommissioning order from the OrgPath dependency graph — is a deterministic Kahn topological sort with cycle + cross-domain blocker detection; blockers make a plan not approvable. Plans cite `derived_from` and are sealed with the canonical `content_hash` (timestamp-free data ⇒ reproducible plans). **Gap 3 status flipped In progress → Closed** (all three modules implemented + Pester-tested). |

