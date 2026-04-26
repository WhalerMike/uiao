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
| DRIFT-IDENTITY | P1 | ✅ Implemented (state-diff + runtime issuer-chain) |

DRIFT-AUTHZ ships both the state-diff and consent-envelope detectors. DRIFT-IDENTITY now ships both the state-diff classifier and the runtime issuer-chain validator. All five drift classes are implemented.

### CI gate health

| Workflow | Status |
|---|---|
| schema-validation.yml | ✅ Blocking |
| pytest.yml | ✅ Blocking |
| substrate-drift.yml | ✅ Blocking |
| metadata-validator.yml | ✅ Blocking |
| quarto.yml | ✅ Blocking |
| ruff.yml | ✅ Blocking |
| link-check.yml | ✅ Blocking |

---

## Risk register

These are the conditions that could block progress or invalidate existing canon if left unaddressed.

**R1 — Test-tier vacuum (Critical).** All nine active adapters are registered as `active` but have zero test evidence. Per UIAO_131, `active` status implies conformance-gate passage. It does not. This is documented drift in the registry itself. If the registry is presented to an agency evaluator before tier-1 fixtures exist, the gap becomes a credibility issue.

**R2 — P1 drift classes unimplemented (resolved).** As of §0.4 + §0.5, DRIFT-AUTHZ and DRIFT-IDENTITY both ship state-diff and runtime detectors. All five drift classes (DRIFT-SCHEMA, DRIFT-PROVENANCE, DRIFT-SEMANTIC, DRIFT-AUTHZ, DRIFT-IDENTITY) are implemented; substrate walker registry-hygiene gates flag adapters missing the canon declarations (`scope:`, `trust-anchor:`) needed for runtime validation.

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

### 0.5 — DRIFT-IDENTITY implementation (pending → **complete** ✅)

DRIFT-IDENTITY detects issuer-resolution failures: when a certificate or
identity claim cannot be traced to the expected trust anchor. P1 severity.

**Status (2026-04-25):** shipped end to end. Two complementary detectors
now produce `drift_class="DRIFT-IDENTITY"` findings:

1. **State-diff detector** (`uiao.governance.drift.classify_identity_drift`,
   shipped previously): catches OrgPath / lifecycle / required-field
   inconsistencies between expected and actual snapshots.

2. **Runtime issuer-chain detector**
   (`uiao.governance.issuer_resolution`, new this PR): catches
   adapter-surfaced certificate chains whose terminal issuer doesn't
   match the declared trust anchor (subject DN or SHA-256 fingerprint),
   plus chains that don't link cleanly leaf-to-root.

Shipped:
- `src/uiao/governance/issuer_resolution.py` — `IssuerResolver` with
  `load_trust_anchors(registries)` (merges declared anchors across
  modernization-registry + adapter-registry; later overrides earlier),
  `validate(adapter_id, observed_chain)` → `IssuerChainReport`, and
  `report.as_drift_state(provenance=...)` →
  `DriftState(drift_class="DRIFT-IDENTITY", classification="unauthorized")`
  with a delta listing the offending chain link or anchor mismatch.
- `TrustAnchor` dataclass — accepts subject DN, SHA-256 fingerprint,
  or both; fingerprint preferred under cross-signing.
- `CertificateLink` dataclass — one chain link with subject / issuer /
  optional fingerprint. Resolver coerces input dicts.
- `observed_chain_for_run(run_dir)` — extracts per-adapter chains from
  scheduler-run `evidence.json::normalized_data.certificate_chain`
  (with `issuer_chain` and `raw_data` fallbacks).
- `src/uiao/substrate/walker.py::_scan_issuer_chain` — registry-hygiene
  gate. Every active adapter declaring `certificate-anchored: true`
  MUST also declare a `trust-anchor:`; missing → **P1** finding
  (substrate trust contract; runtime issuer-chain cannot be enforced).
  Reserved and `certificate-anchored: false` adapters skipped.

  **Update (post-§0.5 follow-through):** All 16 active certificate-
  anchored adapters across both registries now carry a `trust-anchor:`
  declaration with the expected vendor root (Microsoft RSA Root CA
  2017 for the Entra/M365 family, DigiCert Global Root CA/G2 for
  CISA / SaaS vendors, ISRG Root X1 for Terraform). Operators replace
  the subject form with a SHA-256 fingerprint when wiring to a real
  tenant. The walker gate was promoted **P2 → P1** in the same pass,
  so the substrate now blocks any future PR that lands an active
  certificate-anchored adapter without an anchor.
- 31 new tests in `tests/test_issuer_resolution.py`: registry loader
  (7), resolver semantics (12 — clean chain to subject anchor / clean
  to fingerprint anchor / unanchored chain / broken chain / missing
  declaration / empty chain / batch / DriftState emission for each
  violation kind), scheduler-run extraction (4 including end-to-end
  scheduler-run → resolver → DriftState), CertificateLink coercion (2),
  substrate-walker scan (5 — P2 missing anchor, clean active adapter,
  certificate-anchored=false skipped, reserved skipped, plus a smoke
  test against live canon asserting zero P1 findings).

Trust-anchor declaration shape (canon convention introduced by this
implementation):

```yaml
- id: entra-id
  certificate-anchored: true
  trust-anchor:
    subject: "CN=Microsoft Identity Verification Root Certificate Authority 2020"
    fingerprint_sha256: "8a4ca3...b9"
```

Adapters without a declared anchor today land as P2 walker findings;
follow-up PRs declare anchors per adapter and promote the gate to P1.

Referenced docs: UIAO_110 §3 (drift class taxonomy), ADR-012 §DT-05.

### 0.6 — link-check baseline burn-down (soft-fail → **blocking** ✅)

The link-check workflow has been flipped from soft-fail to blocking.
Baseline confirmed clean: lychee 0.24.1 against every `.md` and `.qmd`
in the repo with the existing `.lycheeignore` returns 0 errors / 287
OK / 14 redirects / 661 excluded across 572 unique URLs (as of
2026-04-25). The exclude list (Microsoft Learn, FedRAMP PMO,
archive.org, Cisco, retired pre-split monorepo URLs, etc.) is the
result of prior author work distinguishing real link rot from
CI-side false positives — geo-gated cloud responses, dynamic GH
issue/PR paths, vendor URL restructurings without redirects.

Shipped:
- `.github/workflows/link-check.yml`: removed
  `continue-on-error: true`. Workflow now blocks the PR on any
  lychee error. The `--exclude-file .lycheeignore` flag was also
  removed (deprecated in lychee 0.20+; the file is read automatically
  from the repo root).
- Roadmap CI gate-health table updated: `link-check.yml` flips from
  🟡 soft-fail to ✅ blocking.
- Substrate-status CI table updated with the same flip.

Maintenance contract going forward:
- A new genuinely broken link → fix the URL in the same PR.
- A new CI-side false positive (cloud-IP geo-gate, intermittent
  upstream rate-limit, etc.) → add an explanatory entry to
  `.lycheeignore` in the same PR.
- Weekly cron run still detects upstream link rot independent of
  repo changes.

### 0.7 — UIAO_129/130 Application Identity Model (metadata contradiction → **resolved** ✅)

Reconciliation at canon: as of the 2026-04-25 sweep, both specs declare
`status: Current` in their frontmatter (`src/uiao/canon/specs/
application-identity-model.md` line 5 + `application-identity-onboarding-
runbook.md` line 5) **and** in `src/uiao/canon/document-registry.yaml`
(UIAO_129 line 189, UIAO_130 line 194). The metadata contradiction the
roadmap originally tracked no longer exists; both files agree the specs
are Current canon.

What was stale in the derived view: `docs/docs/substrate-status.qmd`
rendered the document-registry table with "draft" / "⚠️ draft only"
on the UIAO_129/130 rows. That row has been updated to "🟡 spec, no
impl" — accurate reality: the specs are Current canon but no
implementation exists yet for the application-identity onboarding
flow against CyberArk and Entra adapters.

Deferred follow-ups (not blocking §0.7 closure):
- Implement the canonical object-identity format for application
  service principals (UIAO_129 §canonical-id-format) — gated on
  Phase 0.1/0.2 entra-id tier-1 evidence.
- Wire the onboarding runbook (UIAO_130) into a `uiao app onboard`
  CLI command — gated on §3.1 Auditor API.
- Tighten spec prose to RFC 2119 keywords so §1.2 spec-test enforcement
  picks up coverage as the implementation lands.

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

### 3.1 — UIAO_105 Auditor API (aspirational → **🟡 working** ✅)

The Auditor API is the external interface through which an ATO package
is assembled and the four governance modules shipped in Phase 3 are
exercised. Pre-existing routers (`src/uiao/api/routes/auditor.py`)
already covered `evidence` / `findings` / `POA&M` / OSCAL / graph endpoints; this pass adds
the four §3.x governance surfaces plus Bearer-auth wiring.

Shipped (this PR):
- `src/uiao/api/routes/_auth.py` — shared Bearer-token dependency
  (`require_auditor`); JWT signature validation deferred to the
  existing `uiao.api.auth.entra_token` module in production.
- `src/uiao/api/routes/ztmm.py` — `GET /api/v1/ztmm` returns the full
  5-pillar `ZTMMReport`; `GET /api/v1/ztmm/{pillar}` returns one
  pillar's score (with synonym parsing — `endpoints` → `devices`,
  `apps` → `applications-and-workloads`, etc.).
- `src/uiao/api/routes/epl.py` — `GET /api/v1/epl/policies` lists
  canonical policies; `GET /api/v1/epl/policies/{id}` fetches one;
  `POST /api/v1/epl/evaluate` runs an `EPLContext` through the
  evaluator and returns matched policies (no dispatch).
- `src/uiao/api/routes/enforcement.py` — `GET /api/v1/enforcement/
  journal` lists journal entries with `policy_id` / `target` /
  `limit` filters; `POST /api/v1/enforcement/dispatch` actually runs
  the runtime against a context and appends to the on-disk journal
  (path from `UIAO_ENFORCEMENT_JOURNAL_PATH`, default
  `output/enforcement/journal.jsonl`).
- `src/uiao/api/routes/archive.py` — `GET /api/v1/archive` lists
  Data Lake entries with `adapter_id` / `run_id` / `evidence_class`
  filters; `GET /api/v1/archive/{run_id}/{adapter_id}` fetches a
  single entry. Reads from `UIAO_ARCHIVE_ROOT` (default
  `output/archive`).
- All four routers wired into `src/uiao/api/app.py` under their
  v1 prefixes alongside the existing `/api/auditor`, `/api/v1/survey`,
  `/api/v1/orgpath` surfaces. Tags surface in the auto-generated
  OpenAPI doc at `/api/openapi.json`.
- 21 new tests in `tests/test_auditor_api_v1.py` using FastAPI's
  `TestClient`: auth (3 — no/empty/dev token), ZTMM (4 — full report,
  single pillar, synonym, 404), EPL (5 — list/get/404/evaluate-match/
  evaluate-no-match), Enforcement (4 — journal empty/with records/
  filtered, dispatch round-trip), Archive (5 — empty/list/filter/
  single/404). Tests run an isolated minimal app so they don't pull
  in the larger Windows-hosted MSAL/Kerberos auth surface.

Deferred:
- Per-tenant scoping (gated on §3.4 Multi-Tenant Isolation).
- Stricter RBAC on the dispatch / write endpoints (today reuses the
  shared Bearer dependency; production deployments bind a stronger
  role check via `uiao.api.auth.entra_token`).
- OpenAPI spec freeze in `src/uiao/canon/specs/api-contract.md` —
  v1 surface is now stable enough to author the canon doc; deferred
  follow-up.

Referenced doc: UIAO_105 Auditor API spec.

### 3.2 — UIAO_108 Compliance Query Language (CQL) (aspirational → **🟡 working** ✅)

CQL is the substrate's read-only query surface over its evidence
sources: the EvidenceGraph (UIAO_113), the EnforcementJournal
(UIAO_111), the Data Lake archive (UIAO_109), and the canon adapter
registries (UIAO_003 / UIAO_131). Sized as a subset of a structured
query language — not full SQL — so the implementation stays small,
deterministic, and dependency-free.

Shipped:
- `src/uiao/governance/cql.py` — `CQLPredicate` + `CQLQuery` data
  model, `parse_query(body)` accepts dicts or YAML strings, eight
  operators (`eq` / `ne` / `in` / `not_in` / `contains` / `gte` /
  `lte` / `exists`), four sources (`findings` / `enforcement` /
  `archive` / `adapters`), `order_by` + `order` + `limit` support.
- `CQLEvaluator(resolver)` runs a parsed query against a
  source-resolution callable. Resolver helpers ship for each source:
  `graph_findings_resolver(graph)` projects `FindingNode`s,
  `journal_records_resolver(records)` and `archive_entries_resolver`
  flatten dataclass records via `as_dict`, `adapters_resolver(...)`
  flattens canon adapter dicts.
- 5 reference queries in `src/uiao/canon/queries/`:
  - `open-drift-authz-findings` — DRIFT-AUTHZ + status=Open, sorted
    by severity desc, top 25
  - `recent-blocks` — enforcement journal, action=block, top 50
  - `high-severity-findings` — severity ∈ {High,P1,P2,Critical}
  - `archive-recent` — most-recently-archived runs
  - `active-modernization-adapters` — active phase-1 adapters
- `src/uiao/api/routes/cql.py` — Auditor API endpoints
  (UIAO_105 §3.1 plug-in): `GET /api/v1/cql/queries` lists canonicals,
  `GET /api/v1/cql/queries/{name}` fetches one,
  `POST /api/v1/cql/evaluate` runs an ad-hoc query body, and
  `POST /api/v1/cql/evaluate/{name}` runs a canonical query against
  the live substrate state (enforcement journal + archive backend +
  canon adapter registries).
- 42 new tests in `tests/test_cql.py`: parser (12 — minimal /
  YAML-string / select / operators / unknown source / unknown op /
  invalid order / negative limit / invalid YAML / non-mapping),
  predicate matchers (6), evaluator (8), source resolvers (5), the
  canonical-queries smoke (4), and FastAPI router (8 — list / get /
  unknown / ad-hoc evaluate / named evaluate / invalid body 400 /
  unknown name 404 / no-auth 401).

Deferred:
- EvidenceGraph snapshot persistence (today the graph is request-
  scoped; a future PR drops a snapshot to disk per scheduler run so
  CQL `findings` queries hit live graph state from the API).
- Time-window filters (e.g. "blocks in the last 24h") — current
  implementation supports `gte`/`lte` on string fields, so callers
  can filter by ISO timestamps; a sugar layer for relative time
  expressions is a follow-up.
- CLI surface (`uiao cql evaluate ...`) — gated on §3.1 CLI parity
  follow-up.

Referenced doc: UIAO_108 CQL spec.

### 3.3 — UIAO_111 Enforcement Runtime (aspirational → **🟡 working** ✅)

The enforcement runtime converts EPL matches into dispatched actions
with structured side-effects + an append-only audit trail. It's the
moving part between the drift detectors / OSCAL emitters (which produce
findings) and the EPL (which says what to do). v1.0 of the runtime +
five default handlers + persistent journal ships in this pass; live
adapter remediation wiring stays separate (a per-adapter dispatcher
landing in the same PR that wires each adapter's actual remediation
API).

Mirrors the §3.5 / §3.6 / §3.7 governance modules: pluggable
abstraction (`EnforcementHandler`), concrete defaults, structured
records, on-disk journaling.

Shipped:
- `src/uiao/governance/enforcement.py` — `EnforcementAction`
  dataclass (one record per dispatched action), abstract
  `EnforcementHandler`, five default handlers (`LoggingHandler`,
  `AlertHandler`, `EscalateHandler`, `BlockHandler`, `RemediateHandler`),
  `EnforcementJournal` (append-only JSONL on disk; read-back included),
  `EnforcementRuntime` (composes EPLEvaluator + handlers + journal,
  exposes `dispatch_context` / `dispatch_finding` / `dispatch_drift_state`
  / `dispatch_matches`).
- Default handlers stay testable: log/alert/escalate produce
  structured intent records; block appends to an in-memory deny-list
  (production swaps in the UIAO_100 scheduler's "skip these adapters"
  set); remediate calls a registered per-adapter callable and records
  success/failure/exception. Production deployments swap real
  backends in.
- Target resolution: defaults to `ctx.adapter_id` when set, else first
  control id, else `"unknown"`. Surfaced in the journal so reviewers
  can correlate.
- 25 new tests in `tests/test_enforcement.py`: each handler (8 —
  log/alert/escalate/block dedupe + remediate skipped/dispatched/
  failure/exception), journal in-memory + disk persistence + read
  round-trip + corrupt-line skip (4), runtime context dispatch /
  finding round-trip / drift-state round-trip / journal recording /
  unknown-handler skip / target fallbacks (10), plus integration
  tests against the canonical EPL policies (3 — DRIFT-AUTHZ →
  block, DRIFT-SEMANTIC High → enforce-mfa + escalate-stale-evidence,
  journal persists across runtime recreation).

Deferred (gated on real adapter remediation surfaces):
- Per-adapter `RemediateHandler` wiring — each adapter author
  registers a callable in their PR that lands the adapter remediation
  API.
- Auditor API endpoint (`POST /v1/enforcement/dispatch` /
  `GET /v1/enforcement/journal`) — gated on §3.1.
- Quarto dashboard "actions taken in last 24h" tile.

Referenced doc: UIAO_111 Enforcement Runtime spec.

### 3.4 — UIAO_112 Multi-Tenant Isolation (aspirational → **🟡 working** ✅)

Multi-tenant isolation is required before any agency can operate the
substrate alongside another agency in a shared environment. v1 ships
the data model + namespace primitives + walker hygiene gate; per-tenant
credential delegation against a real backend (Vault / Key Vault /
SecretsManager) is a follow-up gated on the deployment target.

Shipped:
- `src/uiao/governance/tenancy.py` — `Tenant` (id / name /
  credential_scope / parent_org / retention_years / boundary / status)
  + `TenantContext` (runtime context; `tenant_id` + `actor`) +
  `TenantRegistry` (loader + `require()` + `active()`).
- `load_tenants(paths)` reads `tenants:` from one or more YAMLs (later
  override earlier; missing files silently skipped — single-tenant
  deployments don't require a canon file).
- `TenantContext.default()` synthesizes the default tenant for
  single-tenant deployments. `TenantRegistry.require(DEFAULT_TENANT_ID)`
  produces a synthetic active tenant when no canon declaration exists,
  so the runtime never falls into "no tenant".
- `tenant_scoped_path(base, ctx)` returns `base/<tenant_id>/...` so
  the EnforcementJournal, Data Lake archive, and scheduler-run output
  land under per-tenant subtrees. Single-tenant deployments use
  `base/default/` so adding a second tenant later requires no path
  migration.
- `assert_tenant_match(expected, actual)` raises `PermissionError` on
  cross-tenant access; called by per-resource read paths to enforce
  the substrate isolation contract.
- `src/uiao/substrate/walker.py::_scan_tenants` — registry-hygiene
  scan on `src/uiao/canon/tenants.yaml`. Active tenants must declare
  a non-empty `credential_scope:` (P2 finding tagged `DRIFT-SCHEMA`
  if missing or empty). The file is optional — single-tenant
  deployments without a tenants.yaml produce zero findings.
- 24 new tests in `tests/test_tenancy.py`: model (3), context (2),
  registry loader (6 incl. invalid YAML, missing id, retention
  fallback), registry semantics (3), path helpers (3), tenant-match
  assertion (3), substrate-walker scan (4 incl. live-canon tolerant
  no-file behavior).

Deferred:
- Per-tenant credential backend binding — `credential_scope` field
  ships today; the actual Vault / Key Vault / SecretsManager dispatch
  layer lands in a deployment-target-specific PR.
- Wiring `tenant_scoped_path` into the existing journal / archive /
  scheduler call sites — they currently default to single-tenant
  (the default tenant subdirectory). Migration to explicit per-tenant
  paths happens once a real second tenant lands.
- Auditor API tenant-aware request handlers — depends on the
  authentication backend producing a tenant claim in the JWT.

Referenced doc: UIAO_112 Multi-Tenant Isolation spec.

### 3.5 — UIAO_116 Enforcement Policy Language (EPL) (aspirational → **🟡 working** ✅)

EPL is the policy language the substrate's Enforcement Runtime
(UIAO_111, §3.3) consumes to decide what to do when a DriftState or
finding lands. v1.0 of the language + parser + evaluator + reference
policies + OSCAL surfacing ships in this pass; the Enforcement Runtime
itself remains separate and gated on §3.3.

Shipped:
- `src/uiao/governance/epl.py` — `EPLAction` (log/alert/remediate/block/
  escalate), `EPLTrigger` (drift_class / controls / adapter_ids / pillars
  / severity_min), `EPLPolicy` dataclass, `EPLContext` builder helpers
  (`from_drift_state` / `from_finding`), `EPLEvaluator.evaluate(ctx)`
  returning id-sorted `EPLMatch` list. Severity comparisons span both
  the Finding vocabulary (Low/Medium/High) and the drift-engine
  vocabulary (P5..P1) plus the state-diff classification vocabulary
  (benign/risky/unauthorized) on a single ordinal scale.
- `load_policies(paths)` + `load_canonical_policies()` — YAML loader
  accepting both flat-per-file and `policies:` list shapes; later
  registries override earlier by id.
- `back_matter_resources_for_policies(policies)` — emits OSCAL
  back-matter resources with deterministic UUID v5 keyed on policy id,
  props under `https://uiao.gov/ns/oscal/epl`. Same pattern as the
  §1.4 / §3.6 back-matter resources; OSCAL consumers can navigate from
  a finding to a policy by UUID.
- 5 reference policies in `src/uiao/canon/policies/`:
  - `epl:enforce-mfa` — DRIFT-SEMANTIC, IA-2 family, ≥Medium →
    remediate (compliance-orchestrator), 24h SLA.
  - `epl:block-out-of-scope` — DRIFT-AUTHZ → block (substrate-walker),
    immediate.
  - `epl:escalate-stale-evidence` — DRIFT-SEMANTIC, ≥High →
    escalate (security-operations-center), 4h.
  - `epl:fix-broken-issuer-chain` — DRIFT-IDENTITY, ≥High →
    remediate (compliance-orchestrator), 8h.
  - `epl:audit-schema-drift` — DRIFT-SCHEMA, ≥Medium → alert
    (substrate-walker), 24h.
- `src/uiao/canon/policies/README.md` — policy authoring guide
  documenting the schema and the `epl:<verb>-<subject>` id convention.
- 29 new tests in `tests/test_epl.py`: vocabulary parsing, loader
  (single + list + dedupe + invalid YAML + missing id + unknown action
  fallback), evaluator (wildcard / drift_class / controls intersection
  / severity_min / adapter / pillar / multi-match id-sort), context
  builders, OSCAL projection, and a canonical-policies smoke that
  asserts every reference policy parses, fires under realistic
  finding contexts, and carries actor + sla_hours.

Deferred (gated on §3.3 Enforcement Runtime):
- The runtime itself — the consumer of `EPLEvaluator.evaluate()` that
  actually dispatches actions to adapters. That's where `remediate` →
  call adapter remediation API, `block` → freeze the scheduler dispatch,
  `escalate` → page the SOC.
- Auditor API endpoint (`POST /v1/epl/evaluate`) — gated on §3.1.
- Quarto dashboard policy tile — derived view of the reference set.

Referenced doc: UIAO_116 EPL spec.

### 3.6 — UIAO_120 Zero-Trust Integration (aspirational → **🟡 working** ✅)

Zero-trust integration formalizes the relationship between the substrate's
adapter outputs and the CISA Zero Trust Maturity Model (ZTMM) v2.0 pillars.

**Status (2026-04-25):** core scoring ships. Substrate-status dashboard
surface deferred to a follow-up doc PR.

Shipped:
- `src/uiao/governance/ztmm.py` — `ZTMMPillar` (5 pillars: Identity,
  Devices, Networks, Applications-and-Workloads, Data) + `ZTMMMaturity`
  (4 stages: Traditional, Initial, Advanced, Optimal).
- `AdapterZTMMDeclaration` dataclass; `load_ztmm_declarations(registries)`
  reads `ztmm-pillars: [...]` from canon (later overrides earlier; bare
  list accepted; synonyms like `apps` / `endpoints` normalize cleanly).
- `ZTMMScoreCalculator.score(graph=None)` — projects declarations
  + EvidenceGraph state into a `ZTMMReport` with per-pillar
  `ZTMMPillarScore` (declared / evidenced / fresh adapter lists +
  computed maturity). Rubric: TRADITIONAL with no declarations,
  INITIAL with ≥1, ADVANCED with ≥2 declared + ≥1 evidenced,
  OPTIMAL with ≥3 declared + all fresh.
- `back_matter_resources_for_report(report)` — emits 5 OSCAL back-matter
  resources (one per pillar, deterministic UUID v5 keyed on pillar id)
  with props under `https://uiao.gov/ns/oscal/ztmm` namespace. Same
  pattern as the §1.4 evidence-graph back-matter resources; OSCAL
  consumers can navigate from a control implementation to a pillar
  score by UUID.
- `ztmm-pillars:` declared on every active adapter (16 across both
  registries):
  - **Identity** — entra-id, m365, active-directory, entra-dynamic-groups,
    entra-admin-units, entra-device-orgpath, entra-policy-targeting,
    orgtree-drift-engine, scuba, scubagear, cyberark
  - **Devices** — entra-id, active-directory, entra-device-orgpath
  - **Networks** — palo-alto, infoblox, bluecat-address-manager, terraform
  - **Applications & Workloads** — entra-id, m365, scuba, scubagear,
    service-now, palo-alto, cyberark, entra-policy-targeting, terraform
  - **Data** — m365, scuba, scubagear
- Schema: `ztmm-pillars` field added to
  `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` with
  enum-restricted items (the 5 canonical pillars) and `uniqueItems: true`.
- Substrate-walker hygiene scan
  (`src/uiao/substrate/walker.py::_scan_ztmm_pillars`) — active adapter
  with no `ztmm-pillars:` key → P3 (advisory) finding tagged
  `DRIFT-SCHEMA`. Explicit empty list (`ztmm-pillars: []`) is a valid
  declaration and skipped. Live canon currently clean.
- 30 new tests in `tests/test_ztmm.py`: vocabulary parsing (5),
  registry loader (8 — empty-list / unknown / synonyms / override /
  mod_top_level), score calculator (8 — TRADITIONAL/INITIAL/ADVANCED/
  OPTIMAL transitions, evidence-driven demotion via Open finding,
  per-pillar attribution, overall-rank average), OSCAL back-matter
  projection (4), substrate-walker scan (4), plus a live-canon
  end-to-end smoke that verifies every pillar lands at INITIAL or
  better today.

Deferred (follow-ups):
- Auditor API endpoint (`GET /v1/ztmm`) — gated on §3.1 Auditor API.
- Quarto dashboard pillar tile.
- Promote pillar walker findings from P3 advisory to P2 once the
  substrate-status site widget exists.

Referenced doc: UIAO_120 Zero-Trust Integration spec.

### 3.7 — UIAO_109 Data Lake Model (aspirational → **🟡 working** ✅)

Long-term retention + archival of scheduler-run evidence so compliance
teams can serve audit requests months / years after a finding closed,
the substrate can prove freshness + provenance for any claim still
inside its retention window, and old evidence ages out automatically.

Shipped:
- `src/uiao/storage/data_lake.py` — `RetentionPolicy` (per-adapter,
  reads existing `retention-years:` from canon), `ArchiveEntry`
  (run/adapter/archived_at/retention_until/evidence_class), abstract
  `ArchiveBackend`, concrete `FilesystemArchive` (writes
  `lake_root/<adapter>/<run_id>/` + `_index/<run>__<adapter>.json`
  manifests), `ArchiveManager` (orchestrates archive_run / expire /
  query against any backend).
- `load_retention_policies(registries)` reads existing
  `retention-years:` declarations from
  `modernization-registry.yaml` + `adapter-registry.yaml`. Adapters
  without an explicit value fall through to a configurable default
  (3 years, federal ConMon baseline). `policy_for(adapter_id, …)`
  resolves with the same fallback for ad-hoc lookups.
- 24 new tests in `tests/test_data_lake.py`: retention loader (6),
  policy fallback (2), ArchiveEntry round trip (4 incl.
  past-/within-window expiry semantics), FilesystemArchive backend
  (3), ArchiveManager orchestration (8 — multi-adapter archive,
  evidence-class extraction, default retention for undeclared
  adapter, expire + index cleanup, in-window kept, query filters),
  plus a live-canon smoke verifying every active adapter resolves
  to a positive retention.

Deferred to future PRs:
- S3 / Azure Blob / GCS backends behind the `ArchiveBackend` ABC.
- Cron-driven `uiao archive expire` CLI command (gated on §3.1
  Auditor API CLI surface).
- Hot-vs-cold tiering enforcement (compression, slower-storage move
  at the `hot_period_days` boundary).
- Integration with §3.2 Compliance Query Language for retrieval.

Referenced doc: UIAO_109 Data Lake Model spec.

### 3.8 — UIAO_125–128 Programs: first live delivery — ✅ shipped 2026-04-26

The four program specs (Training, Test Plans, Project Plans, Education) shipped their first deliverable each. The chronological log lives at [`docs/programs/deliveries.qmd`](../programs/deliveries.qmd); future deliveries land as new entries under the same per-program subdirectory.

Shipped:
- UIAO_125 Training — [Adapter-author onboarding session record (2026-04-26)](../programs/training/2026-04-26-adapter-author-onboarding.qmd) covering canon registry declaration, scheduler wire-up, and the §0.4 / §0.5 / §3.6 walker hygiene gates.
- UIAO_126 Test Plans — [ScubaGear conformance test plan](../programs/test-plans/scubagear-conformance-test-plan.qmd) instantiating UIAO_121 against the `scubagear` adapter (Tier 1 / Tier 2 / Tier 3 status).
- UIAO_127 Project Plans — [Acme Federal modernization project plan](../programs/project-plans/agency-acme-modernization-plan.qmd), a synthetic but representative agency engagement plan (Phase 0 → Phase 2, owners, risks, cadence).
- UIAO_128 Education — [Agency onboarding walkthrough](../programs/education/agency-onboarding-walkthrough.qmd), a 15-minute narrative read aimed at an agency CIO / CISO / IAM lead.

The four substrate-status rows for UIAO_125–128 flip from "0 deliveries" to "≥1 delivery" with this PR. Future deliveries are additive; the program subdirectories are now the canonical surface for them.

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
| P1 | UIAO_110 §DRIFT-AUTHZ | Drift Engine — Auth class | ✅ complete | ✅ by v0.3 |
| P1 | UIAO_110 §DRIFT-IDENTITY | Drift Engine — Identity class | ✅ complete | ✅ by v0.3 |
| P2 | UIAO_110 §DRIFT-SEMANTIC | Drift Engine — Semantic class | ✅ complete | ✅ by v0.5 |
| P2 | UIAO_100 | Compliance Orchestrator | 🟡 partial | 🟡 by v0.5 |
| P2 | UIAO_103 | Spec-Test Enforcement | ✅ complete | ✅ by v0.5 |
| P2 | UIAO_113 | Evidence Graph | ✅ working | 🟡→✅ by v0.5 |
| P3 | UIAO_105 | Auditor API | 🟡 working | 🟡 by v1.0 |
| P3 | UIAO_111 | Enforcement Runtime | 🟡 working | 🟡 by v1.0 |
| P3 | UIAO_108 | CQL | 🟡 working | 🟡 by v1.0 |
| P3 | UIAO_116 | EPL | 🟡 working | 🟡 by v1.0 |
| P3 | UIAO_112 | Multi-Tenant Isolation | 🟡 working | 🟡 by v1.0 |
| P3 | UIAO_120 | Zero-Trust Integration | 🟡 working | 🟡 by v1.0 |
| P4 | UIAO_109 | Data Lake | 🟡 working | 🟡 by v1.1 |
| P4 | UIAO_114 | HA / Fault Tolerance | ⚠️ aspirational | assessed by v1.0 |
| P4 | UIAO_115 | Performance Engineering | ⚠️ aspirational | assessed by v1.0 |
| P4 | UIAO_117 | Recovery Layer | ⚠️ aspirational | assessed by v1.0 |
| P4 | UIAO_119 | Tenancy Strategy | ⚠️ aspirational | 🟡 by v1.0 |
| P4 | UIAO_125–128 | Programs (Training, Test Plans, Project Plans, Education) | 🟡 first delivery shipped | first delivery by v1.0 |
| P5 | UIAO_129/130 | Application Identity Model / Runbook | ⚠️ draft | status reconciled by v0.3 |
| P5 | Mainframe adapter | z/OS Connect / MQ bridge | reserved | unblocked or deferred by v1.1 |

---

*This roadmap is a derived view. It does not supersede any canon document. Conflicts between this document and a UIAO_NNN spec resolve in favor of the spec. Update this document when milestones are achieved or targets change.*
