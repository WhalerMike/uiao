---
adr_id: adr-113
title: "OrgPath IdP Transport Activation — Keycloak / Auth0 / PingOne Write Seams (Stage 1)"
status: PROPOSED
decided: 2026-06-19
deciders: Michael Stratton
updated: 2026-06-19
next_review: 2026-12-19
review_trigger: A live-tenant conformance run is added for any of the three transports; a customer declares one of these IdPs as an active binding target; the AWS/GCP/VMware multi-plane transports are proposed (Stage 2); the binding-profile schema changes in a way that affects identity-plane write semantics.
impact: 'Activates the write-back transports for three ADR-099 identity-plane binding profiles — keycloak, auth0, pingone — as the first implementation stage authorized by ADR-098 §D6. Adds uiao.adapters.keycloak_transport, auth0_transport, and pingone_transport (httpx lazy-imported, callable + apply seam modeled on uiao.adapters.okta_transport) with happy-path + failure-mode tests in tests/test_orgpath_idp_transports.py. Registers keycloak-orgpath, auth0-orgpath, and pingone-orgpath as mission-class: identity modernization adapters at status=proposed. Changes no facet semantics (UIAO_151), no profile YAML, no Microsoft runtime behavior, and no boundary scope (Moderate/Commercial only). The AWS, GCP, and VMware profiles remain transport-deferred and are explicitly staged to a follow-on ADR because they are multi-plane and require cloud SDKs.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-113-orgpath-idp-transport-activation.html
---

# ADR-113: OrgPath IdP Transport Activation — Keycloak / Auth0 / PingOne (Stage 1)

## Status

**PROPOSED** — 2026-06-19.

This ADR is the implementation increment authorized in advance by
[ADR-098 §D6](adr-098-orgpath-vendor-neutral-binding-profiles.md) ("executable
canon is deferred to implementation") and predicted by the
[ADR-099](adr-099-orgpath-idp-binding-profile-expansion.md) review trigger
("The first PingOne / Keycloak / Auth0 binding-profile write-back transport
ships"). It ships code and registry entries; it changes no doctrine.

## Context

ADR-098 decoupled the OrgPath 15-facet model from the Microsoft
`onPremisesExtensionAttribute1..15` storage slots and recast the slot table as
the `microsoft-entra` reference binding profile, declaring AWS, GCP, Okta,
generic LDAP, and VMware as first-class targets. ADR-099 added three more
identity-plane targets — **Keycloak / Red Hat build of Keycloak**, **Auth0**,
and **PingOne** — each a pure-identity profile on the `okta` shape (the ten
named codebook facets as custom user attributes, no overflow).

Both ADRs deferred the per-target *write-back transports* to implementation.
The result was an asymmetry: the executable profile YAMLs exist and load under
`schemas/orgpath/binding-profile.schema.json`, the planner
(`uiao.modernization.orgtree.profile_assign.BindingProfilePlanner`) routes
facet writes to their locators, and the Okta and LDAP profiles have shipped
transports (`okta_transport.py`, `ldap_transport.py`) — but Keycloak, Auth0,
and PingOne had a profile and a plan with **no write seam**. A planned
operation set for those three could be computed but not applied.

These three are the lowest-risk transports to ship first:

- They are **pure-identity, single-plane** profiles — no workload tags, no
  enforcement groups, no overflow rule to exercise.
- They are **HTTP/bearer-token** APIs that fit the existing
  `(method, path, body) -> dict` callable pattern exactly, so no new transport
  abstraction is needed.
- Keycloak gives the **open-source IdP estate** a covered write path, directly
  advancing the ADR-085 vertical-agnostic positioning for customers who do not
  run a commercial IdP.

The AWS, GCP, and VMware profiles are multi-plane (identity + workload, and for
VMware + enforcement) and require cloud SDKs and the per-profile overflow rule.
They are deliberately **not** in this stage.

## Decision

### D1. Ship the three identity-plane write transports

Add three transport modules under `src/uiao/adapters/`, each modeled
byte-for-byte on `okta_transport.OktaTransport` (lazy `httpx` import; callable
`(method, path, body) -> dict`; `from_environment` constructor that takes
operator-supplied config and never hardcodes a host; `apply(operations)`
convenience that dispatches **only** `op == "write"` operations and silently
ignores `uncaptured` overflow casualties so they remain visible as drift):

| Module | Class | Native write |
|---|---|---|
| `keycloak_transport.py` | `KeycloakTransport` | `PUT /admin/realms/{realm}/users/{id}` with `attributes: {facet: [value]}` |
| `auth0_transport.py` | `Auth0Transport` | `PATCH /api/v2/users/{id}` with `app_metadata: {facet: value}` |
| `pingone_transport.py` | `PingOneTransport` | `PATCH /v1/environments/{env}/users/{id}` with `{facet: value}` |

Each carries a Bearer access token and resolves its base URL (and realm /
environment id where applicable) from operator config. Only commercial /
on-prem endpoints are in scope (Moderate/Commercial boundary per ADR-098 §D4).

### D2. Register the three adapters

Add three `mission-class: identity` modernization adapters to
`src/uiao/canon/modernization-registry.yaml`, modeled on `okta-orgpath`, each
at `status: proposed`, `ssot-mutation: never`, `gcc-boundary: gcc-moderate`,
referencing UIAO_193 and pointing `implementation.python_module` at the new
transport and `implementation.tests` at `tests/test_orgpath_idp_transports.py`.

| Adapter id | Vendor | License |
|---|---|---|
| `keycloak-orgpath` | Red Hat / Keycloak community | Apache-2.0 |
| `auth0-orgpath` | Okta (Auth0) | Commercial |
| `pingone-orgpath` | Ping Identity | Commercial |

### D3. Profiles, schema, and codebook are untouched

No profile YAML changes status, the codebook (UIAO_151) is unchanged, and the
Microsoft reference profile and its runtime are byte-for-byte undisturbed. This
ADR adds a write seam to existing plans; it does not alter what a plan contains.

### D4. AWS / GCP / VMware are explicitly staged to a follow-on ADR

The remaining ADR-098 targets are multi-plane and SDK-bound. Their transports,
the per-profile overflow rule, and the enforcement-plane projection (VMware
NSX) are **Stage 2**, to be authorized by a separate ADR with cloud-SDK
dependency declarations. This ADR closes the IdP write-seam gap only.

## Consequences

**Positive**

- The three highest-demand non-Microsoft IdPs (Keycloak, Auth0, PingOne) move
  from *plan-only* to *plan-and-apply*; the "OrgPath governs any IdP" claim is
  now demonstrable end-to-end for five IdPs (Entra, Okta, LDAP + these three).
- The open-source estate (Keycloak) has a covered write path with no commercial
  IdP dependency, advancing ADR-085 positioning.
- Zero blast radius on the Microsoft estate: the reference profile, drift
  engine, dynamic-group library, and device adapters are untouched.

**Negative / deferred**

- The transports are unit-tested against recording fakes, not live tenants; a
  live-tenant conformance harness is follow-on work (it is this ADR's review
  trigger).
- AWS/GCP/VMware remain transport-deferred — the multi-cloud *workload* and
  *enforcement* story is not advanced by this stage.
- Adapters land at `status: proposed`; promotion to `active` requires the live
  conformance run per the established `okta-orgpath` precedent.

## Alternatives considered

1. **Ship all six remaining targets at once.** Rejected: AWS/GCP/VMware are
   multi-plane and SDK-bound; bundling them would delay the clean IdP win and
   mix a large, dependency-heavy change with three trivial ones. The
   "one or more, staged" path is the sanctioned pattern.
2. **Leave the three as plan-only until a customer demands one.** Rejected: the
   asymmetry (plan with no apply) is a latent trap, and Keycloak coverage is a
   standing positioning gap, not a speculative feature.

## Related work

- [ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md) — authorizes
  binding-profile transports as deferred implementation (§D6).
- [ADR-099](adr-099-orgpath-idp-binding-profile-expansion.md) — adds the
  keycloak / auth0 / pingone profiles whose transports this ADR ships.
- [ADR-085](adr-085-universal-enterprise-positioning.md) — vertical-agnostic
  positioning this stage operationalizes for the open-source IdP estate.
- `uiao.adapters.okta_transport` / `uiao.adapters.ldap_transport` — the
  shipped-transport precedent these three follow.
- [UIAO_193](../UIAO_193_OrgPath_MultiCloud_Binding.md) — the binding-profile
  specification.
