---
id: ADR-A-DRAFT
title: "SAML as a Third Trust-Anchor Type for Application Identity"
status: draft
date: 2026-05-04
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-004  # workload-identity-federation-default
  - ADR-049  # microsoft-adapter-coverage-expansion
canon_refs:
  - UIAO_129  # Application Identity Model — to be amended
  - VISION.md
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4, Clause 1752.224-70(c) — Identification and Authentication"
  - "Solicitation 24322626R0007 Amd 4, Clause 1752.224-71 — Identification and Authentication Certification"
  - "NIST SP 800-53 Rev 5, IA-02 (01, 02)"
---

# ADR-A (DRAFT): SAML as a Third Trust-Anchor Type for Application Identity

> **Draft status.** This ADR is held in `inbox/HRIT Modernization/proposed-canon-additions/`.
> Promote to `src/uiao/canon/adr/` and allocate a real ADR-NNN identifier at the
> canon-merge governance review per repo invariant I5 (`AGENTS.md`).

## Status

Draft — pending governance review.

## Context

UIAO_129 §2 (`src/uiao/canon/specs/application-identity-model.md:38-45`) declares
the **Trust anchor** binding (binding #4 of six) as one of:

> *"mTLS cert + SAN; OIDC/JWT"*

The OPM Federal HRIT Modernization Solicitation 24322626R0007 (Amd 4) imposes a
contractual mandate that the canon does not currently model:

- **Clause 1752.224-70(c)** (PWS p. 99): the contractor's solution shall, at the
  time of award, integrate directly with OPM's IdP via **SAML** assertions from
  third-party software, per NIST SP 800-53-5 IA-02 (01, 02).
- **Clause 1752.224-71** (PWS p. 100): offerors must include in their proposal
  **bid-time evidence** of the ability to accept a SAML assertion from a
  third-party software.

For federal HRIT engagements, SAML is therefore not an implementation detail —
it is a bid-window evaluation criterion. UIAO canon as written would force
HRIT-bound applications to declare a trust-anchor binding that does not match
the contractual reality.

Additionally, federated SSO for legacy SaaS, GovCloud reciprocity scenarios,
and many existing federal IdP integrations remain SAML-anchored. OIDC/JWT is
the strategic direction but SAML is the present-day load-bearing pattern.

## Decision

1. Amend UIAO_129 §2 binding #4 (Trust anchor) to enumerate **three**
   trust-anchor types rather than two:

   | Type | When used | Authority |
   |---|---|---|
   | **mTLS cert + SAN** | Persistent service-to-service flows; high-assurance overlay | Certificate / Token Service |
   | **OIDC / JWT** | Ephemeral API calls; cross-domain integrations; modern federated authn | Token Service / IdP |
   | **SAML 2.0 assertion** *(new)* | Federation with legacy / federal IdPs (e.g., OPM Entra); bid-window contractual assertions | IdP (e.g., OPM Entra) |

2. Amend UIAO_129 §3 (Authoritative Bindings) — Trust binding paragraph — to
   add: *"SAML 2.0 for federation with federal and legacy IdPs where the IdP is
   the authority of record (e.g., OPM Entra under Federal HRIT 24322626R0007)."*

3. Update the JSON Schema at
   `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` to recognize
   `saml` as a valid `trust-anchor.type` value alongside `mtls` and `oidc`.

4. No drift-class changes required — `DRIFT-IDENTITY` already covers SAN /
   audience-restriction mismatch; SAML's `Audience` and `Subject` fields map to
   the existing identity-binding contract.

## Consequences

**Positive**

- HRIT-bound application identities can declare their trust anchor without
  forcing a falsified mtls-or-oidc choice.
- Bid-window evidence (Clause 1752.224-71) maps cleanly to the canon's
  trust-anchor binding — the same artifact (a working SAML federation) is both
  proposal evidence and runtime trust anchor.
- Canon now reflects the population of federal IdPs as they actually integrate.

**Negative**

- One more trust-anchor type to support in adapter conformance tests
  (UIAO_121 / UIAO_131 fixtures).
- The OIDC-first migration narrative (per ADR-004 workload-identity federation
  default) needs a clarifying sentence: SAML is **permitted** for legacy and
  federal-IdP federation, but new workload-identity issuance still defaults to
  Workload Identity Federation with OIDC.

**Neutral**

- mTLS remains the trust anchor for service-to-service inside the substrate;
  SAML is *only* for human-user / cross-organization federation.

## Alternatives considered

1. **Treat SAML as a sub-case of OIDC.** Rejected — SAML's XML assertion model,
   audience semantics, and IdP-binding mechanics are different enough that
   collapsing them produces ambiguous canon. NIST SP 800-53 IA-02(01,02) names
   SAML explicitly.
2. **Defer SAML support to per-adapter ADRs.** Rejected — SAML is a *type* of
   trust anchor (a peer of mTLS and OIDC), not an adapter-specific concern.
   Modeling it in UIAO_129 is the correct scope.
3. **Make trust-anchor type free-form / extensible.** Rejected — the closed
   enum is what makes drift detection deterministic. Extension belongs in a
   future ADR if a fourth type emerges.

## Implementation footprint (post-merge)

| File | Change |
|---|---|
| `src/uiao/canon/specs/application-identity-model.md` | Amend §2 binding #4 row + §3 Trust binding paragraph |
| `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` | Add `saml` to `trust-anchor.type` enum |
| `tests/canon/test_application_identity_model.py` | Add SAML trust-anchor case |
| `src/uiao/canon/adr/adr-NNN-saml-trust-anchor.md` | This document, renamed and ID-allocated |
| `src/uiao/canon/document-registry.yaml` | UIAO_129 version bump entry |

## References

- Solicitation 24322626R0007 Amd 4, Clauses 1752.224-70 / 1752.224-71 (PWS pp. 99–100)
- NIST SP 800-53 Rev 5 — IA-02 (01, 02)
- `inbox/HRIT Modernization/HRIT-IAM-Findings.md` §3 (the contractual context)
- UIAO_129 — Application Identity Model
- ADR-004 — Workload Identity Federation Default (related, not superseded)
