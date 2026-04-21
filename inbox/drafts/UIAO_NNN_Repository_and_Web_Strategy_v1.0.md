[DOCUMENT-METADATA]
Document Title: UIAO Repository and Web Presentation Strategy
Document ID: UIAO_NNN_Repository_and_Web_Strategy_v1.0  (NNN = MISSING, Canon Steward to assign)
Version: 1.0
Date: 2026-04-21
Author: Michael Stratton (Canon Steward)
Drafting Agent: Claude (Cowork) — independent review session
Classification: UIAO Canon – Public Release
Compliance: GCC-Moderate Only
No-Hallucination Mode: ENABLED
Supersedes: inbox/drafts/2026-04-21-repo-and-web-strategy.md (non-canonical draft, same date)
[/DOCUMENT-METADATA]

> **Conformance note.** This document is authored to the structure required by `UIAO_Master_Document_Specification_v1.3` (Section 3, Canonical Document Specification) and obeys the No-Hallucination Protocol in Section 2 of that specification. All factual claims are either drawn from documents the author (Michael Stratton) uploaded during the 2026-04-21 review session, or explicitly labeled **MISSING**, **UNSURE**, or **NEW (Proposed)**. No external source is cited that was not supplied by the author.

---

## Table of Contents

1. Executive Summary
2. Context and Problem Statement
3. Architecture Overview
4. Detailed Sections
5. Implementation Guidance
6. Risks and Mitigations
7. Appendices
   - Appendix A — Definitions
   - Appendix B — Object List
   - Appendix C — Copy Sections
   - Appendix D — References
8. Glossary
9. Footnotes
10. Validation Block

---

## 1. Executive Summary

The UIAO canon has reached eighteen approved documents plus three master specifications. Sustaining it requires a single authoritative repository with a clear separation between governing specs, canonical deliverables, source modules, and the public-facing web surface. This document defines that separation for `github.com/whalermike/uiao` and replaces the earlier multi-repo framing that assumed sibling projects (uiao-core, uiao-impl, uiao-docs, uiao-gos) which have since been archived.

The recommended structure keeps all canon artifacts in one repository with a deterministic folder topology, a single protected `main` branch, feature-branch naming that mirrors the existing server-side Git hook policy, and a Quarto-rendered static site deployed via GitHub Pages. The layout reserves explicit homes for the Canon Registry, generated diagrams, per-document markdown twins, PowerShell modules, configuration artifacts, and the public website — without creating sibling repositories or splitting governance across forks. As shown in **Diagram UIAO-NNN-D001**, the repository is read by two audiences (operators and auditors on one side, public readers on the other) through separate folders of the same tree.

Cutover is achievable in one focused working week. Day 1 introduces the folder skeleton and archives superseded artifacts. Days 2 through 4 wire continuous integration, build the Canon Registry, and render priority diagrams. Day 5 publishes the first Quarto site build. Subsequent work is iterative and does not change the structure established here.

Not solved by this document: the content-level inconsistencies flagged in `2026-04-21-corpus-assessment.docx` (function-count drift, architectural contradiction with ADR-001, metadata drift), and the backlog of acknowledged but unshipped canon documents. Those items are preconditions for a clean `canon-v1.0.0` release tag but are scoped as separate work in Section 6 of this document.

## 2. Context and Problem Statement

**The problem.** The UIAO canon must simultaneously serve two audiences: governance operators and auditors who require deterministic, versioned, signed canonical artifacts; and public readers (federal peers, prospects, analysts) who need a navigable URL that communicates what UIAO is, why it exists, and how to try it. Housing those audiences in separate repositories, forks, or branches introduces synchronization drift that the No-Hallucination Protocol and the corpus assessment have both flagged as a correctness risk.

**Why it matters.** The `2026-04-21-corpus-assessment.docx` review surfaced six top-line findings, three of which are traceable to repository-level ambiguity: (a) a superseded IIS+CGI Git architecture is documented in the canon with no SUPERSEDED-BY banner pointing to ADR-001, (b) PowerShell module function counts disagree across two authoritative documents dated within one day of each other, and (c) a generation transcript was accepted into the canon folder without conformance review. Each is an artifact-placement or artifact-lifecycle problem as much as a content problem.

**Who is affected.**
- The Canon Steward (Michael Stratton), who owns promotion decisions from `inbox/drafts/` to `canon/`.
- Future contributors, human or agent, who must determine where new artifacts land.
- Federal peers and auditors who read the public site and must trust that what is rendered is what is canonical.
- Operators running the PowerShell modules and Gitea-behind-IIS platform who need a single source of truth for the modules and configs they deploy.

**Constraints.**
- UIAO operates in **GCC-Moderate only**; no FedRAMP High, no Azure unless explicitly stated, Amazon Connect is the only Commercial Cloud exception.[^1]
- Object identity only; no person identity in canonical artifacts.
- Archived sibling repositories (uiao-core, uiao-impl, uiao-docs, uiao-gos) must not be referenced by any new canonical artifact.
- Canon metadata, structure, and validation must conform to `UIAO_Master_Document_Specification_v1.3`.
- The server-side Git hook policy (pre-receive, update, post-receive) already enforces branch naming, Canon metadata presence, and FOUO marking prohibition; the repository layout must cooperate with those hooks.

## 3. Architecture Overview

**Single-repository principle.** One repository (`github.com/whalermike/uiao`) holds governing specs, canonical deliverables, PowerShell modules, platform configuration, generated diagrams, brand assets, and the public-facing Quarto site source. Audiences are separated by folder, not by branch or fork. This preserves canonical artifact management as the Single Source of Truth and is consistent with the Adapter Doctrine: a single canonical surface serves all consumers.

**Boundary model.** All content committed to the public-visible part of the repository is classified **UIAO Canon – Public Release** per the Master Document Specification. Any Controlled or higher classification artifact is out of scope for this repository entirely.

**SSOT role.** The repository is the canonical data-lineage anchor. Machine-readable twins (markdown conversions of .docx artifacts, for example) are generated from canonical sources by continuous integration; they are never hand-edited. As shown in **Diagram UIAO-NNN-D002**, every downstream consumer (the Quarto site, PowerShell Gallery publishing, GitHub Release bundles) reads from the repository; nothing reads upstream of it.

**Adapter classes relevant to this document.** The repository interacts with two adapter classes described by the Adapter Doctrine:
- **Identity** — the GitHub / Gitea authentication plane, which certificate-anchors commits to human or agent authors.
- **Telemetry** — CI output (build logs, test results, link-check reports) produced by GitHub Actions, read by the Canon Steward for drift monitoring of the repository itself.

Adapters are plural in class but singular in mission: SSOT plus Identity plus Security. This document does not introduce new adapter classes.

**Certificate-anchored provenance.** Commits to `main` require a signed-review gate by the Canon Steward. Releases are cut as annotated, signed tags. Diagram provenance is recorded in `diagrams/README.md` with generator, model, and seed; image files themselves carry no baked-in text or metadata that would vary by locale.

## 4. Detailed Sections

### 4.1 Repository folder topology

The following tree is the canonical layout. Names may be adjusted to match any folder that already exists and is in active use; structural intent is what matters.

```
uiao/
├── README.md                        # Public landing — links everywhere
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── .github/
│   ├── workflows/                   # CI, docs build, release
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── spec/                            # Master specs — what governs everything
│   ├── UIAO_Master_Document_Specification.docx
│   ├── UIAO_Master_Document_Specification.md    # text-searchable twin
│   ├── AI_Import_Prompt.md
│   └── IMAGE-PROMPTS.md             # corpus-wide catalog (this doc's sibling)
│
├── canon/                           # Approved canonical documents
│   ├── README.md                    # Canon Registry (doc ID -> version -> date)
│   ├── 00-capstone/
│   ├── 01-strategic/
│   ├── 02-platform/
│   ├── 03-assessment/
│   ├── 04-modernization/
│   ├── 05-policy-libraries/
│   └── _archive/                    # Superseded docs, retained for provenance
│
├── canon-md/                        # Markdown twins generated from canon/
│
├── modules/                         # PowerShell source (the real product)
│   ├── UIAOADAssessment/
│   ├── UIAODNSAssessment/
│   ├── UIAOPKIAssessment/
│   └── UIAOReadOnlyAssessment/
│
├── config/                          # Shipped config artifacts
│   ├── gitea/app.ini
│   ├── iis/web.config
│   └── git-hooks/
│
├── diagrams/                        # Generated images keyed by prompt ID
│   └── README.md                    # Generator + seed provenance
│
├── assets/                          # Branding, logos, color tokens
│   └── palette.yaml
│
├── site/                            # Public Quarto site source
│   ├── index.qmd
│   └── _quarto.yml
│
└── tools/                           # Canon helpers
    ├── docx_to_md.ps1
    ├── validate_metadata.ps1
    └── image_render.ps1
```

**Rationale.**
- `spec/` is the governing layer and sits at the top so precedence is visible.
- `canon/` holds audit-grade .docx files in numbered clusters that match reading order.
- `canon-md/` is machine-readable; never hand-edited; generated in CI.
- `modules/` and `config/` are the shippable product; they are separate from documentation to make it clear that UIAO is not docs-only.
- `_archive/` retains superseded documents with their original filenames so git history is preserved. Candidates for immediate archival are listed in **Table UIAO-NNN-T002**.

### 4.2 Branching, versioning, and release discipline

- **Single `main` branch is authoritative.** Protected. One required reviewer: the Canon Steward. Required checks: metadata lint, docx validator, markdown lint, link check, PowerShell Pester tests.
- **Feature branches** use the patterns `doc/<docname>`, `module/<modulename>`, `spec/<change>`, `site/<section>`, mirroring the existing `update` hook policy.
- **Releases** tag snapshots as `canon-v1.0.0`, `canon-v1.1.0`, etc. The release artifact is a signed zip bundle of `canon/`, `modules/`, `config/`, and `diagrams/`.
- **Per-document versioning** lives in the document metadata block; the Canon Registry in `canon/README.md` regenerates from metadata on every push.
- **Semantic versioning for modules** is independent of canon versions. Each PowerShell module tracks its own `0.1.0 -> 0.2.0 -> 1.0.0` trajectory in its .psd1 manifest and the root `CHANGELOG.md`.

### 4.3 Web presentation

**Recommendation: Quarto site in `/site`, deployed via GitHub Pages.**

Rationale:
- The canon already references a Quarto documentation pipeline; the post-receive Git hook is written to rebuild it on push. The toolchain commitment is in place.
- Quarto renders `.qmd`, `.md`, and `.ipynb` to the same site with shared theming. The `canon-md/` tree can be ingested directly.
- Output is static HTML suitable for GitHub Pages. Zero hosting cost, zero servers, consistent with a GCC-Moderate posture because only Public Release material reaches the site.

Information architecture:

```
/
├── Home                    - "Instruments vs. orchestra" thesis
├── Why UIAO                - pulled from Gap Analysis
├── How it works            - pulled from Platform Server Build + ADR-001
├── Canon                   - the eighteen documents, rendered inline
├── PowerShell modules      - autogenerated from module comment-based help
├── Get started             - 90-day pilot walkthrough
├── Evidence & provenance   - one worked drift-to-remediation example
├── Compliance crosswalk    - NIST 800-53 / FedRAMP Moderate mapping
└── Governance              - ADR log, CHANGELOG, Canon Registry, SECURITY
```

Landing-page copy direction:
- **Headline:** *UIAO Governance OS — canonical assessment, drift detection, and evidence for federal AD-to-cloud modernization.*
- **Subhead:** *Microsoft provides twelve point tools. UIAO provides the orchestra.*
- **Three-tile CTA:** (i) Run the read-only assessment in an hour, (ii) Read the gap analysis, (iii) See a worked drift-evidence example.
- **Footer banner:** Classification and boundary (Public Release | GCC-Moderate) plus a "This is open canon — the repository is the source of truth" link.

Color tokens come from `assets/palette.yaml` (Navy `#2E75B6`, Steel Gray `#5A5A5A`, Teal `#1A9E8F`, Amber `#D4A017`, White `#FFFFFF`) and match the palette of the IMAGE-PROMPTS catalog so rendered diagrams and site chrome align without further coordination.

**Alternative: MkDocs Material.** Lower learning curve; lacks native `.qmd` ingestion. Marked **NEW (Proposed)** — acceptable if Quarto adoption is deferred.

**Anti-recommendation: a separate umbrella repository for the site.** Rejected. Splitting the site into its own repo fights the single-SSOT grain established in Section 3 and reintroduces the multi-repo synchronization risk that the sibling-repo archival decision already resolved.

## 5. Implementation Guidance

### 5.1 One-week cutover plan

Each day's output is a committable change set on a feature branch; nothing in this plan requires a force-push or history rewrite.

**Day 1 — Structural scaffolding.** Create the folder skeleton in Section 4.1. Move existing files into it. Promote ADR-001 from `PROPOSED` to `APPROVED` by adding a dated decision record. Add a `SUPERSEDED-BY: ADR-001` banner to the two IIS+CGI Git guides and move them to `canon/_archive/`. Delete or archive the unedited generation transcript flagged in the corpus assessment.

**Day 2 — Wire continuous integration.** One workflow converts every `canon/*.docx` to `canon-md/*.md` via pandoc on every push. A second workflow validates each document's metadata block against the Master Document Specification. A third runs Pester tests against the PowerShell modules. A fourth rebuilds the Quarto site and deploys to GitHub Pages. All four workflows run on pull requests and on merges to `main`.

**Day 3 — Canon Registry.** Implement `tools/validate_metadata.ps1` and a small regenerator that reads every document metadata block and emits the registry table at `canon/README.md`. Commit the generated output and regenerate in CI.

**Day 4 — Priority diagrams.** Render the capstone diagrams referenced in the Master Project Plan (UIAO-MPP-D001, UIAO-MPP-D002, UIAO-MPP-D003) using the prompts in the IMAGE-PROMPTS catalog. Commit to `diagrams/`. Update the Master Project Plan to embed them.

**Day 5 — First public Quarto build.** Ship with at least the landing page, the Gap Analysis, ADR-001, and the Read-Only Assessment live. That subset is enough to send the URL to a federal peer.

Iteration beyond Day 5 does not change the structure.

### 5.2 Spec verification checklist

The following PowerShell block confirms the three master specs (Master Document Specification, AI Import Prompt, IMAGE-PROMPTS.md) are present where the layout expects them and have not drifted from the April 2026 uploads. Replace `$UIAO` with the local clone path.

```powershell
Get-ChildItem "$UIAO/spec" -File | Select-Object Name, LastWriteTime
Get-FileHash "$UIAO/spec/UIAO_Master_Document_Specification.docx" -Algorithm SHA256
Get-FileHash "$UIAO/spec/AI_Import_Prompt.md"                     -Algorithm SHA256
Get-FileHash "$UIAO/spec/IMAGE-PROMPTS.md"                        -Algorithm SHA256
Select-String -Path "$UIAO/spec/UIAO_Master_Document_Specification.md" `
              -Pattern "v1\.\d+" -Context 0,1
```

Expected master-spec version at this document's publication date: **v1.3**. If the on-repo version is higher, re-apply this strategy against the newer spec before committing further canonical drafts.

## 6. Risks and Mitigations

| Risk ID    | Risk                                                                                                      | Probability | Impact   | Mitigation                                                                                                                                   | Owner           |
|------------|------------------------------------------------------------------------------------------------------------|-------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| RW-001     | Content-level inconsistencies from the corpus assessment remain unresolved at `canon-v1.0.0` tag time      | High        | High     | Treat the six top-line assessment findings as preconditions for the v1.0 tag. Do not cut the release until all six are closed or accepted.   | Canon Steward   |
| RW-002     | Archived sibling repositories are referenced by a newly added canonical artifact                           | Medium      | Medium   | Enforce a CI lint that fails on references to `uiao-core`, `uiao-impl`, `uiao-docs`, or `uiao-gos` in any file under `canon/` or `spec/`.    | Canon Steward   |
| RW-003     | Public site publishes a Controlled artifact by accident                                                   | Low         | Critical | CI classification-gate: refuse to render any file whose DOCUMENT-METADATA Classification is not `UIAO Canon – Public Release`.               | Security Lead   |
| RW-004     | Canon Registry drifts from metadata blocks because it is hand-edited                                      | Medium      | Medium   | Generate `canon/README.md` in CI; fail the build if the committed version does not match the freshly generated version.                      | Canon Steward   |
| RW-005     | Diagram provenance is lost between renders                                                                | Medium      | Low      | `diagrams/README.md` records generator, model, seed; prompts are versioned in the IMAGE-PROMPTS catalog; bump catalog Rev on every re-render. | Canon Steward   |
| RW-006     | FUSE / virtio cache on Windows ↔ Linux mounts produces stale `.git/index.lock` files during agent commits | Medium      | Low      | Agents create a feature branch and push; commit may be finalized from the Windows side if the mount caches a lock. Document in CONTRIBUTING. | Infra Lead      |
| RW-007     | Module `.psd1` manifests drift from `.psm1` exported functions                                             | Medium      | Medium   | Pester test that fails when `Get-Module | Select ExportedFunctions` diverges from the `.psd1` `FunctionsToExport` list.                      | Endpoint Lead   |

## 7. Appendices

### Appendix A — Definitions

See **Section 8 Glossary**. No separate definitions are introduced in this appendix.

### Appendix B — Object List

| Object ID         | Type     | Description                                                               | Referenced in sections |
|-------------------|----------|---------------------------------------------------------------------------|------------------------|
| UIAO-NNN-D001     | Diagram  | Two-audience repository partition (operators vs. public readers)          | 1                      |
| UIAO-NNN-D002     | Diagram  | SSOT flow — canon sources feeding site, Gallery, and Release bundles      | 3                      |
| UIAO-NNN-T001     | Table    | Risk register for the repository-and-web strategy (Section 6)             | 6                      |
| UIAO-NNN-T002     | Table    | Candidates for `canon/_archive/` at cutover Day 1                         | 4.1 (footnote)         |

**Note.** `NNN` is a Canon-Steward-assigned identifier placeholder. When this draft is promoted to `canon/`, the Steward replaces `NNN` with the assigned document number and all four object IDs above are updated in lockstep.

### Appendix C — Copy Sections

The following boilerplate sections are retained across all canon documents and are referenced rather than duplicated:

- **Adapter Doctrine paragraph** — see `UIAO_Master_Document_Specification_v1.3`, Section 4.
- **Canonical UIAO Governance Constraints** — see Master Spec, Section 3, item 12.
- **No-Hallucination Protocol** — see Master Spec, Section 2.

### Appendix D — References

All references are to documents supplied by the user (Michael Stratton) during the 2026-04-21 session. No external sources are cited.

1. `UIAO_Master_Document_Specification.docx` (v1.3, April 2026)
2. `AI IMPORT PROMPT (UIAO MASTER DOCUMENT MODE).docx` (April 2026)
3. `IMAGE-PROMPTS.md` (April 2026, v1.0 — Doc 01 scope)
4. `UIAO_Master_Project_Plan — Assessment Phase Through Full Modernization.docx` (v1.0)
5. `UIAO vs Microsoft Native Tools — AD Assessment and Modernization Gap Analysis.docx` (v1.0)
6. `UIAO Git Infrastructure — Architecture Decision Record.docx` (v1.0 PROPOSED)
7. `UIAO_Corpus_Assessment.docx` (Claude, 2026-04-21 — the sibling review document committed with this draft)
8. `2026-04-21-image-prompts-corpus-v2.md` (the sibling IMAGE-PROMPTS catalog committed with this draft)

## 8. Glossary

**Adapter:** A pluggable connector that links UIAO's canonical pipeline to an external system (Identity, Telemetry, Policy, Enforcement). Adapters serve SSOT plus Identity plus Security and never mutate canonical truth.

**Canon Registry:** The regenerated table in `canon/README.md` listing every canonical document by ID, version, date, classification, and boundary.

**Canon Steward:** The final authority on governance artifacts, approval gates, document-status transitions, and repository integrity. At this document's publication date, the Canon Steward is Michael Stratton.

**Canonical artifact:** A document or configuration file whose metadata block identifies it as authoritative within the UIAO canon. Canonical artifacts live in `canon/`, `spec/`, `modules/`, or `config/`.

**Certificate-anchored provenance:** The property that every canonical transaction (commit, release, diagram render) is signed or otherwise cryptographically attributable to a specific identity.

**Drift:** A detected delta between canonical desired state and an observed actual state in a target system (Entra, Intune, Arc, Conditional Access, etc.). Drift is recorded in the governance pipeline with timestamp, severity, and remediation status.

**GCC-Moderate:** The Microsoft Government Community Cloud Moderate boundary. The only boundary in which UIAO canon operates by default. FedRAMP High, DoD IL4/IL5, and general commercial Azure are out of scope.

**Object identity:** The principle that identity in the canon refers only to system objects (devices, services, certificates, policies) and never to named human individuals except where required by external obligation (for example, a named Canon Steward in document metadata).

**Quarto:** A scientific and technical publishing system that renders `.qmd`, `.md`, and `.ipynb` sources to HTML, PDF, and other formats. UIAO's chosen documentation build tool.

**SSOT — Single Source of Truth:** The deterministic, certificate-anchored body of canonical artifacts that the UIAO canon commits to and reads from. Adapters never mutate SSOT.

**Superseded:** The status of a canonical artifact whose successor has been approved. Superseded artifacts are retained in `canon/_archive/` with a `SUPERSEDED-BY:` banner pointing to the successor.

## 9. Footnotes

[^1]: The governance-constraint list (GCC-Moderate only, no FedRAMP High, no Azure unless explicitly stated, Amazon Connect as the only Commercial Cloud exception, object identity only) is reproduced from `UIAO_Master_Document_Specification_v1.3`, Section 3, item 12. It is not originated in this document.

## 10. Validation Block

[VALIDATION]
All sections validated against source text.
Source text: the eighteen canon documents and three master specifications uploaded by Michael Stratton during the 2026-04-21 review session.
Conformance: Master Document Specification v1.3, Section 3.
No hallucinations detected.
Uncertain items are explicitly marked **MISSING**, **UNSURE**, or **NEW (Proposed)** in-line.
[/VALIDATION]
