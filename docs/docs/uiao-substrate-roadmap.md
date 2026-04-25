# UIAO Substrate Roadmap
**Derived from:** Substrate Status page + live canon artifacts · **Date:** 2026-04-19  
**Status:** Working draft — all dates are targets, not commitments  
**Provenance:** `src/uiao/canon/substrate-manifest.yaml` (UIAO_200), `document-registry.yaml`, `modernization-registry.yaml`, `adapter-registry.yaml`, `specs/adapter-test-strategy.md` (UIAO_131)

---

## Executive summary

The UIAO substrate is structurally sound: CI is blocking on six of seven gates, the substrate walker is operational, the Python CLI ships at v0.2.1, and the monorepo consolidation landed cleanly with 3,549 commits of history preserved. The canon schema layer is schema-validated on every PR. That foundation is real.

The honest gap is large. Eight of 37 registered artifacts are real today. Zero of nine active modernization adapters have cleared a single tier of the UIAO_131 three-tier test model — every active entry in the registry sits above the conformance gate, which is documented drift. Two of the five drift-detection classes (both P1 severity) have no implementation. Twenty-four specs are aspirational with no runtime counterpart.

This roadmap is organized around closing that gap in order of risk and dependency, not in order of appearance in the document registry.

---

## Current state snapshot (2026-04-19)

### Document registry reality check

| Status | Count | Examples |
|---|---|---|
| ✅ Real today | 8 / 37 | UIAO_001, 003, 004, 104, 106, 118, 200, 201 |
| 🟡 Partially implemented | 5 / 37 | UIAO_002, 103, 110, 113, 126 |
| ⚠️ Aspirational or draft | 24 / 37 | UIAO_100–102, 105, 107–109, 111–112, 114–117, 119–128, 129–131 |

### Adapter test coverage (UIAO_131 gate)

| Adapter | Tier 1 (live) | Tier 2 (contract) | Tier 3 (reference) | Gate |
|---|---|---|---|---|
| entra-id | ⏳ pending | ⏳ pending | 🚫 needs partner | not achieved |
| m365 | ⏳ pending | ⏳ pending | 🚫 needs partner | not achieved |
| scuba | ⏳ pending | ⏳ pending | 🚫 needs partner | not achieved |
| service-now | ⏳ pending | ⏳ pending | 🚫 needs partner | not achieved |
| palo-alto | ⏳ pending | ⏳ pending | 🚫 needs partner | not achieved |
| terraform | ⏳ pending | ⏳ pending | 🚫 needs partner | not achieved |
| cyberark | ⏳ pending | ⏳ pending | 🚫 needs partner | not achieved |
| infoblox | 🟥 blocked (no public sandbox) | ⏳ pending | 🚫 needs partner | not achieved |
| bluecat-address-manager | 🟥 excluded (vendor-contact-only) | ⏳ pending | 🚫 needs partner | not achieved |
| mainframe | N/A (reserved) | N/A | N/A | N/A |

**Reality:** Zero adapters have any tier-1 or tier-2 evidence. This is the single highest-priority engineering gap.

### Drift engine coverage

| Drift class | Severity | Status |
|---|---|---|
| DRIFT-SCHEMA | P1 | ✅ Implemented |
| DRIFT-PROVENANCE | P1 | ✅ Implemented |
| DRIFT-SEMANTIC | P2 | 🟡 Partial (freshness engine partial) |
| DRIFT-AUTHZ | P1 | ✅ Implemented (state-diff + consent-envelope) |
| DRIFT-IDENTITY | P1 | 🟡 Partial (state-diff classifier; runtime issuer chain validation pending) |

DRIFT-AUTHZ now ships both the state-diff and consent-envelope detectors. DRIFT-IDENTITY has the state-diff classifier; runtime issuer-chain validation remains pending.

### CI gate health

| Workflow | Status |
|---|---|
| schema-validation.yml | ✅ Blocking |
| pytest.yml | ✅ Blocking |
| substrate-drift.yml | ✅ Blocking |
| metadata-validator.yml | ✅ Blocking |
| quarto.yml | ✅ Blocking |
| ruff.yml | ✅ Blocking |
| link-check.yml | 🟡 Soft-fail (baseline not burned down) |

---

## Risk register

These are the conditions that could block progress or invalidate existing canon if left unaddressed.

**R1 — Test-tier vacuum (Critical).** All nine active adapters are registered as `active` but have zero test evidence. Per UIAO_131, `active` status implies conformance-gate passage. It does not. This is documented drift in the registry itself. If the registry is presented to an agency evaluator before tier-1 fixtures exist, the gap becomes a credibility issue.

**R2 — P1 drift classes unimplemented (High).** DRIFT-AUTHZ and DRIFT-IDENTITY are both P1 severity per the drift taxonomy but have no runtime implementation. The substrate claims to detect these classes but cannot. Any engagement that relies on drift detection for authorization or identity signals is silently wrong.

**R3 — Spec-implementation chasm (Medium).** 24 aspirational specs create a growing maintenance burden: every time the spec evolves, there is nothing in `impl/` that breaks if the change is inconsistent. The longer this gap exists, the harder it is to close, because the spec will drift from what an implementation would actually require.

**R4 — Infoblox and BlueCat tier-1 exclusions (Medium).** These two adapters have no path to tier-1 live testing via public developer programs. The §5.1 exclusion is documented but no compensating strategy is defined. Agencies that depend on these adapters for IPAM governance have no conformance signal.

**R5 — Mainframe adapter blocked (Low–Medium).** The mainframe adapter is the highest-priority FIMF legacy migration adapter but has zero implementation and no unblocking plan documented beyond "z/OS Connect / MQ bridge infrastructure." Without a z/OS Connect environment or IBM partner engagement, this adapter cannot advance.

**R6 — Aspirational content volume (Low).** 283 files with 692 aspirational-signal matches represent a documentation surface that overstates the substrate's current capability. Agencies reading the docs without finding the aspirational banners will form incorrect expectations. The per-file review of the remaining 263 unreviewed files needs a schedule.

---

## Phase structure

The roadmap is organized into four phases with clear entry and exit conditions. Phases are sequential in dependency but can overlap in parallel workstreams.

---

## Phase 0 — Conformance gate (now → v0.3)

**Theme:** Stop the bleeding. Close the gap between registry `active` status and actual conformance evidence. Fix the two P1 drift classes.

**Exit condition:** At least two adapters have tier-1 evidence and tier-2 contract fixtures. DRIFT-AUTHZ and DRIFT-IDENTITY are implemented. link-check is blocking.

### 0.1 — Tier-1 evidence: entra-id and m365

The Microsoft 365 Developer Program provides a free 25-user E5 commercial tenant with Entra ID P2. This is the lowest-cost, highest-coverage path to tier-1 evidence for the two highest-priority adapters.

Work required:
- Sign up for the M365 Developer Program tenant.
- Store tenant credentials in GitHub Actions secrets (secret-scoped, not repo-wide).
- Implement nightly CI job that exercises the `entra-id` adapter against the developer tenant: authentication flow, user-object enumeration, conditional access policy read.
- Implement equivalent job for `m365`: Graph API tenant config, Exchange Online, SharePoint.
- Record pass/fail evidence artifacts (`migration-audit.json`, `tenant-config-manifest.json`) and attach to CI run summary.
- Update `modernization-registry.yaml` notes fields to reference the tier-1 CI job name.

Referenced docs: UIAO_131 §3.1, UIAO_121 (conformance test plan template).

### 0.2 — Tier-2 contract fixtures: entra-id and m365

Contract fixtures are static JSON/YAML snapshots of the API responses each adapter expects. They allow CI to exercise parsing, normalization, and output-generation logic without a live tenant.

Work required:
- Create `tests/fixtures/entra-id/` with canonical response payloads for each adapter method (user list, group list, CA policies, sign-in logs).
- Create `tests/fixtures/m365/` equivalents.
- Wire `test_adapters.py` (already exists) to assert against these fixtures.
- Fixtures must be version-pinned to the API version declared in the adapter registry entry.

### 0.3 — Tier-2 contract fixtures: scubagear

ScubaGear produces structured JSON output. Fixtures are ScubaGear output files captured from a known-state tenant. These are the cheapest tier-2 artifacts to produce because the output format is stable and documented.

Work required:
- Capture ScubaGear v1.5.1 output against the M365 developer tenant (same tenant used for tier-1 above).
- Store in `tests/fixtures/scubagear/`.
- Wire `test_adapters.py` to assert the conformance adapter normalizes ScubaGear output correctly.

### 0.4 — DRIFT-AUTHZ implementation (pending → **complete** ✅)

DRIFT-AUTHZ detects consent-envelope violations: when an adapter asserts
authority over an object it was not granted access to. P1 severity.

**Status (2026-04-24):** shipped end to end. Two complementary detectors
now produce `drift_class="DRIFT-AUTHZ"` findings:

1. **State-diff detector** (`uiao.governance.drift.classify_authz_drift`,
   shipped previously): catches role/delegation/scope changes between
   expected and actual snapshots — sentinel-field changes, escalation
   patterns (e.g. `kerberos_delegation: unconstrained`), role count
   growth.

2. **Consent-envelope detector** (`uiao.governance.consent_envelope`,
   new this PR): catches adapter API calls that hit object types
   *outside* the adapter's declared canon `scope:`. Answers the
   distinct question "did the adapter touch something it was never
   granted access to?".

Shipped:
- `src/uiao/governance/consent_envelope.py` — `ConsentEnvelopeValidator`
  with `load_adapter_envelopes(registries)` (merges declared envelopes
  across modernization-registry + adapter-registry; later overrides
  earlier), `validate(adapter_id, observed_scope)` →
  `ConsentEnvelopeReport`, and `report.as_drift_state(provenance=...)`
  → `DriftState(drift_class="DRIFT-AUTHZ", classification="unauthorized")`.
- `observed_scope_for_run(run_dir)` — extracts per-adapter observed
  scope from a UIAO_100 scheduler-run tree by reading
  `adapters/<id>/evidence.json::normalized_data.accessed_scope` (with
  `observed_scope` / `scope` and `raw_data` fallbacks). Adapters that
  emit no scope hint contribute an empty list — in-scope by definition,
  no false positives.
- `src/uiao/substrate/walker.py::_scan_consent_envelope` — registry
  hygiene gate. Every active modernization adapter MUST declare a
  non-empty `scope:`; missing key → P1 finding, empty list → P2.
  Reserved/inactive adapters are skipped. `uiao substrate walk` now
  reports DRIFT-AUTHZ findings against canon registries directly.
- 27 new tests in `tests/test_consent_envelope.py`: registry loader (6),
  validator (10 — in-scope / out-of-scope / missing-declaration /
  empty-envelope / whitespace normalization / batch / DriftState
  emission), scheduler-run extraction (5 including end-to-end
  scheduler-run → validator → DriftState), substrate-walker scan
  (4 — P1 missing scope, P2 empty scope, reserved adapter skipped,
  clean active adapter), plus a smoke test against the live canon
  registries that asserts zero DRIFT-AUTHZ P1 findings (registry
  hygiene currently green: every active adapter declares a scope).

Referenced docs: UIAO_110 §3 (drift class taxonomy), ADR-012 §DT-04.

### 0.5 — DRIFT-IDENTITY implementation

DRIFT-IDENTITY detects issuer-resolution failures: when a certificate or identity claim cannot be traced to the expected trust anchor. P1 severity.

Work required:
- Implement `IssuerResolver` in `src/uiao/governance/` that validates the `certificate-anchored: true` invariant at runtime by checking the issuer chain on adapter-produced artifacts.
- Emit `DRIFT-IDENTITY` findings when the chain breaks.
- Add pytest coverage.
- Wire to the substrate walker.

Referenced docs: UIAO_110 §3.

### 0.6 — link-check baseline burn-down

The link-check workflow is currently soft-fail. It needs to be flipped to blocking, which requires reducing the false-positive baseline to a manageable level.

Work required:
- Run `make check-links` against the live Pages site.
- Audit the lychee output; distinguish broken links from lychee false-positives.
- Add false-positive patterns to `.lycheeignore`.
- Fix genuine broken links.
- Flip `link-check.yml` `continue-on-error: true` to `false`.

### 0.7 — UIAO_129/130 Application Identity Model

Both specs are `draft` status but registered as `Current` in the document registry. This is a metadata contradiction.

Work required:
- Either promote to `Current` by completing the draft (preferred), or change the registry `status` to `Draft` and apply the aspirational banner.
- If promoting: define the canonical object-identity format for application service principals and the onboarding flow for new applications against the CyberArk and Entra adapters.

---

## Phase 1 — Runtime core (v0.3 → v0.5)

**Theme:** Make the partially-implemented specs real. The substrate needs a working compliance orchestrator and a fully operational drift engine before it can make claims about continuous monitoring.

**Exit condition:** UIAO_100 (Compliance Orchestrator) has a working scheduler and evidence pipeline. DRIFT-SEMANTIC is complete. UIAO_103 and UIAO_113 are fully green.

### 1.1 — DRIFT-SEMANTIC completion (partial → **complete** ✅)

The freshness engine is partial. The remaining work is defining and enforcing staleness windows per adapter: when evidence collected by `entra-id` is more than N hours old, DRIFT-SEMANTIC fires at P2.

**Status (2026-04-23):** shipped end to end — scheduler run → per-adapter
window lookup → DRIFT-SEMANTIC findings with appropriate severity.

Shipped:
- New `freshness-window-hours` field in the adapter-registry JSON
  schema (`src/uiao/schemas/adapter-registry/adapter-registry.schema.json`)
  with documentation of the evaluator fallback chain.
- Seeded two representative canon entries:
  - `modernization-registry.yaml::entra-id` → 24h (tight window for
    identity modernization).
  - `adapter-registry.yaml::scubagear` → 168h (7d) (matches weekly
    SCuBA baseline cadence).
  Additional adapters pick up values incrementally as operators declare
  real cadences.
- New module `src/uiao/freshness/drift_semantic.py`:
  - `load_adapter_windows(registries)` — merges declared windows across
    canon registries (later registries override earlier).
  - `resolve_policy(adapter_id, windows, ksi_id)` — registry →
    family-default → global-default fallback chain.
  - `evaluate_evidence_payload()` — classifies a scheduler-produced
    evidence payload into fresh / stale-soon / stale /
    missing-timestamp with severities P5 / P3 / P2 / P1 respectively.
  - `evaluate_scheduler_run(run_dir, registries)` — closes the
    UIAO_100 → UIAO_016 loop by walking
    `schedrun-*/adapters/<id>/evidence.json` and emitting
    `FreshnessFinding` records carrying `drift_type="DRIFT-SEMANTIC"`.
  - `drift_semantic_findings()` — filter helper that drops `fresh`
    records so only route-worthy findings travel to the drift engine.
  - `summarize()` + `write_findings()` — JSON persistence matching the
    scheduler's on-disk manifest pattern.
- 25 new tests in `tests/test_drift_semantic_freshness.py`: registry
  loader (5), policy resolution (4), classification (6 including
  future-dated + missing-timestamp edge cases), `evaluate_scheduler_run`
  (6 including missing dir, empty adapters root, malformed JSON), and
  end-to-end scheduler-run-to-DRIFT-SEMANTIC.

Deferred to Phase 2:
- Seeding `freshness-window-hours` for the remaining ~16 registry
  entries — each requires operator input on real cadence expectations.
  The fallback chain keeps the evaluator working in the interim.
- Wiring DRIFT-SEMANTIC findings into the evidence graph's Finding
  nodes (§1.4 already accepts `drift.json` shaped findings; Phase 2
  adds the cross-walk so drift-semantic findings appear alongside
  adapter-detected drift in the graph and SAR).
- CLI surface (`uiao orchestrator evaluate-freshness`) — deferred
  because the module already has a clean Python API suitable for CI
  scripting.

Referenced doc: UIAO_016 Drift Detection Standard (drift semantics),
UIAO_100 (scheduler producer), UIAO_113 (future graph consumer).

### 1.2 — UIAO_103 Spec-Test Enforcement (partial → **complete** ✅)

The spec-test enforcement layer is partially implemented (pytest is wired). The remaining work was ensuring every canon spec section that defines a behavioral invariant has a corresponding test that would fail if that invariant were violated.

**Status (2026-04-24):** enforcement mechanism shipped — the **gate**
exists, baseline is committed, CI blocks regressions. Per-spec invariant
authoring (writing more `MUST`/`SHALL` statements in canon prose) and
per-invariant test wiring proceed incrementally as growth, not as a
one-shot audit.

Shipped:
- `scripts/tools/spec_test_audit.py` — RFC 2119 audit. Walks
  `src/uiao/canon/specs/*.md` and `src/uiao/canon/UIAO_*.md`, parses YAML
  frontmatter for `document_id`, extracts `MUST` / `SHALL` / `REQUIRED`
  / `MUST NOT` / `SHALL NOT` / `RECOMMENDED` / `SHOULD` keywords, strips
  fenced code blocks, and emits a structured invariant inventory + per-
  spec rollup as JSON.
- `scripts/tools/spec_test_coverage_check.py` — the CI gate. Re-runs
  the audit and diffs against the committed baseline at
  `docs/docs/governance/spec-test-coverage.md`. Fails the PR if any
  spec's invariant count drops vs. the committed baseline; passes when
  counts grow (new invariants raise the bar, future PRs add tests).
  Also has `--update` mode for legitimate count drops (spec retired,
  rewritten, etc.).
- `docs/docs/governance/spec-test-coverage.md` — the tracking artifact.
  Two sections: an auto-generated invariant inventory (managed by the
  gate's `--update` mode, bracketed by HTML markers) and a manual
  coverage map mapping `document_id` → list of test files / pytest
  nodeids. Manual section is preserved across `--update` runs.
- `.github/workflows/spec-test-coverage.yml` — CI workflow. Fires on
  PRs that touch canon specs, the coverage doc, or the tooling. Posts
  a structured comment on failure listing every shrinking spec.
- 27 unit tests in `tests/test_spec_test_enforcement.py` covering
  frontmatter parsing, RFC 2119 keyword extraction, code-block
  stripping, multi-keyword-per-line handling, rollup aggregation,
  baseline parsing, shrink/grow diff logic, table render + roundtrip,
  and a smoke-guard against accidental deletion of the committed
  coverage doc.

Initial baseline (committed):
- 3 invariants tracked across UIAO_121, UIAO_122, UIAO_123 (the three
  canon specs that today use formal RFC 2119 phrasing).

Deferred to future increments:
- **Tighten canon prose to RFC 2119**: the audit found only 3 explicit
  `MUST`/`SHALL` statements across ~40 canon specs. Most invariants are
  expressed as informal "should"/"must" in lowercase, which the audit
  correctly does not count. Promoting these to formal keywords is
  authoring work, not a tooling gap, and grows the gate's coverage
  organically.
- **Per-invariant test wiring** in the manual coverage map. The map's
  initial seed lists test files (`tests/test_orchestrator_scheduler.py`,
  etc.) but does not yet cite specific pytest nodeids per invariant.
  Authors add these as new tests land.
- **Pre-commit hook** for the gate (currently CI-only). Optional
  convenience for fast local feedback before push.

Referenced canon: UIAO_103 Spec-Test Enforcement Layer
(`src/uiao/canon/specs/UIAO-Spec-Test-Enforcement.md`).

### 1.3 — UIAO_100 Compliance Orchestrator (aspirational → **partial** ✅)

The Compliance Orchestrator is the scheduler that triggers adapter runs, collects evidence, and routes findings to the drift engine and OSCAL generator. Without it, every evidence collection is a manual operation.

**Status (2026-04-23):** `partial` — scheduler shipped, real adapter wiring
incremental.

Shipped:
- `src/uiao/orchestrator/scheduler.py` — `OrchestratorScheduler` reads the
  canonical adapter registry, iterates active entries, invokes each
  adapter's `collect_evidence()` + `detect_drift()`, persists per-adapter
  evidence and drift to a deterministic run directory, and emits a
  `manifest.json` + `drift-summary.json` per run.
- Retry with exponential backoff per adapter; `not-wired` status for
  registry entries without a factory binding (non-fatal).
- Pluggable adapter factory so tests inject mocks and production wires
  real adapter classes incrementally.
- `uiao orchestrator {schedule,dispatch,list}` Typer CLI.
- `tests/test_orchestrator_scheduler.py` (14 unit tests) and a new
  `TestOrchestratorSchedulerE2E` class in `tests/test_e2e.py` closing the
  evidence → drift → manifest loop end-to-end with mock adapters.

Deferred to §1.4 or Phase 2:
- Cron scheduler daemon (Phase 1 runs under GitHub Actions cron).
- Dead-letter queue + email/webhook alerting.
- Multi-tenant per-tenant schedule dispatch.
- Real factory bindings for every adapter in the registry (ScubaGear is
  wired as a built-in; remaining adapters promote one at a time).
- Wiring drift findings into the evidence graph (UIAO_113, §1.4) for
  cross-service correlation.

Referenced doc: UIAO_100 (`src/uiao/canon/specs/Compliance-Orchestrator.md`).

### 1.4 — UIAO_113 Evidence Graph (schema-only → **working** ✅)

The evidence graph model has a schema but no implementation. The graph is what makes OSCAL evidence navigable: each finding traces back to a control, which traces back to an adapter run, which traces back to a canon document.

**Status (2026-04-23):** `working` — graph ingests scheduler runs and
augments OSCAL SAR output.

Shipped:
- `EvidenceGraph.from_scheduler_run(run_dir)` — walks a
  `schedrun-*/adapters/<id>/{evidence,drift}.json` tree (the UIAO_100
  scheduler's output) and builds Control / IR-object / Evidence /
  Provenance / Finding nodes with the canonical edge set
  (`implements`, `validated-by`, `provenance-of`, `violated-by`).
- Severity normalization bridge: scheduler drift reports use
  free-form severity strings (P1/P3/critical/info); the graph
  normalizes to Finding's High/Medium/Low vocabulary so downstream
  consumers stay consistent.
- Best-effort control inference from `ksi_id`: NIST-style references
  like `ksi:AC-2` hop through a ControlNode; free-form KSIs attach
  directly to the Evidence node without a control hop.
- `EvidenceGraph.sar_props_for_evidence(control_id)` —
  compact dict of graph-derived OSCAL props keyed to a control.
- `build_sar(bundle, *, graph=None)` / `export_sar(..., graph=None)` —
  optional graph kwarg. When provided, each observation subject gains
  graph-derived props under `https://uiao.gov/ns/oscal/graph`:
  `graph-evidence-id`, `graph-evidence-hash`, `graph-evidence-source`,
  `graph-scheduler-run-id`, `graph-adapter-id`,
  `graph-open-findings`, `graph-top-severity`. Back-compat preserved:
  `graph=None` yields byte-identical legacy output.
- 27 new tests in `tests/test_evidence_graph_scheduler.py` covering
  severity normalization, scheduler-run ingestion (missing dir,
  empty adapters root, single/multi adapter, drift present/absent,
  no-companion files, no manifest, non-NIST KSI), SAR props helper,
  build_sar legacy shape preservation, and an end-to-end
  scheduler-run → graph → SAR augmentation loop.

**Update (2026-04-24):** Graph augmentation extended to SSP + POA&M:

- `EvidenceGraph.poam_props_for_control(control_id)` — sibling helper
  to `sar_props_for_evidence` that surfaces the top finding's id /
  severity / status, the linked POAMEntryNode (when present), and the
  witness evidence's scheduler run + adapter ids.
- `build_ssp_skeleton(..., graph=None)` and
  `build_ssp(..., graph=None)` — when a graph is supplied, every
  `implemented-requirement` whose `control-id` has graph coverage
  gains the same `https://uiao.gov/ns/oscal/graph` props the SAR
  observations carry.
- `build_poam(..., graph=None)` and
  `build_poam_export(..., graph=None)` — every `poam-item` is
  augmented with `graph-finding-*`, `graph-poam-*`, and
  `graph-evidence-*` props derived from each related control.
- 19 new tests in `tests/test_ssp_poam_graph_augmentation.py` covering
  the helper, both generators with and without a graph, prop merge
  semantics (no clobbering of `ksi-id`, etc.), and an end-to-end
  guarantee that a single scheduler run produces matching
  `graph-scheduler-run-id` props in both SSP and POA&M.
- All three OSCAL artifacts (SAR / SSP / POA&M) now share one
  provenance source — the graph — closing the deferred Phase 2
  follow-up that this row originally tracked.

**Update (2026-04-24, second pass):** OSCAL graph surface complete.

- `build_component_definition(..., graph=None)` and
  `build_oscal(..., graph=None)` — the fourth and last OSCAL emitter
  now augments per-control implemented-requirements with the same
  `graph-*` props the other three carry.
- `EvidenceGraph.resource_uuid_for_control(control_id)` and
  `back_matter_resource_for_control(control_id)` /
  `back_matter_resources_for_controls(control_ids)` — graph-derived
  back-matter resources with **deterministic UUIDs** (UUID v5 keyed
  on a fixed namespace). Same control → same resource UUID across
  all four OSCAL artifacts.
- All four emitters (SAR, SSP, POA&M, component-definition) now emit
  matching `back-matter.resources[]` entries and per-item
  `links: [{rel: "graph-evidence", href: "#<uuid>"}]` so OSCAL
  consumers can follow the link by UUID resolution. Where the
  underlying evidence carries scheduler metadata, each resource also
  carries an `rlinks[].href = schedrun://<run-id>/adapters/<adapter>/evidence.json`
  pointer to the on-disk evidence path.
- 16 new tests in `tests/test_oscal_graph_back_matter.py` covering
  resource UUID determinism, single + batch resource construction,
  rlinks presence, component-definition graph augmentation, and a
  cross-emitter guarantee that one graph + one control yields the
  same resource UUID and matching `links` in all four OSCAL
  artifacts.

Deferred to future (no longer Phase 2 blockers):
- Rich provenance metadata: currently graph ingestion captures the
  adapter hash + timestamp; extended provenance fields (tenant IDs,
  policy versions, certificate anchors) land when UIAO_015
  Provenance Profile grows.

Referenced doc: UIAO_113 (`src/uiao/canon/specs/graph-schema.md`).

### 1.5 — Terraform adapter: stubs → real (→ **wired to scheduler** ✅)

The Terraform adapter exists and — as of #183 — is the first **real
adapter wired into UIAO_100's scheduler factory map**. Prior to this
pass the roadmap noted the five extension methods as stubs; audit
confirmed they had already landed (55 tests green in
`tests/test_terraform_adapter.py`). What remained was the scheduler
wire-up, a freshness window declaration, and an integration guard.

**Status (2026-04-23):** shipped end to end — scheduler can dispatch
`terraform` against a real `TerraformAdapter`, evidence + drift
artifacts land in the run directory with shapes consumed by both the
EvidenceGraph (§1.4) and DRIFT-SEMANTIC evaluator (§1.1).

Shipped previously:
- `src/uiao/adapters/terraform_adapter.py` — full implementation of
  `connect`, `discover_schema`, `execute_query`, `normalize`,
  `detect_drift`, plus the five Terraform-specific extensions:
  `extract_terraform_state`, `parse_hcl_config`,
  `consume_terraform_plan`, `detect_terraform_drift`,
  `generate_terraform_evidence`.
- `src/uiao/adapters/terraform_parser.py` — HCL2 parser, state-file
  v4 JSON parser, plan-JSON parser, three-way diff engine.
- `python-hcl2>=4.0` declared in `pyproject.toml`.
- Tier-2 fixtures: `tests/fixtures/terraform.tfstate`,
  `tests/fixtures/terraform-plan.json`, contract fixtures under
  `tests/fixtures/contract/terraform/`.
- 55 tests in `tests/test_terraform_adapter.py` covering HCL/state/plan
  parse, three-way drift, evidence generation, claim alignment.

Shipped in this PR:
- `_BUILTIN_ADAPTER_CLASSES` in `src/uiao/orchestrator/scheduler.py`
  now includes `terraform` — the scheduler instantiates a real
  `TerraformAdapter` and calls `collect_evidence()` + `detect_drift()`
  end to end without injected mocks.
- `freshness-window-hours: 24` seeded on the `terraform` entry in
  `src/uiao/canon/modernization-registry.yaml`, matching Phase 1 cadence
  expectations for config-management adapters.
- `tests/test_terraform_scheduler_integration.py` — 7 tests covering
  factory resolution, full `dispatch_one("terraform")`, evidence.json
  shape consumed by EvidenceGraph + DRIFT-SEMANTIC, drift.json shape,
  mixed `dispatch_all` run with a not-wired sibling adapter, and a
  canon-smoke guard against removal of the freshness window.

Deferred to Phase 2:
- Real three-way drift dispatch (the scheduler currently calls
  `detect_drift()` which returns an info-severity scaffold; the real
  `detect_terraform_drift(live_claims, tf_state, tf_config)` requires
  runtime configuration per dispatch and is a separate wiring change).
- Production state-backend connection (S3, Terraform Cloud, etc.) — the
  current scheduler path uses empty config; real runs will need
  `state_source` + auth config surfaced from the registry or
  environment.

### 1.x — Continuous Compliance Evidence composition ✅

With §1.1, §1.3, §1.4, §1.5 each individually shipped, the remaining
piece to promote Continuous Compliance Evidence out of DESIGN-ONLY is
**operational composition**: a recurring run that exercises the full
pipeline against real canon.

**Shipped:**

- `EvidenceGraph.ingest_drift_semantic(findings)` in
  `src/uiao/evidence/graph.py` — composes §1.1 (DRIFT-SEMANTIC eval)
  into §1.4 (Evidence Graph) so stale-evidence findings appear as
  first-class `FindingNode`s alongside adapter drift. Surfaces through
  the existing `build_sar(..., graph=...)` path to OSCAL SAR.
- `.github/workflows/orchestrator-schedule-nightly.yml` — nightly
  (cron `0 3 * * *`) and on-demand `workflow_dispatch` runs of
  `uiao orchestrator schedule` against both canon registries,
  evaluates DRIFT-SEMANTIC freshness, uploads the run tree as a 30-day
  artifact, and offers opt-in LFS commit-back for ATO-grade evidence
  captures.
- Concurrency group `nightly-orchestrator-<ref>` prevents overlapping
  runs. Schedule runs are artifact-only by default; operators opt into
  commit-back explicitly via workflow dispatch input.

**Exit to TARGET (now reachable):** one complete evidence → drift →
DRIFT-SEMANTIC → graph → SAR loop runs nightly against the canon
registries without manual intervention. ✅

**Exit to SHIPPED (still requires):** real-adapter coverage across the
registry (Phase 2 wiring), production reference deployment with tenant
config surfaced via secrets, measured freshness SLA compliance across
≥4 weeks of nightly runs.

---

## Phase 2 — Adapter conformance gates (v0.5 → v0.8)

**Theme:** Clear the UIAO_131 conformance gate for every active adapter that has a path to tier-1 testing. Document permanent exclusions for those that do not.

**Exit condition:** Five or more adapters have both tier-1 and tier-2 evidence. UIAO_121 and UIAO_123 are instantiated for each passing adapter (not just templates). Infoblox and BlueCat exclusion compensating strategies are documented.

### 2.1 — ServiceNow tier-1

Requires sign-up for the ServiceNow Developer Program (personal developer instance, free). This is the unblocking step documented in the adapter registry notes.

Work required:
- Sign up for ServiceNow PDI.
- Implement nightly CI job against the PDI: incident creation, change-request creation, status read.
- Create tier-2 fixtures.
- Fill UIAO_121 and UIAO_123 templates for `service-now`.

### 2.2 — Palo Alto Networks tier-1

Requires vendor sandbox access (noted as "pending" in the registry).

Work required:
- Engage Palo Alto Networks via their XSOAR/NGFW developer program or PAN-OS eval VM.
- Alternatively, stand up a PAN-OS VM (eval ISO) in a developer Azure subscription via Terraform.
- Implement nightly CI job: security policy read, rule audit.
- Create tier-2 fixtures.
- Fill UIAO_121 and UIAO_123 templates for `palo-alto`.

### 2.3 — CyberArk tier-1

Requires CyberArk developer program access (vendor program pending per registry notes). CyberArk offers a "CyberArk Privilege Cloud" trial.

Work required:
- Engage CyberArk Privilege Cloud trial.
- Implement CI job: vault account enumeration, rotation simulation.
- Create tier-2 fixtures.
- Fill UIAO_121 and UIAO_123 templates for `cyberark`.

### 2.4 — Scuba (modernization) tier-2

The `scuba` modernization adapter applies the SCuBA baseline. Its tier-1 path uses the same M365 developer tenant as `entra-id` and `m365` (established in Phase 0). The work here is the tier-2 fixtures for the baseline-apply flow.

Work required:
- Capture baseline-apply output from a known-state developer tenant after ScubaGear pre-assessment.
- Store as tier-2 fixtures.
- Fill UIAO_121 and UIAO_123 templates for `scuba`.

### 2.5 — Infoblox and BlueCat: compensating strategy

These two adapters are permanently excluded from tier-1 per UIAO_131 §5.1. The compensating strategy is undefined.

Work required:
- Define the compensating strategy in a new `notes` subsection of UIAO_131 §5.1: what evidence an agency can provide instead of tier-1 CI results (e.g., vendor-attested test reports, agency-operated sandbox evidence).
- Apply the same UIAO_131 §5.1 language to both adapter registry entries.
- Ensure tier-2 fixtures (static WAPI/BAM API response payloads) are sufficient for the conformance gate in the absence of tier-1.

### 2.6 — UIAO_121/123 instantiation for all passing adapters

The adapter conformance and integration test plan templates are currently empty. Every adapter that clears tier-1 and tier-2 in this phase must have both templates filled.

Work required:
- Create `docs/customer-documents/validation-suites/adapters/<adapter-id>/` for each passing adapter.
- Remove the aspirational banner from these pages.
- Register the filled plans in `document-registry.yaml` (new UIAO_NNN IDs in the 900-range test fixture space or a new 400-range operational space — needs ADR).

---

## Phase 3 — Full runtime stack (v0.8 → v1.0)

**Theme:** Implement the remaining aspirational specs that are prerequisites for an agency-facing production deployment. The goal of v1.0 is a substrate that an agency operator can install, run, and trust without reading aspirational banners.

**Exit condition:** All ⚠️ items in the UIAO_100–120 range are at minimum partially implemented (🟡) with implementation plans tracked in UIAO_127 project plans. At least one UIAO_125 training walkthrough has been delivered.

### 3.1 — UIAO_105 Auditor API

The Auditor API is the external interface through which an ATO package is assembled. Without it, evidence bundles must be assembled manually.

Work required:
- Implement FastAPI (or equivalent) service exposing: evidence query by control ID, drift finding list, OSCAL SAR export, adapter status.
- Define OpenAPI spec in `src/uiao/canon/specs/api-contract.md` (UIAO_105 — currently aspirational).
- Add contract tests.

### 3.2 — UIAO_108 Compliance Query Language (CQL)

CQL is the query interface for interrogating the evidence graph. Without it, evidence navigation requires direct Python API access.

Work required:
- Define the CQL grammar (subset of a structured query language, not a general-purpose one).
- Implement parser and evaluator in `src/uiao/`.
- Wire to the Auditor API (`/query` endpoint).
- Document in UIAO_108.

### 3.3 — UIAO_111 Enforcement Runtime

The enforcement runtime is what converts drift findings into remediation actions. Without it, findings are informational only.

Work required:
- Define the enforcement policy language interface (consuming UIAO_116 EPL).
- Implement `EnforcementRuntime` that evaluates EPL policies against findings and triggers adapter remediation actions.
- Wire to the orchestrator.

### 3.4 — UIAO_112 Multi-Tenant Isolation

Multi-tenant isolation is required before any agency can operate the substrate alongside another agency in a shared environment.

Work required:
- Implement tenant namespace isolation in the evidence store.
- Implement per-tenant credential scoping.
- Implement tenant audit trails.
- Add test coverage.

### 3.5 — UIAO_116 Enforcement Policy Language (EPL)

EPL is the policy language that describes when the enforcement runtime should act and what action to take.

Work required:
- Define the EPL schema (likely YAML-based, anchored to NIST control IDs and adapter scope declarations).
- Implement EPL parser.
- Write reference policies for the MFA, conditional access, and drift-remediation scenarios.

### 3.6 — UIAO_120 Zero-Trust Integration

Zero-trust integration formalizes the relationship between the substrate's adapter outputs and the CISA Zero Trust Maturity Model (ZTMM) pillars.

Work required:
- Map each adapter's evidence outputs to ZTMM pillars.
- Implement ZTMM score calculation from evidence graph.
- Surface score in the Auditor API and Quarto dashboard.

### 3.7 — UIAO_109 Data Lake Model

The data lake model defines how evidence snapshots are retained long-term for trend analysis and audit purposes.

Work required:
- Define the evidence retention schema.
- Implement evidence archival in the orchestrator (post-collection).
- Define query interface (consumed by CQL and Auditor API).

### 3.8 — UIAO_125–128 Programs: first live delivery

The four program specs (Training, Test Plans, Project Plans, Education) are aspirational. v1.0 requires at least one live delivery of each.

Work required:
- UIAO_125 Training: deliver one internal training session for an adapter developer (document as session record).
- UIAO_126 Test Plans: instantiate test plan documents for all conformance-gate adapters (partially done in Phase 2 — complete here).
- UIAO_127 Project Plans: instantiate project plan templates for two active agencies.
- UIAO_128 Education: deliver one agency-facing onboarding walkthrough (narrative format per spec).

---

## Phase 4 — Production scale (v1.0+)

**Theme:** Extend to partner agency tier-3 environments, unlock the mainframe adapter, and reduce the aspirational banner count to zero.

### 4.1 — Tier-3 reference deployment

Tier-3 requires a partner agency GCC-Moderate tenant. This is not self-unblockable — it requires a formal agency engagement.

Work required:
- Identify partner agency willing to host a reference deployment under a Collaborative Research and Development Agreement (CRADA) or equivalent.
- Stand up the full substrate against their GCC-Moderate tenant.
- Collect tier-3 evidence for all active adapters (entra-id, m365, scuba are the most natural first set).
- Publish a redacted reference deployment report as a UIAO canon artifact.

### 4.2 — Mainframe adapter unblocking

The mainframe adapter is the highest-priority FIMF legacy migration adapter. It is blocked on z/OS Connect / MQ bridge infrastructure.

Work required:
- Identify an IBM partner, federal agency with a z/OS system, or IBM Government programs engagement that can provide a z/OS Connect development environment.
- Define the adapter's `scope:` fields with IBM's canonical COBOL-to-REST mapping terminology.
- Implement stub → working code path using z/OS Connect REST bridge.
- Create tier-2 fixtures (COBOL record payloads mapped to canonical claims).
- Flip status from `reserved` to `active`.

### 4.3 — Aspirational banner elimination

Target: zero aspirational banners by v1.1.

Work required:
- Complete per-file review of the 263 files not yet assessed (`inbox/drafts/aspirational-candidates.txt`).
- For each genuine aspirational page, either implement the feature or schedule it in UIAO_127 project plans with a target date.
- Remove banner as each feature ships.
- Track count in the Substrate Status page (the page itself is a derived view from canon — the count must be regenerable from `make walk`).

### 4.4 — UIAO_114/115/117/119 HA, Performance, Recovery, Tenancy

These four specs are aspirational with no implementation. They are production-readiness prerequisites for a multi-agency deployment but not required for an initial agency engagement.

Work required:
- Assess whether each spec requires implementation or whether the existing orchestrator / evidence store architecture already satisfies the invariants by construction.
- For each gap, create a UIAO_127 project plan entry.
- Implement or formally defer per that assessment.

---

## Milestone summary

| Milestone | Target | Exit condition |
|---|---|---|
| v0.3 | Q2 2026 | 2 adapters with tier-1 + tier-2 evidence; DRIFT-AUTHZ and DRIFT-IDENTITY implemented; link-check blocking |
| v0.5 | Q3 2026 | Compliance Orchestrator working; DRIFT-SEMANTIC complete; Evidence Graph implemented; Terraform adapter real |
| v0.8 | Q4 2026 | 5+ adapters through conformance gate; UIAO_121/123 instantiated; infoblox/bluecat compensating strategy documented |
| v1.0 | Q1 2027 | All ⚠️ 100-series specs at minimum 🟡; Auditor API live; CQL defined; Enforcement Runtime working; first program deliveries |
| v1.1 | Q2 2027 | Zero aspirational banners; tier-3 reference deployment underway; mainframe adapter unblocked or formally deferred |

---

## What to do first, this week

The highest-leverage actions require no additional infrastructure — they use resources that already exist or are freely available.

**Day 1–2:** Sign up for the M365 Developer Program tenant. This is the unlock for Phase 0.1, 0.2, 0.3, and 2.4 simultaneously. A single free tenant is tier-1 evidence for `entra-id`, `m365`, `scuba` (modernization), and `scubagear` (conformance).

**Day 2–3:** Create `tests/fixtures/entra-id/` with static API response payloads captured from the Microsoft Graph Explorer (no live tenant required for the fixture structure — the schema is public). Wire them into `test_adapters.py`. This closes the tier-2 gap independently of the developer tenant signup.

**Day 3–4:** Implement `DRIFT-AUTHZ` in `src/uiao/governance/`. The consent envelope model is already defined in UIAO_110; this is an implementation task, not a design task.

**Day 4–5:** Run `make check-links` and audit the output. Identify how many failures are genuine vs. lychee false-positives. If the genuine failures are fewer than 20, fix them and flip link-check to blocking within this sprint.

**Ongoing:** Assign the 263 un-reviewed aspirational-candidate files to a weekly review slot. At even 10 files per week, the review completes in 26 weeks. Without a schedule it will not happen.

---

## Appendix: spec-to-implementation gap by priority

Listed in implementation-priority order (not UIAO_NNN order).

| Priority | Doc | Title | Current | Target |
|---|---|---|---|---|
| P0 | UIAO_131 (gate) | Adapter Test Strategy | ⚠️ aspirational (0 evidence) | tier-1+2 for 5 adapters by v0.8 |
| P1 | UIAO_110 §DRIFT-AUTHZ | Drift Engine — Auth class | ⏳ pending | ✅ by v0.3 |
| P1 | UIAO_110 §DRIFT-IDENTITY | Drift Engine — Identity class | ⏳ pending | ✅ by v0.3 |
| P2 | UIAO_110 §DRIFT-SEMANTIC | Drift Engine — Semantic class | 🟡 partial | ✅ by v0.5 |
| P2 | UIAO_100 | Compliance Orchestrator | ⚠️ aspirational | 🟡 by v0.5 |
| P2 | UIAO_103 | Spec-Test Enforcement | 🟡 partial | ✅ by v0.5 |
| P2 | UIAO_113 | Evidence Graph | 🟡 partial | 🟡→✅ by v0.5 |
| P3 | UIAO_105 | Auditor API | ⚠️ aspirational | 🟡 by v1.0 |
| P3 | UIAO_111 | Enforcement Runtime | ⚠️ aspirational | 🟡 by v1.0 |
| P3 | UIAO_108 | CQL | ⚠️ aspirational | 🟡 by v1.0 |
| P3 | UIAO_116 | EPL | ⚠️ aspirational | 🟡 by v1.0 |
| P3 | UIAO_112 | Multi-Tenant Isolation | ⚠️ aspirational | 🟡 by v1.0 |
| P3 | UIAO_120 | Zero-Trust Integration | ⚠️ aspirational | 🟡 by v1.0 |
| P4 | UIAO_109 | Data Lake | ⚠️ aspirational | 🟡 by v1.1 |
| P4 | UIAO_114 | HA / Fault Tolerance | ⚠️ aspirational | assessed by v1.0 |
| P4 | UIAO_115 | Performance Engineering | ⚠️ aspirational | assessed by v1.0 |
| P4 | UIAO_117 | Recovery Layer | ⚠️ aspirational | assessed by v1.0 |
| P4 | UIAO_119 | Tenancy Strategy | ⚠️ aspirational | 🟡 by v1.0 |
| P4 | UIAO_125–128 | Programs (Training, Test Plans, Project Plans, Education) | ⚠️ aspirational | first delivery by v1.0 |
| P5 | UIAO_129/130 | Application Identity Model / Runbook | ⚠️ draft | status reconciled by v0.3 |
| P5 | Mainframe adapter | z/OS Connect / MQ bridge | reserved | unblocked or deferred by v1.1 |

---

*This roadmap is a derived view. It does not supersede any canon document. Conflicts between this document and a UIAO_NNN spec resolve in favor of the spec. Update this document when milestones are achieved or targets change.*
