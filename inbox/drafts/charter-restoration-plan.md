---
title: "Charter Restoration Plan — Layered Restoration, Compliance-First Sequencing"
status: draft
authored_by: "Claude (session w/ Mike Stratton, 2026-05-04)"
intent: "Layered-restoration plan; charter binding above current operational stack; small additive PRs (PR-A through PR-L)"
revision_history:
  - "v1 (2026-05-04): Identified V3 as charter, drafted 6-PR plan"
  - "v2 (2026-05-04): TwoPager added, charter set expanded to 4 (CHARTER-001..004)"
  - "v3 (2026-05-04): V3 explicitly superseded by V4U (Mar 7), then UIAO-V1 (Mar 9). UIAO-V1 is the actual current charter. Charter set expanded to ~10 docs across 3 iterations."
  - "v4 (2026-05-04): MAJOR FRAMING CORRECTION — retract 'drift/overlay' framing for governance/compliance work. Repo correctly prioritized compliance perimeter under non-optional forcing functions (Microsoft vendor pressure to Entra/Intune/Azure ARC; mandatory EOs/NIST/FedRAMP/CISA; E911 federal law; new government-wide initiatives like HRIT and FRPP MS landing weekly). Three-tier mental model adopted: Charter / Compliance Perimeter / Regulatory Absorption. Layered-restoration plan (PR-A through PR-L) replaces reset plan."
  - "v5 (2026-05-05): Architect decisions on all 6 pending items. Charter base confirmed (UIAO-V1 = CHARTER-001, V4U feeders = CHARTER-002..005, V3 = CHARTER-V3-LEGACY). Personal-doc exclusion list confirmed. Telemetry $16.3B PDF + V4 .jpg files BOTH confirmed for ingestion. OMB M-21-31 reconciled into long-form CHARTER-001. Decision #5: agent audit found AtoBZ_clean.md has LOW hallucination risk (~4 invented acronyms) but SEVERE structural corruption (~50% duplicated content, mid-word truncation); AtoBZ and V4U_Master_Reference are complementary not overlapping; ingest BOTH after preprocessing AtoBZ. PR-A fully unblocked."
---

# Charter Restoration Plan (Revision 5 — Architect Decisions Confirmed)

## Architect decisions (2026-05-05) — five of six settled

| # | Decision | Resolution |
|---|---|---|
| 1 | Charter base / supersession chain | **UIAO-V1 = `CHARTER-001` (authoritative current charter); V4U content = `CHARTER-002..005` (feeders); V3 = `CHARTER-V3-LEGACY` (historical predecessor, explicitly superseded by V4U)** |
| 2 | Personal-doc exclusion | **Confirmed — exclude:** `Federal_Resume_Reformatted_v2.docx/pdf`, `CIO Level Resume.docx`, `Download Benefit Summary and Service Verification Letter.pdf`, `1F0840.docx`. Add to ingestion blocklist; do NOT ingest under any tier. |
| 3 | Telemetry $16.3B PDF (`Federal Cloud Telemetry Gap...$16.3B Annual 'Blind Ticket' Tax.pdf`) | **Ingest** as `CHARTER-EVIDENCE-TELEMETRY` — supporting evidence for the telemetry-as-control thesis (V4U §10) |
| 4 | V4 `.jpg` working diagrams | **Ingest** as canonical reference diagrams. They confirm load-bearing concepts (Conversation as a layer, V4U Identity-Forward Architecture branding, Source of Authority Chain). PR-A inventories and ingests under `src/uiao/canon/charter/diagrams/`. |
| 5 | `AtoBZ_clean.md` vs `V4U_Master_Reference` reconciliation | **RESOLVED — ingest BOTH per audit (path b + c hybrid).** Agent audit (2026-05-05) found low hallucination risk (only ~4 invented acronyms) but **severe structural corruption** — `AtoBZ_clean.md` is ~50% duplicated content (Appendices A-Z and AA-AZ each emitted twice) and ends mid-word at line 35669 (`## 1. Introducti`). Critically, AtoBZ and V4U_Master_Reference are **complementary, not overlapping**: V4U holds strategic + Federal Mandate Crosswalk + Source of Authority + NPE Assurance + 17-Point Canon; AtoBZ holds 52 abstract object-model appendices. **Ingest both, with AtoBZ cleaned first.** See "AtoBZ Audit Findings" section below. |
| 6 | OMB M-21-31 (TwoPager-only mention) | **Reconcile** into long-form `CHARTER-001` so all charter docs cite the same federal mandate set. Audit other potential mandate-citation gaps between long-form and short-form charter docs in same pass. |

**PR-A is now FULLY UNBLOCKED.** PR-A scope:

- Ingest `CHARTER-001` (UIAO-V1 main spec, `UIAO-Main-Spec-v1.md` Mar 9) with light editorial pass
- Ingest `CHARTER-001-APPENDICES` (cleaned `AtoBZ_clean.md` — see preprocessing checklist below)
- Ingest `CHARTER-002` (V4U_Core_Canon_Introduction)
- Ingest `CHARTER-003` (V4U_Master_Reference — strategic content + Federal Mandate Crosswalk + Source of Authority chains + NPE Assurance + 17-Point Canon. **NOT superseded by AtoBZ; complementary content.**)
- Ingest `CHARTER-004-NPE` (Federal_Identity_Fragmentation_and_NPE_Assurance_Model)
- Ingest `CHARTER-005-SOA` (Source_of_Authority_Location_InterAgency)
- Ingest `CHARTER-V3-LEGACY` (V3 long-form + TwoPager) with light editorial pass; mark explicitly superseded by CHARTER-001..005
- Ingest `CHARTER-EVIDENCE-TELEMETRY` (Federal Cloud Telemetry Gap PDF)
- Ingest `CHARTER-001-DIAGRAMS` (V4 .jpg files inventoried)
- Add OMB M-21-31 reconciliation across all charter docs in same pass
- **Author reconciliation ADR** ("Charter Reconciliation — V4U Strategic Layer vs AtoBZ Appendix Layer") explaining the V4U/AtoBZ scope split as deliberate complementary canon, not redundant content
- Carry `tier: foundational, supersedable: false (except V3-LEGACY), load_order: 0` metadata on all
- Apply explicit non-ingest blocklist for personal docs

## AtoBZ Audit Findings (2026-05-05) — required preprocessing before CHARTER-001-APPENDICES ingestion

Agent audit summary:

| Finding | Severity | Evidence |
|---|---|---|
| Hallucination risk | **LOW** | Only ~4 invented acronyms (`UAI` line 22, `UCI-X` line 7607, "UIAO Autonomous Operations Fabric" line 283, "UIAO Assurance and Governance Fabric" line 7876). No fake citations, no fabricated stats, no fake agency case studies. |
| Federal citations | Clean but thin | Only NIST SP 800-207 / 800-63 / 800-53 / 800-157 + OMB M-22-09 cited. No invented mandates. Suspiciously sparse for a "publication-grade canon" — Copilot may have run out of trained-on citations and recycled. |
| Vendor product claims | Clean | Only Entra ID, Login.gov, ID.me, PIV/CAC, SPIFFE/SPIRE named. No invented APIs, no fictional product features. |
| Cross-references | Clean | Zero "see Appendix X" / "Section Y" matches — every appendix is self-contained. (Avoids broken refs but flags lack of integration.) |
| **Structural corruption** | **SEVERE** | Appendix A duplicated at lines 288 + 8462 (identical prose); Appendix Z appears 3 times (lines 2, 8176, 16350); A-Z emitted twice (288-8175, 8462-16350); AA-AT and AL-AY emitted twice; AA-AZ emitted twice (20019-25640, 29670-35660). File ends mid-word at line 35669. **~50% of file is verbatim duplication.** |
| Total file size | 35,669 lines | After dedup: ~17,500 lines |
| Conversion artifacts | Multiple | Garbled metadata bullet lists (e.g. lines 16399-16461); heavy non-breaking hyphen noise (`‑`); pandoc-style truncation. |

**Preprocessing checklist for CHARTER-001-APPENDICES:**

1. Deduplicate appendices A-Z and AA-AZ (keep canonical first occurrence; verify they're truly identical before dropping the second)
2. Recover the truncated tail of Appendix AL (the cliffhanger "## 1. Introducti" at line 35669 — likely lives in the source file `AtoBZ_clean.md` was concatenated from; check OneDrive UIAO-V1 folder for predecessor docs)
3. Normalize non-breaking hyphens (`‑` → `-`) and other em-dash artifacts
4. Repair garbled metadata bullet lists at lines 16399-16461 and similar locations
5. Annotate the four invented acronyms (UAI, UCI-X, "Operations Fabric", "Governance Fabric") as Copilot-assisted derived terms; flag for architect confirmation that these are intended canon (or replace with V3/V4U-consistent terminology)
6. Verify post-cleanup file is structurally sound before ingesting

**Audit confidence: HIGH.** The corruption is mechanical and the V4U/AtoBZ complementary-scope split is unambiguous. AtoBZ cleaned ≈ 95% canon-quality content of the ~50% unique material.

# Charter Restoration Plan (Revision 4 detail follows)

## Framing correction — what this plan IS and IS NOT

**This is NOT a 'fix the drift' plan.** Earlier revisions of this draft used "drift" and "post-V3 governance overlay" language for the repo's governance/compliance work. That framing was wrong. The repo correctly prioritized the compliance perimeter under non-optional forcing functions:

- **Microsoft vendor pressure** is forcing federal agencies onto Entra ID, Intune, and Azure ARC. The repo's `entra` adapter, OrgPath / Three-plane device model, and identity-directory transformation specs (UIAO_135-139) exist *because Microsoft is forcing the transition*. Not optional.
- **Mandatory federal regime** — EO 14028 / 14306, NIST 800-53 Rev 5, FedRAMP Rev 5, CISA SCuBA, BOD 25-01 and successors, OMB memos — these are *operating-license requirements*, not governance flavor. Non-compliance = legal exposure.
- **E911 is federal law** — RAY BAUM's Act, Kari's Law, FCC dispatchable-location rules. UIAO-V1 named E911 7+ times; the repo has zero implementation. This is a **legal gap with real consequences**, not a "would-be-nice."
- **Government-wide initiatives ship weekly** — HRIT (Human Resources Information Technology) and FRPP MS (Federal Real Property Profile, Microsoft variant) landed *this week*. The canon must be able to absorb federal-speed regulatory drops as a structured intake, not ad-hoc.

**"The Compliance and Governance correctly became very important to UIAO"** (architect, 2026-05-04). The plan respects this: existing governance/compliance/transformation/SCuBA/boundary work is correct and stays untouched. The plan adds the *charter binding* and *operational-vision restoration* on top, additively.

## Three-tier mental model

| Tier | Source | Stability | Update cadence |
|---|---|---|---|
| **Charter** | UIAO-V1 (CHARTER-001) + V4U feeders + V3 LEGACY | High — amendments require explicit ADR | Rare (years) |
| **Compliance Perimeter (Implementation)** | Current repo: SCuBA, Transformation, Boundary work, OSCAL, KSI, ConMon, Drift taxonomy, Adapter taxonomy, Evidence Graph, CQL, Enforcement Runtime | Medium — extends as the regulatory perimeter expands | Quarterly |
| **Regulatory Absorption Layer** | New: HRIT, FRPP MS, E911 implementation, Microsoft-forced transition rationale, future BODs/EOs/initiatives | Fast — must absorb federal-speed regulatory drops | Weekly to monthly |

The repo today has the Compliance Perimeter implemented. It lacks: (a) the Charter binding above it; (b) a structured Regulatory Absorption Layer pattern below it; (c) the deferred operational-vision planes (Conversation, Overlay, public-service citizen flows).

## Diagnosis (factual, framing corrected)

The pre-GitHub foundational work for UIAO progressed through three iterations between Feb 26 and Mar 9, 2026 — none of which were ingested into the repo canon:

```
V3 (Feb 26)  →  V4 / V4U (Mar 7-9)  →  UIAO-V1 (Mar 9)  →  [GitHub repo begins, Compliance Perimeter built]
```

Each iteration explicitly built on or superseded the previous one. **None made it into `src/uiao/canon/`.** The `V4U_Core_Canon_Introduction.docx` line 5 states explicitly: **"Supersedes: V3 Introduction"**. UIAO-V1 (Mar 9, post-V4U merger) is the most recent and most refined.

The repo's current AGENTS.md describes the substrate's governance/compliance implementation but does not surface the charter that scopes UIAO's broader purpose. This is the **narrative gap** the plan addresses — the *content* (Compliance Perimeter implementation) is correct; the *framing* (presenting it as the whole purpose) needs the charter binding above it to be honest about scope vs. implementation.

## Source-of-truth chronology

| Date | Folder | Files | Status |
|---|---|---|---|
| **Feb 26** | `V3/` | Introduction (long-form), TwoPager | Original whitepaper — **superseded by V4U** |
| Mar 5 | `V3/` | (resumes, benefits letter, 1F0840) | **Personal docs — not architecture, do NOT ingest** |
| **Mar 7** | `V4/Backup/` | V4G/V4P/V4C audience variants, NPE Assurance, Source of Authority + InterAgency, V4U Outline, "replace V3" rationale, Federal Modernization Summary | V4 working drafts → fed into V4U |
| Mar 7-9 | `V4/` | V4U_Core_Canon_Introduction, V4U_Master_Reference, Intro to Unified UIAO | V4U unified merge of V4G/V4P/V4C |
| **Mar 9** | `UIAO-V1/` | UIAO Main Spec V1 (md+docx), AtoBZ_clean.md (928KB master appendix), Appendix E Policy Architecture, Federal IT Structure Analysis (most recent: Mar 9 20:25) | **Current authoritative charter** |
| Mar 9 → present | `Telemetry/` | Federal Cloud Telemetry Gap PDF ($16.3B Blind Ticket Tax) | Supporting evidence |

## Personal documents — explicit non-ingest list

These sit in the V3/ folder for OneDrive hygiene reasons but are NOT architecture canon:

| File | Reason |
|---|---|
| `V3/Federal_Resume_Reformatted_v2.docx` / `.pdf` | Personal resume |
| `V3/CIO Level Resume.docx` | Personal resume |
| `V3/Download Benefit Summary and Service Verification Letter.pdf` | Personal benefits doc |
| `V3/1F0840.docx` | Likely federal HR form (personal) |
| `V4/*.jpg` (multiple) | Working diagrams — need user judgment per file; default to skip |

If any future session is asked to "ingest the V3 folder," these must be excluded by name. Architect should confirm whether to physically separate personal docs from architecture docs in OneDrive going forward.

## What the repo is missing — full picture

### From V3 (still load-bearing in V4U/UIAO-V1):

- **Conversation as atomic unit** — central V3 primitive, retained as #1 in V4U §6 Seven Fundamental Concepts
- **Public Service First** — explicit V4U §6 #7
- **Specific tool stack** — MINR, NSX, Catalyst SD-WAN, Riverbed AppResponse / NetProfiler, ThousandEyes, ACME PKI, Login.gov, RealID, Intune, CyberArk/BeyondTrust PAM, FIPS 140-3 enforcement
- **Six layers** including Conversation State (silently substituted with "Management" in repo)

### NEW in V4U / UIAO-V1 (post-V3, pre-GitHub, also missing):

- **The "Identity-Forward Architecture" framing** (visible in user-supplied diagrams as "V4U Identity-Forward Architecture")
- **Core thesis: "Federal government structurally frozen at the Client/Server L2-L4 perimeter era"**
- **Operational design principle: "If it degrades the citizen interaction, it does not ship"** — ship-gate, not value statement
- **Seven (not six) Fundamental Concepts** — V4U §6 explicitly enumerates 7, with Public Service First numbered as #7
- **SSOT vs SoA distinction** — Source of Authority is a separate, complementary primitive to SSOT. Repo's UIAO_001 conflates these. V4U enumerates 12 SoA domains
- **Boundary as a distinct architectural layer** — V4U §9 names "Addressing AND Boundary" layers separately. Repo six-plane model omits Boundary
- **Eight Frozen Domains diagnosis** (V4U §2) — Identity, Addressing, Network Security, Endpoint Management, Application Delivery, Telemetry, Governance, Data Protection
- **17-Point Modernization Canon** (V4U §5) — three-tier diagnostic framework (Historical Foundations, Structural Constraints, Modern Requirements)
- **Federal Mandate Convergence table** — OMB M-22-09, CISA ZTMM v2, FedRAMP Rev 5, NIST 800-207, EO 14028, NIST 800-63-4, TIC 3.0 → architecture answers
- **Federal Identity Fragmentation / NPE Assurance Model** — separate canon doc, V4/Backup
- **Source of Authority Location InterAgency** — separate canon doc, V4/Backup
- **Document audience-tier navigation** — V4U/UIAO-V1 specs include a "How to Read This Document" table mapping audiences (CIO/CISO, Architect, Implementation Engineer, Program Manager, Compliance/Legal) to section ranges and appendix references
- **OMB M-21-31** logging maturity (EL3) — mentioned in TwoPager only

### Inferred from UIAO-V1 / AtoBZ structure (not yet read in detail):

The 928KB `AtoBZ_clean.md` is the master A-Z appendix canon. UIAO-V1 main spec references appendices A through ~CA covering: Identity Architecture, Addressing Architecture, Boundary Architecture, Telemetry, Policy Architecture, Identity Lifecycle (JML), Layered Architecture, Playbooks, Pilot Plan, Identity Risk & Assurance, Telemetry Integrity & Correlation, Policy Graph & Rule Semantics, Runtime Model & Evaluation Engine, Federal Identity Regimes, Federal Authority Chains, Citizen Identity Architecture, UIAO Runtime Semantics, Identity-Address-Boundary Triangulation. **Most or all of this content is missing from the repo.**

## Final charter set (Revision 3 — to be confirmed by architect)

| Charter ID | Source | Role | Read status |
|---|---|---|---|
| **CHARTER-001** | `UIAO-V1/UIAO-Main-Spec-v1.md` (Mar 9) | **Authoritative current charter** | Read ~500 of 17K lines |
| **CHARTER-001-A** | `UIAO-V1/UIAO Main Specification V1.docx` | Formatted version of CHARTER-001 | Not read |
| **CHARTER-001-APPENDICES** | `UIAO-V1/AtoBZ_clean.md` (928KB) | Master A-Z appendix canon | Not read |
| **CHARTER-001-POLICY-E** | `UIAO-V1/Appendix E Policy Architecture.docx` | Policy Architecture appendix (standalone) | Not read |
| **CHARTER-001-IT-STRUCTURE** | `UIAO-V1/Federal_IT_Structure_Analysis.docx` (Mar 9 20:25, most recent) | Federal IT structure analysis | Not read |
| **CHARTER-002-NPE** | `V4/Backup/Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md` | NPE Assurance Model | Not read |
| **CHARTER-003-SOA** | `V4/Backup/Source_of_Authority_Location_InterAgency.md` | Source of Authority + InterAgency chains | Not read |
| **CHARTER-004-EXEC** | `V4/V4U_Core_Canon_Introduction.docx` | Executive readable intro | Read |
| **CHARTER-005-MASTER** | `V4/V4U_Master_Reference_All_Sections.docx` | Master reference (likely overlaps with CHARTER-001-APPENDICES) | Not read — confirm overlap before ingest |
| **CHARTER-V3-LEGACY** | `V3/Introduction docx` + TwoPager | Historical predecessor (explicitly superseded), retained for provenance | Read |
| **CHARTER-EVIDENCE-TELEMETRY** | `Telemetry/Federal Cloud Telemetry Gap...$16.3B...PDF` | Supporting evidence for telemetry-as-control thesis | Not read |

All `CHARTER-*` docs at `tier: foundational, supersedable: false (except V3-LEGACY), load_order: 0`.

**Light editorial pass** on all (architect decision #1 from prior session): drop drafting metadata, author meta-frames, drafting-artifact appendices.

## Decisions still needed before PR 1 can be drafted

1. **Charter base** — Confirm UIAO-V1 (Mar 9) as `CHARTER-001`, V4U as feeders (CHARTER-002-005), V3 as `CHARTER-V3-LEGACY`?
2. **Personal docs** — Confirm exclusion list above is correct; flag any false positives
3. **Telemetry $16.3B PDF** — Ingest as supporting evidence reference, or out of scope?
4. **V4 .jpg files** — Skip all, or are any canonical reference diagrams that should be ingested?
5. **CHARTER-005-MASTER vs CHARTER-001-APPENDICES** — V4U_Master_Reference (Mar 7) and AtoBZ_clean (Mar 9) likely overlap. Read both before ingest, then ingest the merged authoritative version, or ingest both and reconcile via ADR?
6. **OMB M-21-31** (TwoPager-only mandate) — keep audience-specific or reconcile into long-form charter?

## What stays untouched (the operational guardrail)

These streams are operationally live with federal-agency impact and are NOT touched by any PR in this plan:

- **SCuBA work** — UIAO_002 spec, ScubaGear adapter, SCUBA_TO_KSI_MAP, ConMon orchestration. KSI evaluation flows depend on it.
- **Transformation work** — UIAO_135-139 (D1.1 specs from #305), OrgPath / Three-plane device model (ADR-034, ADR-038), BlueCat/Infoblox modernization adapters. Federal-agency directory transformation in progress.
- **Boundary work** — gcc-boundary-probe (#308), FINDING-002..009 (#307), gcc-boundary-gap-registry, SentinelProbe + KQL queries. **Federal Moderate agencies depend on this getting fixed; this is the urgent operational work.**
- **ScubaGear upstream pin** and adapter conformance flow
- **Existing CI gates** and their behavior on existing canon
- **Document registry tier structure** — current numbering preserved
- **Existing UIAO_NNN locations and IDs** — no renames, no moves

## Sequencing — Layered Restoration (PR-A through PR-L, additive only)

Small additive PRs, each independently revertible, none touching operational work in flight:

### Phase 1: Charter binding (PR-A through PR-D)

- **PR-A (1 day):** Charter ingestion. New `src/uiao/canon/charter/` directory. Ingests CHARTER-001 (UIAO-V1) + CHARTER-002..N (V4U feeders) + CHARTER-V3-LEGACY. Light editorial pass per architect decision #1. Zero impact on existing canon.
- **PR-B (0.5 day):** AGENTS.md additive restructure. New "Charter and Plane Coverage" section ABOVE current Operating Principles. Operating Principles stay (correct as Governance-plane descriptions); reframed as "Governance plane operating principles." VISION.md gets matching update.
- **PR-C (0.5 day):** Boundary metadata enum extension. Schema-only — add GCC-High, Azure-Government, AWS-GovCloud, vSphere, Federal-Hybrid to the `boundary` enum. **Existing GCC-Moderate docs stay GCC-Moderate.** Zero impact on existing boundary findings or SCuBA work. Future work can declare broader scope.
- **PR-D (1 day):** `src/uiao/canon/charter-implementation-registry.yaml` first cut. For each V4U primitive, lists implementing UIAO_NNN docs. Read-only mapping; doesn't modify existing docs. Plus `ADR-NNN: Foundational Primacy and Charter Amendment Process` documenting the V3 → V4U → UIAO-V1 supersession chain and the layered-restoration framing.

### Phase 2: Bidirectional binding (PR-E and PR-F)

- **PR-E (1 day):** `foundational-trace` field added to metadata-schema as **optional initially**. Documented and validated; not yet required.
- **PR-F (2-3 days):** Backfill `foundational-trace` across existing canon. Each doc gets its charter mapping. Make field **required** at end of this PR. Each doc reviewed for charter primitive(s) it implements/extends/adds.

### Phase 3: Plane coverage and gap surfacing (PR-G and PR-H)

- **PR-G (1-2 days):** Gap-doc placeholders for missing primitives where placeholder is sufficient (Conversation primitive, SoA companion to SSOT, NPE Assurance Model, 17-Point Canon, Eight Frozen Domains, Public Service First as substrate-wide doctrine). Each is a thin canon doc declaring `status: gap` with charter ref. Visible gap > invisible gap.
- **PR-H (1-2 days):** `uiao substrate plane-coverage` CLI. Reads implementation registry; reports per-plane coverage. Plus `DRIFT-FOUNDATIONAL` drift class added to substrate walker.

### Phase 4: Regulatory Absorption Layer (PR-J through PR-L) — NEW

- **PR-J (1-2 days):** Regulatory Intake Pattern. Defines canonical pattern for absorbing new federal initiatives — `UIAO_REG_NNN` doc class with: source authority, mandate scope, charter mapping, implementing UIAO_NNN docs, target compliance date. Plus `regulatory-intake-registry.yaml` and `uiao substrate regulatory-coverage` CLI.
- **PR-K (3-5 days):** **E911 Implementation Roadmap.** Real spec, not gap-doc. Defines dispatchable-location data model, SoA chain (physical/interior location → addressing per V4U §7), binding to Identity (registered user) and Boundary (served boundary class), integration points with InfoBlox/Entra. **High priority — federal law (RAY BAUM, Kari's Law, FCC); current zero implementation is legal exposure.**
- **PR-L (1-2 days):** HRIT and FRPP MS canon entries. Real canon docs (not placeholders) declaring scope, charter mapping (HRIT → Identity plane SoA chain HR → Entra ID; FRPP MS → Boundary plane + physical-location SoA), and integration plan. Authored within the Regulatory Intake Pattern from PR-J.

### Phase 5: Operational vision (incremental — PR-I and beyond)

- **PR-I:** Author actual content for the most load-bearing missing primitives. First: **Conversation primitive** — JSON Schema (ConversationID, identity_state, cert_state, overlay_path, qos, policy_tokens, telemetry_refs), runtime invariants. Wire `ConversationID` as optional field into existing evidence record schema. Each subsequent primitive (SoA companion, Public Service First doctrine, etc.) gets its own PR.

### Cross-cutting ADR

- **ADR-MS (Microsoft-Forced Transition Rationale):** Records *why* OrgPath / Three-plane device model / Entra adapter / Intune / Azure ARC layers exist, the vendor-pressure forcing function, and how they satisfy V4U Identity-plane intent. Future-readers understand they're not arbitrary; they're vendor-mandated. Lands in any PR-A through PR-D timeframe.

**Total effort:** ~2 weeks of mostly low-risk additive PRs. None touches operational work in flight. Conversation primitive (PR-I) is the only place where existing-code touch happens (additive optional `ConversationID` field on evidence records).

## Knock-on architect decisions (revised in v4)

1. **Restore Conversation State plane** in six-plane model — confirmed Yes; lands in PR-I when Conversation primitive is authored
2. **Boundary scope** — REVISED FRAMING: NOT "revert GCC-Moderate-only" (the GCC-Moderate focus is correct urgent work). Instead, **extend the boundary enum** to make GCC-Moderate one of N supported classes (PR-C). Existing work stays intact; new work can declare broader scope as needed.
3. **Add Boundary as a distinct layer** in the eight-layer model — confirmed via UIAO-V1 §9; lands when V4U layer model is canonized in CHARTER-001 (PR-A)
4. **NEW**: Regulatory Absorption Layer pattern adopted (PR-J) to handle federal-speed initiative drops (HRIT, FRPP MS, future BODs/EOs)
5. **NEW**: E911 elevated from gap-doc to real implementation roadmap (PR-K) due to legal exposure

## What I have NOT yet read

To be honest about coverage:

- `AtoBZ_clean.md` (928KB master appendix) — read 0 lines
- `Federal_IT_Structure_Analysis.docx` (Mar 9 20:25, most recent UIAO-V1 doc) — read 0 lines
- `V4U_Master_Reference_All_Sections.docx` (or `.md` in V4/Backup) — read 0 lines
- `Federal Cloud Telemetry Gap...$16.3B...PDF` — read 0 lines
- `V4G.docx` / `V4P.docx` / `V4C.docx` audience variants — read 0 lines
- `Federal_Modernization_Summary.docx` — read 0 lines
- `Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md` — read 0 lines
- `Source_of_Authority_Location_InterAgency.md` — read 0 lines
- `V4U_Unified_Document_Outline.md` — read 0 lines
- `Appendix E Policy Architecture.docx` — read 0 lines
- `V3/TwoPager` — read in full (prior session)
- `V3/Introduction (long-form)` — read in full (prior session)
- `V4/V4U_Core_Canon_Introduction.docx` — read in full
- `V4/Backup/The_new_document_is_meant_to_replace_the_V3_docume.docx` — read first 120 lines
- `UIAO-V1/UIAO-Main-Spec-v1.md` — read first ~500 of 17K lines (sections 1-11 of Introduction)

The architect-decision pause exists precisely because reading another 2 MB of foundational material to *fully* characterize the charter set is high-cost and the decisions in §"Decisions still needed" don't require it. The **ingestion** PR should read everything it ingests; the **planning** doesn't need that depth.

## Plane coverage — revised assessment

Earlier revisions undersold the repo's V4U-plane coverage. With SCuBA, Transformation, and Boundary work correctly attributed:

| V4U Plane | Repo coverage | Implementation forms |
|---|---|---|
| Identity | Substantial | `entra` adapter + UIAO_135-139 transformation specs + OrgPath / Three-plane device model |
| Addressing | Substantial | `infoblox` + `bluecat` modernization adapters |
| **Boundary** | **Substantial** | gcc-boundary-gap-registry + FINDING-002..009 + SentinelProbe + ScubaGear M365 boundary work — **the urgent operational work IS the boundary plane implementation** |
| Overlay | None | (V4U: MINR/NSX/Catalyst SD-WAN — none implemented; deferred behind compliance perimeter) |
| Conversation | None | (no `Conversation` primitive yet; lands in PR-I) |
| Policy | Partial | Enforcement Runtime (UIAO_111) + KSI library + Policy Architecture Appendix E pending |
| Telemetry | Substantial | `uiao.monitoring` + ConMon + Sentinel hook + ScubaGear telemetry + KQL queries |
| Governance | Complete | OSCAL pipeline + drift taxonomy + adapter taxonomy + Evidence Graph + CQL + ADR process — **the substrate's compliance perimeter** |

**Honest summary:** the repo has **substantial-to-complete coverage of 5 of 8 planes** with concrete operational work, **partial coverage of 1 more** (Policy), and **gaps in 2** (Overlay, Conversation). The compliance-first prioritization is correct given forcing functions.

## Four-bucket extension taxonomy (carried forward, framing corrected)

Each existing UIAO_NNN gets a `foundational-trace` declaring its relation to V4U primitives:

1. **`extends`** — UIAO_001 SSOT generalizes V4U's "InfoBlox SSOT for addressing"; Evidence Graph (UIAO_113) extends V4U "evidence loop"; ConMon extends V4U "closed-loop control: Detect → Capture → Correlate → Remediate → Report"; SCuBA Tech Spec (UIAO_002) extends V4U Federal Mandate Convergence (CISA SCuBA mandate)
2. **`adds`** — adapter taxonomy (UIAO_003), drift taxonomy, OSCAL pipeline, KSI library, FedRAMP 20x scaffolding, BOD 25-01 tracking, mission-class taxonomy, CycloneDX SBOM, CQL (UIAO_108), Enforcement Runtime (UIAO_111). All correctly added under regulatory forcing functions.
3. **`modifies`** — six-plane substitution (Conversation State → Management) — needs ADR; restore Conversation in PR-I. SSOT-without-SoA framing — needs SoA companion canon doc (PR-G).
4. **`scopes-out`** — currently zero. Boundary work is correctly focused on GCC-Moderate today; PR-C extends scope without scoping out current work.

PR-F handles the backfill across all existing UIAO_NNN.

## Saved artifacts (this session, 2026-05-04)

- This file: `inbox/drafts/charter-restoration-plan.md`
- Memory: `~/.claude/projects/.../memory/project_uiao_charter_orphan.md`
- Memory: `~/.claude/projects/.../memory/project_charter_restoration_plan.md`
- Memory: `~/.claude/projects/.../memory/project_uiao_regulatory_forcing_functions.md` (new, R4)
- Memory: `~/.claude/projects/.../memory/reference_uiao_foundational_onedrive.md`
- Memory: `~/.claude/projects/.../memory/user_role_mike_stratton.md`
- Memory: `~/.claude/projects/.../memory/feedback_purpose_questions.md`
- Memory: `~/.claude/projects/.../memory/MEMORY.md` (index updated)

## Glossary — terms to use carefully going forward

- ✅ **"Compliance-first prioritization under forcing functions"** — correct framing for governance/compliance buildout
- ✅ **"Layered restoration"** — correct framing for adding charter binding above operational stack
- ✅ **"Regulatory absorption"** — correct framing for HRIT, FRPP MS, future-initiative intake
- ❌ **"Drift"** — RETRACTED. The governance/compliance work was not drift; it was correct response to non-optional pressure. Use only if a *specific* doc actually contradicts charter intent (and even then, the four-bucket taxonomy uses `modifies`, not "drift").
- ❌ **"Governance overlay"** — RETRACTED. The governance/compliance work is **the substrate's compliance perimeter**, not an overlay. It implements V4U §6 #6 (Embedded governance and automation) and the Federal Mandate Convergence table.
- ❌ **"Lost the plot"** — RETRACTED. The plot expanded under regulatory pressure. The charter wasn't lost; it was deferred while urgent compliance work landed.
