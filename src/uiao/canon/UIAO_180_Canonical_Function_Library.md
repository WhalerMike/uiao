---
document_id: UIAO_180
title: "Canonical Function Library — Identity, Group, RBAC, and Tag Primitives"
version: "1.0"
status: Draft
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-05-18"
updated_at: "2026-05-18"
boundary: GCC-Moderate
---

# UIAO_180 — Canonical Function Library

## Purpose

Defines the canonical set of identity, group, RBAC, resource, and tag primitives used by the deterministic provisioner (UIAO_178), the orchestrator (UIAO_100), and any operator-facing tooling. Establishes a single function contract — idempotent, structured input, structured output, logged — so that callers depend on the canonical signature rather than on adapter internals.

## Scope

Applies to in-process Python callers. Out-of-process consumers MAY surface these functions through the CLI; the canonical contract lives in code.

## Function inventory

| Function                       | Purpose                                                | Returns                          |
|--------------------------------|--------------------------------------------------------|----------------------------------|
| `create_user(spec)`            | Create or reconcile an Entra user principal.           | `IdentityResult`                 |
| `disable_user(object_id)`      | Set `uiao.identity.lifecycle = disabled`; sign-out.    | `IdentityResult`                 |
| `delete_user(object_id)`       | Soft-delete an Entra user; respects 30-day window.     | `IdentityResult`                 |
| `assign_role(object_id, role)` | Assign an Entra directory role.                        | `RoleAssignmentResult`           |
| `remove_role(object_id, role)` | Remove an Entra directory role.                        | `RoleAssignmentResult`           |
| `create_group(spec)`           | Create or reconcile a security/M365 group.             | `GroupResult`                    |
| `add_to_group(object_id, group_id)`  | Add a principal to a group (idempotent).         | `GroupMembershipResult`          |
| `remove_from_group(object_id, group_id)` | Remove a principal from a group.             | `GroupMembershipResult`          |
| `create_managed_identity(spec)`| Create an Azure managed identity.                      | `ResourceIdentityResult`         |
| `assign_rbac(object_id, scope, role)` | Assign Azure RBAC at a scope.                   | `RbacAssignmentResult`           |
| `create_resource_group(spec)`  | Create or reconcile an Azure resource group.           | `ResourceResult`                 |
| `apply_tags(object_id, tags)`  | Apply canonical (`uiao.*`) tags per UIAO_177.          | `TagWriteResult`                 |
| `read_tags(object_id)`         | Read canonical and non-canonical tags from an object.  | `TagReadResult`                  |
| `detect_tag_drift(object_id)`  | Compute tag drift records per UIAO_177 §Drift mapping. | `list[DriftRecord]` (UIAO_179)   |
| `correct_tag_drift(object_id)` | Apply corrections for detected tag drift.              | `TagWriteResult`                 |

## Contracts

### Idempotency

Every function accepts the full desired-state payload (or canonical ID where no payload applies). Re-invocation with the same input on an already-converged object returns a result with `outcome = "noop"` and no side effects.

### Structured input

`spec` parameters are typed dataclasses or `TypedDict`s defined in `src/uiao/identity/canonical_functions.py`. Free-form `dict` inputs are explicitly forbidden in the public signature.

### Structured output

Every function returns a result object exposing at minimum:
- `object_id` — canonical ID
- `outcome` — `created` | `updated` | `noop` | `failed`
- `delta` — fields changed (empty for `noop`)
- `drift_records` — `list[DriftRecord]` for any drift observed while reconciling
- `timestamp` — ISO 8601 UTC
- `correlation_id` — optional, propagated from caller

### Logging

Every invocation emits a `ProvisioningStepRecord`-shaped log entry (UIAO_178) at INFO; failures escalate to ERROR with the corresponding `DriftRecord` attached.

### Adapter delegation

Functions are implemented as thin orchestration over the existing adapters (`EntraAdapter`, Azure ARM adapters). They MUST NOT inline vendor calls; all I/O flows through the adapter contract in `src/uiao/adapters/database_base.py` plus its thin-adapter convenience methods (`get_state`, `set_state`, `list_changes`, `apply_change`).

## Implementation surface

- `src/uiao/identity/__init__.py` — re-exports the 15 functions.
- `src/uiao/identity/canonical_functions.py` — function bodies, result dataclasses, idempotency helpers.
- `src/uiao/adapters/database_base.py` — thin-adapter convenience wrappers, used by the canonical functions.

## Stability

These signatures are part of the canonical Python surface. Breaking changes require an ADR and a deprecation cycle of at least one minor release.

## Out of scope

- Bulk operations (handled by the provisioner pipeline directly).
- Direct Microsoft Graph or ARM REST helpers (live in the adapter modules).
