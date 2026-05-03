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

- [ ] **TST-001** [P0] Verify `.coveragerc` (or `[tool.coverage]` in `pyproject.toml`) covers `src/uiao` correctly post-ADR-032
      Path: `.coveragerc` at repo root, or `[tool.coverage.run]` table in `pyproject.toml`
      Done-when: `source = src/uiao`, omit patterns are sensible, `coverage run -m pytest` reports for the single canonical tree.
      Note (2026-05-03): the original "wrong package" complaint (`src/uiao_core`) is from the pre-ADR-032 era. First sub-task: confirm current coverage config and decide whether this is already done or still needed.
- [ ] **TST-002** [P0] Populate empty test file `tests/test_briefing.py` (was 2 bytes pre-consolidation)
      Path: `tests/test_briefing.py`
      Done-when: at least one real test passes and the briefing generator has coverage.
      Note (2026-05-03): verify the file still exists / is still empty post-ADR-032 before opening a PR.
- [ ] **TST-003** [P1] Provide a reusable adapter conformance test base (`BaseAdapterTest`) for adapter unit tests
      Pattern: `from uiao.testing.conformance import BaseAdapterTest` (or similar internal location)
      Paths: `src/uiao/testing/conformance.py` (new) or `tests/conformance/__init__.py`
      Done-when: at least one adapter test inherits `BaseAdapterTest` and exercises the canon contract from CNT-001.
- [ ] **TST-004** [P1] Unit tests for canon validators (`metadata_validator`, `sync_canon`, `drift_detector`, `dashboard_exporter`, `appendix_indexer`)
      Path: `tests/tools/test_validators.py` (verify validators still live in `tools/` or under `src/uiao/`)
      Done-when: each validator has happy-path + failure-path coverage.
- [ ] **TST-005** [P1] E2E pipeline test: schema change → code-gen → adapter conformance → OSCAL output
      Path: `tests/e2e/test_schema_to_oscal.py` (new)
      Done-when: mutating a fixture schema changes the generated OSCAL deterministically and the test catches it.
- [ ] **TST-006** [P2] Coverage gate (≥80%) + artifact upload
      Paths: `.github/workflows/pytest.yml` (add coverage step), `.coveragerc` or `[tool.coverage]` in `pyproject.toml`
      Done-when: CI fails below threshold; coverage HTML/XML uploaded as an artifact.

## CI — CI / Security

- [ ] **CI-001** [P0] Verify `.github/workflows/mypy.yml` actually exercises the codebase on Python-touching PRs
      Path: `.github/workflows/mypy.yml` (exists since 2026-04-18 follow-up; current path filter `src/uiao/**/*.py` is correct for the flat layout).
      Done-when: a PR that touches `src/uiao/**/*.py` triggers the Mypy job; the job runs `pip install -e .[dev]` and `mypy src/uiao` from repo root; new type errors fail the check.
      Note (2026-05-03): closure of CI-012 verified the workflow file is shaped correctly for the flat layout. What's still outstanding is confirming the job actually runs against real Python changes — a small smoke PR adding a no-op type annotation in `src/uiao/` should answer this in one CI cycle.
- [ ] **CI-002** [P1] CodeQL SAST workflow
      Path: `.github/workflows/codeql.yml`
      Done-when: CodeQL runs weekly + on PR; findings surface in the Security tab.
- [ ] **CI-003** [P1] Dependency-review workflow
      Path: `.github/workflows/dependency-review.yml`
      Done-when: PRs changing `pyproject.toml` / `uv.lock` get a diff review with license + vuln flags.
- [ ] **CI-004** [P1] actionlint workflow — validate all workflow YAML against schema
      Path: `.github/workflows/actionlint.yml`
      Done-when: actionlint runs on PRs that touch `.github/workflows/**`.
- [x] **CI-005** [P1] Monorepo path filters on `pytest.yml` + `metadata-validator.yml` so core-only changes skip impl pytest (and vice versa)  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Closure (2026-05-03): the two-tree split that motivated separate path filters no longer exists. A successor item ("scope pytest to source/test changes only, skip pure-docs PRs") may be worth opening if pytest currently runs on docs PRs needlessly — out of scope for this rewrite.
- [ ] **CI-006** [P2] Enable native GitHub secret scanning + push protection; add trufflehog pre-commit hook
      Paths: `.pre-commit-config.yaml`, repo settings
      Done-when: secret-scanning is enabled repo-wide and trufflehog runs locally on commit.
- [ ] **CI-007** [P2] Nightly integration workflow (full E2E suite on schedule + post-merge)
      Path: `.github/workflows/nightly-integration.yml` (new)
      Done-when: workflow runs on cron + on push to `main` and exercises the full pipeline (canon → adapter conformance → OSCAL → KSI evaluation) against fixture data.
- [x] **CI-008** [P2] Surface `impl/.github/workflows/adapter-conformance.yml` and `acceptance-tests.yml` at repo root so they gate PRs  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Closure (2026-05-03): both workflows now live at `.github/workflows/adapter-conformance.yml` and `.github/workflows/acceptance-tests.yml` at repo root after ADR-032. Whether they are configured as **required** status checks (vs. just running) is a branch-protection / repo-settings question — open a separate item if that's still outstanding.
- [x] **CI-009** [P2] Consolidate duplicate link-check workflows (repo-root lychee vs impl PowerShell)  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Closure (2026-05-03): no `impl/` directory exists; only `.github/workflows/link-check.yml` at repo root remains. The PowerShell variant was removed as part of ADR-032.
- [x] **CI-010** [P1] Retire stale `impl/.github/workflows/ci.yml`  ✓ 2026-04-20 — superseded by ADR-032 / PR #111
      Closure (2026-05-03): the entire `impl/` tree was removed; the stale workflow file with it. The root `.github/workflows/pytest.yml` is the sole pytest workflow.
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

- `AGENTS.md`, `README.md`, `CLAUDE.md` (root) — agent + repo entry points.
- `pyproject.toml` (root) — single-package layout, dependencies, dev extras, mypy/ruff config.
- `src/uiao/canon/adr/` — ADRs (ADR-032 documents the consolidation; ADR-046 enforces CLI command structure).
- `src/uiao/canon/adapter-registry.yaml` — current adapter manifest (source of truth for which adapters exist).
- `src/uiao/config.py` — `Settings._resolve_canon_root()` 3-tier canon resolver.
- `src/uiao/adapters/` — adapter implementations (BaseAdapter location TBD per **CNT-001** note).
- `src/uiao/orchestrator/` — wiring seam for **ADP-002** / **ADP-004**.
- `.github/workflows/*.yml` — existing CI surface (no nested workflow trees).
- `Makefile` — local/CI parity targets.

## Existing Reusable Utilities (Do Not Re-build)

- `tools/metadata_validator.py`, `sync_canon.py`, `drift_detector.py`, `dashboard_exporter.py`, `appendix_indexer.py` — validators wired into CI (verify exact location under `tools/` or `src/uiao/tools/`).
- `scripts/validate_{canon,schemas,oscal}.py` — one-shot validators (verify location).
- `scripts/bootstrap.sh` — dev env setup (pre-commit, editable installs, pyright cache).
- `scripts/check-links.ps1` — link crawler used by `make check-links`.
- `.github/workflows/release.yml` — already publishes wheel + CycloneDX SBOM + sigstore.
- `.github/workflows/ruff.yml` — already lints `src/uiao`.

---

## Completed

_Closed items stay in their workstream section above (checkbox flipped to `[x]`, completion line appended). This section intentionally stays short — it is a future aggregator once the log grows long enough to warrant a summary._
