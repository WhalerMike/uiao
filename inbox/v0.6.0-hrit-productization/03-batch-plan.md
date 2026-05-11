# 03 — Batch Plan: HRIT Single-ATO Productization (v0.6.0)

> **Status:** Inbox draft. Not canon. Authored 2026-05-06. Each workstream
> below is a self-contained brief any Claude session can pick up cold.

## Mission (one sentence)

Close the runtime gap that ADR-054 §Implementation explicitly deferred:
make the Single-ATO Reciprocity Model emit signed, OSCAL-mapped,
evidence-graph-anchored reciprocity records per consuming agency, with
ConMon SLA enforcement and configuration-latitude drift detection.

## Acceptance for the release

A maintainer can run, end-to-end, in <15 min on a synthetic three-agency
fixture:

```
uiao reciprocity onboard-agency \
  --controlling-ato OPM-HRIT-2026-001 \
  --consuming-agency TREAS \
  --legal-basis interagency-mou \
  --out-dir /tmp/hrit-recip
```

…and receive a signed, schema-valid `reciprocity-record.json` plus an
OSCAL component-definition scoped to TREAS, both linked into the
evidence graph as `ato-decision → reciprocity-record` edges.

## Phase structure

| Phase | What happens | Concurrency model |
|---|---|---|
| **Phase 0 — Foundation** | Promote ADR-058 to canon, allocate UIAO_143, stub schema, create branch scaffolding | **One** session, sequential |
| **Phase 1 — Batch A** | 10 self-contained workstreams | **Up to 10** sessions in parallel |
| **Phase 2 — Integration** | Merge, full CI green, RC1 tag | **One** session |
| **Phase 3 — Validation** | Lab tenant validation, doc polish | **Up to 3** sessions in parallel |
| **Phase 4 — Release cut** | Tag v0.6.0, CHANGELOG, push | **One** session |

---

## Phase 0 — Foundation (sequential, one session)

**Branch:** `claude/v0.6.0-hrit-foundation`

**Tasks:**
1. Promote `02-proposed-adr-058-draft.md` to
   `src/uiao/canon/adr/adr-058-hrit-productization-mission.md` (status: Accepted)
2. Allocate **UIAO_143** in `src/uiao/canon/document-registry.yaml`
3. Create `src/uiao/canon/specs/hrit-productization.md` (UIAO_143)
   — frontmatter + outline only; sections filled by Batch A
4. Create stub schema `src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`
   with `$schema`, `$id`, and empty `properties` — Batch A WS-A1 fills
5. Create `examples/hrit/.gitkeep` so the directory exists for fixtures
6. Create the 10 Batch A branches on origin (push empty commits)
7. Tag baseline `v0.5.x-pre-hrit`

**Acceptance:**
- ADR-058 in canon, status Accepted
- UIAO_143 registered
- Schema stub passes JSON-Schema meta-validation
- 10 Batch A branches exist on origin and pass CI as no-ops
- `uiao substrate walk` reports zero new findings

---

## Phase 1 — Batch A (parallel, up to 10 sessions)

Each WS owns a disjoint file set. Conflicts are minimized by scope.

### WS-A1 — Reciprocity-Record JSON Schema

- **Branch:** `claude/v0.6.0-ws-a1-reciprocity-schema`
- **Scope (in):** `src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`
- **Scope (out):** Anything outside this file
- **Reads first:** UIAO_140 §6 (lines 102–121), ADR-054, existing `src/uiao/schemas/reciprocal-consumption/registry.schema.json` for style reference
- **Deliverables:**
  - Required fields per UIAO_140 §6 lines 114–121: `controlling_ato_id`, `consuming_agency_code`, `reciprocity_basis`, `legal_basis` (enum from registry schema), `effective_at`, `expires_at`, `configuration_latitude_ref`, `signature` (HMAC-SHA256), `provenance`
  - Required nested `signature` object: `algorithm`, `value`, `signed_at`, `signer`
  - Required `provenance` block conforming to existing metadata schema
- **Acceptance:** Schema validates a synthetic record + an empty object fails; meta-validates against JSON Schema 2020-12
- **Estimated session:** 1 short

### WS-A2 — OSCAL Reciprocity-Record Emitter

- **Branch:** `claude/v0.6.0-ws-a2-reciprocity-emitter`
- **Scope (in):** new `src/uiao/oscal/reciprocity_record.py`; tests under `tests/test_reciprocity_emitter.py`
- **Scope (out):** Schema (WS-A1), CLI (WS-A4), evidence graph (WS-A3)
- **Reads first:** ADR-054 §Implementation, UIAO_140 §7, existing `src/uiao/oscal/orgtree_evidence.py` for emitter pattern, `src/uiao/oscal/generator.py` for SSP/POA&M integration
- **Deliverables:**
  - Function `emit_reciprocity_record(controlling_ato_id, consuming_agency_code, legal_basis, ...) -> dict`
  - HMAC-SHA256 signing with stable content hash excluding volatile fields
  - OSCAL component-definition projection scoped to consuming agency
  - Provenance block citing UIAO_140 + ADR-054
- **Acceptance:** Emits a record that schema-validates against WS-A1 schema; golden-file regression test pinned; signature verifies independently
- **Estimated session:** 1 medium

### WS-A3 — Evidence Graph v1.2 (UIAO_113 amendment)

- **Branch:** `claude/v0.6.0-ws-a3-evidence-graph`
- **Scope (in):** `src/uiao/canon/specs/graph-schema.md` (amendment to v1.2); `src/uiao/evidence/graph.py` if present
- **Scope (out):** Anything else
- **Reads first:** UIAO_113 v1.1, UIAO_140 §6 lines 102–108 (the `ato-decision → reciprocity-record` hierarchy)
- **Deliverables:**
  - Add node types 12–13 to UIAO_113: `ato-decision`, `reciprocity-record`
  - Add edge types: `ato-decision → reciprocity-record`, `reciprocity-record → consuming-agency`
  - Bump version to v1.2 with provenance entry
  - Runtime traversal support if `evidence/graph.py` exists
- **Acceptance:** UIAO_113 frontmatter version is `1.2`; substrate walker emits zero `DRIFT-SCHEMA` findings; new node/edge types referenced from WS-A2 emitter via WS-A6 aggregator integration in Phase 2
- **Estimated session:** 1 medium

### WS-A4 — Reciprocity CLI sub-app

- **Branch:** `claude/v0.6.0-ws-a4-reciprocity-cli`
- **Scope (in):** new `src/uiao/cli/reciprocity.py`; registration line in `src/uiao/cli/app.py`
- **Scope (out):** Emitter (WS-A2), schema (WS-A1)
- **Reads first:** AGENTS.md invariant I6 (sub-app convention), ADR-046, existing CLI sub-apps for pattern, Spec2-D6.1 §7 line 239 (`uiao app onboard-federal` design sketch — adapt to sub-app form)
- **Deliverables:**
  - `uiao reciprocity onboard-agency` — emit reciprocity record (calls WS-A2)
  - `uiao reciprocity list-records` — enumerate registered reciprocity records
  - `uiao reciprocity verify` — verify a record's signature
  - `--help` examples on every command
  - Registration of `reciprocity_app` in `cli/app.py`
- **Acceptance:** `tests/test_cli_help_smoke.py` passes for all three commands; `uiao reciprocity onboard-agency --help` shows a runnable example
- **Estimated session:** 1 medium

### WS-A5 — ConMon SLA Cadence Validator

- **Branch:** `claude/v0.6.0-ws-a5-conmon-sla`
- **Scope (in):** new `src/uiao/monitoring/ato_cadence.py`; new CLI command `uiao conmon ato-cadence-check` in existing `cli/conmon.py`; tests under `tests/test_ato_cadence.py`
- **Scope (out):** Reciprocity emitter
- **Reads first:** UIAO_140 §4 lines 63–75, ADR-054 Q&A #44 + Consequences line 131, existing `cli/conmon.py`
- **Deliverables:**
  - 30-day draft SSP / 45-day final SSP cadence enforcement (timer-gated)
  - 30-day reauthorization window SLA
  - CLI command emits `PASS|WARN|FAIL` with named SLA breaches
  - JSON output for downstream tooling
- **Acceptance:** Tests cover all three thresholds (28d / 32d / 46d / 100d) with deterministic verdicts; integrates with existing ConMon pipeline
- **Estimated session:** 1 medium

### WS-A6 — Per-Agency Reciprocity Bundle Aggregator

- **Branch:** `claude/v0.6.0-ws-a6-bundle-aggregator`
- **Scope (in):** new `src/uiao/oscal/reciprocity_bundle.py`; tests
- **Scope (out):** Emitter (WS-A2), CLI (WS-A4)
- **Reads first:** Spec2-D6.1 §9 line 269, existing `src/uiao/evidence/` for bundle pattern, WS-A2 emitter contract
- **Deliverables:**
  - `aggregate_per_agency_bundle(controlling_ato_id, consuming_agency_code, output_dir) -> Path`
  - Bundles: reciprocity-record + scoped component-definition + scoped assessment-results + provenance manifest
  - Independently verifiable — consuming agency AO validates without UIAO platform access
- **Acceptance:** Bundle round-trips (emit → re-validate from disk); golden-file regression
- **Dependency:** Mocks WS-A2 outputs until Phase 2 wires together
- **Estimated session:** 1 medium

### WS-A7 — Configuration-Latitude Drift Detector

- **Branch:** `claude/v0.6.0-ws-a7-config-latitude`
- **Scope (in):** new `src/uiao/governance/config_latitude.py`; new CQL query under `src/uiao/canon/queries/configuration-latitude-violations.yaml`; tests
- **Scope (out):** Anything else
- **Reads first:** UIAO_140 §5 line 91 (DRIFT-SCHEMA when configuration not in SSP latitude table), existing CQL queries in `canon/queries/`, drift class definitions in `docs/docs/16_DriftDetectionStandard.qmd`
- **Deliverables:**
  - SSP-side: read enumerated configuration-latitude table from SSP YAML
  - Tenant-side: collect observed tenant configuration
  - Diff: emit `DRIFT-SCHEMA` finding (P2 default) when tenant config not in latitude table
  - CQL query for drift findings filtered to configuration-latitude class
- **Acceptance:** Test fixture with intentional latitude violation produces correct finding; conforming tenant produces zero findings
- **Estimated session:** 1 medium

### WS-A8 — Synthetic Three-Agency Fixture + Quickstart

- **Branch:** `claude/v0.6.0-ws-a8-fixture-quickstart`
- **Scope (in):** new `examples/hrit/opm-treas-irs/` (fixture); new `docs/docs/hrit-productization-quickstart.md`
- **Scope (out):** Tests (WS-A9)
- **Reads first:** Spec2-D6.1 §2 (12 federal HRIT systems), existing `docs/docs/quickstart.md` for pattern
- **Deliverables:**
  - Synthetic OPM controlling ATO + Treasury + IRS consuming agencies
  - Per-agency configuration with one intentional latitude violation (for WS-A7 demo)
  - 10-step quickstart from clone → three signed reciprocity records
  - Known-answer table per agency
- **Acceptance:** Quickstart can be executed verbatim by a stranger; stated outputs match what runs produce
- **Estimated session:** 1 medium

### WS-A9 — CI Smoke Test + Reciprocity Tests

- **Branch:** `claude/v0.6.0-ws-a9-ci-tests`
- **Scope (in):** new `tests/test_hrit_productization_smoke.py`; happy-path + lapsed-ATO + configuration-latitude drift tests under `tests/test_reciprocity_*.py`
- **Scope (out):** Other test files outside reciprocity scope
- **Reads first:** Existing `tests/test_quickstart_smoke.py`, `tests/test_cli_help_smoke.py`, ADR-054 line 163 (deferred test cases)
- **Deliverables:**
  - End-to-end smoke against WS-A8 fixture
  - Lapsed-ATO test: reciprocity record past `expires_at` flagged
  - Configuration-latitude drift test
  - Schema-validation assertions (WS-A1) on every emitted record
- **Acceptance:** Smoke runs in <60s; fails closed if any link regresses
- **Dependency:** Mocks WS-A2/A4/A5/A6/A7 outputs until Phase 2 wires
- **Estimated session:** 1 medium

### WS-A10 — KSI Rules + Narrative Doc

- **Branch:** `claude/v0.6.0-ws-a10-ksi-narrative`
- **Scope (in):** new `src/uiao/rules/ksi/KSI-RECIP-*.yaml`; mapping registry append in `src/uiao/rules/ksi/uiao-control-to-ksi-mapping.yaml`; new `docs/docs/22_HRITProductization.qmd`
- **Scope (out):** Anything else
- **Reads first:** Existing KSI files (`KSI-001.yaml`), control mapping registry, UIAO_140 §6, Spec2-D6.1
- **Deliverables (≥8 KSIs):**
  - KSI-RECIP-001: Every reciprocity record cites a `legal_basis` from the enum
  - KSI-RECIP-002: Every reciprocity record references a controlling ATO that exists in registry
  - KSI-RECIP-003: No reciprocity records past `expires_at` without renewal record
  - KSI-RECIP-004: Configuration latitude drift findings have remediation owner assigned
  - KSI-RECIP-005: SSP cadence (30-day draft, 45-day final) met for current ATO cycle
  - KSI-RECIP-006: 30-day reauthorization SLA met
  - KSI-RECIP-007: Per-agency bundle signature verifies
  - KSI-RECIP-008: Evidence graph contains `ato-decision → reciprocity-record` edge for every active record
  - Narrative doc: `22_HRITProductization.qmd` — operational narrative + 2 Mermaid diagrams (record lifecycle, bundle aggregation)
- **Acceptance:** All KSIs validate against `ksi.schema.json`; mapping registry updated; Quarto renders clean; substrate walker zero new findings
- **Estimated session:** 1 long

---

## Phase 2 — Integration (sequential, one session)

**Branch:** `claude/v0.6.0-hrit-integration`

1. Merge Batch A branches in dependency order: A1 → A3 → A2 → A6 → A4 → A5 → A7 → A8 → A9 → A10
2. Wire WS-A2 emitter into WS-A4 CLI (remove A4's mocks)
3. Wire WS-A6 aggregator to consume real WS-A2 outputs
4. Wire WS-A9 smoke against real fixture from WS-A8
5. Run substrate walker; resolve drift findings
6. Full CI sweep (8 blocking gates)
7. Tag `v0.6.0-rc1`

**Acceptance:** All 8 blocking CI gates green; smoke passes against real WS-A8 fixture; zero `DRIFT-PROVENANCE` findings.

---

## Phase 3 — Validation (parallel, up to 3 sessions)

**WS-B1 — Lab tenant dry-run**
- Branch: `claude/v0.6.0-ws-b1-lab-validation`
- Validate RC1 against an actual single-ATO lab tenant (OPM-style); capture deltas; file issues.
- **Note:** Human-in-loop for tenant access.

**WS-B2 — Documentation polish**
- Branch: `claude/v0.6.0-ws-b2-docs`
- Update `README.md`, draft CHANGELOG entry, refresh `canon/adr/index.md` (resync with ADR-032..058 — pre-existing housekeeping debt).

**WS-B3 — Public-surface audit**
- Branch: `claude/v0.6.0-ws-b3-surface-audit`
- Update `AGENTS.md` Public Surface Inventory; add `uiao reciprocity` sub-app to `docs/docs/cli-reference.md`; verify all `--help` examples run.

---

## Phase 4 — Release cut (sequential, one session)

**Branch:** `claude/v0.6.0-release`

1. Merge B1–B3 into integration
2. Final CI sweep
3. Bump `src/uiao/__version__.py` to `0.6.0`
4. Compose CHANGELOG entry (theme summary + breaking changes if any)
5. Tag `v0.6.0`
6. Push tag (triggers `release.yml`)

---

## Self-contained AI session prompt template

For each WS, hand the assigned Claude session this prompt:

```
You are working on UIAO at /home/user/uiao on branch
claude/v0.6.0-ws-XX-<name> (already created on origin).

Read in order before any code change:
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §"WS-XX"
- AGENTS.md (especially invariants I1–I6 and Repository Invariants)
- The "Reads first" list in your WS card
- src/uiao/canon/adr/adr-058-hrit-productization-mission.md
- src/uiao/canon/specs/hrit-productization.md (UIAO_143)

Execute "Deliverables" until "Acceptance" criteria are all met. Run
`ruff check`, `mypy src/uiao`, and `pytest -q tests/test_<your_scope>.py`
before committing. Do not modify files outside your "Scope (in)" list.

Commit with conventional commit format (`feat:`, `test:`, `docs:`).
Push to origin. Do not open a PR — Phase 2 will handle integration.

If you hit a question that needs maintainer judgment, write the
question into inbox/v0.6.0-hrit-productization/questions-WS-XX.md
and stop. Do not guess.
```

## Concurrency rules — file ownership

| Path | Sole owner |
|---|---|
| `src/uiao/schemas/reciprocity-record/` | WS-A1 |
| `src/uiao/oscal/reciprocity_record.py` | WS-A2 |
| `src/uiao/canon/specs/graph-schema.md` | WS-A3 |
| `src/uiao/evidence/graph.py` (if exists) | WS-A3 |
| `src/uiao/cli/reciprocity.py` | WS-A4 |
| `src/uiao/cli/app.py` (one-line additive registration) | WS-A4 |
| `src/uiao/monitoring/ato_cadence.py` | WS-A5 |
| `src/uiao/cli/conmon.py` (one-line additive registration) | WS-A5 |
| `src/uiao/oscal/reciprocity_bundle.py` | WS-A6 |
| `src/uiao/governance/config_latitude.py` | WS-A7 |
| `src/uiao/canon/queries/configuration-latitude-violations.yaml` | WS-A7 |
| `examples/hrit/` | WS-A8 |
| `docs/docs/hrit-productization-quickstart.md` | WS-A8 |
| `tests/test_hrit_productization_smoke.py` | WS-A9 |
| `tests/test_reciprocity_*.py` | WS-A9 |
| `src/uiao/rules/ksi/KSI-RECIP-*.yaml` | WS-A10 |
| `src/uiao/rules/ksi/uiao-control-to-ksi-mapping.yaml` (append-only) | WS-A10 |
| `docs/docs/22_HRITProductization.qmd` | WS-A10 |

Only shared edits are append-only (mapping registry, CLI sub-app
registration in `app.py`/`conmon.py` — single-line adds). Phase 2
resolves any cross-WS conflicts.

## What gets ratified before code

If the maintainer ratifies this plan:

1. Run Phase 0 in a single sequential session
2. Hand each Batch A WS prompt to a separate Claude session in parallel
3. After all 10 commit + push, run Phase 2 integration session
4. After RC1 tag, run Phase 3 in parallel (B1 needs human-in-loop for lab tenant)
5. Phase 4 cuts v0.6.0

Estimated wall-clock: Phase 0 ~1 session, Phase 1 ~10 parallel sessions,
Phase 2 ~1 session, Phase 3 ~3 parallel sessions, Phase 4 ~1 session.
Six sequential gates total; remaining work parallelizes.
