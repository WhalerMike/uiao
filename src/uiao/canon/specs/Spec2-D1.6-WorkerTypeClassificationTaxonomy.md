---
deliverable_id: Spec2-D1.6
title: "Worker Type Classification Taxonomy"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 1
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
sibling_deliverables:
  - Spec2-D1.3
  - Spec2-D1.4
  - Spec2-D2.5
  - Spec2-D2.7
  - Spec2-D2.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D1.6: Worker Type Classification Taxonomy

> **Status (v0.1, 2026-05-01):** Initial draft. Pairs with the
> PowerShell scaffolder at
> [`tools/discovery/Spec2-D1.6-New-WorkerTypeTaxonomy.ps1`](../../../../tools/discovery/Spec2-D1.6-New-WorkerTypeTaxonomy.ps1).
> The taxonomy is referenced by D1.1 §5 (schema enum), D1.3 §3.9
> (license-affinity), D2.5 §2 (conversion matrix), D2.7 §2.2
> (per-worker-type pre-hire windows), and D2.8 §3 (scope filter).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Worker-Type Taxonomy called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 1 → D1.6:

> *Define all worker types and their provisioning implications:
> Full-Time Employee, Part-Time Employee, Contractor, Intern,
> Volunteer, Vendor, External Collaborator. Map each to: license
> assignment, group membership, access scope, retention period.*

D1.6 is the canonical authority for the worker-type enum used
throughout Spec 2. New worker types require an update to this
document AND to D1.1's enum.

### 1.1 Scope

In scope:

- The seven canonical worker types and their semantics.
- Per-type provisioning implications: license tier, group set,
  access scope, retention.
- Per-type pre-hire window defaults (referenced by D2.7).
- Per-type extension-attribute (`extensionAttribute2`) tagging.
- Per-type scope-filter behavior (referenced by D2.8).
- Conversion paths (referenced by D2.5).

Out of scope:

- Per-tenant license-SKU specifics (this is a tenant decision; the
  taxonomy provides the structural categories).
- Per-tenant role-assignment baselines (per-tenant policy).
- Specialized federal worker classes (foreign service officers,
  uniformed military, reservists) — these are tenant extensions
  that map onto the canonical types.

## 2. The Canonical Seven

| Worker type | One-line definition |
|---|---|
| **Full-Time Employee** | Permanent W-2 federal civilian employee, full-time hours |
| **Part-Time Employee** | Permanent W-2 federal civilian employee, less-than-full-time hours |
| **Contractor** | Non-employee with active contract performing work for the agency |
| **Intern** | Time-bounded learning role (typically academic-calendar-aligned) |
| **Vendor** | External party with vendor-of-record status (e.g., embedded service-provider personnel) |
| **Volunteer** | Unpaid worker with formal volunteer status |
| **External Collaborator** | Cross-tenant B2B identity (typically not provisioned through D2.x; B2B has its own flow) |

These seven align with D1.1's `workerType` enum.

## 3. Per-Type Profile

### 3.1 Full-Time Employee (FTE)

| Attribute | Value |
|---|---|
| `workerType` enum | `FullTimeEmployee` |
| Default `extensionAttribute2` (license-affinity) | `FTE-E5` (or tenant-equivalent) |
| Default Microsoft 365 license tier | M365 E5 (or agency-standard tier) |
| Group memberships (default) | Department dynamic group, location dynamic group, all-hands dynamic group, FTE dynamic group |
| Access scope | Full operational access per role |
| D2.7 pre-hire window default | 14 days |
| D2.8 scope filter | Always in scope |
| Retention (post-leaver) | Per agency NARA schedule (typically 7 years) |
| Lifecycle Workflows joiner template | Standard new-hire |

### 3.2 Part-Time Employee (PTE)

| Attribute | Value |
|---|---|
| `workerType` enum | `PartTimeEmployee` |
| Default `extensionAttribute2` | `PTE-E3` (or tenant-equivalent) |
| Default M365 tier | E3 (typically; agency choice) |
| Group memberships | Same as FTE except shifts based on tenant policy |
| Access scope | Full operational access (often subset by role; same as FTE structurally) |
| D2.7 pre-hire window default | 14 days |
| D2.8 scope filter | Always in scope |
| Retention | Same as FTE |
| Lifecycle Workflows joiner template | Standard new-hire |

### 3.3 Contractor

| Attribute | Value |
|---|---|
| `workerType` enum | `Contractor` |
| Default `extensionAttribute2` | `CONTRACTOR-A1` |
| Default M365 tier | F-tier or a contractor-specific SKU; tenant choice |
| Group memberships | Department dynamic group, contractor dynamic group, restricted-access groups |
| Access scope | Per contract scope; typically narrower than employees |
| UPN suffix variant | Often `firstname.lastname.contractor@` (per D1.5 + tenant policy) |
| D2.7 pre-hire window default | 7 days |
| D2.8 scope filter | Always in scope |
| Retention | Often shorter than employees (per agency policy + contract terms) |
| Lifecycle Workflows joiner template | Contractor onboarding |

### 3.4 Intern

| Attribute | Value |
|---|---|
| `workerType` enum | `Intern` |
| Default `extensionAttribute2` | `INTERN-A1` |
| Default M365 tier | F-tier or intern-specific SKU |
| Group memberships | Intern dynamic group + assigned-team groups |
| Access scope | Narrow; supervised |
| D2.7 pre-hire window default | 30 days (academic calendar bound; interns hired well in advance of start) |
| D2.8 scope filter | Always in scope |
| `terminationDate` | Always set at internship end date |
| Retention | Shorter (typically 1–2 years post-termination) |
| Lifecycle Workflows joiner template | Intern onboarding |
| Common conversion path | Intern → FTE per D2.5 §2.1 |

### 3.5 Vendor

| Attribute | Value |
|---|---|
| `workerType` enum | `Vendor` |
| Default `extensionAttribute2` | `VENDOR-A1` |
| Default M365 tier | F-tier or vendor-specific SKU; sometimes no license |
| Group memberships | Vendor dynamic group; restricted access |
| Access scope | Vendor-of-record specific resources only |
| D2.7 pre-hire window default | 0 days (day-of-hire only) |
| D2.8 scope filter | Configurable per agency policy (some agencies exclude vendors from canonical provisioning) |
| Retention | Per vendor contract |
| Lifecycle Workflows joiner template | Vendor onboarding |

### 3.6 Volunteer

| Attribute | Value |
|---|---|
| `workerType` enum | `Volunteer` |
| Default `extensionAttribute2` | `VOLUNTEER-A1` |
| Default M365 tier | F-tier or volunteer-specific SKU |
| Group memberships | Volunteer dynamic group |
| Access scope | Very narrow; specific event/program access |
| D2.7 pre-hire window default | 0 days |
| D2.8 scope filter | Configurable; tenant policy |
| Retention | Short (90 days typical) |
| Lifecycle Workflows joiner template | Volunteer onboarding |

### 3.7 External Collaborator

| Attribute | Value |
|---|---|
| `workerType` enum | `ExternalCollaborator` |
| Default `extensionAttribute2` | NOT used (B2B identity surface) |
| Default M365 tier | None (B2B guest) |
| Group memberships | Per-collaboration scope |
| Access scope | Single-collaboration only |
| D2.7 pre-hire window | N/A |
| D2.8 scope filter | **Excluded by default** — B2B has its own provisioning surface |
| Retention | Per access-review cadence |
| Lifecycle Workflows joiner template | NOT used |

## 4. Conversion Matrix

D2.5's worker-type conversion paths reference this matrix. The
canonical paths (replicated from D2.5 §2.1 for cross-reference):

| From | To | Common case |
|---|---|---|
| Contractor | Full-Time Employee | Contractor-to-FTE conversion |
| Part-Time Employee | Full-Time Employee | Promotion-class conversion |
| Full-Time Employee | Part-Time Employee | Reverse promotion / lifestyle change |
| Full-Time Employee | Contractor | Reverse conversion |
| Intern | Full-Time Employee | Intern-to-FTE |
| Intern | Contractor | Internship → contracted continuation |
| Vendor | Contractor | Vendor → embedded contractor |
| Volunteer | (any paid type) | Volunteer → paid worker (atypical) |
| External Collaborator | (any internal type) | B2B → internal hire (cross-tenant; outside D2.5 v0.1) |

Conversions outside this matrix require explicit ADR-tracked tenant
policy to permit.

## 5. License-Affinity Tag Taxonomy

The `extensionAttribute2` tag values in §3 are illustrative defaults.
Tenants choose their actual tag taxonomy. Constraints:

1. ONE tag per record (no list/multi-value).
2. Stable across versions (changing a tenant's tag scheme requires
   a coordinated re-stamp of all affected records).
3. Used as the primary input to group-based-licensing rule
   evaluation.

## 6. Adapter-Side Mapping

HR systems typically use vendor-specific worker-type values that
don't match D1.6's canonical names. The per-source adapter maps:

| Workday `Worker_Type` (typical) | D1.6 canonical |
|---|---|
| Regular | FullTimeEmployee or PartTimeEmployee (based on hours) |
| Contractor / Contingent Worker | Contractor |
| Intern | Intern |
| ... | ... |

| Oracle HCM `LegislativeWorkerType` | D1.6 canonical |
|---|---|
| EMP | FullTimeEmployee or PartTimeEmployee |
| CWK (Contingent Worker) | Contractor |
| ... | ... |

The adapter's mapping is the tenant's responsibility; the canonical
taxonomy is the contract.

## 7. Adding a New Worker Type

The taxonomy is not closed forever — new worker types may be
warranted. The process:

1. Author an ADR describing the new type and its rationale.
2. Update D1.1's `workerType` enum.
3. Update this document (§3 profile + §4 matrix entries).
4. Update `tools/discovery/Spec2-D1.6-New-WorkerTypeTaxonomy.ps1`
   if it implements taxonomy validation.
5. Coordinate with downstream specs (D2.5 conversion matrix; D2.7
   pre-hire windows; D2.8 scope filter).

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 8.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_135](../UIAO_135_identity-directory-transformation-inventory.md) — referenced for federal-civilian worker-class context.
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 1 → D1.6.

### 8.3 Spec 2 sister deliverables

- [Spec2-D1.1 — Canonical HR Attribute Schema](./Spec2-D1.1-CanonicalHRAttributeSchema.md) §5 — enum binding.
- [Spec2-D1.3 — HR → Entra Mapping Matrix](./Spec2-D1.3-HRToEntraAttributeMappingMatrix.md) §3.9 — license-affinity attribute.
- [Spec2-D1.4 — HR → AD Mapping Matrix](./Spec2-D1.4-HRToADAttributeMappingMatrix.md) §5 — OU placement.
- [Spec2-D2.5 — Conversion Workflow Specification](./Spec2-D2.5-ConversionWorkflowSpecification.md) §2 — conversion matrix.
- [Spec2-D2.7 — Pre-Hire Provisioning Window Specification](./Spec2-D2.7-PreHireProvisioningWindowSpecification.md) §2.2 — per-type windows.
- [Spec2-D2.8 — Provisioning Scope Filter Rules](./Spec2-D2.8-ProvisioningScopeFilterRules.md) §3.1 — workerTypeAllowed list.

### 8.4 Discovery generator

- [`tools/discovery/Spec2-D1.6-New-WorkerTypeTaxonomy.ps1`](../../../../tools/discovery/Spec2-D1.6-New-WorkerTypeTaxonomy.ps1)

### 8.5 Compliance

- NIST SP 800-53 Rev 5: AC-2 (account types), AC-3.
