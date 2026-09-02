---
document_id: UIAO_210
title: "SailPoint IdentityIQ REST API — Vendor Contract Pin"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-08-20"
updated_at: "2026-08-20"
---

# SailPoint IdentityIQ REST API — Vendor Contract Pin

> **Purpose:** Pin the SailPoint IdentityIQ (IIQ) REST API specification as the
> vendor half of the contract for the `sailpoint-iiq-governance` conformance
> adapter slot allocated by ADR-136. Establishes the machine-readable,
> hash-anchored baseline that adapter code is generated and validated against,
> so contract drift surfaces as a diff in CI rather than as a 404 at runtime.

## 1. Why this pin exists

The ServiceNow adapter was written from vendor documentation rather than from a
pinned contract, and compiled its hostname in. The result was code that named
the wrong cloud in three different ways at once, with test fixtures that
asserted the mistake — none of it visible to any gate. That failure mode is
general, not ServiceNow-specific: an integration written from memory or from a
rendered doc page has no artifact a gate can compare against.

This pin closes that gap for IdentityIQ before any adapter code exists:

- Endpoint paths, request shapes, and response schemas resolve to a specific
  file with a specific hash, not to "whatever the docs said when it was
  written."
- Adapter clients can be generated from the spec rather than hand-authored, so
  an upstream change lands as a codegen diff in review.
- Evidence provenance can cite a contract version, which the ADR-092 evidence
  model requires and which a doc URL cannot provide.

**Naming note.** The deployment this pin serves is branded locally as
**Systems Access Management (SAM)**. SAM is an agency brand, not a SailPoint SKU —
the product beneath it is IdentityIQ. Canon uses the product name; customer-
facing material may use either, but adapter code, registry entries, and
evidence records name IdentityIQ so the pinned contract is unambiguous.

## 2. Authority

| Field | Value |
|---|---|
| Document | IdentityIQ REST API (OpenAPI 3.0.3) |
| Authority | SailPoint Technologies, Inc. |
| Upstream repository | [`sailpoint-oss/api-specs`](https://github.com/sailpoint-oss/api-specs) |
| Upstream commit | `9b7cb428d723540e05028f9744bfc0c7afea6cfe` |
| Commit date | 2026-08-20T02:29:41Z |
| Upstream path | `iiq/sailpoint-api.iiq-9.0.yaml` |
| Local copy | [`sailpoint-api.iiq-9.0.yaml`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/external/sailpoint-iiq/sailpoint-api.iiq-9.0.yaml) |
| SHA-256 | `36158d39dbaae28b429194c15ef6eb6ac119b048b2cd7e42f8531a9dd028e9b0` |
| Bytes / lines | 2,623,953 / 65,809 |
| Declared version | `9.0` |
| License | MIT — local copy at [`LICENSE`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/external/sailpoint-iiq/LICENSE), SHA-256 `9096681806a53effbc2c338eb609b7f62c06c36e841bc0ef1a0668ed073b1c4e` (LF-normalised by repo tooling; upstream `89be0d33…af315994`) |

The spec is preserved verbatim as distributed, in YAML, so that future hash
comparisons against the upstream repository remain a byte comparison. It is not
reformatted, not re-serialised to JSON, and not dereferenced.

The spec file is byte-identical to upstream — it arrived LF-only, so the
repo's line-ending normalisation left it untouched, and its SHA-256 above is a
direct upstream comparison. The `LICENSE` copy did get normalised, hence the
two hashes on that row. The spec is the contract anchor; the license is
attribution.

### 2.1 Fallback for 8.x deployments

The same upstream commit carries a second, narrower IIQ spec covering the SCIM
surface only, for deployments still on the 8.x line:

| Field | Value |
|---|---|
| Upstream path | `iiq/sailpoint-api.iiq.yaml` |
| SHA-256 | `8f56e3cd7a447a0e2a82985375bcdc07e0a600cd8a831e2c36b58d97b630f175` |
| Bytes / lines | 768,946 / 15,021 |
| Declared version | `8.3` |
| Title | IdentityIQ SCIM REST API |

It is **recorded but not vendored** — one hash-anchored artifact is enough, and
the pinned commit makes the second file reproducible on demand. If the target
deployment is confirmed to be 8.x, supersede this pin rather than editing it in
place, and vendor the 8.3 file as the primary artifact.

**The deployment version is not yet confirmed.** Pinning the current major is
the defensible default for a `reserved` slot; confirming the running IIQ
version is an activation gate in ADR-136 §Decision 5, not a detail to be
assumed here.

## 3. Scope of this pin

The pinned document declares 504 paths. They are not one contract, and treating
them as one would be the same category of error this pin exists to prevent.

**In scope** — supported integration surfaces:

| Surface | Paths | Notes |
|---|---|---|
| `/identityiq/scim/v2` | 15 | SCIM 2.0: Accounts, Users, Entitlements, Applications, Roles, PolicyViolations, LaunchedWorkflows, ResourceTypes, Schemas, ServiceProviderConfig |
| `/identityiq/rest/*` | 179 | Core REST: certifications, applications, identities, provisioning transactions, role mining, alerts, access requests |
| `/identityiq/external/rest` | 6 | External REST integration endpoints |

**Out of scope** — present in the file, deliberately not part of this contract:

- **`/identityiq/ui/rest/*` (304 paths).** This is the IIQ web console's own
  backend. It is documented in the spec because the spec is exhaustive, not
  because it is a supported integration contract. Adapter code must not bind to
  it; a UI-REST dependency is a `DRIFT-PROVENANCE` finding, because the surface
  can change with any UI change and carries no compatibility promise.
- **Write operations of every kind.** The `sailpoint-iiq-governance` slot is
  allocated `ssot-mutation: never` and conformance-only. Write paths are in the
  pinned file; they are not in the adapter's contract.
- **Plugin-supplied endpoints.** IIQ plugins extend the REST surface at
  deployment time. Anything a plugin adds belongs to the deployment half
  (§4), not to the vendor half.

### 3.1 Authentication caveat

The pinned spec declares exactly one security scheme: `basicAuth` (HTTP Basic).
That is a documentation artifact of the vendor spec, not an acceptable
integration posture for a federal deployment. The authentication mechanism the
adapter actually uses — OAuth2 client credentials against the IIQ OAuth
endpoints, or mTLS — is an activation-ADR decision, and the certificate anchor
is recorded in the registry entry, not inherited from this file. Do not read
the spec's `basicAuth` declaration as a sanctioned credential path.

## 4. The deployment half — required, not yet present

This pin is **one half of a two-part contract**. The vendor spec describes
IdentityIQ as shipped. It does not describe the deployment, and for a branded,
customised IIQ instance the deployment is where most of the real contract lives:

- custom Capabilities and SPRights (the `IDM.SailPointSecurity` class of object)
- Workgroups used as certification and approval targets
- onboarded Applications and their account schemas
- custom Roles, Policies, and their attribute shapes
- plugin-supplied REST endpoints
- BeanShell rules that alter object state the adapter observes

None of that appears in the vendored file, and no vendor spec will ever contain
it. The deployment half is therefore a **site-local object-model export**,
committed beside this pin, hash-anchored the same way, produced before the slot
can move off `reserved`:

| Required artifact | Contents |
|---|---|
| `deployment/object-model.<env>.json` | Capabilities, SPRights, Workgroups, Applications + account schemas, Roles, Policies |
| `deployment/rest-surface.<env>.json` | Plugin-supplied endpoints beyond the vendored spec |
| `deployment/README.md` | Export command, IIQ version, export date, operator, SHA-256 of each artifact |

The exports are configuration inventory, not identity data: object names,
schemas, and rights only. No account records, no entitlement assignments, no
person-identifying attributes — the same `object-identity-only` invariant the
registry entry declares.

Until those artifacts exist, this pin is incomplete by design, and ADR-136
holds the slot at `reserved` for exactly that reason.

## 5. Relationship to UIAO_143 (SCIM Core Schema)

IIQ's `/scim/v2` surface is an RFC 7643 implementation with vendor extensions.
[UIAO_143](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/external/rfc7643/UIAO_143_scim-core-schema-pin.md) pins RFC 7643 as the
substrate-level, vendor-neutral schema; this document pins SailPoint's overlay
on top of it. The layering is deliberate and matches the UIAO_143 §3 exclusion
that puts vendor extensions "adjacent to the consuming adapter, not here."

Consequences worth stating plainly:

- Core `User`, `Group`, and `EnterpriseUser` shapes validate against the
  UIAO_143-derived schemas in `src/uiao/schemas/scim/`. The adapter does not
  redefine them.
- IIQ-specific resources — `Entitlement`, `Application`, `PolicyViolation`,
  `LaunchedWorkflow`, `CheckedPolicyViolation` — have no RFC 7643 counterpart
  and are governed solely by this pin.
- A future SCIM ingestion adapter (UIAO_143 §5) and this adapter speak the same
  core wire format, so the SAM integration is a SCIM consumer with a vendor
  overlay rather than a bespoke REST client.

## 6. Adapter taxonomy note

Per UIAO_003, adapters are runtime connectors with a `class` × `mission-class`
declaration. This document is **not** an adapter — it is a vendor specification
consumed by one. The registered consumer is:

| Adapter id | Registry | class | mission-class | Status |
|---|---|---|---|---|
| `sailpoint-iiq-governance` | conformance | conformance | identity | reserved |

No implementation exists today. That is the point: the contract is pinned
before the code, so building the adapter is an implementation task rather than
a spec-and-build task, and the first commit of adapter code can be reviewed
against something.

## 7. Provenance and drift

- **Source of truth** — `sailpoint-api.iiq-9.0.yaml` in this directory. The
  SHA-256 in §2 is the immutability anchor. Any change to that file without an
  accompanying ADR is a `DRIFT-PROVENANCE` finding.
- **Upstream refresh** — SailPoint publishes continuously to `api-specs`.
  A refresh is a deliberate act: re-fetch at a new commit, re-hash, diff the
  spec, and record what changed in the ADR that authorises the bump. Never
  update the file and the hash in the same silent edit.
- **Deployment refresh** — the §4 exports are re-taken whenever the IIQ
  deployment changes shape (new Application onboarded, Capability added, plugin
  installed). A stale deployment export is the same class of defect as a stale
  vendor spec.
- **Version supersession** — if the deployment is confirmed to be 8.x, or IIQ
  publishes a 10.x line, retire this pin via supersession ADR rather than
  editing in place. UIAO_143 §6 establishes that pattern.
- **What this pin does not promise** — that the pinned spec is accurate.
  SailPoint's IIQ specs have known OpenAPI-generator validity problems upstream
  (`sailpoint-oss/api-specs` issue #61). A pin makes the contract *fixed and
  inspectable*, not *correct*; codegen against it may require patching, and any
  patch belongs in the adapter, never in the vendored file.

## 8. References

- SailPoint `api-specs` — [`https://github.com/sailpoint-oss/api-specs`](https://github.com/sailpoint-oss/api-specs)
- SailPoint IdentityIQ SCIM REST API — [`https://developer.sailpoint.com/docs/api/iiq/identityiq-scim-rest-api/`](https://developer.sailpoint.com/docs/api/iiq/identityiq-scim-rest-api/)
- ADR-136 — SailPoint IdentityIQ (Option C) slot allocation and contract pin
- ADR-059 — SailPoint NERM adapter, boundary-exception carve-out and slot
  allocation (Option C recorded as a deliberate alternative)
- ADR-135 — SailPoint ISC governance, Option B ratification
- ADR-092 — Active Governance (L0–L4 actuation ladder)
- UIAO_143 — SCIM Core Schema (RFC 7643) substrate pin
- UIAO_003 — Adapter Segmentation Overview (adapter taxonomy)
