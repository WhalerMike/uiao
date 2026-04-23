# AGENTS.md — UIAO Consolidated Monorepo

> Repo-root control surface for IDE agent integration. This file is the single agent entry point for the consolidated `src/uiao/` package.
>
> **Naming note:** the filename is `AGENTS.md` — the emerging tool-neutral convention recognized by Claude Code, OpenAI Codex, and other IDE agents. A thin `CLAUDE.md` stub at the repo root still resolves to this content for tools looking specifically for `CLAUDE.md`.

## Repository identity

- **Name:** `WhalerMike/uiao`
- **Purpose:** Unified Identity-Addressing-Overlay Architecture — a FedRAMP-Moderate governance substrate with drift-detected canon, schema-enforced adapters, and OSCAL-native evidence pipelines.
- **Status:** pre-1.0; `main` is the primary development branch.
- **Cloud boundary:** GCC-Moderate (Microsoft 365 SaaS only). Amazon Connect Contact Center is the sole Commercial exception.

## Module topology

Declared machine-readably in [`src/uiao/canon/substrate-manifest.yaml`](src/uiao/canon/substrate-manifest.yaml) (UIAO_200):

| Module | Role | Contents |
|---|---|---|
| [`src/uiao/`](src/uiao/) | **Package** — the single installable `uiao` Python distribution. | Canon (`canon/`), rules (`rules/`), schemas (`schemas/`), KSI library (`ksi/`), adapters (`adapters/`), IR (`ir/`), CLI (`cli/`), governance, evidence, oscal, ssp, substrate walker, orchestrator, etc. |
| [`tests/`](tests/) | Test suite | ~1000+ tests: unit, integration, adapter conformance, substrate drift. |
| [`docs/`](docs/) | Derived documentation | Articles, guides, narratives, Quarto site. Every published doc traces provenance to canon under `src/uiao/canon/`. |
| [`scripts/`](scripts/) | Maintenance scripts | Validators, canon-sync, doc generators, one-shot tooling. |
| [`inbox/`](inbox/) | Scratch surface | Agent-authored drafts. Nothing here is canon. |
| [`.github/workflows/`](.github/workflows/) | CI | Schema validation, pytest, substrate-drift, mypy (non-blocking), ruff, quarto, link-check, release. |

Install: `pip install -e .` from the repo root; the `uiao` CLI entry point is [`uiao.cli.app:app`](src/uiao/cli/app.py).

## Operating principles (substrate-wide)

1. **SSOT** — every claim has exactly one canonical source under `src/uiao/canon/`. All other representations are provenance-anchored pointers.
2. **Canon-anchored evidence** — every artifact the substrate produces cites the canon document ID and version it derives from.
3. **Dual-axis adapter taxonomy** — every adapter declares `class` (modernization | conformance) × `mission-class` (identity | telemetry | policy | enforcement | integration) per UIAO_003.
4. **Schema-first governance** — five JSON Schemas under `src/uiao/schemas/` validate every registry, manifest, and frontmatter edit in CI.
5. **Drift is explicit** — five-class taxonomy (`DRIFT-SCHEMA`, `DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`) defined in [`docs/docs/16_DriftDetectionStandard.qmd`](docs/docs/16_DriftDetectionStandard.qmd).
6. **Version isolation** — no references to any previous version in active canon context; ADRs are append-only with supersession markers.

## Key artifacts

| Concern | Artifact | Purpose |
|---|---|---|
| Module declaration | `src/uiao/canon/substrate-manifest.yaml` (UIAO_200) | What modules exist, their roles, drift-scan scope |
| Workspace binding | `src/uiao/canon/workspace-contract.yaml` (UIAO_201) | Local-root env var, module paths, build-output paths |
| Document registry | `src/uiao/canon/document-registry.yaml` | UIAO_NNN allocations across the canon |
| Modernization adapters | `src/uiao/canon/modernization-registry.yaml` | Change-making adapters (10 entries) |
| Conformance adapters | `src/uiao/canon/adapter-registry.yaml` | Read-only adapters (ScubaGear etc.) |
| Adapter schema | `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` | Constrains both registries |
| Metadata schema | `src/uiao/schemas/metadata-schema.json` | Constrains canon document frontmatter |
| Substrate schema | `src/uiao/schemas/substrate-manifest/substrate-manifest.schema.json` | Constrains UIAO_200 |
| Workspace schema | `src/uiao/schemas/workspace-contract/workspace-contract.schema.json` | Constrains UIAO_201 |

## Substrate walker (the tool agents run first)

```bash
uiao substrate walk              # structured report
uiao substrate walk --json       # machine-readable
uiao substrate drift             # exit-code-only summary (CI-friendly)
```

Source: [`src/uiao/substrate/walker.py`](src/uiao/substrate/walker.py).

Emits `DRIFT-SCHEMA` (module paths exist) and `DRIFT-PROVENANCE` (registry docs resolve) findings.

## CI stack (all live at repo-root `.github/workflows/`)

| Workflow | Trigger | Blocking? |
|---|---|---|
| `schema-validation.yml` | Canon / schemas PRs | ✅ |
| `pytest.yml` | `src/uiao/**`, `tests/**`, `pyproject.toml` | ✅ substrate (fast); 🟡 full suite (soft-fail) |
| `substrate-drift.yml` | Canon / substrate / workspace PRs | ✅ |
| `metadata-validator.yml` | `src/uiao/canon/**/*.md` + metadata schema | ✅ |
| `quarto.yml` | `docs/**` PRs | ✅ render; deploy on main |
| `adapter-conformance.yml` | `src/uiao/adapters/**` + adapter tests | ✅ |
| `ruff.yml` | Python PRs | 🟡 soft-fail (pending lint-debt burn-down) |
| `mypy.yml` | Python PRs | 🟡 soft-fail (never enforced pre-ADR-032) |
| `link-check.yml` | `*.md` / `*.qmd` PRs + weekly | 🟡 soft-fail |
| `release.yml` | Tag `v*.*.*` | — |

> **Lint / type / test debt:** when the `ruff.yml`, `mypy.yml`, and `pytest.yml` path filters were repaired post-ADR-032, 230 pre-existing ruff findings, an unenforced mypy baseline, and an undeclared `fastapi` test dependency (collection error in `tests/test_auditor_api.py`) all surfaced. All three full-suite gates are marked `continue-on-error: true` until the debt is cleared; they still publish findings on every PR. The fast substrate job in `pytest.yml` remains blocking — it catches real package-integrity breakage.

## Commit convention

```
<verb>: <module-or-area> — <description>
```

Common `<verb>`s: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`. Use a scope prefix (e.g. `feat(adapters/bluecat):`) when it clarifies blast radius. Cross-cutting commits are permitted — describe the cross-cut in the body.

## Operating rules

- **Canon edits** → `src/uiao/canon/`, plus a UIAO_NNN entry in `document-registry.yaml` if the document is new. Doctrine changes require an ADR under `src/uiao/canon/adr/`.
- **New CLI commands** ship with happy-path + failure-mode tests in the same PR.
- **Adapters** go under `src/uiao/adapters/` and register in `src/uiao/canon/adapter-registry.yaml` (conformance) or `modernization-registry.yaml` (modernization). Every adapter declares `class` × `mission-class` per UIAO_003.
- **Canon reads at runtime** use `importlib.resources` against `uiao.canon` / `uiao.rules` / `uiao.schemas`, never hardcoded filesystem paths.

## History

The monorepo was consolidated from four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) on 2026-04-17 with full history preserved ([ADR-028](src/uiao/canon/adr/adr-028-monorepo-consolidation-gos-integration.md)). The `uiao-gos` federal/commercial firewall was retired in that pass; its directory-migration adapters (`bluecat-address-manager`, `infoblox`) are now canonical modernization adapters.

On 2026-04-20 the hybrid `core/` + `impl/` + partial `src/` tree was flattened into a single `src/uiao/` package with `pip install -e .` packaging and full runtime deps declared ([ADR-032](src/uiao/canon/adr/adr-032-single-package-consolidation.md)). Everything that used to import from `uiao.impl.*` now imports from `uiao.*`; canon ships inside the package via `importlib.resources`.

## Writing patterns

- **Chunked writes for long content (>≈150 lines), regardless of filetype.** Applies equally to `.md`, `.qmd`, `.py`, `.yaml`, and `.json`. Write the file in 3–5 logical sections using an initial `Write` for section 1 then `Edit` calls to append subsequent sections via unique anchor text. Length — not filetype — determines when to chunk.
    - **Why**: stream-idle timeouts truncate single-Write operations on multi-hundred-line files; each chunk persists as it lands, so a timeout mid-document costs at most one section, not the whole file. Also produces reviewable increments.
    - **Ordering for Python**: imports → constants/dataclasses → utilities → higher-level functions → `main` / CLI. Each chunk depends only on what's already above it.
    - **Ordering for Markdown/Quarto**: frontmatter → overview → principles → body sections → appendices → references. Each chunk is self-contained prose; dependencies are by narrative flow, not execution.
- **Session memory is ephemeral.** Within-session pledges ("I'll use this pattern from now on") do not persist across session boundaries or context compactions. Durable behavior lives in this file — if a pattern is worth adopting, commit it here.

## Agent usage notes

- **Always run `uiao substrate walk` first** on a fresh clone to validate the tree is intact.
- **Canon changes belong under `src/uiao/canon/`.** If a change would create a new canonical governance document, make the PR against `src/uiao/canon/` with a UIAO_NNN allocation in `document-registry.yaml`.
- **Read the relevant ADR before touching doctrinal canon.** ADR-028 retires the firewall; ADR-025 §D7 is superseded; ADR-027 defines adapter retirement.
- **CI is comprehensive.** 6 blocking workflows will catch schema violations, drift, and test regressions before merge.

## Repository Invariants

These rules define how the monorepo is organized and why. Violating any of them breaks either the CLI, the governance model, or the build pipeline. Changes that cross an invariant require an ADR and human review, not a quick fix.

### Directory intent

`src/uiao/` is the **single installable Python package** — runtime code, canon, schemas, rules, KSI, adapters, CLI. Post-ADR-032 there is no sibling `core/` or `impl/` tree: every concern previously split across those directories now lives under `src/uiao/<subpackage>/`. Canon (under `src/uiao/canon/`) is the governance authority — SSOT, ADRs, schemas, rules, KSI, specs, registries. Once canon is production-frozen it is protected: changes require a canon-change ADR and governance-board review. Runtime code consumes canon via `importlib.resources`, never by reaching outside its package.

`tests/` is the **single test suite** — unit, integration, adapter conformance, substrate drift. Authoritative; previously split between `impl/tests/` and `core/tests/`, now consolidated.

`docs/` is **human-readable documentation source only**. Source extensions: `.qmd`, `.md`, `.yml`, `.yaml`, `.puml`. Binary build output (`.docx`, `.pdf`, `.png`, `.epub`, `.pptx`) is **generated**, not authored, and should live in build output directories (`docs/_site/`, `docs/publications/`) that are either gitignored or release-pinned. Never commit binary output into the source tree alongside source files.

`scripts/` is **workspace tooling** — bootstrap, link check, schema validators, reorganization helpers. Short-lived; not imported at runtime.

`inbox/` is **draft staging** — content that isn't canonized yet. Promote to `src/uiao/canon/` or `docs/` when ready.

`deploy/windows-server/` holds the **Windows IIS deployment artifacts** (uvicorn `run.py`, `web.config`, `requirements-windows.txt`) for the FastAPI service in `src/uiao/api/`. Referenced from `src/uiao/api/app.py`.

### Technical invariants

**I1. `src/uiao/` is a single regular package.**
One `__init__.py` at `src/uiao/` level; one distribution named `uiao`; one import root. The pre-ADR-032 PEP 420 namespace split between `src/uiao/*` and `impl/src/uiao/impl/*` is retired — there is no `uiao.impl` subpackage anymore. Imports are always `from uiao.<subpackage> import …`.

**I2. Single CLI entry point: `uiao.cli.app:app`.**
The `uiao` console script registered by `pyproject.toml` resolves directly to `src/uiao/cli/app.py`. No bridge module, no lazy-import indirection, no `sys.path` manipulation. If a CLI subcommand fails on import, debug the subcommand's own imports — not the entry point.

**I3. One `pyproject.toml`, one editable install.**
`pip install -e .` from the repo root installs everything: runtime code, canon, schemas, rules, KSI, adapters (shipped as package-data per the root `pyproject.toml`). There is no sibling `impl/pyproject.toml` and no install-order dance. Dev tooling: `pip install -e ".[dev]"`.

**I4. Canon is a read-only dependency of code.**
Code reads canon via `importlib.resources.files("uiao.canon")` and similar. Code must not write to canon, and must not assume canon is at a particular filesystem path — it may be packaged as resources inside an installed wheel.

**I5. Canon changes flow through the canon-change process.**
Adding, modifying, retiring, or superseding anything under `src/uiao/canon/` requires:

- A new `UIAO_NNN` allocation in `document-registry.yaml` (for new docs)
- A new ADR in `src/uiao/canon/adr/` (for doctrinal changes)
- Governance review

Direct commits that touch canon without an ADR reference are a governance drift signal.
