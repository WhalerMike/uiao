---
document_id: UIAO_177
title: "Canonical Tag Governance — Required Tags, Conflict Resolution, Drift Mapping"
version: "1.0"
status: Draft
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-05-18"
updated_at: "2026-05-18"
boundary: GCC-Moderate
---

# UIAO_177 — Canonical Tag Governance

## Purpose

Defines the canonical tag namespace that UIAO writes and reconciles across Entra and Azure object surfaces. Establishes the required tag set, the policy for non-canonical tags, the conflict-resolution rule, and the mapping from tag drift to the canonical drift taxonomy (ADR-012, UIAO_110).

## Scope

Applies to users, groups, devices, service principals, and Azure resources reached by any UIAO modernization or conformance adapter. Does not redefine document-level metadata (governed by `src/uiao/schemas/metadata-schema.json`).

## Canonical tag namespace

All UIAO-owned tags use the `uiao.` prefix. The reserved keys are:

| Key                       | Type   | Domain                                  | Source of truth                                                |
|---------------------------|--------|-----------------------------------------|----------------------------------------------------------------|
| `uiao.org.path`           | string | OrgPath lineage (`ORG-DIV-DEPT-...`)    | **Derived** from Entra `extensionAttribute1` (UIAO_151).       |
| `uiao.identity.lifecycle` | enum   | `active` \| `leave` \| `disabled`       | Computed from HRIT joiner-mover-leaver signal (UIAO_136).      |
| `uiao.owner`              | string | Canonical identity ID of accountable    | Resolved through ownership service (`src/uiao/governance/ownership.py`). |
| `uiao.boundary`           | enum   | `GCC-Moderate` plus authorized exceptions | UIAO substrate-manifest `gcc-boundary` enum (ADR-033, ADR-059).|

`uiao.identity.lifecycle` is intentionally namespaced under `identity` to avoid collision with the 7-state artifact lifecycle defined by UIAO_169. Tags with the bare key `uiao.lifecycle` MUST NOT be written and, if present, are treated as conflicts.

## Non-canonical tags

Tags that do not begin with `uiao.` are permitted on Azure resources and identity objects. They are recorded by adapters as `non_canonical = true` and excluded from the canonical reconciliation set. UIAO does not remove non-canonical tags.

## Conflict-resolution rule

A canonical tag whose actual value differs from the computed source-of-truth value is a conflict. The resolution rule is:

1. UIAO recomputes the canonical value from its source of truth.
2. UIAO emits a drift record (see §Drift mapping) before any write.
3. UIAO overwrites the canonical key with the computed value during the next deterministic provisioning run (UIAO_178).

Forbidden keys (any `uiao.*` key not listed above, including the bare `uiao.lifecycle`) are removed during the same write pass.

## Derived vs. dual-write semantics

`uiao.org.path` is a **derived** tag: it is materialised onto Azure resources where Azure RBAC, Policy, or cost-management need a tag projection, but the source of truth remains `extensionAttribute1` on the Entra principal. Drift between the tag and the attribute is always resolved by recomputing from the attribute, not the other way around. This preserves UIAO_151 as the codebook authority.

## Drift mapping

Tag-level findings emitted by adapters are object-level facets layered on top of the system-level taxonomy in ADR-012. The mapping is:

| Tag finding                                  | `drift_class` (ADR-012) | `object_facet` (UIAO_177) |
|----------------------------------------------|-------------------------|---------------------------|
| Canonical key missing                        | `DRIFT-SCHEMA`          | `tag`                     |
| Canonical key present but value mismatch     | `DRIFT-SEMANTIC`        | `tag`                     |
| Forbidden `uiao.*` key present               | `DRIFT-SCHEMA`          | `tag`                     |
| `uiao.boundary` outside enum                 | `DRIFT-BOUNDARY`        | `tag`                     |
| `uiao.owner` references unresolved principal | `DRIFT-AUTHZ`           | `tag`                     |

`object_facet` is recorded on every `DriftRecord` per UIAO_179. It does not replace `drift_class`; it groups findings by surface for operator UX.

## Implementation surface

- `src/uiao/governance/tag_governance.py` — `CanonicalTagKey` enum, `TagPolicy` validator, `compute_tag_drift()` entry point.
- `src/uiao/identity/canonical_functions.py` — `apply_tags()`, `read_tags()`, `detect_tag_drift()`, `correct_tag_drift()` (UIAO_180).
- Adapters that surface tags (Entra, Azure Resource Manager) MUST emit findings through `compute_tag_drift()`; they MUST NOT define their own tag vocabularies.

## Out of scope

- Cost-allocation tags maintained by Finance (non-`uiao.*` namespace).
- Intune device tags — covered separately by UIAO_011 once that surface is canonical.
