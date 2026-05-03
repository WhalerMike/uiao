# Agent Backlog — Repository Gap Remediation

> **Scope:** code, adapters, tests, and CI gaps in the `whalermike/uiao` repository — a single flat Python package `uiao` rooted at `src/uiao/` (post-**ADR-032** consolidation, 2026-04-20).
>
> **Out of scope (owned by the Documentation & Training lane):** anything under `docs/`, the Quarto site, narrative markdown (README / CLAUDE.md / AGENTS.md / ARCHITECTURE.md / VISION.md / CONMON.md / PROJECT-CONTEXT.md), tutorials, onboarding guides, CHANGELOG authoring.
>
> **Origin:** seeded from three Explore-agent gap surveys (`core/`, `impl/`, repo-root) on 2026-04-17, branch `claude/assess-repo-gaps-EO8Yq`. Re-added 2026-04-18 from a fresh branch after the original PR #72 was closed unmergeable (3,277 commits of pre-consolidation history); tracked as issue #90. **Path references rewritten 2026-05-03** for the post-**ADR-032** flat-package layout (PR #111, 915 files): `core/` and `impl/` directories no longer exist; the single Python package lives at `src/uiao/`. ADR-031's `uiao.impl.*` namespace was retired by ADR-032. The Integration / Monorepo workstream (INT-001..005) is now mostly superseded — see closure annotations.

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
      Paths: src/uiao/adapters/
      Done-when: only one adapter tree exists; orchestrator imports resolve.
```

### Workstream keys

| Key | Workstream                       |
| --- | -------------------------------- |
| ADP | Adapters & Registry              |
| CNT | Core Contracts & Schemas         |
| TST | Test Infrastructure              |
| CI  | CI / Security                    |
| INT | Integration / Packaging (legacy) |

---

## ADP — Adapters & Registry

- [x] **ADP-001** [P0] Consolidate duplicate adapter code  ✓ 2026-04-17 — prior session — PR #81 + PR #86; finalised 2026-04-20 by ADR-032 / PR #111
      Paths: `src/uiao/adapters/` (sole canonical tree). The pre-consolidation `impl/adapters/` was deleted by PR #86; the entire `impl/` and `core/` two-tree split was collapsed by ADR-032 / PR #111.
      Done-when: single canonical adapter tree; deprecated stubs removed; orchestrator imports resolve; tests green.
- [ ] **ADP-002** [P0] Build adapter registry + dynamic loader (`@register()` decorator)
      Paths: `src/uiao/adapters/__init__.py`, `src/uiao/adapters/registry.py` (new)
      Done-when: adapters self-register; orchestrator enumerates from registry; unit test asserts all expected adapter IDs present.
- [ ] **ADP-003** [P0] Implement the conformance-check module referenced by `adapter-conformance.yml`
      Path: `src/uiao/adapters/conformance_check.py`
      Done-when: CLI emits 330-criteria JSON report; `.github/workflows/adapter-conformance.yml` passes without mocks.
- [ ] **ADP-004** [P1] Wire orchestrator to load adapters via registry (not hardcoded imports)
      Path: `src/uiao/orchestrator/`
      Done-when: removing an adapter module does not require orchestrator edits.
- [ ] **ADP-005** [P1] Reusable adapter test harness (fixtures, mock transport, recording helpers)
      Path: `tests/conftest_adapters.py` (new)
      Done-when: at least two adapter test files share the fixtures.

## CNT — Core Contracts & Schemas

- [ ] **CNT-001** [P0] Promote `BaseAdapter` contract into canon (interface schema exists; doctrine doesn't)
      Paths: `src/uiao/canon/adapter-interface-v1.0.yaml`, `src/uiao/schemas/adapter-registry/base-adapter-interface.json`
      Done-when: the BaseAdapter Python class (under `src/uiao/adapters/`) imports / references the canon contract; conformance-check (ADP-003) consumes the same contract.
      Note (2026-05-03): the BaseAdapter Python class location post-ADR-032 has not been pinpointed — first sub-task of any CNT-001 PR is to find it (likely `src/uiao/adapters/base_adapter.py` or similar) and confirm before promoting.
- [ ] **CNT-002** [P0] Author unified compliance matrix (FedRAMP Rev5 → UIAO control planes → remediation → evidence)
      Path: `src/uiao/canon/data/unified_compliance_matrix.yml`
      Done-when: file validates against a new `src/uiao/schemas/compliance/matrix.json`; referenced by KSI rules without `# TODO` markers.
- [ ] **CNT-003** [P0] Agency parameter tailoring — schema + defaults
      Paths: `src/uiao/schemas/parameters/agency-parameters.json`, `src/uiao/canon/data/parameters.yml`
      Done-when: SSP generation consumes `parameters.yml` and produces agency-tailored OSCAL.
- [ ] **CNT-004** [P1] KSI evaluation engine + seed templates (identity, telemetry, compliance)
      Paths: `src/uiao/ksi/evaluations/`, `src/uiao/rules/` (KSI rule library)
      Done-when: three evaluation templates land and execute against fixture data.
- [ ] **CNT-005** [P1] Populate empty schema subdirs
      Paths: `src/uiao/schemas/{ksi,udc,uiao-api,substrate-manifest,workspace-contract,adapter-registry}/`
      Done-when: each directory contains at least one real JSON Schema (no more `.gitkeep`-only dirs).
- [ ] **CNT-006** [P1] Compliance enforcement policy file
      Path: `src/uiao/canon/compliance/fedramp-moderate-baseline.yaml`
      Done-when: a real policy file exists under `src/uiao/canon/compliance/` and is referenced by validators.
- [ ] **CNT-007** [P2] Canonical OSCAL component definition (data artifact)
      Path: `src/uiao/canon/oscal/uiao-component-definition.json`
      Done-when: artifact validates against OSCAL 1.3 schema in CI.
- [ ] **CNT-008** [P2] Evidence-ingestion schema (uuid, control-id, timestamp, source, confidence)
      Path: `src/uiao/schemas/uiao-api/evidence-ingestion.json`
      Done-when: schema is draft-2020-12 valid and a fixture payload passes validation in CI.
- [ ] **CNT-009** [P2] Telemetry normalization schema referenced by KSI rules
      Path: `src/uiao/schemas/uiao-api/telemetry-normalization.json`
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
- [x] **CI-012** [P0] Fix `mypy.yml` path filters and install scope (workflow currently never runs against impl code)  ✓ 2026-05-03 — misdiagnosed; closed without action
      Path: `.github/workflows/mypy.yml`
      Closure (2026-05-03): added in PR #300 against the assumption that `impl/` was a separate directory. ADR-032 / PR #111 had already collapsed `core/` + `impl/` into a single flat package; the original `mypy.yml` (`paths: src/uiao/**/*.py`, install at root) is correct for that layout. The attempted fix in PR #301 broke the workflow by pointing `working-directory: impl` at a directory that does not exist; PR #301 closed without merge. Whether `mypy.yml` actually exercises the codebase on a Python-touching PR remains tracked by **CI-001**.

## INT — Integration / Packaging (legacy — mostly superseded by ADR-032)

- [x] **INT-001** [P0] Pin `uiao` dependency in `impl/pyproject.toml` (path dep now, package dep once core is published)  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Path: `impl/pyproject.toml` (no longer exists; single root `pyproject.toml` is the only manifest).
      Closure (2026-05-03): the entire premise is moot. ADR-032 collapsed `core/` + `impl/` into a single package; `src/uiao/config.py:_resolve_canon_root()` already implements a 3-tier lookup (env var → `importlib.resources.files("uiao.canon")` → None); canon ships in the installed wheel via `[tool.setuptools.package-data]`. No separate pin is needed.
- [x] **INT-002** [P0] Root `pyproject.toml` with `uv` workspace binding core + impl  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Path: `pyproject.toml` (single manifest at root since ADR-032; no workspace needed).
      Closure (2026-05-03): irrelevant under the flat-package layout. `pip install -e .` (or `uv sync`) at repo root installs the sole package. Workspaces are a multi-package construct with no application here.
- [x] **INT-003** [P1] Resolve version-skew policy between core (0.2.0) and impl (0.2.1)  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Closure (2026-05-03): no skew possible under a single-package layout. Version is set in `src/uiao/__version__.py` and consumed dynamically by `pyproject.toml`.
- [x] **INT-004** [P2] Cross-folder Makefile targets (`make test` → core+impl pytest; `make install-dev` → editable install of both)  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Path: `Makefile` (at repo root).
      Closure (2026-05-03): single package; the existing root `Makefile` is sufficient. Dual-tree concerns dissolved with ADR-032.
- [x] **INT-005** [P2] Migrate `core/` to an installable Python package shipping canon data (Option A from INT-001 decision memo)  ✓ 2026-05-03 — never materialised; superseded retroactively by ADR-032
      Closure (2026-05-03): added in PR #300 against the assumption that `core/` was a separate, not-yet-installable package. ADR-032 (which had already landed) made `core/` part of the single `uiao` package, with canon shipped via `[tool.setuptools.package-data]`. The migration described here is exactly what ADR-032 already did.

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
