# AGENTS.md — UIAO Consolidated Monorepo

> Repo-root control surface for IDE agent integration. Three per-module `AGENTS.md` files (`core/AGENTS.md`, `docs/AGENTS.md`, `impl/AGENTS.md`) exist for module-scoped context; this file is the substrate-level entry point.
>
> **Naming note:** the filename is `AGENTS.md` — the emerging tool-neutral convention recognized by Claude Code, OpenAI Codex, and other IDE agents. Thin `CLAUDE.md` stubs remain at every location so tools looking specifically for `CLAUDE.md` still resolve to this content.

## Repository identity

- **Name:** `WhalerMike/uiao`
- **Purpose:** Unified Identity-Addressing-Overlay Architecture — a FedRAMP-Moderate governance substrate with drift-detected canon, schema-enforced adapters, and OSCAL-native evidence pipelines.
- **Status:** pre-1.0; `main` is the primary development branch.
- **Cloud boundary:** GCC-Moderate (Microsoft 365 SaaS only). Amazon Connect Contact Center is the sole Commercial exception.

## Module topology

Declared machine-readably in [`src/uiao/canon/substrate-manifest.yaml`](src/uiao/canon/substrate-manifest.yaml) (UIAO_200):

| Module | Role | Canon consumer | Contents |
|---|---|---|---|
| [`core/`](core/) | **Authority** | no | Schemas, canon documents, control library, ADRs, enforcement tooling. Single source of truth. |
| [`docs/`](docs/) | Consumer | yes | Articles, guides, narratives, Quarto site. Every doc traces provenance to `core/`. |
| [`impl/`](impl/) | Consumer | yes | Python CLI, generators, adapters, substrate walker, pytest suite. |

Workspace resolution: `$UIAO_WORKSPACE_ROOT` environment variable, never a hardcoded path. Enforced by [`impl/.claude/rules/canon-consumer.md`](impl/.claude/rules/canon-consumer.md).

## Operating principles (substrate-wide)

1. **SSOT** — every claim has exactly one canonical source in `core/`. All other representations are provenance-anchored pointers.
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

Source: [`impl/src/uiao/impl/substrate/walker.py`](impl/src/uiao/impl/substrate/walker.py).

Emits `DRIFT-SCHEMA` (module paths exist) and `DRIFT-PROVENANCE` (registry docs resolve) findings.

## CI stack (all live at repo-root `.github/workflows/`)

| Workflow | Trigger | Blocking? |
|---|---|---|
| `schema-validation.yml` | Canon / schemas PRs | ✅ |
| `pytest.yml` | `impl/**` PRs | ✅ (substrate + full impl) |
| `substrate-drift.yml` | Substrate / registry PRs | ✅ |
| `metadata-validator.yml` | Canon doc PRs | ✅ |
| `quarto.yml` | `docs/**` PRs | ✅ render; deploy on main |
| `ruff.yml` | `impl/**` PRs | ✅ |
| `link-check.yml` | `*.md` / `*.qmd` PRs + weekly | 🟡 soft-fail |
| `release.yml` | Tag `v*.*.*` | — |

## Commit convention (across the monorepo)

```
[UIAO-CORE] <verb>: <artifact-id> — <description>    # core/ changes
[UIAO-DOCS] <verb>: <artifact-id> — <description>    # docs/ changes
[UIAO-IMPL] <verb>: <module> — <description>         # impl/ changes
CI: <description>                                     # .github/ changes
```

Cross-module commits are permitted but must describe the cross-cutting nature in the body.

## Rules loaded automatically

- [`impl/.claude/rules/canon-consumer.md`](impl/.claude/rules/canon-consumer.md) — `impl/` is a canon consumer; no hardcoded canon paths
- [`impl/.claude/rules/test-coverage.md`](impl/.claude/rules/test-coverage.md) — every CLI command needs happy-path + failure-mode tests

## History

The monorepo was consolidated from four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) on 2026-04-17 with full history preserved. The `uiao-gos` federal/commercial firewall was retired per [ADR-028](src/uiao/canon/adr/adr-028-monorepo-consolidation-gos-integration.md); its directory-migration adapters (`bluecat-address-manager`, `infoblox`) are now canonical modernization adapters. See [`docs/narrative/governance-os-directory-migration.md`](docs/narrative/governance-os-directory-migration.md) for the substrate-aligned narrative.

## Writing patterns

- **Chunked writes for long content (>≈150 lines), regardless of filetype.** Applies equally to `.md`, `.qmd`, `.py`, `.yaml`, and `.json`. Write the file in 3–5 logical sections using an initial `Write` for section 1 then `Edit` calls to append subsequent sections via unique anchor text. Length — not filetype — determines when to chunk.
    - **Why**: stream-idle timeouts truncate single-Write operations on multi-hundred-line files; each chunk persists as it lands, so a timeout mid-document costs at most one section, not the whole file. Also produces reviewable increments.
    - **Ordering for Python**: imports → constants/dataclasses → utilities → higher-level functions → `main` / CLI. Each chunk depends only on what's already above it.
    - **Ordering for Markdown/Quarto**: frontmatter → overview → principles → body sections → appendices → references. Each chunk is self-contained prose; dependencies are by narrative flow, not execution.
- **Session memory is ephemeral.** Within-session pledges ("I'll use this pattern from now on") do not persist across session boundaries or context compactions. Durable behavior lives in this file — if a pattern is worth adopting, commit it here.

## Agent usage notes

- **Always run `uiao substrate walk` first** on a fresh clone to validate the tree is intact.
- **Canon changes belong in `core/`.** If a change would create a new canonical governance document, make the PR against `src/uiao/canon/` with a UIAO_NNN allocation.
- **Read the relevant ADR before touching doctrinal canon.** ADR-028 retires the firewall; ADR-025 §D7 is superseded; ADR-027 defines adapter retirement.
- **CI is comprehensive.** 6 blocking workflows will catch schema violations, drift, and test regressions before merge.

## Repository Invariants

These rules define how the monorepo is organized and why. Violating any of them breaks either the CLI, the governance model, or the build pipeline. Changes that cross an invariant require an ADR and human review, not a quick fix.

### Directory intent

`src/uiao/` is the **Core Canon + CLI bridge**. Canon is the governance authority — SSOT, ADRs, schemas, rules, KSI, specs, registries, image registry. Once canon is production-frozen, it is protected: changes require a canon-change ADR and governance-board review. Runtime code consumes canon as resources, never by reaching outside its package.

`impl/` is the **Python implementation layer** — adapters, collectors, governance engine, OSCAL generation, IR transforms, tests. Everything that executes at runtime lives here. Canon is a read target; impl is a change surface.

`core/` is **non-Python reference material** — architecture docs, runtime config JSON, script tooling, compliance reference PDFs. No Python packages live here.

`docs/` is **human-readable documentation source only**. Source extensions: `.qmd`, `.md`, `.yml`, `.yaml`, `.puml`. Binary build output (`.docx`, `.pdf`, `.png`, `.epub`, `.pptx`) is **generated**, not authored, and should live in build output directories (`docs/_site/`, `docs/publications/`) that are either gitignored or release-pinned. Never commit binary output into the source tree alongside source files.

`scripts/` is **workspace tooling** — bootstrap, link check, schema validators, reorganization helpers. Short-lived; not imported at runtime.

`inbox/` is **draft staging** — content that isn't canonized yet. Promote to `src/uiao/canon/` or `docs/` when ready.

### Technical invariants

**I1. `src/uiao/` is a PEP 420 namespace package.**
No `__init__.py` at `src/uiao/` level. This lets `src/uiao/*` and `impl/src/uiao/impl/*` coexist under the `uiao` namespace at import time. Adding a `src/uiao/__init__.py` — even an empty one — captures the namespace and causes `ModuleNotFoundError: No module named 'uiao.impl'`.

**I2. `src/uiao/cli.py` is a lazy-import bridge.**
The import `from uiao.impl.cli.app import app` lives inside `main()`, not at module top level. This defers resolution until after sys.path is fully populated. Do not rewrite it to eager-import at module level, and do not add `sys.path` manipulation — if `uiao.impl` is not resolving, the fix is elsewhere (I1 or I3), not in `cli.py`.

**I3. Install order: impl first, root last.**
Both `pyproject.toml` (root) and `impl/pyproject.toml` register a `uiao` console script. Last install wins the entry-point collision; the root bridge must win. Canonical install sequence:

    pip install -e impl/
    pip install -e .

Installing in the other order makes `impl`'s direct `uiao.impl.cli.app:app` entry point win, which eagerly imports and fails the moment I1 is ever violated.

**I4. Canon is a read-only dependency of code.**
Code reads canon via `importlib.resources.files("uiao.canon")` and similar. Code must not write to canon, and must not assume canon is at a particular filesystem path — it may be packaged as resources inside an installed wheel.

**I5. Canon changes flow through the canon-change process.**
Adding, modifying, retiring, or superseding anything under `src/uiao/canon/` requires:

- A new `UIAO_NNN` allocation in `document-registry.yaml` (for new docs)
- A new ADR in `src/uiao/canon/adr/` (for doctrinal changes)
- Governance review

Direct commits that touch canon without an ADR reference are a governance drift signal.
