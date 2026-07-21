---
document_id: UIAO_209
title: "Spec3-D2.1 — Non-Human Identity Registry: Data Model, Lifecycle, and Orphan Drift Types"
version: "1.0"
status: Draft
owner: "Michael Stratton"
created_at: "2026-07-21"
updated_at: "2026-07-21"
canon_adrs:
  - ADR-130   # Non-Human SSOT Registry — the designation this spec implements
  - ADR-059   # SailPoint adapter family — sailpoint-machine-identity conformance slot
  - ADR-016   # Human JML — the lifecycle model extended here
  - ADR-114   # AI System JML — the worked non-human JML pattern (AI class)
  - ADR-012   # Canonical drift taxonomy — home of the finding types bound here
  - ADR-092   # Active Governance — actuation ladder for registry-driven remediation
publish_to_site: true
---

# UIAO_209 — Spec3-D2.1 — Non-Human Identity Registry

## Overview

ADR-130 designates the **Non-Human Identity (NHI) Registry** as the single
source of truth for service accounts, workload identities, and app
registrations: every NHI exists in the registry *first* — with purpose,
scope, expiry, and a human owner — and the directory object is provisioned
from it. This spec implements that designation: the registry data model,
the non-human JML lifecycle, the reconciliation loop against the estate,
and the drift finding types (ADR-130 D4) that make orphan detection a
first-class output of the canonical taxonomy.

Companion: Spec3-D1.1 (Get-ServiceAccountScan) is the estate-side
discovery pass. Before this registry exists, that scan is measurement
without origination; once the registry exists, the scan's output becomes
the estate half of the reconciliation diff below.

## The registry record

One record per NHI. Fields marked ● are mandatory at provision time; a
record that cannot fill them is not provisioned.

| Field | Meaning |
|---|---|
| ● `nhi_id` | Registry-assigned stable identifier (survives re-platforming; never reused) |
| ● `nhi_class` | `service-account` \| `workload-identity` \| `app-registration` \| `automation-account` |
| ● `display_name` | Human-readable name (naming-convention gated) |
| ● `purpose` | What this identity exists to do — one sentence, falsifiable |
| ● `owner` | Human owner, **resolvable in the HR SSOT** (the ADR-130 Human-Anchor Rule); plus `deputy` for continuity |
| ● `scope` | The permissions/roles the identity is granted — the least-privilege envelope; anything observed beyond it is drift |
| ● `expiry` | Review-by date; no NHI is perpetual |
| ● `credential_policy` | Allowed credential types (managed identity preferred > certificate > secret) and rotation cadence |
| ● `environment` | Tenant/boundary the identity may exist in |
| `join_key` | Naming-plane anchor (where the NHI binds to an addressable asset) |
| `status` | `requested` → `active` → `suspended` → `decommissioned` |
| `provenance` | The originating request, its authoritative authorization, and the PIM activation that executed provisioning — the MACD-R clause 1–3 record |

The registry is a data-model designation, not a product selection
(ADR-130 D1). The `sailpoint-machine-identity` slot reserved by ADR-059 is
its conformance surface; a registry implemented as a governed table with
this schema conforms equally.

## Lifecycle — non-human JML

Extends ADR-016 exactly as ADR-114 did for the AI class:

| Event | Trigger | Required chain |
|---|---|---|
| **Joiner** (provision) | Approved registry record enters `active` | MACD-R clauses 1–3: registry origin, SSOT-routed authorization, JIT-elevated execution; directory object created *from* the record |
| **Mover** (rescope / re-owner) | Scope change, purpose change, or ownership transfer | Same chain; owner transfer is mandatory on the owner's leaver event — the leaver's anchored NHI estate is part of their offboarding surface |
| **Leaver** (decommission) | Expiry, purpose end, or owner decision | Credential revocation before object deletion (the ADR-114 deprovisioning sequence, generalized); registry record retained as `decommissioned` for audit |
| **Reset** (rotation) | Cadence from `credential_policy`, or compromise | The high-risk verb (ADR-130 D5): every rotation is a logged MACD-R with its own authorization and PIM activation — rotation outside the registry's record is drift |

## Reconciliation and the drift bindings (ADR-130 D4)

The reconciliation loop diffs the registry against the estate (directory
service principals, app registrations, automation accounts, key-vault
credential inventories; Spec3-D1.1 supplies the AD-side pass). Finding
types, bound into the ADR-012 taxonomy:

| Finding type | Condition | Severity |
|---|---|---|
| `DRIFT-COMPLIANCE::nhi-orphan` | Estate object with no registry record | **P2**; **P1** when the object holds privileged scopes |
| `DRIFT-COMPLIANCE::nhi-owner-unresolvable` | Registry owner (and deputy) no longer resolvable in the HR SSOT | P2 — clause 2 cannot resolve an approver; freeze non-emergency MACD-R until re-anchored |
| `DRIFT-COMPLIANCE::nhi-ghost` | Registry `decommissioned` but the estate object persists | P2 — the ghost-credential gap (ADR-114's finding class, generalized) |
| `DRIFT-COMPLIANCE::nhi-scope-exceeded` | Observed grants exceed the registry `scope` envelope | P2 |
| `DRIFT-COMPLIANCE::nhi-expired` | `expiry` passed with no mover/leaver event | P3 |
| `DRIFT-COMPLIANCE::nhi-rotation-overdue` | Credential age exceeds `credential_policy` cadence | P3; P2 for secrets (vs certificates/managed identities) |

Registration of these identifiers in the drift-engine type registry is the
implementation follow-up; this spec is their canonical definition.

Every finding's remediation travels the MACD-R lifecycle and closes under
Closure Provenance: the closure carries the re-scan payload proving the
condition cleared, and the finding stream feeds continuous monitoring
automatically — orphan count, ownerless count, and rotation-overdue count
are derived reporting, never compiled.

## Non-goals

- Not the non-employee **human** registry (that is the NERM-class CIR,
  ADR-055/ADR-059).
- Not a directory replacement: the directory remains the estate the
  registry provisions into and reconciles against — a projection, never
  an origination surface.
- Not a product selection; conformance is schema + lifecycle + findings,
  per ADR-130.
