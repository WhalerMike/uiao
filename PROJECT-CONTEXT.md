# PROJECT-CONTEXT.md – Single Source of Truth for UIAO Ecosystem

## ⚠️ Format & Authority Hierarchy (CRITICAL)

To prevent Agent formatting conflicts, follow this order of precedence for **format, naming, and presentation decisions**:

1. **[FORMAT-CANON.md](https://github.com/WhalerMike/uiao-core/blob/main/FORMAT-CANON.md)** — Absolute authority for file structure, naming conventions, casing, indentation, quoting, and styling.
2. **`schemas/`** — Ultimate authority for OSCAL field types, JSON structure, and validation constraints.
3. **`AGENTS.md`** — Defines task roles, implementation behavior, and code-level workflow rules.
4. **This file (`PROJECT-CONTEXT.md`)** — Defines architectural intent, orchestration, and project history.
5. **`UIAO-MEMORY.md`** — Persistent correction log and operational lessons learned; apply all matching correction rules before retrying failed work.

**Agent Rule**: If a format decision is not explicitly defined in `FORMAT-CANON.md`, follow the closest existing gold-standard file. If ambiguity still remains, stop and ask for clarification. Never substitute training defaults.

---

**Last Updated**: 2026-04-03
**Owner**: whalermike (Michael Stratton)
**Mission**: Build a production-capable, single-YAML-canon pipeline that generates auditor-accepted FedRAMP Moderate Rev 5 artifacts with real evidence and continuous monitoring hooks.

## Core Architecture (Do Not Deviate Without Updating This File)

* **Primary Repo**: uiao-core <https://github.com/WhalerMike/uiao-core>
* **Document Compiler Repo**: uiao-docs <https://github.com/WhalerMike/uiao-docs>
* **Validation Target**: uiao-validation-targets <https://github.com/WhalerMike/uiao-validation-targets>
  + FastAPI mock service running at <http://localhost:8000> (or Docker)
  + Endpoints: /health, /ingest-evidence, /telemetry, /validation/fedramp-rev5-baseline
  + All evidence must use `prop:id` prefix and valid UUIDv4
* **Single Source of Truth**: The YAML canon file in uiao-core
* **Output Artifacts**: OSCAL 1.3.0 (Component Definition, SSP skeleton, POA&M), Markdown/DOCX/PDF/HTML via uiao CLI

## AI Orchestration Rules (All Agents Must Follow)

1. **AI HIERARCHY (single source of truth)**

   * **Claude Code** = Canon Steward + Lead Architect + Harsh Reviewer. Primary decision-maker for architecture, canon governance, and PR gating. Owns the repo directly via GitHub integration. Read `docs/BRIEFING-SPEC.md` on first session and implement `generate-briefing` command.
   * **Comet-Perplexity** (running Claude Sonnet) = Orchestrator + Browser Agent. Owns web search, browser-driven evidence collection from live vendor portals, and task queue management. Defers all architecture decisions to Claude Code.
   * **GitHub Copilot** = Fast implementation layer only. Executes well-scoped tasks with persistent repo memory. Never makes primary architecture or canon decisions.
   * **Gemini** = Image and diagram generation only. Produces architectural visuals via Imagen. No repo write access beyond `assets/images/`.

2. **Memory & Context**

   * Always read this file + FORMAT-CANON.md + AGENTS.md + UIAO-MEMORY.md before starting any work
   * **Claude Code session zero**: read `docs/BRIEFING-SPEC.md` and implement the `generate-briefing` command
   * Run `uiao generate-briefing` at the start of every Claude Code session to establish current system state before taking any action
   * After any significant change or mistake, update the relevant memory file and this PROJECT-CONTEXT.md if architecture decisions change
   * Never assume context from previous sessions — explicitly reference files
   * **Role separation**: UIAO-MEMORY.md is the live append-only correction log; PROJECT-CONTEXT.md is the static governance doc. Do not mix their roles.

3. **Quality Gates (Non-Negotiable)**

   * All code must pass ruff linting, pip-audit, and existing CI
   * OSCAL artifacts must validate with compliance-trestle
   * Evidence sent to validation-targets must include proper `prop:id`
   * Before any PR/merge: Claude Code canon review and approval required
   * Use parallel Git worktrees for complex tasks
   * **Agent rate-limit rule**: ALWAYS enforce <=8 concurrent agents across all systems. Queue remaining tasks in waves.

4. **Current Priorities (April 2026)**

   * **[SESSION ZERO]** Claude Code: read `docs/BRIEFING-SPEC.md` and implement `uiao generate-briefing` command
   * Claude Code established as Canon Steward and lead GitHub agent (Grok retired)
   * Tight integration between uiao-core and uiao-validation-targets (CLI commands to test against live target)
   * Full SSP control narrative templating with organization-defined parameters
   * Realistic POA&M generation from telemetry events
   * Evidence collection & linking (OSCAL back-matter) — browser-driven collection via Comet-Perplexity
   * Migrate pipeline to secure/GitHub Enterprise-ready setup
   * Expand validation-targets with more scenarios (failure injection, high-volume telemetry, scan imports)
   * Publish generated documents to uiao-docs via GitHub Actions

## Automated Diagram Generation

Diagrams are defined in `canon/diagrams.yaml` (single source of truth) and rendered via the pipeline below:

```
canon/diagrams.yaml
    └─ generate_diagrams_from_canon()
           ├─ writes visuals/<key>.mermaid
           └─ render_mermaid_file() → assets/images/mermaid/<key>.png
                                            └─ embedded in DOCX / PPTX
```

* **CLI**: `uiao generate-diagrams` — writes `.mermaid` files and renders all PNGs.
* **Auto-integration**: `uiao generate-docs` calls diagram generation automatically (pass `--skip-diagrams` to opt out).
* **Post-processing**: `replace_mermaid_blocks_with_images()` in `docs.py` replaces fenced `mermaid` blocks with `<img>` tags so DOCX/PPTX/PDF renderers can embed the PNGs.
* **Live site**: `mkdocs.yml` loads Mermaid 10 ESM from CDN for real-time browser rendering on GitHub Pages.
* **15 canonical diagrams confirmed in** `assets/images/mermaid/`: `unified_arch`, `vendor_logic`, `multi_plane_integration`, `executive_dashboard_status`, `roadmap_gantt_visual`, `schema_validation_flow`, `enforcement_pipeline_logic`, `mgmt_plane_flow`, `frontend_integration_map`, `incident_escalation_tree`, `leaver_killswitch_flow`, `mover_scenario_workflow`, `jinja_normalization`, `appendix_library`, `user_to_app_zt_journey`.
* **Gemini Imagen** generates high-resolution architectural PNGs on demand via `uiao generate-gemini`.
* Target: FedRAMP Moderate Rev 5 baseline
* Focus: 20x Phase 2 (machine-readable evidence over narrative bloat, continuous monitoring, KSI mapping)
* POA&M statuses allowed: open, closed, risk-accepted, false-positive, operational-requirement, vendor-dependency, not-applicable
* Public repo rule: Never commit CUI or production artifacts here

## Key File Locations (verified 2026-04-03)

| What | Where |
|------|-------|
| Vendor overlays (Big 7) | `data/vendor-overlays/*.yaml` (9 files) |
| Control library | `data/control-library/*.yml` (131 files) |
| OSCAL artifacts | `exports/oscal/` |
| Mermaid PNGs | `assets/images/mermaid/` (15 PNGs) |
| Gemini PNGs | `assets/images/` |
| Briefing spec | `docs/BRIEFING-SPEC.md` |
| Reference architecture | `01_Canon/uiao-reference.docx` |
| Leadership briefing | `exports/docx/UIAO_Leadership_Briefing_v1.0.docx` |
| CI workflows | `.github/workflows/` (23 workflows) |
| Drift reports | `reports/drift-report.json` |

## Decision Log (Add new entries at top)

* 2026-04-03: BRIEFING-SPEC.md created at docs/BRIEFING-SPEC.md. Defines `uiao generate-briefing` CLI command — owner's daily dashboard document. Pulls from live repo sources: MEMORY.md, vendor-overlays/, control-library/, OSCAL exports, PROJECT-CONTEXT.md, CHANGELOG.md, drift-report.json. Quality target: matches 01_Canon/uiao-reference.docx visual standard.
* 2026-04-03: Key file locations table added to PROJECT-CONTEXT.md. vendor-overlays/ (NOT overlays/) confirmed as Big 7 source. 131 control YAMLs and 15 Mermaid PNGs confirmed from directory tree.
* 2026-04-02: AI hierarchy restructured. Grok retired. Claude Code promoted to Canon Steward and Lead Architect with direct GitHub integration. Comet-Perplexity (running Claude Sonnet) retained as orchestrator and browser/evidence agent. Gemini role locked to image generation only. Copilot retained for fast implementation. Stack simplified from four-model hierarchy to two-model core (Claude Code + Comet-Perplexity).
* 2026-03-26: FORMAT-CANON.md created as primary format authority. PROJECT-CONTEXT.md updated to establish format authority hierarchy before all other project context. All agents must read FORMAT-CANON.md before making any format decisions.
* 2026-03-24: Automated diagram generation implemented (copilot/diagram-automation). `canon/diagrams.yaml` is now the single source of truth for all Mermaid diagrams. `generate-docs` auto-generates PNGs; `generate-diagrams` CLI command available for standalone use. Mermaid fences post-processed to `<img>` tags in Markdown for DOCX/PPTX/PDF pipelines.
* 2026-03-24: Grill Master RE-PLAN fix-PR merge loop proven at scale (PRs #52, #54, #55, #56).
* 2026-03-24: Created PROJECT-CONTEXT.md to prevent context collision across Comet/Copilot/Claude layers
* 2026-03-24: uiao-validation-targets bootstrapped as live mock telemetry endpoint
* 2026-03-23: Agentic workflow bootstrapped with AGENTS.md

---

**Instruction to All Agents**:
Before starting any task, read this file in full. If your change affects architecture, update this file and reference the commit. Ruthlessly simplify orchestration — do not create new agents without updating this context.
