---
title: "ADR-029: Substrate v1 Ready for Release"
adr: "ADR-029"
status: ACCEPTED
date: "2026-04-17"
deciders: ["WhalerMike"]
extends: ["ADR-028"]
---

# ADR-029: Substrate v1 Ready for Release

## Status

ACCEPTED

## Context

Between ADR-028 (2026-04-17 morning) and this ADR (same day, evening), the substrate was extensively operationalized. ADR-028 described the *decision* to dissolve `uiao-gos` and consolidate into a monorepo; it did not capture the complete set of operational outcomes that followed. Those outcomes need to be canonically recorded so future readers — human and agent — can reconstruct what "substrate v1" comprises without reading ~55 PR descriptions.

This ADR ratifies the state of the substrate as of 2026-04-17 end-of-day and declares it ready for the first tagged release (`v0.2.0`).

## Decision

The UIAO substrate is **ready for its first release** under the following closed artifact set:

### 1. Governance artifacts (canon)

- **`UIAO_200` Substrate Manifest** (`core/canon/substrate-manifest.yaml`) — declares the 3 modules (`core/`, `docs/`, `impl/`), their roles, canon-consumer relationships, and the drift-scan scope (`DRIFT-SCHEMA`, `DRIFT-PROVENANCE`).
- **`UIAO_201` Workspace Contract** (`core/canon/workspace-contract.yaml`) — declares the local-to-remote binding via `$UIAO_WORKSPACE_ROOT`, module paths, drift-scan roots, and enumerated build-output paths.
- **`UIAO_121–UIAO_124`** — four adapter-framework specs renumbered from slug-style ids and registered in `document-registry.yaml`.
- **ADR-028** retires the `uiao-gos` federal/commercial firewall (superseding ADR-025 §D7).
- **31 total canon documents** registered in `document-registry.yaml`.

### 2. Schema infrastructure

Four JSON Schemas constrain every registered canon object:

- `core/schemas/adapter-registry/adapter-registry.schema.json` (Draft-07) — both adapter registries
- `core/schemas/metadata-schema.json` (Draft 2020-12) — canon document frontmatter
- `core/schemas/substrate-manifest/substrate-manifest.schema.json` (Draft 2020-12) — UIAO_200
- `core/schemas/workspace-contract/workspace-contract.schema.json` (Draft 2020-12) — UIAO_201

### 3. Adapter posture

`core/canon/modernization-registry.yaml` — 10 entries, 9 active:

| Adapter | Status | Phase |
|---|---|---|
| `entra-id` | active | phase-1 |
| `m365` | active | phase-1 |
| `service-now` | active | phase-1 |
| `palo-alto` | active | phase-1 |
| `scuba` | active | phase-1 |
| `terraform` | active | phase-1 |
| `cyberark` | active | phase-1 *(promoted 2026-04-17)* |
| `infoblox` | active | phase-1 *(promoted 2026-04-17)* |
| `bluecat-address-manager` | active | phase-1 *(created 2026-04-17 from gos integration)* |
| `mainframe` | reserved | phase-planning *(z/OS Connect infrastructure pending)* |

All 10 validate against `adapter-registry.schema.json` with canonical invariants uniformly applied: `gcc-boundary: gcc-moderate`, `ssot-mutation: never`, `certificate-anchored: true`, `object-identity-only: true`.

### 4. Runtime tooling

- **Substrate Walker** (`impl/src/uiao/impl/substrate/walker.py`) — detects `DRIFT-SCHEMA` + `DRIFT-PROVENANCE` at rest. Exposed via `uiao substrate walk` / `uiao substrate drift` with 10 passing tests.
- **Drift Engine** (`impl/src/uiao/impl/governance/drift.py`) — per-resource runtime drift classification. Unchanged since the consolidation but now the sole drift implementation (`directory_migration/drift/drift_engine.py` retired).
- **Directory-migration reference code** under `impl/src/uiao/impl/directory_migration/adapters/ipam/` — four markdown reference docs pointed to by the IPAM adapter registry entries. Previous ARC-5 Python scaffolding (38 files, ~1,600 LOC of broken imports) retired.

### 5. CI stack

Seven live workflows at `.github/workflows/` — **six blocking**, one soft-fail:

| Workflow | Status | Trigger |
|---|---|---|
| `schema-validation.yml` | **blocking** | PRs touching `core/canon/**` or `core/schemas/**` |
| `pytest.yml` | **blocking** (substrate + full impl) | PRs touching `impl/**` |
| `substrate-drift.yml` | **blocking** | Substrate / registry PRs |
| `metadata-validator.yml` | **blocking** | Canon doc PRs |
| `quarto.yml` | **blocking** render; deploy on main | `docs/**` PRs |
| `ruff.yml` | **blocking** | `impl/**` PRs |
| `link-check.yml` | soft-fail | Any Markdown/Quarto PR + weekly cron |
| `release.yml` | tag-triggered | `v*.*.*` tag push — builds wheel + sdist, generates CycloneDX SBOM, sigstore signs all artifacts |
| `release-drafter.yml` | continuous | Every push to main + PR label change — maintains the draft release |

### 6. Repository infrastructure

- `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md` at repo root
- `.github/CODEOWNERS` auto-requesting `@WhalerMike` on canon + schema + adapter PRs
- `.github/dependabot.yml` (weekly, pip + github-actions)
- `.github/PULL_REQUEST_TEMPLATE.md` + 4 structured issue templates
- `.devcontainer/devcontainer.json` + `scripts/bootstrap.sh` + `.pre-commit-config.yaml`
- `.editorconfig` + `Makefile` (11 developer targets)
- `.lycheeignore` for link-check false positives
- `CHANGELOG.md` at repo root (pre-1.0 SemVer with breaking-change notice)
- `docs/docs/glossary.qmd` — canonical vocabulary page

### 7. Optimization outcomes

- **Monorepo consolidation** preserved **3,549 commits of history** from the four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`).
- **Working-tree reduction:** 128.9 MB from two pngquant passes; 160 MB from retiring tracked build artifacts; 795 KB from 4 junk text-file deletions. Total ~290 MB reduction.
- **Dead code retired:** 38 Python files / ~1,600 LOC of ARC-5 scaffolding (with broken imports) under `directory_migration/`; 3 stub duplicate provider adapters.
- **Canon drift retired:** 16 residual ruff errors fixed; 4 slug-style `document_id` values renumbered to proper `UIAO_NNN` entries; 10 mechanical stale-ref fixes across config/schema files.

## Consequences

**Positive.**

- **First release ready.** `v0.2.0` can be tagged with a coherent artifact surface, complete provenance, and signed attestations.
- **Contributor-ready.** A new developer can clone and reach productive state in under a minute (`bash scripts/bootstrap.sh`).
- **Canon-agent-ready.** The repo-root `CLAUDE.md` + per-module `CLAUDE.md` files + the canonical glossary give AI agents an unambiguous entry point.
- **Enforcement by default.** Six of seven CI gates are blocking. Schema violations, drift, test regressions, and canon-frontmatter errors all fail CI.

**Negative / tradeoffs.**

- **Link-check remains soft-fail.** Burning down the baseline requires the CI artifact to be triaged (follow-up PR).
- **Runtime drift classes `DRIFT-SEMANTIC`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`** are not yet implemented. Their home is `core/canon/specs/drift.md` (UIAO_110); implementation is genuine engineering out of scope for substrate v1.
- **The `mainframe` adapter** remains `reserved/phase-planning` pending z/OS Connect / MQ bridge infrastructure — not blocking v0.2.0 since it's a roadmap item, not a regression.

**Neutral.**

- **Pre-1.0 semantics.** Minor version bumps may carry breaking changes until `v1.0.0`. Documented in `CHANGELOG.md`.

## What "substrate v1" is NOT

To bound the scope of this ADR:

- It is **not** a claim that the adapters run end-to-end against live tenants. Each active adapter has at least scaffold tests, not integration-level production validation.
- It is **not** a FedRAMP ATO package. The artifacts are in place (OSCAL generators, KSI rules, control library) but a real ATO requires agency-side execution with a 3PAO.
- It is **not** feature-complete for runtime drift detection. See Consequences § negative.

## References

- ADR-028 — Monorepo consolidation and integration of `uiao-gos` (the preceding decision)
- ADR-025 §D7 — Federal/commercial firewall (superseded by ADR-028)
- `core/canon/substrate-manifest.yaml` (UIAO_200) — machine-readable module declaration
- `core/canon/workspace-contract.yaml` (UIAO_201) — machine-readable workspace binding
- `CHANGELOG.md` [Unreleased] — the PR-by-PR narrative of how substrate v1 came together
- `docs/docs/glossary.qmd` — canonical vocabulary
