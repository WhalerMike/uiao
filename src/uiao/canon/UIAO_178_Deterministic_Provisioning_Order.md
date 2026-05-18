---
document_id: UIAO_178
title: "Deterministic Provisioning Order — Eight-Step Idempotent Pipeline"
version: "1.0"
status: Draft
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-05-18"
updated_at: "2026-05-18"
boundary: GCC-Moderate
# Draft canon, pending reconciliation review (see PR #556). Will flip
# to true and gain a docs/.qmd entry once status moves to Current.
publish_to_site: false
---

# UIAO_178 — Deterministic Provisioning Order

## Purpose

Specifies the canonical order in which UIAO mutates Entra and Azure state during identity, access, and resource provisioning. Establishes the idempotency, reversibility, determinism, and logging contracts that any provisioning runtime MUST satisfy. Complements UIAO_136 (HR-agnostic provisioning architecture) by pinning the step order at runtime.

## Scope

Applies to every change-making (modernization-class) flow that creates, modifies, or retires identity and resource state through UIAO. Does not apply to read-only conformance adapters.

## Eight-step pipeline

Each provisioning request is decomposed into the following ordered steps. A step is only attempted when its precondition is satisfied; a step that is already in the desired state completes as a no-op.

| # | Step                       | Precondition                                  | Postcondition                                                  |
|---|----------------------------|-----------------------------------------------|----------------------------------------------------------------|
| 1 | `identity_create`          | HRIT record present                           | Entra principal exists                                         |
| 2 | `orgtree_place`            | Step 1 done                                   | `extensionAttribute1` set to canonical OrgPath (UIAO_151)      |
| 3 | `tag_assign`               | Step 2 done                                   | Canonical `uiao.*` tags written per UIAO_177                   |
| 4 | `access_assign`            | Step 3 done                                   | Group memberships and entitlements applied                     |
| 5 | `resource_identity_create` | Step 4 done, resource scope present           | Managed identity exists in target subscription                 |
| 6 | `rbac_assign`              | Step 5 done                                   | Role assignments applied at the canonical scope                |
| 7 | `device_bind`              | Step 6 done, device join in request           | Device-to-principal binding recorded                           |
| 8 | `boundary_enforce`         | Steps 1–7 done                                | Boundary tags and Conditional Access targeting verified        |

The order is canonical. Implementations MUST NOT reorder steps. A step that is not applicable to a given request (e.g. step 7 for a non-device flow) is skipped explicitly, not silently.

## Contracts

### Idempotency

Every step accepts the full desired-state payload and computes its own delta from observed state. Re-invoking the pipeline with the same input MUST converge to the same final state without raising on already-present resources.

### Determinism

Given the same input payload and the same observed external state, the pipeline produces the same sequence of writes. Wall-clock time, retry jitter, and adapter pagination ordering MUST NOT influence the canonical step order or the payload of any individual write.

### Reversibility

Each step records a structured rollback descriptor. A failure at step N halts the pipeline and applies rollback descriptors for steps 1..N-1 in reverse order. Rollback is best-effort but each rollback action is logged with the same provenance shape as the forward write.

### Logging

Every step emits a `ProvisioningStepRecord` containing:
- `request_id` — caller-supplied correlation key
- `step` — one of the eight names above
- `object_id` — canonical principal or resource ID
- `outcome` — `applied` | `noop` | `rolled_back` | `failed`
- `delta` — fields that changed (empty for `noop`)
- `timestamp` — ISO 8601 UTC
- `drift_records` — list of `DriftRecord` entries emitted during the step (UIAO_179)

Records are appended to the substrate evidence ledger via the orchestrator (UIAO_100).

## Implementation surface

- `src/uiao/orchestrator/provisioner.py` — `DeterministicProvisioner`, `ProvisioningRequest`, `ProvisioningStepRecord`.
- `src/uiao/orchestrator/orchestrator.py` — invokes the provisioner for change-making flows.
- The 13 canonical functions in UIAO_180 are the primitives the provisioner calls; the provisioner contains the order, the functions contain the side effects.

## Drift mapping

Provisioning steps emit drift records during their delta computation. The mapping from step facet to ADR-012 class is:

| Step                      | Primary `drift_class` on mismatch | `object_facet` |
|---------------------------|-----------------------------------|----------------|
| `identity_create`         | `DRIFT-IDENTITY`                  | `identity`     |
| `orgtree_place`           | `DRIFT-SEMANTIC`                  | `identity`     |
| `tag_assign`              | `DRIFT-SCHEMA`                    | `tag`          |
| `access_assign`           | `DRIFT-AUTHZ`                     | `access`       |
| `resource_identity_create`| `DRIFT-IDENTITY`                  | `resource`     |
| `rbac_assign`             | `DRIFT-AUTHZ`                     | `access`       |
| `device_bind`             | `DRIFT-IDENTITY`                  | `device`       |
| `boundary_enforce`        | `DRIFT-BOUNDARY`                  | `boundary`     |

## Out of scope

- HRIT inbound transformations (UIAO_136).
- Schedule and cadence of provisioning runs (UIAO_100 / orchestrator scheduler).
- Authorization of the provisioning runtime itself (UIAO_154 delegation matrix).
