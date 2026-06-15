---
adr_id: adr-098
title: "OrgPath Vendor-Neutral Binding Profiles — Multi-Cloud OrgPath Beyond Microsoft Extension Slots"
status: PROPOSED
decided: 2026-06-10
deciders: Michael Stratton
updated: 2026-06-10
next_review: 2026-12-10
review_trigger: The first non-Microsoft binding profile ships a write-back transport; a customer declares a multi-cloud OrgPath adoption; a new enforcement-plane vendor is added to the Zero Trust target list; the binding-profile schema is promoted from spec to executable canon.
impact: 'Decouples the OrgPath 15-facet identity model from the Microsoft `onPremisesExtensionAttribute1..15` storage slots fixed by ADR-078. Introduces vendor-neutral binding profiles as the canonical storage-contract abstraction, with the Microsoft slot mapping recast as the reference profile rather than the schema. Establishes AWS, GCP, Okta, generic LDAP, and VMware (Workspace ONE Access / vSphere / NSX) as first-class binding-profile targets at the Moderate and Commercial boundaries. Positions OrgPath facets as the cross-vendor Zero Trust policy subject. Specifies UIAO_193 as the binding-profile specification; executable profile YAML + JSON Schema and per-target adapters are deferred to implementation. Does not change the codebook (UIAO_151) facet semantics or the Microsoft runtime behavior.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-098-orgpath-vendor-neutral-binding-profiles.html
---

# ADR-098: OrgPath Vendor-Neutral Binding Profiles

## Status

**PROPOSED** — 2026-06-10.

This ADR is doctrine pending Governance Board acceptance. It establishes the storage-contract abstraction that lets OrgPath govern identity, workload, and enforcement surfaces beyond the Microsoft estate. It changes no runtime behavior, schema, or registry entry on acceptance; those land in the implementation phase the ADR authorizes.

## Context

[ADR-078](adr-078-orgpath-attribute-schema-15-facet.md) made Model C — the 15-facet multi-attribute model — the canonical OrgPath schema, and bound each facet to a specific Microsoft `onPremisesExtensionAttribute` slot (`extensionAttribute1..15`). [ADR-035](adr-035-orgpath-codebook-binding.md) published the codebook as executable canon at `src/uiao/canon/data/orgpath/codebook.yaml`, validated by `src/uiao/schemas/orgpath/codebook.schema.json`. The drift engine (UIAO_163), dynamic-group library (UIAO_152), Administrative Unit mapping (UIAO_154), and the device-plane adapters all read facets out of those numbered slots.

This is the correct contract for the Microsoft estate, and it is the first deployed boundary. But it conflates two distinct things:

1. **What a facet *means*** — the codebook semantics (Region, Department, Division, Role, CostCenter, Classification, HireDate, TermDate, ClearanceLevel, AccountType, plus five reserved). These are vendor-neutral: every directory, cloud, and workload platform has a notion of organizational placement, role, and lifecycle.
2. **Where a facet *lives*** — the storage locator. Today that is hard-wired to `onPremisesExtensionAttribute1..15`. No other identity system, cloud platform, or enforcement surface has those slots.

Per [ADR-085](adr-085-universal-enterprise-positioning.md), the UIAO core engine is vertical-agnostic; any artifact that couples the *core* to a single vendor is a positioning bug. The OrgPath storage binding is exactly such a coupling: the facet model is universal, but its only expression is Microsoft-shaped. Three forces make this coupling load-bearing now:

- **Multi-cloud reality.** Enterprises run identity and workloads across AWS, GCP, and private cloud (VMware) alongside Microsoft. OrgPath cannot be the organizational substrate if it can only be *stamped* on Entra objects.
- **VMware as a three-plane target.** VMware spans identity (Workspace ONE Access), workload/device (vSphere/vCenter tags & categories), and enforcement (NSX security tags/groups). It proves the storage contract must handle more than IdP user attributes.
- **Zero Trust enforcement.** ZT policy engines (NSX, Palo Alto dynamic address groups, Elisity policy groups, cloud-native security groups) need a stable, vendor-independent *policy subject*. OrgPath facets are the natural subject — but only if they can be projected onto each enforcement surface through a defined contract.

Until the storage contract is decoupled from Microsoft slots, every non-Microsoft adapter must reinvent its own facet storage, and there is no canonical place to declare how facets project onto a given vendor. This ADR fixes that once.

### Boundary scope

This decision and everything it authorizes is scoped to the **Moderate and Commercial** boundaries only. No GovCloud, sovereign, or high-side endpoints are in scope; every binding profile and transport resolves only commercial / GCC-Moderate endpoints. High-side boundary enums, if ever needed, are added in lockstep with their own authorizing ADR per the AGENTS.md boundary-enum rule.

## Decision

### D1. The codebook facet is the canonical subject; storage is a profile, not the schema

The 15-facet codebook (UIAO_151 narrative, `codebook.yaml` executable) remains the single source of truth for **what facets mean**. A new abstraction — the **binding profile** — declares **where each facet lives** on a given target platform. A binding profile is a per-target map from each codebook facet to a native *storage locator* (an attribute name, a tag key, a label, a custom-attribute id) plus the read/write mechanics for that surface. The facet model is invariant across profiles; only the locator and transport differ.

### D2. The Microsoft slot mapping becomes the reference profile

The `extensionAttribute1..15` assignment fixed by ADR-078 is recast as the **`microsoft-entra` reference binding profile** — the canonical worked example, not the schema. ADR-078's slot table stands unchanged as the content of that profile. No Microsoft runtime behavior changes. Existing tenants and adapters continue to read and write the numbered slots exactly as today; they are simply now understood as *one profile among several* rather than the storage contract itself.

### D3. First-class binding-profile targets

The following targets are declared first-class at the Moderate and Commercial boundaries. Their facet→locator contracts are specified in [UIAO_193](../UIAO_193_OrgPath_MultiCloud_Binding.md):

| Profile | Plane(s) | Native storage surface |
|---|---|---|
| `microsoft-entra` | identity, device | `onPremisesExtensionAttribute1..15`; Arc tags (reference profile) |
| `aws` | identity, workload | IAM Identity Center user/group attributes; resource tags |
| `gcp` | identity, workload | Cloud Identity user attributes; resource labels |
| `okta` | identity | Universal Directory profile attributes (custom schema) |
| `ldap` | identity | Directory attributes (schema-extension or reserved attributes) |
| `vmware` | identity, workload, enforcement | Workspace ONE Access user attributes; vSphere/vCenter tags & categories; NSX security tags / groups |

VMware is intentionally a three-plane profile: it is the proof that the binding-profile contract is not IdP-centric — the same facet set projects onto a workload (vSphere VM) and an enforcement construct (NSX group), not only a user object.

### D4. Boundary is profile-scoped and Moderate/Commercial-only

Each profile resolves only commercial / GCC-Moderate endpoints. Profiles MUST NOT hardcode endpoints; they resolve via the existing cloud-resolution seams (the Graph/ARM cloud resolvers for `microsoft-entra`, and per-profile equivalents for the others). The `commercial` cloud value also serves GCC-Moderate per [ADR-033](adr-033-gcc-boundary-drift-class.md). High-side endpoints are out of scope.

### D5. OrgPath facets are the cross-vendor Zero Trust policy subject

Enforcement-plane adapters consume facets *through a binding profile's read side* rather than re-deriving organizational placement per vendor. A facet predicate (e.g. `Department=IT AND Classification=Contractor`) resolves to the native policy-group construct of each enforcement surface — NSX security group, Palo Alto dynamic address group, Elisity policy group, cloud-native security group. This makes OrgPath the stable subject for microsegmentation and least-privilege across a mixed estate, and aligns facet drift (DRIFT-IDENTITY, UIAO_163) with continuous Zero Trust verification. UIAO_193 specifies the facet→enforcement projection and the CISA ZTMM pillar mapping. This is complementary to — not a replacement for — the read-only Zero Trust *assessment* digest in `uiao.adapters.zta` (which scores a Microsoft tenant's posture); this ADR concerns the *enforcement* subject across vendors.

### D6. UIAO_193 is the specification; executable canon is deferred to implementation

This ADR authorizes the binding-profile model and names the targets. The **binding-profile JSON Schema** (`src/uiao/schemas/orgpath/binding-profile.schema.json`), the **executable per-target profile YAML** (`src/uiao/canon/data/orgpath/binding-profiles/<target>.yaml`), and the **per-target mapping + transport modules** are deferred to the implementation phase that follows acceptance, each landing with happy-path + failure-mode tests per AGENTS.md. UIAO_193 specifies the schema in normative prose so implementation has an unambiguous target.

### D7. Non-Microsoft identity adapters register `mission-class: identity`

Every modernization adapter registered to date is `mission-class: integration`. A binding-profile write-back adapter for a non-Microsoft IdP (Okta, LDAP, Workspace ONE Access) is the first `mission-class: identity` modernization adapter and MUST register as such per UIAO_003. Read-only profile assessors register as `class: conformance`, `mission-class: identity`. Each adapter declares its `gcc-boundary` value at the Moderate/Commercial scope; no high-side enum is introduced.

## Consequences

**Positive**

- OrgPath becomes the genuine organizational substrate across Microsoft, AWS, GCP, VMware, Okta, and generic LDAP — not a Microsoft-only stamp.
- The Microsoft estate is undisturbed: the reference profile *is* the ADR-078 slot table, so existing tenants, the drift engine, and the device adapters keep working byte-for-byte.
- Zero Trust enforcement gets a stable, vendor-independent policy subject; microsegmentation rules express against facets, not per-vendor attribute soup.
- New profiles are additive — a vendor is onboarded by writing a profile (locator map) + a transport, mirroring the established AD-mapping / Graph-transport / ARM-transport pattern. No core change is required.
- Drift detection generalizes: the engine validates facet *values* against the codebook independently of where they are stored, so DRIFT-IDENTITY works against any profile.

**Negative / deferred**

- Two SSOTs to reconcile per profile until a cross-check job lands: the UIAO_193 normative profile table and the executable profile YAML (mirrors the UIAO_151 ↔ `codebook.yaml` situation noted in ADR-035).
- Facet *value* enumerations are global (codebook) but some targets cannot store all 15 facets natively (e.g. a tag-key-count limit, attribute-length limits); the spec must define a deterministic overflow/composition rule per profile. This is specified in UIAO_193 but not yet exercised in code.
- The enforcement projection (facet predicate → native policy group) introduces a second mapping surface per enforcement vendor; its conformance tests are part of the implementation phase, not this ADR.
- VMware product naming is in flux post-acquisition; profile locators are pinned to product *surfaces* (Workspace ONE Access attributes, vSphere tags, NSX groups) rather than brand names to limit churn.

## Alternatives considered

1. **Per-adapter ad-hoc storage (status quo).** Each non-Microsoft adapter invents its own facet storage. Rejected: no canonical contract, no drift generalization, every adapter re-litigates the same mapping, and ADR-085's vertical-agnostic positioning stays aspirational.
2. **A second composite-string model for non-Microsoft targets.** Pack all facets into one attribute/tag on platforms with few attribute slots. Rejected: ADR-078 already retired composite paths for the reasons that apply here too (text-parsing fragility, not expressible in policy predicates). The overflow rule in D-deferred handles slot-poor targets without resurrecting composites as the primary model.
3. **Treat each cloud as a separate codebook.** Rejected: fragments the facet semantics, defeats the cross-boundary reconciled plane, and makes Zero Trust policy non-portable.

## Related work

- [ADR-078](adr-078-orgpath-attribute-schema-15-facet.md) — fixes the 15-facet model and the Microsoft slot table now recast as the reference profile.
- [ADR-035](adr-035-orgpath-codebook-binding.md) — executable codebook binding this ADR generalizes across profiles.
- [ADR-085](adr-085-universal-enterprise-positioning.md) — vertical-agnostic positioning this ADR operationalizes for OrgPath storage.
- [ADR-033](adr-033-gcc-boundary-drift-class.md) — the GCC-Moderate / Commercial boundary drift class; carries the boundary semantics (the `commercial` value also serves GCC-Moderate) that the non-Microsoft profiles inherit.
- [ADR-007](adr-007-multi-cloud-adapter.md) — multi-cloud adapter model.
- [UIAO_193](../UIAO_193_OrgPath_MultiCloud_Binding.md) — the binding-profile specification authorized by this ADR.
- `uiao.adapters.zta` — read-only Zero Trust assessment digest; complementary to the enforcement subject defined here.
