---
document_id: UIAO_001
title: "UIAO Single Source of Truth (SSOT)"
version: "1.1"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-23"
boundary: "GCC-Moderate"
---

# UIAO Single Source of Truth (SSOT)

The UIAO SSOT is the authoritative origin for every identity, addressing,
enforcement, telemetry, and governance object handled by the substrate.
All other representations are **provenance-anchored pointers**, not copies.
SSOT is the foundation of the Governance OS, the root of the provenance
chain, and the baseline against which every Drift class is evaluated.

## Scope

This document defines what the SSOT **is**, where it **lives**, and how
runtime code is allowed to **consume** it. It does not enumerate every
canonical artifact — that inventory lives in the document registry
([`src/uiao/canon/document-registry.yaml`](document-registry.yaml)) and
the substrate manifest
([`src/uiao/canon/substrate-manifest.yaml`](substrate-manifest.yaml),
UIAO_200).

## Topology (post-ADR-032)

Canon ships as package data inside the single installable `uiao`
distribution rooted at `src/uiao/`. The authoritative layout is declared
by **UIAO_200 Substrate Manifest v2.0**:

| Canon surface | Path | Role |
|---|---|---|
| Canon documents | `src/uiao/canon/` | SSOT — governance artifacts, ADRs, specs, registries |
| Schemas | `src/uiao/schemas/` | Schema authority — JSON Schema (Draft-07 + 2020-12) |
| Rules | `src/uiao/rules/` | Canon-consumer rule + KSI rule library |
| KSI library | `src/uiao/ksi/` | Key Security Indicator evaluation data |

The pre-ADR-028 four-repo model (`uiao-core` / `uiao-docs` / `uiao-impl` /
`uiao-gos`) and the pre-ADR-032 three-module model (`core/` / `docs/` /
`impl/`) are both retired. See
[ADR-028](adr/adr-028-monorepo-consolidation-gos-integration.md),
[ADR-032](adr/adr-032-single-package-consolidation.md), and
[ADR-044](adr/adr-044-substrate-governance-realignment.md) for the
doctrinal history.

## Canon-consumer rule

Runtime code **must** resolve canon artifacts via
`importlib.resources.files("uiao.canon") / ...` (or equivalent for
`uiao.schemas`, `uiao.rules`, `uiao.ksi`). This guarantees:

- Canon is addressable from any CWD inside the installed package.
- Canon survives installation from a built wheel.
- Canon is **read-only at runtime** — the only writers are the
  canon-change process (human PR + ADR) and scripts under `scripts/`
  explicitly marked as canon-edit tooling.

Hardcoded absolute paths, `Path(__file__).parent / "../canon/..."`-style
reach-arounds, and sibling-checkout fallbacks are forbidden outside test
fixtures. The full rule is at
[`src/uiao/rules/canon-consumer.md`](../rules/canon-consumer.md).

## Provenance chain

Every artifact the substrate produces cites the canon document ID and
version it was derived from:

- Derived artifacts (OSCAL bundles, SSPs, reports, exports) carry a
  `provenance:` block with `source`, `version`, `derived_at`, `derived_by`
  (metadata schema at
  [`src/uiao/schemas/metadata-schema.json`](../schemas/metadata-schema.json)).
- Canon documents with `classification: DERIVED` require provenance;
  `classification: CANONICAL` documents do not derive from anything and
  are leaves of the chain.
- Cryptographic anchoring uses SHA-256 over canonical-JSON-serialized
  claim content; the image pipeline anchors additional PNG bytes hashes
  (UIAO_202).

## Drift baseline

The five-class drift taxonomy defined in
[`docs/docs/16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd)
is evaluated against SSOT:

| Class | Means |
|---|---|
| `DRIFT-SCHEMA` | Declared module path or registry-cited document does not exist |
| `DRIFT-SEMANTIC` | Content changed in a way that weakens a policy invariant |
| `DRIFT-PROVENANCE` | Canon cites a code or document path that does not resolve |
| `DRIFT-AUTHZ` | Role assignments, delegation scopes, or privilege claims diverge from canon |
| `DRIFT-IDENTITY` | Identity objects (users, service principals, computers) cannot be reconciled to a canonical OrgPath |

Severities `P1`–`P4`. The substrate-drift CI gate fires on any P1 blocker
against canon content; `uiao substrate walk` prints the full report with
P2 warnings for narrative drift (editorial cleanup, non-blocking).

## Canon change process

Every modification under `src/uiao/canon/` must:

1. Add or update a `UIAO_NNN` allocation in
   [`src/uiao/canon/document-registry.yaml`](document-registry.yaml).
2. For doctrinal changes (supersession, retirement, scope shift), add a
   new ADR under [`src/uiao/canon/adr/`](adr/).
3. Pass governance review before merge.

Direct commits to canon without an ADR reference are a governance drift
signal. The full invariant set (I1–I5) is documented in
[AGENTS.md § Repository Invariants](../../../AGENTS.md#repository-invariants).

## Cross-references

- [AGENTS.md](../../../AGENTS.md) — repo-root agent integration guide
- [UIAO_200](substrate-manifest.yaml) — Substrate Manifest (module topology)
- [UIAO_201](workspace-contract.yaml) — Workspace Contract (local/remote binding)
- [ADR-044](adr/adr-044-substrate-governance-realignment.md) — post-ADR-032 realignment
- [`src/uiao/rules/canon-consumer.md`](../rules/canon-consumer.md) — runtime read rules
