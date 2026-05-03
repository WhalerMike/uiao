# Agent Backlog — Repository Gap Remediation

> **Scope:** code, adapters, tests, integration, and CI gaps in the `whalermike/uiao` monorepo (`core/` canon + `impl/` runtime; `gos` merged into `impl/adapters/` and documentation).
>
> **Out of scope (owned by the Documentation & Training lane):** anything under `docs/`, the Quarto site, narrative markdown (README / CLAUDE.md / AGENTS.md / ARCHITECTURE.md / VISION.md / CONMON.md / PROJECT-CONTEXT.md), tutorials, onboarding guides, CHANGELOG authoring.
>
> **Origin:** seeded from three Explore-agent gap surveys (`core/`, `impl/`, repo-root) on 2026-04-17, branch `claude/assess-repo-gaps-EO8Yq`. Re-added 2026-04-18 from a fresh branch after the original PR #72 was closed unmergeable (3,277 commits of pre-consolidation history); tracked as issue #90. Path references updated for the ADR-031 / PR #88 / PR #89 PEP-420 namespace rename (`uiao_impl` → `uiao.impl`).

---

## Format Conventions

- **Appendable.** New items go to the bottom of the relevant workstream section. Closed items stay in place (do not delete) so history is visible.
- **Stable IDs.** Every task has an ID of the form `<WS>-NNN` where `<WS>` ∈ `{ADP, CNT, TST, CI, INT}`. IDs never renumber — allocate the next free number in the workstream when appending.
- **Checkbox status.** `- [ ]` open, `- [x]` complete.
- **Completion annotation.** When closed, flip the checkbox and append `✓ YYYY-MM-DD — <agent/author> — <PR #NNN or commit sha>` on the same line as the title.
- **Priority tag.** `[P0]` blocking, `[P1]` high, `[P2]` normal. Priority may be edited in place as reality changes.
- **Reference paths.** Every task lists concrete file paths.
- **Acceptance criteria.** Each task carries a one-line *Done-when* describing the finish condition.

### Example (completed item)

```
- [x] **ADP-001** [P0] Consolidate duplicate adapter code  ✓ 2026-04-20 — @agent-ci — PR #142
      Paths: impl/adapters/cloud/*, impl/src/uiao/impl/adapters/
      Done-when: only one adapter tree exists; orchestrator imports resolve.
```

### Workstream keys

| Key | Workstream                  |
| --- | --------------------------- |
| ADP | Adapters & Registry         |
| CNT | Core Contracts & Schemas    |
| TST | Test Infrastructure         |
| CI  | CI / Security               |
| INT | Integration / Monorepo      |

---

## ADP — Adapters & Registry

- [x] **ADP-001** [P0] Consolidate duplicate adapter code  ✓ 2026-04-17 — prior session — PR #81 + PR #86
      Paths: `impl/src/uiao/impl/adapters/` (sole surviving tree); `impl/adapters/` deleted entirely by PR #86 (SCuBA runtime relocated to `impl/scuba-runtime/`).
      Done-when: single canonical adapter tree; deprecated stubs removed; orchestrator imports resolve; tests green.
- [ ] **ADP-002** [P0] Build adapter registry + dynamic loader (`@register()` decorator)
      Paths: `impl/src/uiao/impl/adapters/__init__.py`, `impl/src/uiao/impl/adapters/registry.py`
      Done-when: adapters self-register; orchestrator enumerates from registry; unit test asserts all expected adapter IDs present.
- [ ] **ADP-003** [P0] Implement the conformance-check module referenced by `adapter-conformance.yml`
      Path: `impl/src/uiao/impl/adapters/conformance_check.py`
      Done-when: CLI emits 330-criteria JSON report; `impl/.github/workflows/adapter-conformance.yml` passes without mocks.
- [ ] **ADP-004** [P1] Wire orchestrator to load adapters via registry (not hardcoded imports)
      Path: `impl/orchestrator/orchestrator.py`
      Done-when: removing an adapter module does not require orchestrator edits.
- [ ] **ADP-005** [P1] Reusable adapter test harness (fixtures, mock transport, recording helpers)
      Path: `impl/tests/conftest_adapters.py`
      Done-when: at least two adapter test files share the fixtures.

## CNT — Core Contracts & Schemas

- [ ] **CNT-001** [P0] Promote `BaseAdapter` contract into `core/` (currently only lives in `impl/`)
      Paths: `core/canon/adapter-interface-v1.0.yaml`, `core/schemas/adapter-registry/base-adapter-interface.json`
      Done-when: `impl/src/uiao/impl/adapters/base_adapter.py` imports / references the canon contract.
- [ ] **CNT-002** [P0] Author unified compliance matrix (FedRAMP Rev5 → UIAO control planes → remediation → evidence)
      Path: `core/data/unified_compliance_matrix.yml`
      Done-when: file validates against a new `core/schemas/compliance/matrix.json`; referenced by KSI rules without `# TODO` markers.
- [ ] **CNT-003** [P0] Agency parameter tailoring — schema + defaults
      Paths: `core/schemas/parameters/agency-parameters.json`, `core/data/parameters.yml`
      Done-when: impl SSP generation consumes `parameters.yml` and produces agency-tailored OSCAL.
- [ ] **CNT-004** [P1] KSI evaluation engine + seed templates (identity, telemetry, compliance)
      Paths: `core/ksi/evaluations/`, `core/ksi/rules/`
      Done-when: three evaluation templates land and execute against fixture data.
- [ ] **CNT-005** [P1] Populate empty schema subdirs
      Paths: `core/schemas/{ksi,udc,uiao-api,substrate-manifest,workspace-contract,adapter-registry}/`
      Done-when: each directory contains at least one real JSON Schema (no more `.gitkeep`-only dirs).
- [ ] **CNT-006** [P1] Compliance enforcement policy file
      Path: `core/compliance/fedramp-moderate-baseline.yaml`
      Done-when: `core/compliance/` has a real policy file referenced by validators.
- [ ] **CNT-007** [P2] Canonical OSCAL component definition (data artifact)
      Path: `core/exports/oscal/uiao-component-definition.json`
      Done-when: artifact validates against OSCAL 1.3 schema in CI.
- [ ] **CNT-008** [P2] Evidence-ingestion schema (uuid, control-id, timestamp, source, confidence)
      Path: `core/schemas/uiao-api/evidence-ingestion.json`
      Done-when: schema is draft-2020-12 valid and a fixture payload passes validation in CI.
- [ ] **CNT-009** [P2] Telemetry normalization schema referenced by KSI rules
      Path: `core/schemas/uiao-api/telemetry-normalization.json`
      Done-when: schema is referenced by at least one KSI rule and validates a fixture event.

## TST — Test Infrastructure

- [ ] **TST-001** [P0] Fix `impl/.coveragerc` — currently points to `src/uiao_core` (wrong package); omits uiao generators
      Path: `impl/.coveragerc`
      Done-when: `source = src/uiao/impl`, omit patterns updated, `coverage run -m pytest` reports for the correct tree.
- [ ] **TST-002** [P0] Populate empty test file `impl/tests/test_briefing.py` (currently 2 bytes)
      Path: `impl/tests/test_briefing.py`
      Done-when: at least one real test passes and the briefing generator has coverage.
- [ ] **TST-003** [P1] Export conformance test suite from `core/` so impl adapters can import it
      Pattern: `from uiao.core.tests.conformance import BaseAdapterTest`
      Paths: `core/tests/conformance/test_adapter_contract.py`, `core/tests/conformance/__init__.py`, `core/pyproject.toml` (extras)
      Done-when: an impl adapter inherits `BaseAdapterTest` and CI executes it.
- [ ] **TST-004** [P1] Unit tests for core validators (`metadata_validator`, `sync_canon`, `drift_detector`, `dashboard_exporter`, `appendix_indexer`)
      Path: `core/tests/tools/test_validators.py`
      Done-when: each validator has happy-path + failure-path coverage.
- [ ] **TST-005** [P1] E2E pipeline test: core schema change → impl code-gen → adapter conformance → OSCAL output
      Path: `impl/tests/e2e/test_schema_to_oscal.py`
      Done-when: mutating a fixture schema changes the generated OSCAL deterministically and the test catches it.
- [ ] **TST-006** [P2] Coverage gate (≥80%) + artifact upload
      Paths: `impl/.github/workflows/ci.yml` (new step), `impl/.coveragerc`
      Done-when: CI fails below threshold; coverage HTML/XML uploaded as an artifact.

## CI — CI / Security

- [ ] **CI-001** [P0] Invoke `mypy src/` in impl CI (mypy is in dev deps but never runs)
      Path: `.github/workflows/mypy.yml` (new, at repo root — the in-folder `impl/.github/workflows/ci.yml` still does a stale cross-repo checkout; see **CI-010**).
      Done-when: mypy step runs on every PR and fails on new type errors.
- [ ] **CI-002** [P1] CodeQL SAST workflow
      Path: `.github/workflows/codeql.yml`
      Done-when: CodeQL runs weekly + on PR; findings surface in the Security tab.
- [ ] **CI-003** [P1] Dependency-review workflow
      Path: `.github/workflows/dependency-review.yml`
      Done-when: PRs changing `pyproject.toml` / lockfiles get a diff review with license + vuln flags.
- [ ] **CI-004** [P1] actionlint workflow — validate all workflow YAML against schema
      Path: `.github/workflows/actionlint.yml`
      Done-when: actionlint runs on PRs that touch `.github/workflows/**`.
- [ ] **CI-005** [P1] Monorepo path filters on `pytest.yml` + `metadata-validator.yml` so core-only changes skip impl pytest (and vice versa)
      Paths: `.github/workflows/pytest.yml`, `.github/workflows/metadata-validator.yml`
      Done-when: a core-only PR does not re-run impl pytest and vice versa.
- [ ] **CI-006** [P2] Enable native GitHub secret scanning + push protection; add trufflehog pre-commit hook
      Paths: `.pre-commit-config.yaml`, repo settings
      Done-when: secret-scanning is enabled repo-wide and trufflehog runs locally on commit.
- [ ] **CI-007** [P2] Nightly integration workflow (full cross-module suite on schedule + post-merge)
      Path: `.github/workflows/nightly-integration.yml`
      Done-when: workflow runs on cron + on push to `main` and exercises core ↔ impl end-to-end.
- [ ] **CI-008** [P2] Surface `impl/.github/workflows/adapter-conformance.yml` and `acceptance-tests.yml` at repo root so they gate PRs
      Path: `.github/workflows/impl-integration.yml` (new)
      Done-when: the new root workflow invokes both jobs as required status checks.
- [ ] **CI-009** [P2] Consolidate duplicate link-check workflows (repo-root lychee vs impl PowerShell)
      Paths: `.github/workflows/link-check.yml` (extend), `impl/.github/workflows/link-check.yml` (delete)
      Done-when: only one link-check workflow remains; it covers root + impl; `make check-links` still works.
- [ ] **CI-010** [P1] Retire stale `impl/.github/workflows/ci.yml`
      Path: `impl/.github/workflows/ci.yml`
      Context: this workflow still does `actions/checkout@v4 with: repository: WhalerMike/uiao, ref: main, path: uiao` — that's the pre-consolidation split. The authoritative impl test workflow is `.github/workflows/pytest.yml` at the repo root. The in-folder file either needs to be deleted or rewritten to use local `core/` (and repoint `UIAO_CANON_PATH` accordingly).
      Done-when: only one impl pytest workflow runs per PR; no job references the old separate repo.
- [ ] **CI-011** [P1] Fix `link-check.yml` rotted URL(s) surfaced by issue #91 (lychee soft-failing on unrelated PRs)
      Path: `.github/workflows/link-check.yml` (or the URL on `main` that lychee can't reach)
      Done-when: a fresh PR touching neither `*.md` nor `*.qmd` shows green link-check; lychee artifact is empty or contains only accepted codes.

## INT — Integration / Monorepo

- [ ] **INT-001** [P0] Pin `uiao` dependency in `impl/pyproject.toml` (path dep now, package dep once core is published)
      Path: `impl/pyproject.toml`
      Done-when: `pip install -e impl/` pulls core automatically; `UIAO_CANON_PATH` env fallback is documented, not required.
      Note (2026-04-17): deferred — `core/pyproject.toml` declares `packages = []` (data-only, no Python package). Choose one first: (a) make core an installable package that ships canon data, or (b) formalise the `UIAO_CANON_PATH` env-var resolver with a fallback that locates `../core` relative to the installed impl. Landing either change is a prerequisite for this item.
- [ ] **INT-002** [P0] Root `pyproject.toml` with `uv` workspace binding core + impl
      Path: `pyproject.toml` (new, repo root)
      Done-when: `uv sync` at repo root installs both packages editable.
- [ ] **INT-003** [P1] Resolve version-skew policy between core (0.2.0) and impl (0.2.1)
      Paths: `core/pyproject.toml`, `impl/pyproject.toml`, plus a short `inbox/drafts/VERSIONING.md` note.
      Done-when: both packages follow a written policy (locked same-major-minor, or independent with compat matrix).
- [ ] **INT-004** [P2] Cross-folder Makefile targets (`make test` → core+impl pytest; `make install-dev` → editable install of both)
      Path: `Makefile`
      Done-when: a fresh clone running `make install-dev && make test` exercises both packages.

---

## Critical Files to Read Before Executing Any Task

- `core/PROJECT-CONTEXT.md`, `core/AGENTS.md`, `core/ARCHITECTURE.md` — canon intent (read-only reference; do **not** edit, that's the docs lane).
- `impl/PROJECT-CONTEXT.md`, `impl/AGENTS.md` — impl intent.
- `core/pyproject.toml`, `impl/pyproject.toml` — package layout.
- `core/canon/adapter-registry.yaml` — current adapter manifest (source of truth for which adapters exist).
- `impl/src/uiao/impl/adapters/base_adapter.py` — current BaseAdapter (to be promoted per **CNT-001**).
- `impl/orchestrator/orchestrator.py` — wiring seam for **ADP-002** / **ADP-004**.
- `.github/workflows/*.yml` and `impl/.github/workflows/*.yml` — existing CI surface.
- `Makefile` — local/CI parity targets.

## Existing Reusable Utilities (Do Not Re-build)

- `core/tools/metadata_validator.py`, `sync_canon.py`, `drift_detector.py`, `dashboard_exporter.py`, `appendix_indexer.py` — validators wired into CI.
- `core/scripts/validate_{canon,schemas,oscal}.py` — one-shot validators.
- `scripts/bootstrap.sh` — dev env setup (pre-commit, editable installs, pyright cache).
- `scripts/check-links.ps1` — link crawler used by `make check-links`.
- `.github/workflows/release.yml` — already publishes impl wheel + CycloneDX SBOM + sigstore.
- `.github/workflows/ruff.yml` — already lints impl.

---

## Completed

_Closed items stay in their workstream section above (checkbox flipped to `[x]`, completion line appended). This section intentionally stays short — it is a future aggregator once the log grows long enough to warrant a summary._
