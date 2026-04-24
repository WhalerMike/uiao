# UIAO CLI Surface Audit — v0.4.0 baseline

Audit date: 2026-04-23
Baseline commit: `687db3bd` (post-PR #187)
Scope: M1 of [Phase 1 adoption readiness](https://github.com/WhalerMike/uiao/issues/183)

## Headline numbers

| Metric | Value |
|---|---|
| Total commands | **48** (40 top-level + 8 under sub-apps) |
| Commands with any help text | 48 (100%) |
| Commands with a runnable example in help | **4 (8%)** |
| Hidden/legacy commands | 0 |
| Source lines in `cli/app.py` | 1,375 |
| Already-modularized sub-apps | 6 (`evidence`, `ksi`, `orchestrator`, `oscal`, `scuba`, `substrate`) |

## Current inventory

| Command | Example? | Purpose |
|---|---|---|
| `adapter-run` | — | Run a vendor adapter and align claims (DNS-style, no heavy OSCAL conversion). |
| `adapter-run-scuba` | ✅ | Run SCuBA adapter: ingest a ScubaGear assessment report. |
| `canon-check` | — | Check canon YAML files for consistency. |
| `conmon-dashboard` | — | Export the KSI continuous monitoring dashboard. |
| `conmon-export-oa` | — | Export an OSCAL ongoing-authorization evidence artifact. |
| `conmon-process` | — | Process a Sentinel alert and auto-upsert a POA&M entry. |
| `evidence build` | ✅ | Build a canonical evidence bundle from a KSI result JSON file. |
| `generate-all` | — | Run the full UIAO generation pipeline. |
| `generate-artifacts` | — | Generate DOCX + PPTX with embedded PlantUML and Gemini visuals. |
| `generate-briefing` | — | Generate personal briefing document from live repo state. |
| `generate-diagrams` | — | Generate PlantUML .puml files and render them to PNG. |
| `generate-docs` | — | Render Jinja2 templates into Markdown docs. |
| `generate-docx` | — | Generate a rich DOCX leadership briefing with embedded visuals. |
| `generate-gemini` | — | Generate images via Gemini API. |
| `generate-pptx` | — | Generate a leadership briefing PPTX deck. |
| `generate-sbom` | — | Generate a CycloneDX 1.4 SBOM. |
| `generate-ssp` | — | Generate an OSCAL SSP from canon YAML. |
| `generate-visuals` | — | Render PlantUML diagrams to PNG for DOCX/PPTX embedding. |
| `ir-auditor-bundle` | — | Run full pipeline and write all auditor artifacts to a directory. |
| `ir-dashboard` | — | Build IR governance dashboard. |
| `ir-diff` | — | Diff two SCuBA runs. |
| `ir-drift-detect` | — | Detect drift between two IR state JSON files. |
| `ir-evidence-bundle` | — | Build a canonical EvidenceBundle from a SCuBA transform. |
| `ir-freshness` | — | Compute evidence freshness and generate refresh actions. |
| `ir-freshness-schedule` | — | Build a refresh job schedule from stale evidence. |
| `ir-generate-sar` | — | Generate an OSCAL Assessment Results (SAR) document. |
| `ir-governance-report` | — | Run full governance pipeline: SCuBA → IR → Evidence → Actions → Report. |
| `ir-poam-export` | — | Export POA&M rows (FAIL + WARN only) from a SCuBA run. |
| `ir-scuba-transform` | — | Transform normalized SCuBA JSON → IR Evidence objects. |
| `ir-ssp-inject` | — | Inject live SCuBA evidence into OSCAL SSP. |
| `ir-ssp-report` | — | Generate SSP narrative + lineage. |
| `ir-validate` | — | Validate a normalized SCuBA JSON file for IR pipeline conformance. |
| `ksi evaluate` | ✅ | Evaluate an IR file against KSI rules. |
| `orchestrator dispatch` | — | Dispatch a single adapter by registry ID. |
| `orchestrator list` | — | List adapters the scheduler would dispatch. |
| `orchestrator schedule` | — | Dispatch every active adapter in the registry. |
| `oscal generate` | ✅ | Generate OSCAL artifacts (POA&M + SSP) from a Plane 3 evidence bundle. |
| `scuba transform` | — | Transform a SCuBA assessment file into canonical IR JSON (Plane 1). |
| `substrate drift` | — | Bootstrap drift check: DRIFT-SCHEMA + DRIFT-PROVENANCE only. |
| `substrate walk` | — | Walk the substrate: validate module paths and canon document registry. |
| `validate` | — | Validate an OSCAL document against its schema. |
| `validate-ssp` | — | Validate OSCAL artifacts with compliance-trestle Pydantic models. |

## Findings

### F1 — Mixed layout: six nice sub-apps alongside 36 flat commands

The repo has already moved `evidence`, `ksi`, `orchestrator`, `oscal`, `scuba`, `substrate` into proper sub-apps (each in its own `cli/*.py` module). Good pattern. But 36 commands still live flat at the top level in `cli/app.py` (1,375 lines), grouped only by hyphen-prefixed naming convention:

| Prefix family | Count | Should be |
|---|---|---|
| `ir-*` | 13 | `ir` sub-app |
| `generate-*` | 11 | `generate` sub-app |
| `conmon-*` | 3 | `conmon` sub-app |
| `adapter-run*` | 2 | `adapter` sub-app |
| `canon-*` | 1 | `canon` sub-app (or merged into existing) |
| `validate*` | 2 | `oscal` sub-app (both validate OSCAL artifacts) |

After rationalization the top level is ~11 sub-apps instead of 40 flat commands.

### F2 — 92% of commands have no runnable example

Only 4 of 48 commands (`adapter-run-scuba`, `evidence build`, `ksi evaluate`, `oscal generate`) include an example invocation in their help text. A stranger reading `uiao ir-scuba-transform --help` sees one line of description and a parameter list — they have to read source (or guess) to learn the invocation shape.

### F3 — Ambiguous top-level `validate`

`validate` is a generic verb with no object. It currently validates OSCAL documents. In a rationalized tree it'd be `oscal validate` (no ambiguity, parallel to `oscal generate`, `oscal validate-ssp`).

### F4 — `generate-ssp` is not under `generate`, which doesn't exist as a group

Half-migration artifact: `generate-all` exists as a flat command that internally chains all the other `generate-*` commands, but there's no `generate` group for them to live under. Today `uiao generate --help` prints "No such command 'generate'".

### F5 — No smoke test for CLI surface

No test in `tests/` invokes every command's `--help`. Means an import regression in any of the 48 commands ships silently until a user hits it. (Example: the `api` [routes.py → routes/] split in PR #158 had a latent import bug that existed for an unknown period because nothing ever imported `uiao.api.routes`.)

## Proposed rationalized layout

```
uiao --help
├── adapter
│   ├── run              (was: adapter-run)
│   └── run-scuba        (was: adapter-run-scuba)
├── canon
│   └── check            (was: canon-check)
├── conmon
│   ├── dashboard        (was: conmon-dashboard)
│   ├── export-oa        (was: conmon-export-oa)
│   └── process          (was: conmon-process)
├── evidence
│   └── build            [unchanged]
├── generate
│   ├── all              (was: generate-all)
│   ├── artifacts        (was: generate-artifacts)
│   ├── briefing         (was: generate-briefing)
│   ├── diagrams         (was: generate-diagrams)
│   ├── docs             (was: generate-docs)
│   ├── docx             (was: generate-docx)
│   ├── gemini           (was: generate-gemini)
│   ├── pptx             (was: generate-pptx)
│   ├── sbom             (was: generate-sbom)
│   ├── ssp              (was: generate-ssp)
│   └── visuals          (was: generate-visuals)
├── ir
│   ├── auditor-bundle   (was: ir-auditor-bundle)
│   ├── dashboard        (was: ir-dashboard)
│   ├── diff             (was: ir-diff)
│   ├── drift-detect     (was: ir-drift-detect)
│   ├── evidence-bundle  (was: ir-evidence-bundle)
│   ├── freshness        (was: ir-freshness)
│   ├── freshness-schedule (was: ir-freshness-schedule)
│   ├── generate-sar     (was: ir-generate-sar)
│   ├── governance-report (was: ir-governance-report)
│   ├── poam-export      (was: ir-poam-export)
│   ├── scuba-transform  (was: ir-scuba-transform)
│   ├── ssp-inject       (was: ir-ssp-inject)
│   ├── ssp-report       (was: ir-ssp-report)
│   └── validate         (was: ir-validate)
├── ksi
│   └── evaluate         [unchanged]
├── orchestrator
│   ├── dispatch         [unchanged]
│   ├── list             [unchanged]
│   └── schedule         [unchanged]
├── oscal
│   ├── generate         [unchanged]
│   ├── validate         (was top-level: validate)
│   └── validate-ssp     (was top-level: validate-ssp)
├── scuba
│   └── transform        [unchanged]
└── substrate
    ├── drift            [unchanged]
    └── walk             [unchanged]
```

## Decision points (owner action required)

### D1 — Rollout strategy for the rename

The rationalization is a breaking change on public CLI names. Three options, ranked:

**Option A — Big bang in v0.5.0 (recommended).** Repo has zero external users; this is the cheapest moment to break names. Ship all renames in one PR with an ADR (next free: ADR-045). Adopters that install v0.5.0 get the new names; no shim code to maintain.

**Option B — Additive with deprecation window.** Keep old names working, register new names alongside them, emit DeprecationWarning from old names. Remove in v0.6.0. Costs ~1.5× the implementation work and carries deprecation shims forward one release. Only worth it if external users exist — and they don't yet.

**Option C — Keep names as-is.** Rejected: ambiguity (F3), half-migration (F4), and the 40-flat-command UX will become a permanent wart once the first external user arrives. This is exactly the right window to fix it.

### D2 — Scope of M1 PR

Option A's M1 PR would bundle:
1. Module split: carve `ir/`, `generate/`, `conmon/`, `adapter/`, `canon/` out of `cli/app.py` (shrinks 1,375 → ~200 lines).
2. Sub-app registration: register new sub-apps in `cli/app.py`.
3. Smoke test: `tests/test_cli_help_smoke.py` that invokes `--help` on every command (addresses F5).
4. Docstring backfill: add a runnable example to every command (addresses F2).
5. ADR-045 ratifying the rename + the convention going forward ("new commands MUST live under a sub-app").

### D3 — Minor naming questions

- `ir validate` and `oscal validate` — same verb, different objects. Acceptable (sub-app disambiguates) or confusing (users type wrong one)?
- `ir generate-sar` vs moving it to `generate sar` — it generates an OSCAL artifact but from the IR pipeline. Two defensible homes.
- `adapter run` vs `adapter run-scuba` — if more adapter-specific runners land, a single `adapter run --vendor scuba` with a `--vendor` option may age better than vendor-specific sub-commands.

## Recommended next step

Approve **Option A**. I'll produce the M1 PR (module split + smoke test + docstring backfill + ADR-045). Target ~2 focused commits: one for the mechanical rename + module split, one for the docstring backfill + smoke test.
