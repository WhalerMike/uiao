---
adr_id: adr-136
title: "SailPoint IdentityIQ — Option-C Slot Allocation and Vendor Contract Pin"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-08-20
next_review: 2027-02-20
review_trigger: The target deployment's IdentityIQ version is confirmed (this ADR pins the 9.0 spec on a documented assumption); the `sailpoint-iiq-governance` slot promotes from reserved to active (a per-adapter activation ADR is required first); the deployment-half object-model export lands (UIAO_210 §4); SailPoint publishes a 10.x IIQ line or retires the 9.0 spec; the branded "SAM" deployment is confirmed to be ISC-based rather than IdentityIQ, which would retire this ADR by supersession
impact: "Adopts Option C — the IdentityIQ on-prem path that ADR-059 recorded as a deliberate alternative and never decided — narrowly, for a single read-only conformance slot. Allocates `sailpoint-iiq-governance` at `status: reserved`, and pins the vendor half of its contract as UIAO_210 (SailPoint's own OpenAPI spec, vendored verbatim and hash-anchored, at upstream commit 9b7cb428). Unlike ADR-059 and ADR-135, this allocation requires NO boundary expansion: IdentityIQ is customer-hosted inside the agency boundary, so the slot takes the existing `gcc-moderate` value, the `gcc-boundary` schema enum is unchanged, and AGENTS.md's Commercial-exception list is untouched — this ADR adds no fourth exception. Establishes the two-part contract doctrine for deployment-customised vendor products: the vendor spec is only half, and a site-local object-model export is the other half, required before activation. Registry-shaped and pin-shaped; no runtime code, no schema change, no adapter implementation."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-136-sailpoint-identityiq-option-c-slot-allocation.html
---

# ADR-136: SailPoint IdentityIQ — Option-C Slot Allocation and Vendor Contract Pin

## Status

**PROPOSED** — 2026-08-20

## Context

### Thread 1 — Option C was recorded and never decided

[ADR-059](adr-059-sailpoint-adapter-family.md) §Decision 1 named three paths for
SailPoint in UIAO and adopted exactly one:

- **Option A** — NERM only, narrow Commercial-exception carve-out. *Adopted.*
- **Option B** — the full ISC family with a broader boundary expansion.
  *Deferred to a future ADR; later ratified by [ADR-135](adr-135-sailpoint-isc-governance-option-b-ratification.md), narrowly.*
- **Option C** — **IdentityIQ on-prem only.** *Recorded as a deliberate
  alternative in §Notes. Never decided, before or since.*

The registry reflects that history exactly: `sailpoint-nerm`,
`sailpoint-isc-governance`, and `sailpoint-machine-identity` all exist as
reserved slots. There is no IdentityIQ slot anywhere in either registry.

### Thread 2 — the deployment in front of us is Option C

The agency's access-request and certification system is branded **Systems
Access Manager (SAM)**. SAM is not a SailPoint product name — the SKU list is
Identity Security Cloud, IdentityIQ, File Access Manager, Cloud Access
Management, and NERM. SAM is a local brand over a SailPoint deployment, and the
signals point to IdentityIQ: an internally-branded portal, a customer-hosted
footprint, and an AD-mastered estate of twelve trees whose org topology SAM
reads to route access requests and certifications.

That matters because the API surfaces are not interchangeable. ISC is a
continuously-versioned cloud REST API; IdentityIQ is a versioned on-premises
product whose integration surface is SCIM 2.0 plus a core REST API tied to the
installed release. Binding SAM work to `sailpoint-isc-governance` would bind it
to the wrong product, the wrong contract, and the wrong boundary value.

### Thread 3 — a boundary expansion is not required here, and that is the point

ADR-059 and ADR-135 each had to buy their slot with a Commercial exception,
because NERM and ISC are SailPoint-hosted SaaS. IdentityIQ is not: it runs on
customer infrastructure, inside the agency's own boundary. The
`gcc-boundary: gcc-moderate` value already covers it. No enum extension, no
AGENTS.md amendment, no fourth named exception.

This is the cheapest SailPoint slot UIAO can allocate, and the asymmetry is
worth stating rather than leaving implicit: the deployment model, not the
vendor, determines the boundary cost.

### Thread 4 — write the contract down before writing the code

The ServiceNow adapter was built from vendor documentation and compiled its
hostname in. It named the commercial cloud in the collector and adapter, an
invented `.gov` domain in two orchestrators, and the commercial host again in
the test fixtures — which meant the recorded contract asserted the bug and no
gate could see it. The defect class was not "someone typed the wrong string";
it was "there was no artifact any gate could compare the code against."

IdentityIQ is the opportunity to not repeat that. No adapter code exists yet,
so the contract can be pinned first and the implementation reviewed against it.

## Decision

Six positions.

### 1. Adopt Option C, narrowly, for one read-only conformance slot

This ADR adopts the IdentityIQ path ADR-059 recorded and left open — scoped to
a **single conformance (read-only) slot**. It does not allocate a modernization
sibling, does not activate anything, and does not extend to File Access Manager
or Cloud Access Management, which are separate products with separate surfaces
and deserve their own decisions if they ever arrive.

### 2. Allocate `sailpoint-iiq-governance` as reserved

One new slot in `src/uiao/canon/adapter-registry.yaml`:

| Adapter id | Registry | class | mission-class | Initial status |
|---|---|---|---|---|
| `sailpoint-iiq-governance` | conformance | conformance | identity | reserved |

Per [ADR-059](adr-059-sailpoint-adapter-family.md) §Decision 6 and ADR-049
precedent, this ADR is registry-shaped, not implementation-shaped. The slot
lands `reserved`; activation requires a per-adapter ADR modeled on ADR-035.

The slot binds to ADR-092's **identity** control-plane slot at **rung L1
(Observe)**, matching its `ssot-mutation: never` declaration — the same posture
ADR-135 §Decision 3 set for `sailpoint-isc-governance`, and for the same
reason.

### 3. No boundary expansion — `gcc-moderate`, unchanged enum

`sailpoint-iiq-governance` takes `gcc-boundary: gcc-moderate`. The
`gcc-boundary` enum in `adapter-registry.schema.json` is **not** extended, and
AGENTS.md's cloud-boundary statement is **not** amended. UIAO's Commercial
exceptions remain exactly three: Amazon Connect, SailPoint NERM, SailPoint ISC
Governance.

This is a substantive decision, not a formality. Had SAM been ISC-based, this
ADR would have had to justify a fourth exception. It does not, because
IdentityIQ is customer-hosted.

### 4. Pin the vendor contract as UIAO_210

[UIAO_210](../specs/external/sailpoint-iiq/UIAO_210_identityiq-api-contract-pin.md)
pins SailPoint's own OpenAPI 3.0.3 specification for IdentityIQ 9.0, vendored
verbatim from `sailpoint-oss/api-specs` at commit `9b7cb428`, hash-anchored at
SHA-256 `36158d39…d028e9b0`, under its MIT license with the license text
carried alongside. The 8.3 SCIM-only spec at the same commit is recorded by
hash as the 8.x fallback but not vendored.

Two scope exclusions are load-bearing and are decided here, not left to
implementer discretion:

- **`/identityiq/ui/rest/*` is out of contract.** It is 304 of the spec's 504
  paths and it is the IIQ web console's own backend — exhaustively documented,
  not a supported integration surface. An adapter binding to it is a
  `DRIFT-PROVENANCE` finding.
- **The spec's `basicAuth` declaration is not an authorization.** It is the
  only security scheme the vendor spec declares. The adapter's actual
  authentication — OAuth2 client credentials or mTLS — is an activation-ADR
  decision with a certificate anchor recorded in the registry.

### 5. The contract has two halves; the second one gates activation

A vendor spec describes IdentityIQ as shipped. It cannot describe a branded,
customised deployment — custom Capabilities and SPRights (the
`IDM.SailPointSecurity` class of object), Workgroups used as certification
targets, onboarded Applications and their account schemas, plugin-supplied
endpoints, BeanShell rules.

Per UIAO_210 §4, a **site-local object-model export** is committed beside the
vendor pin, hash-anchored the same way, before the slot leaves `reserved`. The
exports carry configuration inventory only — object names, schemas, and rights
— never account records or entitlement assignments, consistent with the slot's
`object-identity-only` declaration.

This generalises beyond SailPoint. Any vendor product whose real contract is
substantially deployment-defined — ServiceNow's `sys_dictionary` is the other
live example — needs both halves, and pinning only the vendor half is a false
sense of coverage.

### 6. Activation gates

The per-adapter activation ADR must record, at minimum:

1. **The confirmed IdentityIQ version**, and whether the 9.0 pin or the 8.3
   fallback is the operative contract. This ADR pins 9.0 on a documented
   assumption; it does not pretend the version is known.
2. **The confirmed product identity** — that SAM is IdentityIQ. If it proves
   ISC-based, this ADR is retired by supersession and the work returns to
   `sailpoint-isc-governance`.
3. **The authentication mechanism and certificate anchor**, per §4 above.
4. **The deployment-half exports**, per §5.
5. **SSOT-conflict resolution**, per ADR-059 §Decision 5. IdentityIQ ships
   native AD and Entra connectors that overlap `active-directory`, `entra-id`,
   and `entra-id-governance`. UIAO holds SSOT for Entra/AD writes; the
   activation ADR declares which sources IIQ reads and the fail-closed
   behaviour if it attempts a write to a UIAO-SSOT object. The concern is
   bounded here — the slot is conformance-only and `ssot-mutation: never` —
   but the contract must record it.

## Consequences

### Positive

- SAM work has a correct home. It is no longer forced onto an ISC slot that
  names the wrong product and the wrong boundary.
- The contract exists before the code, so the first adapter commit can be
  reviewed against something, and upstream drift surfaces as a diff.
- No boundary cost. The cheapest SailPoint slot in the registry, because of
  where the product runs.
- The two-part pin doctrine is now written down and immediately reusable for
  ServiceNow, whose deployment half is equally unpinned today.
- The SCIM surface layers cleanly on the existing UIAO_143 (RFC 7643) pin
  rather than inventing a parallel wire format.

### Negative / costs

- A 2.6 MB YAML artifact enters canon — by a wide margin the largest tracked
  text file in the repo. It is under the 4 MB pre-commit guard, and the
  alternative (a pin that cannot be verified offline) defeats the purpose.
- The pinned version rests on an unconfirmed assumption. Mitigated by making
  confirmation an explicit activation gate rather than a silent premise.
- A fourth reserved SailPoint slot, none of them activated. The registry now
  records more SailPoint intent than SailPoint integration. That is a real
  accumulation cost, accepted because reserving is how this repo records a
  decision without pretending to have built anything.

### Risks

- **SAM is ISC-based after all.** Retire by supersession; the pin is discarded
  and the work returns to `sailpoint-isc-governance`. Cost is one ADR and one
  vendored file, no code.
- **The pinned spec is inaccurate.** SailPoint's IIQ specs have known
  OpenAPI-generator validity problems upstream (`api-specs` issue #61). A pin
  makes the contract fixed and inspectable, not correct. Codegen may require
  patching; patches belong in the adapter, never in the vendored file.
- **The deployment export never gets taken**, leaving the slot reserved
  indefinitely. This is the honest outcome if nobody can run an export — better
  than an adapter built against guesses about custom object names.

## Notes

### Relationship to the other SailPoint slots

| Slot | Product | Hosting | Boundary | Ratified by |
|---|---|---|---|---|
| `sailpoint-nerm` | NERM | SailPoint SaaS | `commercial-exception-sailpoint-nerm` | ADR-059 |
| `sailpoint-isc-governance` | ISC Governance | SailPoint SaaS | `commercial-exception-sailpoint-isc` | ADR-135 |
| `sailpoint-machine-identity` | ISC Machine Identity | SailPoint SaaS | `commercial-exception-sailpoint-isc` | *un-ratified* |
| `sailpoint-iiq-governance` | IdentityIQ | Customer-hosted | `gcc-moderate` | **this ADR** |

These are four distinct products, not naming variants. This ADR does not
ratify, alter, or activate any of the first three.

### Out of scope

- File Access Manager and Cloud Access Management — separate products, separate
  surfaces, no slot allocated here.
- Any modernization-side (write) IIQ slot.
- Adapter implementation, client codegen, and test fixtures.
- The ServiceNow deployment-half pin, which §5 argues for but does not perform.

### Pattern model

ADR-059 (slot allocation shape), ADR-135 (narrow ratification of a deferred
option), ADR-049 (multi-slot allocation precedent), UIAO_143 (external-spec pin
shape: verbatim artifact, hash anchor, supersession rather than in-place edit).
