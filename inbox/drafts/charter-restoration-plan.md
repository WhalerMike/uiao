---
title: "Charter Restoration Plan — Reconciling UIAO with the Pre-GitHub Foundational Canon (V3 → V4U → UIAO-V1)"
status: draft
authored_by: "Claude (session w/ Mike Stratton, 2026-05-04)"
intent: "Becomes PR 1 (charter ingestion + non-goals doctrine) when ready"
revision_history:
  - "v1 (2026-05-04): Identified V3 as charter, drafted 6-PR plan"
  - "v2 (2026-05-04): TwoPager added, charter set expanded to 4 (CHARTER-001..004)"
  - "v3 (2026-05-04): MAJOR REVISION — V3 explicitly superseded by V4U (Mar 7), then UIAO-V1 (Mar 9). UIAO-V1 is the actual current charter. Charter set expanded to ~10 docs across 3 iterations."
---

# Charter Restoration Plan (Revision 3)

## Diagnosis

The pre-GitHub foundational work for UIAO progressed through three iterations between Feb 26 and Mar 9, 2026 — none of which were ingested into the repo canon:

```
V3 (Feb 26)  →  V4 / V4U (Mar 7-9)  →  UIAO-V1 (Mar 9)  →  [GitHub repo begins]
```

Each iteration explicitly built on or superseded the previous one. **None made it into `src/uiao/canon/`.** The repo canon began with `UIAO_001 SSOT` and accumulated post-V3 governance overlay (canon abstraction, adapter taxonomy, drift detection, OSCAL pipelines, KSI library, SCuBA spec, ConMon program, Evidence Graph, CQL, Enforcement Runtime, OrgPath) — all valuable, none of which is the purpose. The repo describes **what the substrate IS** (a FedRAMP governance machine) but does not state **what UIAO is FOR** (the V4U/UIAO-V1 thesis: "the federal government is structurally frozen at the Client/Server L2-L4 perimeter era; identity-forward modernization is the only path forward").

The `V4U_Core_Canon_Introduction.docx` line 5 states explicitly: **"Supersedes: V3 Introduction"**. The "replace V3" doc in V4/Backup confirms V4 was designed to replace V3 because V3 lacked strategic framing, federal mandate convergence, FICAM/ICAM alignment, and the paradigm-shift argument. UIAO-V1 (Mar 9, post-V4U merger) is the most recent and most refined.

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

## Sequencing implications (still 6 PRs, but PR 1 is now bigger)

The original 6-PR plan still holds, but PR 1 expands substantially:

- **PR 1 (keystone)** now ingests ~10 charter docs across 3 iterations, not 4 from one iteration. Includes the SSOT-vs-SoA reconciliation in UIAO_001. ADR-NNN expands to acknowledge the V3 → V4U → UIAO-V1 supersession chain
- **PR 4 (missing primitives)** expands from "Conversation + Public Service First" to also include: SoA primitive + 12 SoA domains canon, Boundary layer canon, Identity-Forward framing in AGENTS.md/VISION.md, "If it degrades citizen interaction, it does not ship" as substrate-wide ship-gate
- **PR 6 (recovery audit)** expands to include the eight-frozen-domains diagnosis canonization and the 17-Point Canon ingestion

## Knock-on architect decisions (still pending from Revision 2)

1. **Restore Conversation State plane** in six-plane model (revert silent "Management" substitution) — confirmed Yes
2. **Restore federal hybrid cloud boundary** (revert GCC-Moderate / M365-only contraction) — confirmed Yes
3. **Now also**: **add Boundary as a distinct layer** — eight-layer model: Identity → Addressing → Boundary → Overlay → Conversation → Policy → Telemetry → Governance (UIAO-V1 §9)?

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

## Recovery audit (PR 6) — expanded scope

The four-bucket extension taxonomy applied against UIAO-V1 (not just V3) means more existing repo canon may need re-tiering:

1. **`extends`** — UIAO_001 SSOT generalizes V4U's "InfoBlox SSOT for addressing"; Evidence Graph extends V4U "evidence loop"; ConMon extends V4U "closed-loop control: Detect → Capture → Correlate → Remediate → Report"
2. **`adds`** — adapter taxonomy, drift taxonomy, OSCAL pipeline, KSI library, SCuBA spec, FedRAMP 20x, BOD 25-01, mission-class taxonomy, CycloneDX SBOM, CQL, Enforcement Runtime, OrgPath, Three-plane device model
3. **`modifies`** — six-plane substitution (Conversation State → Management); SSOT-without-SoA framing; boundary contraction (federal hybrid cloud → M365-only)
4. **`scopes-out`** — currently zero, but may apply to retired V3 tools if architect decides not to restore (TBD case-by-case)

Every existing UIAO_NNN gets reviewed against this expanded taxonomy in PR 6.

## Saved artifacts (this session, 2026-05-04)

- This file: `inbox/drafts/charter-restoration-plan.md`
- Memory: `~/.claude/projects/.../memory/project_uiao_charter_orphan.md`
- Memory: `~/.claude/projects/.../memory/project_charter_restoration_plan.md`
- Memory: `~/.claude/projects/.../memory/user_role_mike_stratton.md`
- Memory: `~/.claude/projects/.../memory/feedback_purpose_questions.md`
- Memory: `~/.claude/projects/.../memory/MEMORY.md` (index updated)

After this revision: also adds chronology + personal-doc exclusion to memory.
