---
id: ADR-052
title: "PIV / USAccess Conformance Adapter — Federal Personnel Trust-Anchor Authority"
status: accepted
date: 2026-05-04
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-051  # SAML trust anchor (companion HRIT IAM ADR)
  - ADR-053  # opm-azure-apim-adapter
  - ADR-054  # single-ato-reciprocity
  - ADR-049  # microsoft-adapter-coverage-expansion (precedent for reserved slot pattern)
canon_refs:
  - UIAO_129  # Application Identity Model — binding #4 Trust anchor
  - VISION.md # NIST SP 800-63 reference
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4, Clause 1752.224-70(b) — PIV-based authentication for OPM users"
  - "Solicitation 24322626R0007 Amd 4, PWS p. 112 — phishing-resistant MFA (PIV/CAC)"
  - "OMB M-22-09 — Federal Zero Trust Strategy"
  - "HSPD-12 — Common Identification Standard for Federal Employees and Contractors"
  - "FIPS 201-3 — Personal Identity Verification of Federal Employees and Contractors"
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-052-piv-usaccess-adapter.html
---

# ADR-052: PIV / USAccess Conformance Adapter — Federal Personnel Trust-Anchor Authority

## Status

Accepted.

## Context

UIAO canon references NIST SP 800-63 identity assurance levels in
`docs/governance/VISION.md` ("encoded in the addressing and overlay layers"),
but no adapter exists for **PIV / CAC certificate observation** — i.e., the
federal Personal Identity Verification credential issued under HSPD-12 and
FIPS 201-3, primarily through GSA's **USAccess** managed service.

The HRIT Modernization Solicitation 24322626R0007 (Amd 4) imposes:

- **Clause 1752.224-70(b)** (PWS p. 99): OPM users authenticate via
  **PIV-based authentication, federated SSO, or other phishing-resistant
  mechanism**.
- **PWS p. 112** (Zero Trust posture): phishing-resistant MFA "e.g., PIV/CAC"
  named explicitly as the federal pattern.
- **OMB M-22-09**: phishing-resistant MFA mandate; PIV is the canonical
  satisfaction.

For UIAO to model this contractually, the PIV credential must be a
**first-class observable trust-anchor surface** with its own conformance
adapter that validates issuance authority, certificate chain to the Federal
Common Policy CA, and revocation state via OCSP / CRL.

The existing `pki-ca` reserved slot in `src/uiao/canon/adapter-registry.yaml`
is *generic* (any PKI). Federal PIV has additional requirements — Federal
Common Policy CA chaining, FASC-N or UUID identifier semantics, role
certificate vs. authentication certificate distinction — that warrant a
dedicated adapter slot.

## Decision

1. Reserve a new conformance-adapter slot `piv-usaccess` in
   `src/uiao/canon/adapter-registry.yaml` with:

   - `class: conformance`
   - `mission-class: identity` (PIV is *the* federal identity credential)
   - `status: reserved`
   - `phase: phase-planning`
   - `vendor: GSA`
   - Scope: `piv-credential-issuance`, `piv-authentication-certificates`,
     `federal-common-policy-chain`, `ocsp-validation`, `crl-distribution`
   - Controls: `IA-2(1)`, `IA-2(2)`, `IA-5(2)`, `SC-12`, `SC-13`, `SC-17`,
     `PE-2` (physical-logical access integration)

2. **No paired modernization adapter at this time.** PIV issuance is performed
   by GSA-operated USAccess infrastructure; UIAO is a downstream consumer of
   the credential, never an issuer. If a future ADR introduces a derived-PIV
   issuance flow (NIST SP 800-157), a paired modernization adapter can be
   allocated then.

3. The adapter, when activated, satisfies the **Trust anchor binding (#4 of
   six)** in UIAO_129 §2 for any Application Identity whose principal is a
   federal employee or contractor. Combined with ADR-051 (SAML trust anchor),
   this completes the federal-personnel authentication chain:
   PIV-cert → SAML-assertion-to-OPM-Entra → Application Identity binding.

4. The adapter conforms to UIAO's `certificate-anchored: true` and
   `ssot-mutation: never` invariants — it observes credential state, never
   mutates it.

## Consequences

**Positive**

- UIAO models federal-personnel authentication contractually.
- HRIT bid-window evidence (working SAML to OPM Entra **plus** PIV-based
  authn for OPM users) maps to two adjacent canon entries — ADR-051's SAML
  trust-anchor type and this ADR's PIV adapter — with clear separation of
  concerns.
- Closes a long-standing gap where NIST SP 800-63 IAL/AAL/FAL was named in
  VISION but had no adapter to observe at runtime.
- Sets the pattern for adjacent federal credential authorities (CAC for DoD
  via DEERS / RAPIDS; future derived-PIV issuance).

**Negative**

- Activation requires GSA / USAccess API access, which is not publicly
  documented. Initial implementation may rely on consuming PIV certificates
  via the standard X.509 chain rather than a USAccess-direct API — that's
  acceptable; the adapter scope is "PIV credential observation," not
  "USAccess platform integration."
- Tier-1 conformance (UIAO_131) likely EXCLUDED initially — no public
  developer sandbox; compensating evidence per UIAO_131 §5.1.1 (vendor-
  attested test report from GSA OR agency-operated PIV smartcard fixture).

**Neutral**

- No effect on existing adapters. The generic `pki-ca` reserved slot remains
  for non-PIV PKI observation.

## Alternatives considered

1. **Subsume PIV under the generic `pki-ca` slot.** Rejected — PIV's federal
   trust framework (Federal Common Policy CA, FASC-N, role-vs-auth cert
   distinction) is materially different from generic PKI. Conflating the two
   produces an unwieldy adapter with branching scope.
2. **Defer until a federal customer activates it.** Rejected — UIAO canon is
   meant to *enable* federal customers, and HRIT is the inflection point.
   Reserving the slot now makes the architecture legible to bid-stage
   evaluators.
3. **Pair with a modernization adapter for derived-PIV issuance.** Deferred
   — derived-PIV (NIST SP 800-157) is a distinct issuance pattern that will
   warrant its own ADR once an agency adopts it. Out of scope here.

## Implementation

| File | Change | Status |
|---|---|---|
| `src/uiao/canon/adapter-registry.yaml` | New entry `id: piv-usaccess` (reserved slot) | done in same PR |

## References

- Solicitation 24322626R0007 Amd 4, Clause 1752.224-70(b) (PWS p. 99)
- Solicitation 24322626R0007 Amd 4, PWS p. 112 (Zero Trust posture)
- HSPD-12 — Common Identification Standard for Federal Employees and Contractors
- FIPS 201-3 — Personal Identity Verification
- NIST SP 800-63-3, NIST SP 800-157 (derived PIV)
- OMB M-22-09 — Federal Zero Trust Strategy
- ADR-051 — SAML trust anchor (companion change)
- `inbox/HRIT Modernization/HRIT-IAM-Findings.md` §3.1, §6.2
