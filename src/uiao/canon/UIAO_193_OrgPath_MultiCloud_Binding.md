---
document_id: UIAO_193
title: "OrgPath Multi-Cloud Binding Profiles — Vendor-Neutral Storage Contract & Zero Trust Subject"
version: "1.0"
status: Draft
owner: Michael Stratton
created_at: "2026-06-10"
updated_at: "2026-06-10"
publish_to_site: true
publication_style: include
lifecycle: aspirational
lifecycle_review: "2026-12-10"
---

# UIAO_193: OrgPath Multi-Cloud Binding Profiles

> **The OrgPath facet model is universal; its storage is a profile.** Per [ADR-098](adr/adr-098-orgpath-vendor-neutral-binding-profiles.md), the 15-facet codebook (UIAO_151) defines *what facets mean*; a **binding profile** defines *where each facet lives* on a target platform. The Microsoft `onPremisesExtensionAttribute1..15` mapping from [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md) is recast here as the `microsoft-entra` **reference profile** — the canonical worked example, not the schema. This document specifies the binding-profile contract for the Moderate and Commercial boundaries and positions OrgPath facets as the cross-vendor Zero Trust policy subject.

## Purpose

This specification makes OrgPath the organizational substrate across a mixed enterprise estate — Microsoft, AWS, GCP, VMware, Okta, and generic LDAP — without forking the facet model per vendor. It defines:

1. The **binding-profile** abstraction: a per-target map from each codebook facet to a native storage locator, plus the read/write mechanics for that surface.
2. The normative **binding-profile schema** that the executable per-target YAML (deferred to implementation per ADR-098 §D6) must satisfy.
3. The **per-target profiles** for the first-class targets at the Moderate and Commercial boundaries — the original six per [ADR-098](adr/adr-098-orgpath-vendor-neutral-binding-profiles.md) §D3, plus the three IdP targets (PingOne, Keycloak, Auth0) added by [ADR-099](adr/adr-099-orgpath-idp-binding-profile-expansion.md).
4. The **Zero Trust** projection: how facet predicates resolve to native enforcement-policy constructs across vendors, and how this maps to the CISA Zero Trust Maturity Model pillars.

The facet *semantics* and *value enumerations* remain the exclusive province of the codebook (UIAO_151 narrative; `data/orgpath/codebook.yaml` executable). This document never redefines a facet — it only declares where facets are stored and how they are projected onto policy.

## Scope

Covers all 15 codebook facets across the nine first-class binding-profile targets (the six in ADR-098 §D3 plus PingOne / Keycloak / Auth0 in ADR-099). Applies to the read (assess), derive, write-back (stamp), and enforcement-projection stages of the OrgPath lifecycle. Boundary scope is **Moderate and Commercial only** — every profile resolves only commercial / GCC-Moderate endpoints; no GovCloud, sovereign, or high-side surfaces are in scope. The `commercial` cloud value also serves GCC-Moderate per ADR-033.

Out of scope: the facet semantics themselves (UIAO_151), the drift taxonomy mechanics (UIAO_163), and the Microsoft-tenant Zero Trust *assessment* digest (`uiao.adapters.zta`), which scores posture rather than enforcing policy. This document concerns the cross-vendor enforcement *subject* and the storage contract.

## Background — why decouple storage from the facet model

ADR-078 bound each facet to a numbered Microsoft extension slot, and ADR-035 published the codebook as executable canon read out of those slots. That contract is correct for the Microsoft estate and is the first deployed boundary. But it conflates *meaning* (vendor-neutral) with *storage location* (Microsoft-shaped). No AWS account, GCP organization, VMware vCenter, Okta org, or LDAP directory has `onPremisesExtensionAttribute1..15`. ADR-098 separates the two: the facet stays canonical; the storage locator becomes a per-profile concern. This document is the specification ADR-098 §D6 authorizes.

## The binding-profile model

A **binding profile** is a named, versioned document that answers three questions for one target platform:

1. **Locator** — for each codebook facet, what is the native storage key on this platform (an attribute name, a tag key, a label key, a custom-attribute id)?
2. **Mechanics** — how are those locators read and written (which API surface, which identity/permission model, which endpoint-resolution seam at the Moderate/Commercial boundary)?
3. **Constraints** — what native limits apply (attribute count, key/value length, allowed character set, tag-count caps), and what is the deterministic *overflow rule* when the platform cannot store all 15 facets natively?

The profile is the *only* place a vendor-specific storage decision is recorded. The facet model, the drift engine, the dynamic-group semantics, and the Zero Trust predicate language all sit above the profile and are profile-agnostic: they operate on facets, and the profile resolves facets to and from native storage.

### Lifecycle stages and where the profile participates

| Stage | What happens | Profile's role |
|---|---|---|
| **Assess (read)** | Read native objects from the target | Maps native locators → facet candidates |
| **Derive** | Translate source attributes → codebook values | Source→facet mapping (per ADR-035 / `ad_mapping.py` pattern) validates against codebook |
| **Write-back (stamp)** | Persist facet values onto target objects | Maps facets → native locators; transport executes the write at the resolved endpoint |
| **Drift** | Compare observed facets vs codebook | Profile-agnostic: the engine validates facet *values* regardless of storage |
| **Enforce (project)** | Resolve a facet predicate to a native policy group | Profile read side feeds the enforcement projection |

The Assess→Derive→Write-back pipeline mirrors the established Microsoft pattern exactly: `OrgPathMapping` (`src/uiao/modernization/orgtree/ad_mapping.py`) derives facets, and the Graph/ARM transports write them. A new profile contributes a `<target>_mapping.py` and a `<target>_transport.py` of the same shape — this is the implementation phase ADR-098 authorizes, not part of this spec.

## Facet carriage — SCIM provisioning and token claims

A binding profile says *where* a facet is stored on a target and *how* it
projects to that target's enforcement constructs. A separate concern is
**carriage**: how a facet *travels* to the systems that consume it across a
heterogeneous IdP estate — particularly downstream applications and the
SASE / SSE access layer ([UIAO_013](UIAO_013_OrgPath_in_Zero_Trust_and_SASE.md)),
which often integrate only via standard provisioning and federation
protocols, not vendor-native attribute APIs. Two open mechanisms carry
facets without coupling consumers to any one IdP:

1. **SCIM 2.0 (provisioning / sync).** Where a target IdP or application is
   SCIM-capable, facets are carried as **custom schema extension**
   attributes on the SCIM `User` (and, where modeled, `Group`) resource.
   SCIM is the provisioning-plane analog of the per-target write-back
   transport: the profile's facet→locator map names the SCIM extension
   attribute keys, and the transport is a SCIM client rather than a
   vendor-specific SDK. This is the natural carriage for the `okta` and
   `ldap` identity profiles and for any generic SCIM-capable consumer; a
   `generic-scim` profile is the obvious additive target under the same
   contract (its addition follows the ADR-098 target-list process, not
   this spec).
2. **Token claims (SAML / OIDC federation).** For runtime access decisions,
   facets are projected as **custom claims** in SAML assertions and OIDC
   ID / access tokens via the IdP's claim-mapping surface. A downstream app
   or SASE / SSE proxy then receives consistent organizational context —
   the same facet vocabulary — regardless of which IdP minted the token.
   This is the federation-plane analog of the certificate carriage that
   UIAO_012 specifies for NAC / 802.1X: the carrier differs (a claim, not
   a cert SAN), but the principle is identical — the OrgPath value rides
   the credential the relying party already trusts. Token-claim carriage
   composes with the token-bound transport doctrine in
   [ADR-066](adr/adr-066-application-aware-networking-and-token-bound-transport.md).

Carriage is profile-aware but consumer-agnostic: the facet *values* are the
codebook's (UIAO_151), so a claim or SCIM attribute is just another
projection of the same governed subject. Accordingly, **carriage drift is
DRIFT-IDENTITY**: a SCIM-provisioned attribute or an emitted token claim
whose facet value diverges from canon is the same continuous-verification
signal as a divergent native locator (UIAO_163), surfaced through the same
path. Boundary is unchanged — Moderate / Commercial only; claims and SCIM
attributes carry organizational metadata, and the sensitive
Classification / ClearanceLevel combination with subject identity is
handled in-boundary per "Boundary and handling" below.

## Binding-profile schema (normative)

The executable per-target profile at `src/uiao/canon/data/orgpath/binding-profiles/<target>.yaml` (deferred to implementation) MUST satisfy the following contract. The JSON Schema (`src/uiao/schemas/orgpath/binding-profile.schema.json`) lands with the implementation; this table is its normative source.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | semver string | yes | Profile-schema version (independent of the codebook version). |
| `profile_id` | kebab-case string | yes | Stable identifier (`microsoft-entra`, `aws`, `gcp`, `okta`, `ldap`, `vmware`, `pingone`, `keycloak`, `auth0`). Never renamed; retire via `status` + successor. |
| `display_name` | string | yes | Human-readable name. |
| `status` | enum | yes | `reference` \| `proposed` \| `active` \| `deprecated`. The `microsoft-entra` profile is `reference`. |
| `boundary` | enum | yes | `commercial` \| `gcc-moderate`. High-side values are out of scope per ADR-098. |
| `planes` | array of enum | yes | One or more of `identity`, `workload`, `enforcement`. |
| `endpoint_resolution` | string | yes | Name of the resolution seam (never a hardcoded host) used to reach the target at the declared boundary. |
| `facet_bindings` | array | yes | One entry per facet that this profile stores natively (see below). |
| `overflow` | object | conditional | Required when the target cannot store all bound facets natively; declares the deterministic overflow rule (see "Overflow"). |
| `constraints` | object | no | Native limits: max attribute/tag count, key/value length, allowed charset. |

Each `facet_bindings[]` entry:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `facet` | string | yes | Codebook facet name (`region`, `department`, …). MUST exist in `codebook.yaml`. |
| `locator` | string | yes | Native storage key on this target (attribute name, tag key, label key, custom-attribute id). |
| `locator_kind` | enum | yes | `attribute` \| `tag` \| `label` \| `custom_attribute` \| `group_membership`. |
| `writable` | boolean | yes | Whether the write-back transport may set this locator (some surfaces are read-only sources). |
| `notes` | string | no | Per-facet caveats (length truncation, value-set divergence handled in the mapping). |

**Overflow.** When a target's native surface holds fewer keys than the facets bound to it, the profile MUST declare a deterministic overflow rule rather than silently dropping facets. The permitted rules are: `priority` (store the highest-priority facets per a declared ordering; surface the rest as DRIFT-IDENTITY "uncaptured"), or `composite-secondary` (store primary facets natively and pack overflow facets into a single reserved composite key as `facet=value;…`, parsed back on read). `composite-secondary` is a *secondary* mechanism only — it never replaces native per-facet storage for the primary facets, per the ADR-078 rationale that retired composite paths as a primary model.

## Per-target binding profiles

The following profiles are specified at the Moderate and Commercial boundaries. Locators below are the *canonical defaults*; tenant overrides are an operator concern (the mapping-YAML pattern), not a canon change.

### `microsoft-entra` (reference profile)

- **Planes:** identity, workload (device).
- **Identity storage:** `onPremisesExtensionAttribute1..15` on the directory object, exactly per ADR-078's slot table (Region→1, Department→2, Division→3, Role→4, CostCenter→5, Classification→6, HireDate→7, TermDate→8, ClearanceLevel→9, AccountType→10, reserved 11–15).
- **Workload storage:** Arc-connected machine tags (key = facet name, value = facet value).
- **Endpoint resolution:** the Graph cloud resolver for identity; the ARM resolver for the device plane — both at the commercial / GCC-Moderate boundary.
- **Constraints:** 15 named slots; no overflow needed (the facet count equals the slot count by construction).
- **Role:** this profile is the worked reference. It changes no Microsoft runtime behavior; it documents the existing contract as one profile.

### `aws`

- **Planes:** identity, workload.
- **Identity storage:** IAM Identity Center user and group attributes (custom attribute keys named for the facet). Where the directory is externally federated, facets are sourced from the upstream IdP profile and projected onto Identity Center attributes.
- **Workload storage:** resource tags on EC2/SSM-managed instances (tag key = facet name).
- **Endpoint resolution:** commercial-partition Identity Center and resource-tagging endpoints. GovCloud partitions are out of scope.
- **Overflow:** none for identity (attributes are arbitrary); resource-tag count limits apply on the workload plane — `priority` overflow with the facet ordering Region, Department, Division, Role, Classification, CostCenter, AccountType first.

### `gcp`

- **Planes:** identity, workload.
- **Identity storage:** Cloud Identity user custom attributes (schema-defined custom-attribute keys named for the facet).
- **Workload storage:** resource labels on Compute Engine instances (label key = lowercased facet name; label values are constrained to `[a-z0-9_-]`, so the mapping lowercases/normalizes facet values and records the normalization in `notes`).
- **Endpoint resolution:** commercial Cloud Identity and Compute endpoints.
- **Overflow:** label-count and charset limits apply on the workload plane — `priority` overflow plus value normalization handled in the mapping.

### `okta`

- **Planes:** identity.
- **Identity storage:** Universal Directory custom profile attributes (custom schema properties named for the facet).
- **Endpoint resolution:** the org's commercial API endpoint (resolved, never hardcoded).
- **Overflow:** none — Universal Directory custom attributes are arbitrary; all 15 facets bind natively.
- **Note:** Okta is the cleanest pure-identity profile; it is a strong first beachhead alongside `ldap`.

### `ldap`

- **Planes:** identity.
- **Identity storage:** directory attributes. Two binding modes: **schema-extension** (a governed auxiliary objectClass exposing 15 attributes named for the facets — preferred where schema changes are permitted), or **reserved-attribute** (map facets onto unused standard attributes via a tenant locator table — for directories where schema extension is not allowed).
- **Endpoint resolution:** the directory host/port from operator config; commercial/on-prem only.
- **Overflow:** none in schema-extension mode; in reserved-attribute mode, `priority` overflow when fewer than 15 reserved attributes are available.

### `vmware` (three-plane proof)

VMware is bound across all three planes — the proof that the contract is not IdP-centric.

- **Identity plane — Workspace ONE Access:** user attributes (custom user-attribute keys named for the facet), sourced from the directory of record and projected onto Access user profiles for SSO/Conditional-Access-equivalent policy.
- **Workload plane — vSphere / vCenter:** tags organized into one **category per facet** (category name = facet name; tag name = facet value). vSphere tag categories with single-cardinality enforce one value per facet per VM, matching the one-facet-per-slot discipline of the reference profile.
- **Enforcement plane — NSX:** security tags / security groups. Facet values become NSX security tags on VMs; facet predicates compile to NSX groups with tag-based membership (see Zero Trust below).
- **Endpoint resolution:** commercial vCenter / NSX manager / Workspace ONE Access endpoints from operator config.
- **Overflow:** vSphere tag-category count is generous; `priority` overflow only if a tenant caps categories. NSX security-tag scope holds the enforcement-relevant subset (typically Department, Division, Role, Classification, AccountType).
- **Naming note:** locators are pinned to product *surfaces* (Workspace ONE Access attributes, vSphere tags/categories, NSX security tags/groups), not brand names, to limit post-acquisition churn.

### `pingone` (ADR-099)

- **Planes:** identity.
- **Identity storage:** PingOne directory custom user attributes (custom attribute keys named for the facet).
- **Endpoint resolution:** the PingOne region API endpoint from operator config (resolved, never hardcoded); commercial only.
- **Overflow:** none — PingOne custom attributes are arbitrary; all 10 named facets bind natively.
- **Carriage note:** PingFederate is the federation hub for runtime claim carriage to relying parties (see "Facet carriage"); this profile governs directory *storage*, not token emission. PingOne (directory) is the storage surface; PingFederate (federation) and PingDirectory are distinct Ping surfaces — locators pin to PingOne directory attributes to limit brand-surface churn.

### `keycloak` (ADR-099)

- **Planes:** identity.
- **Identity storage:** Keycloak user attributes (arbitrary key/values named for the facet). Applies equally to the Red Hat build of Keycloak.
- **Endpoint resolution:** the Keycloak realm admin REST endpoint from operator config; commercial / on-prem only.
- **Overflow:** none — user attributes are arbitrary; all 10 named facets bind natively.
- **Carriage note:** protocol mappers project attributes into OIDC / SAML tokens per "Facet carriage". This is the open-source counterpart to the `okta` profile.

### `auth0` (ADR-099)

- **Planes:** identity.
- **Identity storage:** the Auth0 user profile `app_metadata` namespace (administrator-controlled, not user-editable — distinct from `user_metadata`). Locators are the bare facet names scoped to `app_metadata`, recorded as a profile-level note rather than repeated per locator.
- **Endpoint resolution:** the Auth0 tenant Management API endpoint from operator config; commercial only.
- **Overflow:** none — `app_metadata` is an arbitrary object; all 10 named facets bind natively.
- **Carriage note:** a custom Auth0 Action surfaces facets as token claims per "Facet carriage". This is the CIAM-oriented identity profile.

## Zero Trust — OrgPath as the cross-vendor policy subject

Zero Trust requires that every access and segmentation decision be made against a verified subject, continuously, with least privilege. The hard part in a mixed estate is that each enforcement surface speaks its own dialect of "who/what is this." OrgPath solves this at the substrate layer: **the codebook facet set is the stable, vendor-independent policy subject**, and each binding profile's read side projects facets onto the native policy construct of an enforcement surface. A microsegmentation rule is authored once against facets and compiles per vendor.

This is complementary to `uiao.adapters.zta`, which is a read-only digest of a Microsoft tenant's Zero Trust *assessment* (posture scoring). This section concerns the *enforcement subject* across vendors — what policy is written against, not how a single tenant is scored.

### OrgPath as the Zero Trust policy subject

A facet predicate is a boolean expression over codebook facets — e.g. `Department=IT AND Classification=Contractor AND ClearanceLevel<Secret`. Because facets are profile-agnostic, the same predicate is meaningful whether the subject was stamped via the `microsoft-entra`, `okta`, `aws`, or `vmware` profile. The predicate is the unit of policy authoring; the profile is the unit of projection. This is the OrgPath analog of attribute-based access control, with the codebook supplying the governed, drift-checked attribute vocabulary.

### Facet-driven microsegmentation — projection to native enforcement constructs

The enforcement projection resolves a facet predicate to the native dynamic-membership construct of each surface. The construct evaluates the facet values stored by that surface's binding profile (NSX security tags, cloud resource tags, etc.), so membership stays live as facets change.

| Enforcement surface | Native construct | How the facet predicate projects |
|---|---|---|
| VMware NSX | Security group with tag-based membership | Predicate → group whose membership criteria match NSX security tags (one tag per facet value) |
| Palo Alto NGFW | Dynamic Address Group (DAG) | Predicate → DAG match criteria over tags registered for the workload |
| Elisity | Policy group | Predicate → policy group keyed on the identity/asset attributes Elisity ingests (Entra/AD/Intune and peers) |
| AWS | Security group / referenced resource tags | Predicate → tag-scoped security-group references or policy conditions over resource tags |
| GCP | Firewall rules with network tags / secure tags | Predicate → secure-tag-scoped firewall rules (facet values normalized to the GCP charset) |
| Microsoft (reference) | Dynamic group / Conditional Access | Predicate → dynamic membership rule over `onPremisesExtensionAttribute` slots (UIAO_152) |

The projection table is normative for *which construct* a profile targets; the executable predicate→construct compiler is part of the enforcement-adapter implementation phase, with conformance tests per surface.

### Least privilege and conditional access via facet predicates

Least-privilege entitlements and conditional-access-equivalent policies are authored as facet predicates rather than per-system group sprawl. `Role=Engineer AND Division=CyberOps` scopes a privileged entitlement; `Classification=Contractor` triggers step-up or session constraints. Because the predicate vocabulary is the codebook, entitlement reviews and access certifications reason over the same governed facets the drift engine validates — closing the gap between "what policy says" and "what identity actually carries."

### Continuous verification — drift as a Zero Trust signal

Zero Trust's "continuously verify" tenet maps directly onto OrgPath drift. The drift engine (UIAO_163) validates observed facet values against the codebook independently of storage profile, emitting `DRIFT-IDENTITY` when a subject's facets diverge from canon (uncaptured, stale, deprecated, or out-of-enumeration values). A facet that drifts is a subject whose policy projection is no longer trustworthy — so DRIFT-IDENTITY is a first-class continuous-verification signal that should gate or flag enforcement, not merely a governance report. The overflow rule's "uncaptured" facets surface as DRIFT-IDENTITY by the same path, so a slot-poor target cannot silently degrade the Zero Trust subject.

### Mapping to the CISA Zero Trust Maturity Model pillars

OrgPath binding profiles touch every ZTMM pillar by giving each a common subject:

| ZTMM pillar | OrgPath contribution |
|---|---|
| **Identity** | The facet set is the governed identity attribute vocabulary; identity-plane profiles (Entra, Okta, LDAP, AWS Identity Center, GCP Cloud Identity, Workspace ONE Access) store it. |
| **Devices** | Workload-plane profiles (Arc tags, EC2/Compute tags, vSphere tags) carry facets onto device/VM objects, so device policy reasons over the same subject as identity policy. |
| **Networks** | Enforcement projection compiles facet predicates to network-segmentation constructs (NSX groups, DAGs, firewall tags). |
| **Applications & Workloads** | Workload tags + enforcement groups scope app/workload access by facet. |
| **Data** | Classification and ClearanceLevel facets are the data-sensitivity subject for downstream data-access policy. |
| **Cross-cutting: Visibility & Analytics** | Drift telemetry (DRIFT-IDENTITY) is the continuous-verification feed. |
| **Cross-cutting: Governance** | The codebook + binding profiles are the governed control plane; changes flow through the canon ADR process. |

## Drift and reconciliation across profiles

Drift is profile-agnostic at the value layer: the engine validates facet values against the codebook regardless of where they are stored. Two profile-specific drift conditions are added by this spec:

- **Uncaptured-facet drift** — a facet that the profile's overflow rule could not store natively; surfaced as DRIFT-IDENTITY "uncaptured" so it is never silently lost.
- **Cross-profile divergence** — when the same subject is represented under more than one profile (e.g. an identity stamped in Entra and projected to NSX), the reconciled cross-boundary plane compares facet values across profiles; a mismatch is DRIFT-IDENTITY "cross-profile". This is the multi-cloud generalization of the single-plane reconciliation ADR-035 noted as deferred.

## Relationship to existing canon

- **UIAO_151 (codebook)** — unchanged SSOT for facet semantics and value enumerations. This spec stores and projects those facets; it never redefines them.
- **ADR-078** — its slot table is now the content of the `microsoft-entra` reference profile.
- **ADR-035** — its executable-codebook binding is generalized here across profiles; the YAML↔narrative reconciliation caveat applies per-profile.
- **ADR-098** — authorizes this spec and the binding-profile model (the original six targets).
- **ADR-099** — amends ADR-098 §D3 to add the `pingone` / `keycloak` / `auth0` identity-plane targets specified above.
- **UIAO_152 / UIAO_154** — dynamic groups and Administrative Units are the Microsoft profile's projection; the enforcement-projection table generalizes that pattern across vendors.
- **UIAO_163** — the drift engine consumes facets from any profile; this spec adds the uncaptured and cross-profile drift conditions.
- **`uiao.adapters.zta`** — complementary read-only Zero Trust assessment digest; this spec is the enforcement subject, not posture scoring.
- **UIAO_012 / UIAO_013** — certificate carriage (NAC / 802.1X) and the Zero Trust / SASE access-decision transport; the "Facet carriage" section above is the multi-IdP federation analog of UIAO_012's cert carriage and feeds UIAO_013's SASE consumers.

## Boundary and handling

All profiles and their transports are **Moderate and Commercial only**. No GovCloud, sovereign, or high-side endpoints are specified or permitted; the `commercial` cloud value also serves GCC-Moderate per ADR-033. Facet values projected onto enforcement surfaces are organizational metadata, not secrets, but the *combination* of Classification/ClearanceLevel facets with subject identity is sensitive and is handled in-boundary. A new high-side boundary, if ever required, is introduced only with its own authorizing ADR per the AGENTS.md boundary-enum rule.

## Implementation roadmap (authorized by ADR-098, deferred from this spec)

This document is the specification; the following are the implementation deliverables it targets, each landing with happy-path + failure-mode tests:

1. **Binding-profile JSON Schema** — `src/uiao/schemas/orgpath/binding-profile.schema.json` implementing the normative table above.
2. **Executable per-target profiles** — `src/uiao/canon/data/orgpath/binding-profiles/{microsoft-entra,aws,gcp,okta,ldap,vmware,pingone,keycloak,auth0}.yaml` (the last three per ADR-099, shipped at `status: proposed`).
3. **Per-target mapping + transport modules** — `<target>_mapping.py` (Source→facet) and `<target>_transport.py`, mirroring `ad_mapping.py` / Graph / ARM transports; commercial/Moderate endpoint resolution only.
4. **Adapter-registry entries** — non-Microsoft identity adapters register `mission-class: identity` (a first), read-only assessors as `class: conformance`.
5. **Enforcement-projection compiler** — facet predicate → native policy construct per surface (NSX, Palo Alto, Elisity, AWS, GCP), with per-surface conformance tests.
6. **Platform wiring** — extend `orgtree assess` / `govern` to accept a `--profile` selector; extend the multi-cloud SaaS governance plane to span profiles.
7. **Carriage transports** — a SCIM 2.0 client transport (custom schema extension) and a token-claim mapping projector (SAML / OIDC), each emitting DRIFT-IDENTITY on carriage divergence, per "Facet carriage" above. A `generic-scim` profile, if adopted, follows the ADR-098 target-list process.

## References

- [ADR-098 — OrgPath Vendor-Neutral Binding Profiles](adr/adr-098-orgpath-vendor-neutral-binding-profiles.md)
- [ADR-099 — OrgPath Binding-Profile Targets — IdP Expansion (PingOne, Keycloak, Auth0)](adr/adr-099-orgpath-idp-binding-profile-expansion.md)
- [ADR-078 — OrgPath Attribute Schema (15-Facet)](adr/adr-078-orgpath-attribute-schema-15-facet.md)
- [ADR-035 — OrgPath Codebook Executable Binding](adr/adr-035-orgpath-codebook-binding.md)
- [ADR-085 — Universal-Enterprise Positioning](adr/adr-085-universal-enterprise-positioning.md)
- [UIAO_151 — OrgPath Codebook](UIAO_151_OrgPath_Codebook.md)
- [UIAO_163 — Drift Detection Engine Specification](UIAO_163_Drift_Detection_Engine_Specification.md)
- CISA Zero Trust Maturity Model — pillar reference for the ZT projection mapping.
