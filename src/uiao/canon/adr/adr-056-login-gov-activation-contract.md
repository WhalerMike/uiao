---
id: ADR-056
title: "Login.gov Federation Service — Activation Contract (Stage 2)"
status: accepted
date: 2026-05-05
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-035  # pattern for adapter activation ADRs
  - ADR-051  # SAML trust anchor (federation context)
  - ADR-055  # Customer Identity Canon Block (the parent block)
canon_refs:
  - UIAO_141  # Customer Identity Model
  - UIAO_142  # Customer KYC Onboarding & Reciprocity Runbook
  - VISION.md
mandate_traceability:
  - "ADR-055 §Decision item 4 — first per-adapter activation modeled on ADR-035"
  - "OMB M-19-17 — Enabling Mission Delivery through Improved ICAM"
  - "OMB M-22-09 — Federal Zero Trust Strategy"
  - "NIST SP 800-63-3 — IAL/AAL/FAL"
---

# ADR-056: Login.gov Federation Service — Activation Contract (Stage 2)

## Status

Accepted.

## Context

ADR-055 reserved twelve KYC-block adapter slots, including the
`login-gov-federation-service` slot in `modernization-registry.yaml`
(GSA Login.gov FAL-2 federated citizen IdP). The slot is currently
`status: reserved` — the canonical name and contract are claimed,
but no per-adapter activation has bound it to implementation.

Per the established three-stage adapter lifecycle (canon → docs
scaffold → impl code), the Login.gov adapter is at the boundary
between Stage 1 (slot reserved in canon) and Stage 2 (activation
contract documented). Stage 3 (implementation in
`src/uiao/adapters/`) will follow a separate PR once this contract
is approved.

This ADR is the **Stage 2 activation contract** for
`login-gov-federation-service`. It is the first activation ADR
of the KYC canon block and sets the pattern for the eleven
remaining KYC adapter slots (one per authority of record).

Login.gov is the first activation because:

1. **It is foundational.** The other eleven KYC slots
   (SSA / IRS / GSA SAM / USCIS / DHS e-Verify / Treasury OFAC /
   state DMV / DCSA / VA / vital records / ID.me) all assume that
   *some* federated IdP is already issuing the citizen-facing
   identity assertion that the consuming agency then verifies
   against the authority-of-record. Login.gov is that IdP.
2. **It is publicly operated and OMB-mandated.** Login.gov is a
   GSA Technology Transformation Services product with a public
   developer portal (`developers.login.gov`) and a clear OMB
   M-22-09 alignment story. Activation has fewer external
   dependencies than the authority-of-record adapters, which
   require per-agency MOUs.
3. **It serves the broadest population.** Login.gov already
   serves the IRS, SSA, USCIS, DHS, OPM, and many smaller
   federal-civilian portals — activating it once unlocks the
   FAL-2 federated identity claim for every consuming agency
   the platform will onboard.

## Decision

The `login-gov-federation-service` adapter slot retains
`status: reserved` until Stage 3 implementation lands. This ADR
defines the activation contract that Stage 3 must satisfy.

### 1. Functional contract

The adapter exposes two operational surfaces:

**Provisioning surface (modernization, change-making):**

- Register a new agency application with Login.gov via the
  Partner Dashboard API or the Login.gov Identity Sandbox APIs.
- Configure the application's accepted IAL (1, 2, or 2-Strict)
  and AAL (1, 2, or 3) per the consuming agency's risk profile.
- Issue and rotate the SAML signing certificates and OIDC client
  credentials used for the trust anchor (per ADR-051).
- Maintain the application's redirect URIs, logout URIs, and
  attribute-bundle scope.

**Verification surface (modernization-side observability of issuance):**

- Consume Login.gov's emitted SAML assertions / OIDC ID tokens
  at the consuming agency's portal endpoint.
- Validate signature, audience, IAL/AAL claim, and `not-before` /
  `not-on-or-after` constraints.
- Bind the validated assertion to a Customer Identity Record
  (UIAO_141 §2) — populating the canonical identifier (UUID
  from Login.gov), IAL, AAL, FAL bindings; setting the federation
  authority to `login-gov-federation-service`; the
  authority-of-record binding remains the per-attribute service
  (SSA for SSN, IRS for TIN, etc.).
- Emit `kyc-inbound-verification` events to the evidence graph
  per UIAO_113 v1.1 / UIAO_141 §8.

### 2. Trust anchor

`trust-anchor` for the adapter is `Federal Common Policy CA G2`
as already declared in `modernization-registry.yaml`. Login.gov's
SAML signing certificates chain to this root via GSA's PKI.

When OIDC is in use (rather than SAML), the same chain anchors
the JWT signing keys via the `iss` claim resolution to
`https://secure.login.gov`.

### 3. Configuration latitude per consuming agency

Each consuming agency declares its required posture in the
substrate manifest:

- `ial`: `1` | `2` | `2-strict`
- `aal`: `1` | `2` | `3`
- `attributes`: ordered subset of {`email`, `given_name`,
  `family_name`, `phone`, `address`, `dob`, `social_security_number`}
- `redirect_uri`: agency portal callback URL
- `logout_uri`: agency portal logout endpoint

The adapter validates configuration latitude against this list at
load time; configurations outside the list emit `DRIFT-AUTHZ`.

### 4. Implementation footprint (Stage 3)

| Path | Purpose |
|---|---|
| `src/uiao/adapters/login_gov.py` | `LoginGovAdapter` class subclassing the modernization-adapter base |
| `src/uiao/adapters/login_gov/saml.py` | SAML assertion validation + signature verification |
| `src/uiao/adapters/login_gov/oidc.py` | OIDC ID-token validation; JWKS rotation |
| `src/uiao/adapters/login_gov/partner_api.py` | Partner Dashboard API client (app registration, cert rotation) |
| `tests/adapters/test_login_gov_saml.py` | Tier-1 fixtures: signed SAML assertions, audience/timing/IAL boundary cases |
| `tests/adapters/test_login_gov_oidc.py` | Tier-1 fixtures: signed OIDC tokens, JWKS rotation |
| `tests/adapters/test_login_gov_integration.py` | Tier-2 fixtures: full inbound-verification flow with a sandbox-issued assertion |

When Stage 3 lands, the modernization-registry entry is updated:
`status: reserved` → `status: active`; phase `phase-planning` →
`phase-2` (consistent with the existing phase markers).

### 5. Conformance evidence pathway

Tier-1 conformance per UIAO_131:

- **Tier-1 (Fixture)**: signed SAML assertions and OIDC tokens
  issued from Login.gov's developer sandbox, captured into
  fixtures and replayed at test time. Sandbox access is public.
- **Tier-2 (Sandbox)**: live integration against the Login.gov
  Identity Sandbox — runs against a separate sandbox tenant per
  consuming agency.
- **Tier-3 (Production)**: live integration against
  `secure.login.gov` — runs only when the consuming agency has
  filed an Inter-Agency Agreement with GSA Technology
  Transformation Services.

Tier-1 status is **NOT EXCLUDED** (Login.gov has a public
developer sandbox), unlike several authority-of-record adapters
that require closed agency channels. This is one reason
Login.gov is the right first activation.

### 6. Drift evaluation

The adapter participates in all five drift classes (per UIAO_141 §7):

- `DRIFT-IDENTITY`: assertion subject mismatch with cached CIR
- `DRIFT-AUTHZ`: configuration outside the latitude in §3, or a
  consuming agency without a registered Login.gov application
- `DRIFT-PROVENANCE`: assertion accepted without an emitted
  `kyc-inbound-verification` event
- `DRIFT-SCHEMA`: assertion missing required attributes per the
  agency's declared `attributes` list
- `DRIFT-SEMANTIC`: cached IAL/AAL claim drifted from the live
  Login.gov assertion (assertion claims IAL-1 but cache shows
  IAL-2, etc.)

### 7. Reciprocity model

Login.gov is a federated **IdP**, not an authority of record.
Customer attributes verified by Login.gov (email, name, phone,
DOB, SSN where claimed) are *self-asserted by the user*; for
authority-of-record verification, a second-leg request to the
appropriate attribute service (SSA / IRS / etc.) is required.

The adapter does **not** participate in the
reciprocal-consumption registry directly — it issues identity
assertions, it doesn't disclose attributes from an authority
of record. The authority-of-record adapters do that.

This distinction matters for compliance: a Login.gov assertion
alone does not satisfy a federal-benefits eligibility check that
requires authoritative SSN verification. The runbook (UIAO_142)
already enforces this separation.

## Consequences

**Positive**

- The first KYC-block adapter has a documented activation
  contract; the eleven remaining slots can model their
  activation ADRs on this one (just as the HRIT ADRs modeled on
  ADR-035 / ADR-049).
- Citizen-portal federated authentication is canonically
  represented; the FAL-2 binding in UIAO_141 §2 has a real
  authority terminating it.
- Stage 3 implementation has a clear scope (4 Python modules,
  3 test files) and conformance plan (Tier-1 sandbox-replayable).
- Login.gov is OMB-aligned (M-19-17 federal customer ICAM,
  M-22-09 phishing-resistant MFA), so this activation also
  satisfies the broader federal Zero Trust posture.

**Negative**

- Stage 3 implementation is real work — Tier-1 fixtures need
  capturing, SAML signature validation needs careful boundary
  testing, and the Partner Dashboard API contract may change
  (Login.gov is actively iterating the federal-IdP surface).
- The adapter remains `reserved` until Stage 3 lands; in the
  interim, no agency can use the slot for actual federation.
- This ADR doesn't cover the ID.me sibling slot
  (`id-me-federation-service`) — that's a separate activation
  ADR because ID.me's commercial-licensing and per-agency
  procurement model is materially different.

**Neutral**

- The `id-me-federation-service` slot (ADR-055) remains
  `status: reserved` and unaffected by this ADR. A follow-up
  ADR will activate it on its own per-agency engagement timeline.

## Alternatives considered

1. **Flip the slot to `active` immediately, before code lands.**
   Rejected — `active` status implies the adapter is in
   production use; without code, the status would mislead
   consumers. Better to keep `reserved` until Stage 3 ships.
2. **Activate Login.gov and ID.me in the same ADR.** Rejected —
   ID.me's commercial-license model differs materially. Each gets
   its own activation ADR.
3. **Defer activation entirely until the first agency engagement
   needs it.** Rejected — the activation contract is general,
   not engagement-specific. Documenting it now (Stage 2)
   accelerates the first agency engagement when it comes.
4. **Activate one of the authority-of-record adapters first
   (e.g., SSA).** Rejected — the authority-of-record adapters
   all assume an upstream federated IdP is already in place.
   Login.gov is that IdP. Activating an authority-of-record
   adapter without a federation issuer would leave a contract gap.

## Implementation

| File | Change | Status |
|---|---|---|
| `src/uiao/canon/adr/adr-056-login-gov-activation-contract.md` | This ADR | done in this PR |

Stage 3 (separate PR):

| File | Change | Status |
|---|---|---|
| `src/uiao/adapters/login_gov.py` | New `LoginGovAdapter` | deferred |
| `src/uiao/adapters/login_gov/{saml,oidc,partner_api}.py` | Implementation modules | deferred |
| `tests/adapters/test_login_gov_*.py` | Tier-1 + Tier-2 tests | deferred |
| `src/uiao/canon/modernization-registry.yaml` | `login-gov-federation-service.status`: `reserved` → `active`; `phase`: `phase-planning` → `phase-2` | deferred (lands with Stage 3) |

## References

- ADR-035 — pattern for adapter activation ADRs
- ADR-051 — SAML trust anchor (companion change)
- ADR-055 — Customer Identity Canon Block (parent)
- UIAO_141 — Customer Identity Model (binding model)
- UIAO_142 — Customer KYC Onboarding & Reciprocity Runbook
- OMB M-19-17 — Enabling Mission Delivery through Improved ICAM
- OMB M-22-09 — Federal Zero Trust Strategy
- NIST SP 800-63-3 — IAL/AAL/FAL
- https://login.gov/
- https://developers.login.gov/
