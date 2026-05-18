# UIAO Canonical Function Library — Proposal Draft

> **Status:** Inbox draft. Not canon. Promoting any part of this document
> to `src/uiao/canon/` requires a UIAO_NNN allocation in
> `document-registry.yaml` and an ADR per AGENTS.md §I5. Until then, do
> not import or depend on the function names below.

## Purpose

Provide a reusable, audited code library for common Entra ID and Azure
operations performed across UIAO's modernization adapters
(`src/uiao/canon/modernization-registry.yaml`) so that each adapter does
not re-implement (and re-bug) the same primitives. Targets the GCC-Moderate
cloud boundary declared in AGENTS.md.

## Required functions

| Function | Domain | Notes |
|---|---|---|
| `create_user(spec)` | Entra users | Returns `{id, upn, created_at}` |
| `disable_user(id)` | Entra users | Sets `accountEnabled=false` |
| `delete_user(id)` | Entra users | Soft-delete via Graph |
| `assign_role(principal, role, scope)` | Entra RBAC | Directory + AU scopes |
| `remove_role(principal, role, scope)` | Entra RBAC | Inverse of `assign_role` |
| `create_group(spec)` | Entra groups | Security / M365 / dynamic |
| `add_to_group(group, principal)` | Entra groups | Member or owner |
| `remove_from_group(group, principal)` | Entra groups | Inverse |
| `create_managed_identity(spec)` | Azure identity | System- or user-assigned |
| `assign_rbac(principal, role, scope)` | Azure RBAC | ARM scope path |
| `create_resource_group(spec)` | Azure ARM | Region + tags |
| `apply_tags(resource_id, tags)` | Azure tags | Merges, does not replace |
| `read_tags(resource_id)` | Azure tags | Returns observed map |
| `detect_tag_drift(resource_id, expected)` | Azure tags | Returns `TagDriftReport` |
| `correct_tag_drift(resource_id, expected)` | Azure tags | Applies remediation |

## Cross-cutting contract

Every function in this library **must**:

- **Be idempotent.** Calling the same function twice with the same input
  reaches the same end state and is safe to retry. `create_*` functions
  return the existing object if it already matches the spec; `assign_*`
  is a no-op when the assignment already exists; `delete_*` is a no-op
  when the target is already absent.
- **Accept structured input.** Typed dataclass / pydantic model for the
  spec argument — no positional string soup, no kwargs grab-bag.
- **Return structured output.** Typed result object containing at minimum:
  `{action, object_id, changed: bool, observed_state, provenance}`. The
  `changed` flag is what makes idempotency observable.
- **Log actions.** Every call emits a structured log record with
  function name, input hash, decision (`created` / `noop` / `updated` /
  `deleted` / `failed`), and a provenance chain to the calling adapter.
  Logs are the evidence trail the governance pipeline consumes.

## Relationship to the canonical adapter framework

This is a **library**, not an adapter. It does not subclass
`DatabaseAdapterBase` and does not appear in any adapter registry. It is
intended for *use by* `mission-class = identity` and
`mission-class = integration` modernization adapters — its functions are
the building blocks those adapters compose.

## Open questions for canon review

1. **Module path.** Candidate: `src/uiao/canonical_functions/` (sibling
   to `adapters/`) vs. `src/uiao/adapters/_graph_canonical/` (co-located
   with the Graph endpoint resolver per AGENTS.md "Microsoft Graph
   adapters" rule). The former is preferred if Azure-ARM functions are in
   scope; the latter if scope is Graph-only.
2. **Cloud-boundary coupling.** Functions touching Graph must use
   `uiao.adapters._graph_clouds.resolve_graph_base()` and accept the
   standard `cloud` config key. Functions touching ARM need an analogous
   helper that does not yet exist — its introduction is a prerequisite
   ADR.
3. **Idempotency proof.** Does the library ship adapter-conformance-style
   tests (golden input → golden output → re-run is a no-op) gated in
   `.github/workflows/adapter-conformance.yml`, or its own workflow?
4. **Provenance integration.** Should the return-shape's `provenance`
   field be a full `ProvenanceRecord` (per the evidence pipeline) or a
   lighter envelope? Coupling to `ProvenanceRecord` ties the library's
   release cadence to the evidence module's.
5. **`detect_tag_drift` / `correct_tag_drift` taxonomy.** Tag drift is
   not currently a class in the five-class drift taxonomy (UIAO docs
   `16_DriftDetectionStandard`). Either it folds into `DRIFT-SEMANTIC`
   or warrants a new class — requires an ADR either way.

These must be resolved before any module under `src/uiao/` imports from
this library.
