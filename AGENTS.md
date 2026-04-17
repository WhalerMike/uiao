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

Declared machine-readably in [`core/canon/substrate-manifest.yaml`](core/canon/substrate-manifest.yaml) (UIAO_200):

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
4. **Schema-first governance** — five JSON Schemas under `core/schemas/` validate every registry, manifest, and frontmatter edit in CI.
5. **Drift is explicit** — five-class taxonomy (`DRIFT-SCHEMA`, `DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`) defined in [`docs/docs/16_DriftDetectionStandard.qmd`](docs/docs/16_DriftDetectionStandard.qmd).
6. **Version isolation** — no references to any previous version in active canon context; ADRs are append-only with supersession markers.

## Key artifacts

| Concern | Artifact | Purpose |
|---|---|---|
| Module declaration | `core/canon/substrate-manifest.yaml` (UIAO_200) | What modules exist, their roles, drift-scan scope |
| Workspace binding | `core/canon/workspace-contract.yaml` (UIAO_201) | Local-root env var, module paths, build-output paths |
| Document registry | `core/canon/document-registry.yaml` | UIAO_NNN allocations across the canon |
| Modernization adapters | `core/canon/modernization-registry.yaml` | Change-making adapters (10 entries) |
| Conformance adapters | `core/canon/adapter-registry.yaml` | Read-only adapters (ScubaGear etc.) |
| Adapter schema | `core/schemas/adapter-registry/adapter-registry.schema.json` | Constrains both registries |
| Metadata schema | `core/schemas/metadata-schema.json` | Constrains canon document frontmatter |
| Substrate schema | `core/schemas/substrate-manifest/substrate-manifest.schema.json` | Constrains UIAO_200 |
| Workspace schema | `core/schemas/workspace-contract/workspace-contract.schema.json` | Constrains UIAO_201 |

## Substrate walker (the tool agents run first)

```bash
uiao substrate walk              # structured report
uiao substrate walk --json       # machine-readable
uiao substrate drift             # exit-code-only summary (CI-friendly)
```

Source: [`impl/src/uiao_impl/substrate/walker.py`](impl/src/uiao_impl/substrate/walker.py).

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

The monorepo was consolidated from four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) on 2026-04-17 with full history preserved. The `uiao-gos` federal/commercial firewall was retired per [ADR-028](core/canon/adr/adr-028-monorepo-consolidation-gos-integration.md); its directory-migration adapters (`bluecat-address-manager`, `infoblox`) are now canonical modernization adapters. See [`docs/narrative/governance-os-directory-migration.md`](docs/narrative/governance-os-directory-migration.md) for the substrate-aligned narrative.

## Agent usage notes

- **Always run `uiao substrate walk` first** on a fresh clone to validate the tree is intact.
- **Canon changes belong in `core/`.** If a change would create a new canonical governance document, make the PR against `core/canon/` with a UIAO_NNN allocation.
- **Read the relevant ADR before touching doctrinal canon.** ADR-028 retires the firewall; ADR-025 §D7 is superseded; ADR-027 defines adapter retirement.
- **CI is comprehensive.** 6 blocking workflows will catch schema violations, drift, and test regressions before merge.
