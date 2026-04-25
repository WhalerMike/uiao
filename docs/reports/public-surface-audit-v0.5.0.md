# UIAO Public Surface Audit — v0.5.0 baseline

Audit date: 2026-04-24
Baseline commit: `91c59f91` (post-PR #201)
Scope: M5 of [Phase 1 adoption readiness](https://github.com/WhalerMike/uiao/issues/183)
Predecessor: [`docs/reports/cli-surface-audit-v0.4.0.md`](cli-surface-audit-v0.4.0.md)

## Goal

Close the gap between what's *implemented* in the codebase and what
an external user can *reach* through the documented public surfaces
(CLI commands and FastAPI routes). The motivating prompt: the
pre-OSS ghost `v1.0.0` tag (commit `b8f7001d`, retired in PR #170)
advertised "Auditor API, CQL Engine, Enforcement Runtime" as the
v1.0 deliverable. This audit checks each one against the v0.5.0
public surface and decides for each: **expose**, **document as
library-only**, or **retire**.

## Headline numbers

| Metric | Value |
|---|---|
| Top-level Python modules under `src/uiao/` | 30 |
| CLI sub-apps after [ADR-046](../../src/uiao/canon/adr/adr-046-cli-surface-convention.md) | 11 |
| Total CLI commands | 44 |
| FastAPI route handlers (gated behind `[api]` extra) | 17 |
| Modules with **no** public surface (CLI or API) | 1 (`enforcement`) |
| Modules that are public (powering CLI/API) but library-callable | every other module |

## Inventory by module

Categorisation legend: **CLI** = reachable from `uiao …`; **API** =
reachable from `[api]` extra FastAPI routes; **library** = importable
but not directly user-facing; **internal** = supports another module
and not intended as a public surface.

| Module | Surface | Reachable as | Notes |
|---|---|---|---|
| `abstractions/` | internal | — | Type stubs / protocols. Library-only by design. |
| `adapters/` | CLI | `uiao adapter run <vendor>`, `uiao adapter run-scuba` | 13 adapters; Terraform / ScubaGear / Entra / Intune / etc. |
| `api/` | API | FastAPI routes (uvicorn-served) | 5 route modules: `auditor`, `boundary`, `health`, `orgpath`, `survey`. 17 endpoints total. |
| `auditor/` | CLI + API | `uiao ir auditor-bundle`, `GET /auditor/{evidence,findings,poam,oscal/*,graph/*}` | Generator (CLI) + reader (API). |
| `canon/` | CLI | `uiao canon check` | 1 command. |
| `cli/` | — | (the CLI itself) | |
| `collectors/` | internal | — | Adapter helpers. Library-only. |
| `config.py` | internal | — | Settings loader. |
| `coverage/` | library | — | Powers `uiao ir ssp-report`. |
| `cql/` | CLI | `uiao cql query` | Compliance Query Language engine (UIAO_108). 1 command. |
| `dashboard/` | CLI | `uiao ir dashboard`, `uiao conmon dashboard` | |
| `diff/` | CLI | `uiao ir diff` | |
| `directory_migration/` | library | — | Modernization adapter helper modules. |
| `enforcement/` | **import-only** | — | **GAP — see F1.** UIAO_111 Enforcement Runtime: 223 lines, 7 classes (`EPLPolicy`, `EnforcementAdapter`, `EnforcementRuntime`, …), 5-phase pipeline, full test coverage at `tests/test_enforcement_runtime.py`. Not reachable from any CLI/API. |
| `evidence/` | CLI + API | `uiao evidence build`, `uiao evidence graph`, `GET /auditor/graph/{control_id}` | Bundle + Graph (UIAO_113). |
| `freshness/` | CLI | `uiao ir freshness`, `uiao ir freshness-schedule` | |
| `generators/` | CLI | `uiao generate {ssp,docs,docx,pptx,sbom,…}` (11 commands) | |
| `governance/` | CLI | `uiao ir governance-report`, `uiao ir drift-detect` | Drift classification + governance actions. |
| `ir/` | CLI | `uiao ir {scuba-transform,evidence-bundle,…}` (14 commands) | The largest sub-app surface. |
| `ksi/` | CLI | `uiao ksi evaluate` | 1 command. |
| `models/` | internal | — | Pydantic schemas. Library-only. |
| `modernization/` | internal | — | Modernization-class adapter implementations. |
| `monitoring/` | CLI | `uiao conmon {process,export-oa,dashboard}` | Sentinel hook + ongoing-auth. |
| `onboarding/` | library | — | `wizard.py` — interactive setup, not CLI-registered. |
| `orchestrator/` | CLI + API | `uiao orchestrator {list,dispatch,schedule}` | UIAO_100. Compliance Orchestrator. |
| `oscal/` | CLI | `uiao oscal {generate,validate,validate-ssp}` | |
| `rules/` | internal | — | KSI rule registry (data, not code). |
| `schemas/` | internal | — | JSON Schema authority. |
| `ssp/` | library | — | Powers `uiao ir ssp-report` and `uiao ir ssp-inject`. |
| `substrate/` | CLI | `uiao substrate {walk,drift}` | |
| `utils/` | internal | — | Common helpers. |
| `validators/` | library | — | Powers `uiao ir validate`. |

## Findings

### F1 — Enforcement Runtime is import-only

`src/uiao/enforcement/runtime.py` (223 lines, UIAO_111) implements
the Enforcement Runtime that the ghost-v1.0.0 tag advertised as
shipped: 6-state machine (`EVALUATING` → `COMPLIANT` / `VIOLATED` →
`ENFORCING` → `REMEDIATED` / `FAILED`), batch run, EPL policy
contract, no-op fallback adapter. Test coverage at
`tests/test_enforcement_runtime.py` exercises all the paths.

But there is **no `uiao enforcement` sub-app**. A user who wants to
run an enforcement loop has to import `EnforcementRuntime` from a
Python script. That's a real adoption bug — the feature exists, has
tests, has its own UIAO_NNN, and is not reachable from the documented
public surface.

### F2 — Auditor API is gated behind `[api]` extra and undocumented in CLI quickstart

The 9 routes under `/auditor/*` (evidence, findings, poam,
oscal/{sar,ssp,poam,sap}, graph/{control_id}) are the highest-value
read API for a downstream auditor's compliance dashboard. Today they
ship behind `pip install "uiao[api]"`. That gate is appropriate
(FastAPI + uvicorn + msal are weighty deps) but the quickstart
doesn't mention them. A v0.5.0+ adopter who reads `quickstart.md`
believes UIAO is CLI-only and never discovers the API.

### F3 — `cql query` is the only CQL surface

`uiao cql query` exposes one command. CQL ([UIAO_108](../../src/uiao/canon/specs/cql.md))
supports more than read-queries — saved-query registries, schema
introspection, query-plan inspection. None of those are CLI-reachable.
Whether this is a gap depends on what CQL is *intended* to be: a
canonical query language with discoverability, or a single-shot eval.
Owner decision.

### F4 — `evidence graph` is dual-surfaced; the rest of `evidence` is one-trick

`uiao evidence` only exposes 2 commands (`build`, `graph`). The
underlying module has builder, bundler, collector, ksi_linker, linker,
poam — most of which are reachable indirectly via `uiao ir
{evidence-bundle,poam-export}` but never through `uiao evidence` itself.
That's not a bug — `ir` is the canonical SCuBA→IR→evidence pipeline
sub-app — but a user typing `uiao evidence --help` may reasonably
expect to see more.

## Decisions needed

### D1 — Expose Enforcement Runtime via CLI

Options:

- **D1a (recommended):** add `uiao enforcement run --policy <yaml> --evidence <path>` that loads policies + an evidence bundle and runs one cycle of the 5-phase pipeline. Wire to `EnforcementRuntime` directly.
- **D1b:** add a sub-app `uiao enforcement {run,list-policies,evaluate}` with full state-machine introspection. Larger surface; appropriate if enforcement is meant to be operator-facing.
- **D1c:** retire `enforcement/` from public surface. Explicitly document it as library-only, remove the UIAO_111 advertising. Defensible if owner decides enforcement isn't ready.

The repo has tests, an UIAO_NNN, ADR coverage. D1c retreats from a feature; D1a is the minimum viable exposure that closes the gap. Recommend D1a for v0.5.0 with a follow-up PR for the full sub-app shape (D1b) when there's an external user driving requirements.

### D2 — Mention `[api]` extra in the quickstart

Add a sub-section to `docs/docs/quickstart.md` after step 5 titled
"Want a REST API?" pointing at `pip install "uiao[api]"` and the
auditor/health/survey/orgpath/boundary endpoints. ~10 lines, no code
changes. Recommend yes.

### D3 — Retain `cql` as single-command sub-app, or extend?

- **D3a (recommended):** retain. CQL is a query language; `query` is
  its core verb; saved-query support is a future feature, not a v0.5.0
  gap.
- **D3b:** extend with `uiao cql {query,list-saved,explain,schema}`. Useful only if the
  saved-query registry actually exists (it doesn't — UIAO_108 §4 is
  proposed but not implemented).

Recommend D3a. Revisit when saved-query support lands.

### D4 — `evidence` sub-app scope

- **D4a (recommended):** keep `evidence` at 2 commands. The IR pipeline
  sub-app (`ir`) is the canonical evidence-flow surface. Document the
  redundancy / division of responsibility in the rule
  `src/uiao/rules/canon-consumer.md`.
- **D4b:** flatten — drop `uiao evidence` entirely; everything routes
  through `ir`.
- **D4c:** expand — add `evidence {linker,collector,build-poam}` etc.

Recommend D4a. The split between `evidence` (canonical bundle) and
`ir` (pipeline-stage operations on evidence) is principled; keep it
but document it.

## Comparison to ghost-v1.0.0 advertising

| Ghost-v1.0.0 feature | Status today | Action |
|---|---|---|
| **Auditor API** | dual-surface (CLI + 9 API routes); test coverage at `tests/test_auditor_api.py` + `test_auditor_bundle.py` | ✅ shipped — documentation gap (D2) |
| **CQL Engine** | CLI + module; test coverage at `tests/test_cql_engine.py` | ✅ shipped (single-command sub-app per D3a) |
| **Enforcement Runtime** | **import-only**; test coverage at `tests/test_enforcement_runtime.py`; CLI gap | ❌ **shipped but unreachable — D1** |
| **Evidence Graph (UIAO_113)** | dual-surface (`uiao evidence graph` + `GET /auditor/graph/{control_id}`); landed in PR #185, #196, #200 | ✅ shipped |
| **Terraform adapter** | CLI: `uiao adapter run terraform` | ✅ shipped |
| **Compliance Orchestrator (UIAO_100)** | CLI: 3-command sub-app | ✅ shipped |

**Score: 5/6 fully exposed.** Enforcement Runtime is the only ghost-v1.0.0 promise the v0.5.0 public surface fails to keep.

## Recommended PR sequence

1. **D1a — Enforcement CLI** (1 PR, ~80 lines): add
   `src/uiao/cli/enforcement.py` with one command `uiao enforcement
   run`. Register in `cli/app.py`. Add smoke test. Document in
   `UIAO_008 CLI Reference`. Tag as v0.5.0 enforcement-runtime exposure.

2. **D2 — Quickstart `[api]` mention** (1 PR, ~15 lines): augment
   `docs/docs/quickstart.md` step-7 with a "Want a REST API?" block.
   Add CI check that `uvicorn uiao.api.app:app` starts (already exists
   in `tests/test_api_smoke.py`).

3. **D4a documentation** (1 PR, ~30 lines): write a brief
   "evidence-vs-ir division of responsibility" note in
   `src/uiao/rules/canon-consumer.md` explaining why both sub-apps
   exist and when to use each.

After those land, **Phase 1 exit criterion** is met: every
ghost-v1.0.0 promise reachable through the documented public surface,
and the quickstart points adopters at every available shape (CLI +
optional API).

## Out of scope

- Per-route auth on the FastAPI surface (already mTLS + Entra-anchored;
  documented in `src/uiao/api/auth/`)
- The `boundary`, `orgpath`, `survey` routes' depth — they're CLI-less
  by design (operationally invoked over HTTP, not from a shell)
- Modernization-adapter classes — `modernization/` is intentionally
  internal; modernization adapters are accessed via the same
  `uiao adapter run <vendor>` surface as conformance adapters
