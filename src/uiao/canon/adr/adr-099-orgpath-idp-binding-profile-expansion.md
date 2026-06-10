---
adr_id: adr-099
title: "OrgPath Binding-Profile Targets — IdP Expansion (PingOne, Keycloak, Auth0)"
status: PROPOSED
decided: 2026-06-10
deciders: Michael Stratton
updated: 2026-06-10
next_review: 2026-12-10
review_trigger: The first PingOne / Keycloak / Auth0 binding-profile write-back transport ships; a customer declares one of these IdPs as a binding target; a fourth IdP is proposed for first-class status; the binding-profile schema is changed in a way that affects identity-plane profiles.
impact: 'Amends ADR-098 §D3 by adding three identity-plane targets — PingOne (Ping Identity), Keycloak / Red Hat build of Keycloak, and Auth0 — to the first-class OrgPath binding-profile target list. Each is a pure-identity profile modeled on the okta reference shape (the 10 named codebook facets as custom directory attributes, no overflow). Adds three executable profile YAMLs at status=proposed, extends CANONICAL_PROFILE_IDS, and updates UIAO_193 with their per-target sections. Changes no facet semantics (UIAO_151), no Microsoft runtime behavior, and no boundary scope (Moderate/Commercial only). Per-target write-back/assess transports remain deferred to implementation, exactly as ADR-098 §D6 deferred them for the original six.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-099-orgpath-idp-binding-profile-expansion.html
---

# ADR-099: OrgPath Binding-Profile Targets — IdP Expansion

## Status

**PROPOSED** — 2026-06-10.

This ADR is doctrine pending Governance Board acceptance. It is a narrow,
additive amendment to [ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md):
it adds three identity-plane targets to the binding-profile target list and
nothing else. It introduces no new mechanism, schema field, or boundary
value. On acceptance it changes no runtime behavior; the executable profiles
it adds ship at `status: proposed` (specified, no transport yet), mirroring
the original six.

## Context

ADR-098 established the binding-profile abstraction — the codebook facet is
the canonical *subject*, a binding profile declares *where* each facet lives
on a target — and enumerated six first-class targets: `microsoft-entra`
(reference), `aws`, `gcp`, `okta`, `ldap`, `vmware`. [UIAO_193](../UIAO_193_OrgPath_MultiCloud_Binding.md)
specified them and #896 shipped the executable YAML + loader + schema.

ADR-098 deliberately enumerated a *closed* initial set and made adding a
target a governed decision (its §D3 is the SSOT for the target list). Three
identity providers come up repeatedly in mixed-estate identity governance and
are natural next targets:

- **PingOne (Ping Identity).** Common in large enterprise and federal-adjacent
  estates; PingOne directory holds arbitrary custom user attributes, and
  PingFederate is a federation hub for claim carriage (UIAO_193 §Facet carriage).
- **Keycloak / Red Hat build of Keycloak.** The dominant open-source IdP; user
  attributes are arbitrary key/values, making it a clean pure-identity target
  and the open-source counterpart to the `okta` profile.
- **Auth0.** Widely used for application/CIAM identity; facets live in the
  `app_metadata` namespace on the user profile.

All three are **pure-identity, attribute-arbitrary** providers — the same
shape as `okta`: the 10 named facets bind one-to-one as custom attributes
with no overflow. Adding them is therefore low-risk and mechanical; the only
reason it is an ADR at all is that ADR-098 §D3 is the governed SSOT for the
target list, so extending it is a doctrine change (per AGENTS.md invariant I5),
not a quiet edit.

### Why now, why these three, why not more

The portability of the OrgPath model is a recurring customer question, and
the binding-profile contract was built precisely so a new vendor is onboarded
by writing a profile, not by changing the core. These three are the highest-
demand identity targets not already covered. This ADR does **not** open the
list to arbitrary growth: each future target is its own governed decision.
SailPoint is intentionally **excluded** as a binding-profile *storage* target
— it is an IGA governance consumer (ADR-059 adapter family), not a directory
that stores facets; it reads facets to drive roles/correlation rather than
holding them as the system of record.

### Boundary scope

This decision and the profiles it adds are scoped to the **Moderate and
Commercial** boundaries only, identical to ADR-098 §"Boundary scope". Every
profile resolves only commercial / GCC-Moderate endpoints; no high-side
surfaces are in scope. A high-side boundary, if ever needed, is added with its
own authorizing ADR per the AGENTS.md boundary-enum rule.

## Decision

### D1. Three identity-plane targets are added to the ADR-098 §D3 list

The first-class binding-profile target list (ADR-098 §D3) is extended with:

| Profile | Plane(s) | Native storage surface |
|---|---|---|
| `pingone` | identity | PingOne directory custom user attributes (claim carriage via PingFederate) |
| `keycloak` | identity | Keycloak user attributes (custom key/values) |
| `auth0` | identity | Auth0 user profile `app_metadata` namespace |

The original six remain exactly as ADR-098 fixed them. This ADR adds rows; it
edits none.

### D2. Each is a pure-identity profile on the okta shape

All three bind the 10 named codebook facets (`region`, `department`,
`division`, `role`, `cost_center`, `classification`, `hire_date`, `term_date`,
`clearance_level`, `account_type`) as `custom_attribute` locators named for
the facet (snake_case), with **no overflow** — attribute surfaces are
arbitrary on all three. The five reserved codebook slots are unbound until a
tenant declares them, identical to `okta`. `auth0` records the `app_metadata`
namespace as a profile-level note; locators remain the bare facet names so
round-tripping is deterministic.

### D3. Profiles ship at `status: proposed`; transports deferred

The executable profiles (`pingone.yaml`, `keycloak.yaml`, `auth0.yaml`) ship
at `status: proposed` — specified and schema-valid, no shipped transport —
exactly as ADR-098 §D6 deferred transports for the original six. The
`<target>_mapping.py` / `<target>_transport.py` modules and any adapter-
registry entries (`mission-class: identity` per ADR-098 §D7) land in a later
implementation phase, each with happy-path + failure-mode tests.

### D4. `CANONICAL_PROFILE_IDS` is the code mirror of §D1

`uiao.modernization.orgtree.binding_profiles.CANONICAL_PROFILE_IDS` is
extended with the three ids so `load_all_binding_profiles()` loads and
validates them. The set in code and the §D1 list are the same fact in two
places; a divergence is a `DRIFT-PROVENANCE` signal (the UIAO_193 ↔ YAML
reconciliation caveat ADR-098 already noted, now spanning nine profiles).

### D5. No change to anything else

Facet semantics (UIAO_151), the binding-profile schema, the boundary enum,
the overflow rules, the enforcement-projection model, and all Microsoft
runtime behavior are unchanged. This ADR is purely additive to the target
list.

## Consequences

**Positive**

- The two highest-demand enterprise IdPs (PingOne, Keycloak) and the dominant
  CIAM IdP (Auth0) become first-class OrgPath targets — the portability story
  ADR-098 set up is now concrete for the IdP plane, not only the cloud plane.
- Zero marginal core change: the additions are data (YAML) + one tuple entry,
  proving the "onboard a vendor by writing a profile" claim.
- Keycloak gives the open-source estate a covered path, broadening reach
  beyond commercial SaaS IdPs.

**Negative / deferred**

- Nine profiles now share the UIAO_193-narrative ↔ executable-YAML
  reconciliation surface ADR-098 flagged; a cross-check job remains the right
  long-term fix.
- No transport ships here, so these targets are specified-but-not-executable
  until the implementation phase — the same state the original six are in.
- PingOne vs PingFederate vs PingDirectory are distinct Ping surfaces; the
  `pingone` profile pins to PingOne directory attributes for storage and notes
  PingFederate for claim carriage, to avoid brand-surface churn.

## Alternatives considered

1. **Leave the list at six; document the others as "write your own profile."**
   Rejected: these three are high-demand enough to warrant first-class,
   schema-valid, drift-checked profiles rather than per-customer reinvention —
   which is exactly the anti-pattern ADR-098 §Alternatives-1 rejected.
2. **Add SailPoint as a binding-profile target.** Rejected: SailPoint is an
   IGA *consumer* of facets (roles/correlation), not a directory that stores
   them as the system of record. It belongs to the ADR-059 adapter family and
   the enforcement/consumer plane, not the storage-contract list.
3. **Open the target list to any IdP via a generic profile.** Rejected for
   now: a `generic-scim` profile is the right vehicle for the long tail
   (UIAO_193 §Facet carriage roadmap) and is its own governed decision; this
   ADR keeps the first-class list curated.

## Related work

- [ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md) — establishes the binding-profile model and the original six-target list this ADR amends.
- [ADR-078](adr-078-orgpath-attribute-schema-15-facet.md) — the 15-facet model; its slot table is the `microsoft-entra` reference profile.
- [ADR-035](adr-035-orgpath-codebook-binding.md) — executable codebook binding generalized across profiles.
- [ADR-085](adr-085-universal-enterprise-positioning.md) — vertical-agnostic positioning this expansion operationalizes for the IdP plane.
- [ADR-059](adr-059-sailpoint-adapter-family.md) — SailPoint adapter family; why SailPoint is a consumer, not a storage profile.
- [UIAO_193](../UIAO_193_OrgPath_MultiCloud_Binding.md) — the binding-profile specification; gains `pingone` / `keycloak` / `auth0` per-target sections.

