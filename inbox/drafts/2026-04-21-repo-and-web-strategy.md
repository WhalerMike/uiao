# UIAO — GitHub Repository and Web Presentation Strategy

**Document ID:** UIAO_STRAT_001_Repo_Web_v1.0
**Classification:** UIAO Canon — Public Release candidate
**Boundary:** GCC-Moderate
**Date:** 21 April 2026
**Prepared for:** Michael Stratton — Canon Steward
**Scope:** Repository layout and public web presentation for the 18 UIAO canon documents plus the three master specs (Master Document Specification, AI Import Prompt, IMAGE-PROMPTS.md)

> **Verification note.** The request to confirm that the three uploaded specs are the current versions in `github.com/whalermike/uiao` could not be completed from this environment. GitHub is blocked by the Cowork egress allowlist (only `*.anthropic.com` and `*.claude.com` are reachable), and public web search did not return the repository (likely private or unindexed). Verification is deferred; a manual comparison checklist is in §5 so you can run it in ninety seconds when you next have a shell on a machine with repo access.

---

## 1. Governing principle

Two audiences must be served by the same GitHub repository without compromising either:

- **Operators and auditors** who need to treat UIAO as a controlled canon — deterministic, versioned, signed, with a clear `main` that never carries speculative work.
- **Readers and prospects** who need a single URL that explains what UIAO is, why it matters, and how to try it.

The strategy below keeps those audiences in one repository, separated by folder, not by branch or fork.

---

## 2. Repository layout

Target tree for `github.com/whalermike/uiao` (names are suggestions — keep any that match what is already live):

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
│   └── IMAGE-PROMPTS.md             # comprehensive image prompt catalog
│
├── canon/                           # The 18 approved documents
│   ├── README.md                    # Canon Registry (doc ID -> version -> date)
│   ├── 00-capstone/
│   │   └── UIAO_Master_Project_Plan.docx
│   ├── 01-strategic/
│   │   ├── UIAO_vs_Microsoft_Native_Tools.docx
│   │   └── Corpus_Overview.docx     # rewrite of the old transcript file
│   ├── 02-platform/
│   │   ├── ADR-001_Git_Infrastructure.docx       # promoted to APPROVED
│   │   ├── UIAO_Platform_Server_Build_Guide.docx
│   │   └── UIAO_CLI_and_Operations_Guide.docx
│   ├── 03-assessment/
│   │   ├── UIAO_AD_Interaction_Guide.docx
│   │   ├── UIAO_Read_Only_AD_Assessment_Guide.docx
│   │   └── UIAO_PowerShell_Module_Reference.docx
│   ├── 04-modernization/
│   │   ├── UIAO_Identity_Modernization_Guide.docx
│   │   ├── UIAO_DNS_Modernization_Guide.docx
│   │   ├── UIAO_PKI_Modernization_Guide.docx
│   │   └── AD_Computer_Object_Conversion_Guide.docx
│   ├── 05-policy-libraries/
│   │   ├── UIAO_Conditional_Access_Policy_Library.docx
│   │   ├── UIAO_Intune_Policy_Templates.docx
│   │   └── UIAO_Azure_Arc_Policy_Library.docx
│   └── _archive/                    # Superseded docs, retained for provenance
│       ├── UIAO_Git_Server_WS2025_IIS.docx
│       ├── Git_on_Windows_Server_2025_IIS.docx
│       └── UIAO_platform_and_modernization_guides.docx
│
├── canon-md/                        # Markdown twins of every canon doc
│   └── (same tree as canon/, .md files, generated via pandoc in CI)
│
├── modules/                         # PowerShell source (the real product)
│   ├── UIAOADAssessment/
│   │   ├── UIAOADAssessment.psd1
│   │   ├── UIAOADAssessment.psm1
│   │   └── tests/
│   ├── UIAODNSAssessment/
│   ├── UIAOPKIAssessment/
│   └── UIAOReadOnlyAssessment/
│
├── config/                          # Shipped config artifacts
│   ├── gitea/app.ini
│   ├── iis/web.config
│   └── git-hooks/
│       ├── pre-receive
│       ├── update
│       └── post-receive
│
├── diagrams/                        # Generated images keyed by prompt ID
│   ├── README.md                    # How to regenerate + provenance
│   ├── UIAO-MPP-D001.png
│   ├── UIAO-MPP-D002.png
│   └── ...
│
├── assets/                          # Branding, logos, color tokens
│   ├── logo/
│   ├── palette.yaml                 # Navy/Gray/Teal/Amber tokens
│   └── fonts.md
│
├── site/                            # Public website source (see §3)
│   ├── index.qmd                    # landing
│   ├── _quarto.yml
│   ├── overview/
│   ├── canon/
│   ├── get-started/
│   └── assets/
│
└── tools/
    ├── docx_to_md.ps1               # Canon conversion helper
    ├── validate_metadata.ps1        # Enforce UIAO Master Spec metadata block
    └── image_render.ps1             # Calls your chosen image generator
```

**Rationale for the split.**

- `spec/` is the governing layer. Everything else must be validatable against it. Keeping it at the top, named plainly, signals authority.
- `canon/` holds the audit-grade .docx files because that is the format stakeholders actually consume. Each cluster is a numbered folder so that file ordering matches reading order for a newcomer.
- `canon-md/` is the machine-readable twin. It should be generated by CI from the .docx, never hand-edited — drift between the two would re-create the inconsistency problem the earlier assessment flagged. Consumers who need `grep`-able text (including the website build) read from here.
- `modules/`, `config/`, `git-hooks/` are the actual shippable product. Separating them from the documentation makes it clear that UIAO is not a docs-only project.
- `_archive/` retains superseded documents with their original filenames so the git history stays intact. The IIS-only Git guides move here when ADR-001 is promoted to APPROVED; the old chat-transcript doc moves here at the same time, with a README note explaining what it is.

---

## 3. Branching, versioning, and release discipline

- **Single `main` branch is authoritative.** Protected. Required reviews: 1 Canon Steward. Required checks: metadata lint, docx validator, markdown lint, link check, PowerShell Pester tests.
- **Feature branches** use the pattern `doc/<docname>`, `module/<modulename>`, `spec/<change>`, `site/<section>`. This mirrors the branch naming already enforced by your `update` Git hook.
- **Releases** tag the full canon at a snapshot: `canon-v1.0.0`, `canon-v1.1.0`, etc. The release artifact is a zip bundle of `canon/`, `modules/`, `config/`, and `diagrams/` — exactly what an offline operator needs.
- **Per-document versioning** stays in the document metadata block (already required by the Master Doc spec). The Canon Registry in `canon/README.md` shows each document's current version at a glance. CI regenerates that table from metadata blocks; never hand-maintain it.
- **Semantic versioning for modules** — `UIAOADAssessment` gets its own `0.1.0 -> 0.2.0 -> 1.0.0` track, independent of canon versions. Keep module versions in sync with their .psd1 manifests and with `CHANGELOG.md` entries.

---

## 4. Web presentation

Two options were considered. The recommendation is the first.

### 4.1 Recommendation — Quarto site in `/site`, deployed via GitHub Pages

Why Quarto:
- The corpus already references a "UIAO Quarto documentation pipeline" and the post-receive hook is designed to rebuild it. You are already committed to this toolchain.
- Quarto renders .qmd, .md, and .ipynb to the same site with consistent theming. You can ingest the `canon-md/` tree directly without a conversion step.
- Output is static HTML suitable for Pages — zero hosting cost, zero servers, fits a GCC-Moderate posture because the public site contains only Public Release material.

Information architecture for the public site:

```
/
├── Home (landing)                   - "Instruments vs. orchestra" thesis
├── Why UIAO                         - pulled from the Gap Analysis
├── How it works                     - pulled from Platform Server Build + ADR-001
├── Canon                            - the 18 docs, rendered inline from canon-md
│   ├── By cluster
│   └── By document ID (registry)
├── PowerShell modules               - autogen from module comment-based help
├── Get started                      - 90-day pilot walkthrough
├── Evidence & provenance            - the one worked example (see Tier-3 rec)
├── Compliance crosswalk             - NIST 800-53 / FedRAMP Moderate mapping
└── Governance                       - ADR log, CHANGELOG, Canon Registry, SECURITY
```

Landing-page copy direction (do not open with a `pip install` line — the real product is PowerShell-first):

- **Headline:** *UIAO Governance OS — canonical assessment, drift detection, and evidence for federal AD-to-cloud modernization.*
- **Subhead:** *Microsoft provides twelve point tools. UIAO provides the orchestra.*
- **Three tile CTA row:** (1) Run the read-only assessment in an hour, (2) Read the gap analysis, (3) See a worked drift evidence example.
- **Footer banner:** Classification and boundary (Public Release | GCC-Moderate), plus a "This is open canon — the repository is the source of truth" link back to GitHub.

Color tokens come from `assets/palette.yaml` (Navy `#2E75B6`, Steel Gray `#5A5A5A`, Teal `#1A9E8F`, Amber `#D4A017`, White `#FFFFFF`) — the same palette as IMAGE-PROMPTS.md, so text and figures match out of the box.

### 4.2 Alternative — MkDocs Material

If Quarto feels heavy for the first pass, MkDocs Material is a smaller learning curve. It ingests plain markdown, has an excellent search, and renders the Navy/Teal/Amber palette with a two-line theme config. Cost: you lose Quarto's native .qmd/notebook support, which matters if you ever want to embed live PowerShell transcripts or chart output.

### 4.3 Anti-recommendation — a separate umbrella repo just for the site

Earlier in this conversation Claude recommended an umbrella repo specifically for the landing page. Given the Master Document Spec requires canonical artifact management in a single governance pipeline, splitting the site into its own repo fights that grain. Keep the site in `/site` under the same repo, behind the same protected `main`.

---

## 5. Spec verification checklist

Run this in a shell with the repository cloned to confirm the three uploaded files are in fact the current specs. Replace `$UIAO` with your local clone path.

```powershell
# 1. Confirm the three files exist where they should
Get-ChildItem "$UIAO/spec" -File | Select-Object Name, LastWriteTime

# 2. Hash the local clone and compare to the uploads
Get-FileHash "$UIAO/spec/UIAO_Master_Document_Specification.docx" -Algorithm SHA256
Get-FileHash "$UIAO/spec/AI_Import_Prompt.md"                     -Algorithm SHA256
Get-FileHash "$UIAO/spec/IMAGE-PROMPTS.md"                        -Algorithm SHA256

# 3. Compare the versions inside the Master Spec
Select-String -Path "$UIAO/spec/UIAO_Master_Document_Specification.md" `
              -Pattern "v1\.\d+" -Context 0,1
```

The uploaded specs:

- `AI IMPORT PROMPT (UIAO MASTER DOCUMENT MODE).docx` — last modified 14 April 2026, 17 KB.
- `UIAO_Master_Document_Specification.docx` — dated April 2026, labels itself `v1.3`, last modified 14 April 2026, 25 KB.
- `IMAGE-PROMPTS.md` — last modified 12 April 2026, 7.7 KB, covers **Doc 01 (Executive Brief) only** — eight images. This is **not** a corpus-wide prompt file; the expanded version is delivered separately.

Expected outcomes of the checklist above:

| Check | If it passes | If it fails |
|---|---|---|
| Files exist at `spec/` | Layout matches this strategy | Move/rename files per §2 |
| SHA-256 matches uploads | These are current | Open the newer version, diff, and merge |
| Spec version is `v1.3` | Uploads are current | Promote the newer to `main` |

---

## 6. Cutover plan (one focused week)

**Day 1** — merge the repo-layout scaffolding. Create the folder skeleton, move existing files into it, promote ADR-001 from PROPOSED to APPROVED, add a SUPERSEDED-BY banner to the two IIS+CGI Git guides and move them to `canon/_archive/`, delete or archive the old chat-transcript doc.

**Day 2** — wire CI. One workflow converts every `canon/*.docx` to `canon-md/*.md` via pandoc on every push; a second validates each document's metadata block against the Master Doc spec; a third runs Pester tests against the PowerShell modules; a fourth rebuilds the Quarto site and deploys to Pages.

**Day 3** — build the Canon Registry. A small script reads every docx metadata block, emits a table keyed by Document ID showing Version, Date, Classification, Boundary, Status. Commit the generated `canon/README.md`; regenerate it in CI.

**Day 4** — render the priority diagrams from `IMAGE-PROMPTS.md` (specifically the capstone Master Project Plan diagrams: UIAO-MPP-D001 through D003). Commit to `diagrams/`. Update the Master Project Plan to embed them.

**Day 5** — ship the first public Quarto build. Even if only the landing page, Gap Analysis, ADR-001, and the Read-Only Assessment are live, that is enough to send a link to a federal peer.

Everything after that is iteration.

---

## 7. What this strategy does not solve

- It does not fix the internal contradictions flagged in the earlier corpus assessment. Those are document-level edits (function counts, boundary wording, author attribution); no layout plan resolves them. Treat those as preconditions for a clean `canon-v1.0.0` tag.
- It does not ship the missing P2 documents (DR Playbook, Ops Runbook, Governance Dashboard Design). The layout reserves a home for them under the appropriate cluster; writing them is still owed.
- It does not validate the PowerShell modules. The repo structure assumes they work; Pester tests in CI will catch regressions but not initial quality issues.

Those are separate work. This document is about where everything lives, how it is versioned, and how it reaches a reader.
