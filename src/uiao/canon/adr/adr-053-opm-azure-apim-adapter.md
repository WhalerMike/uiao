---
id: ADR-053
title: "OPM Azure APIM Integration Adapter — Centralized Federal API Gateway Authority"
status: accepted
date: 2026-05-04
deciders:
  - governance-steward
  - integration-engineer
supersedes: []
related_adrs:
  - ADR-051  # SAML trust anchor
  - ADR-052  # PIV / USAccess
  - ADR-054  # single-ato-reciprocity
  - ADR-049  # microsoft-adapter-coverage-expansion
canon_refs:
  - UIAO_129  # Application Identity Model — amended by this ADR
  - UIAO_130  # Application Identity Onboarding Runbook — amended by this ADR
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4, Appendix B p. 82 — Integration Layer Requirements"
  - "Solicitation 24322626R0007 Amd 4, Appendix B p. 84 — Core-HCM API Boundary"
  - "Q&A #149 — APIM access scope"
---

# ADR-053: OPM Azure APIM Integration Adapter — Centralized Federal API Gateway Authority

## Status

Accepted.

## Context

The HRIT Modernization Solicitation 24322626R0007 (Amd 4) Appendix B (PWS
pp. 82, 84) mandates that **all persistent OPM-side integrations** flow
through an OPM-hosted Azure API Management (APIM) gateway, which performs:

- **OAuth 2.0 enforcement** at the gateway (not just at the application)
- Rate limiting and IP filtering
- Data-format transformation (XML ↔ JSON)
- API documentation and developer onboarding
- Monitoring, logging, analytics for all API traffic
- FedRAMP Moderate / FISMA / NIST SP 800-53 compliance

UIAO canon currently models the `entra-id` modernization adapter and the
`terraform` adapter, but **does not model the OPM APIM gateway itself as an
Authority-Plane component**. For HRIT-bound applications, the APIM gateway
is the point at which:

1. OAuth 2.0 access tokens are validated against scope claims.
2. mTLS for backend connections is terminated and re-originated.
3. Cross-agency API consumption is gated, audited, and rate-limited.
4. The "Core HCM API boundary" is enforced — the contractor is responsible
   only up to the APIM ingress; OPM and downstream agencies operate their
   own consumers.

Without canon for this gateway, HRIT-derived application identities cannot
declare the gateway as a binding authority for their **policy-segmentation**
and **trust-relay** functions. The UIAO_129 §3 binding model implicitly
assumes a flat consumer-to-authority topology that does not match the
HRIT-mandated three-tier topology (consumer → APIM → Core-HCM).

## Decision

1. Reserve a new modernization-adapter slot `opm-azure-apim` in
   `src/uiao/canon/modernization-registry.yaml` with:

   - `class: modernization`
   - `mission-class: integration`
   - `status: reserved`
   - `phase: phase-planning`
   - `vendor: Microsoft` (APIM is the underlying service; OPM operates the
     instance)
   - Scope: `oauth2-token-validation`, `api-rate-limiting`,
     `mtls-termination`, `payload-transformation`, `developer-portal`,
     `cross-agency-api-routing`
   - Controls: `AC-4`, `AC-17`, `AU-2`, `AU-12`, `IA-2`, `IA-8`, `SC-7`,
     `SC-8`, `SC-13`, `SC-23`, `CA-9`

2. Amend UIAO_129 §3 (Authoritative Bindings) — Trust binding paragraph —
   to clarify the **issuance vs. enforcement** distinction. The application's
   trust anchor (binding #4) is still issued by the Certificate / Token
   Service or IdP authority. Where a contractually-mandated API gateway
   intermediates (e.g., OPM APIM under HRIT 24322626R0007), the gateway is
   the *enforcement* surface, not the *issuance* surface. (This amendment is
   bundled with ADR-051's narrative changes in the same UIAO_129 v1.1 bump.)

3. Amend UIAO_130 §2 Preconditions (Authority Plane reachable list) to add
   API Gateway as a sixth authority (where contractually mandated, e.g.,
   OPM APIM under Federal HRIT 24322626R0007) alongside IPAM, IAM,
   Certificate / Token Services, and Policy Engine.

4. The adapter conforms to UIAO's `certificate-anchored: true` and
   `ssot-mutation: never` invariants — APIM enforces policy declared
   elsewhere, never authors it.

## Consequences

**Positive**

- HRIT-bound applications can declare the OPM APIM gateway as their explicit
  enforcement surface, closing the canonical-gap that currently forces the
  gateway into "implementation detail" status.
- Drift between the gateway's enforced policy and the canon's policy
  declaration becomes a `DRIFT-AUTHZ` finding, observable by the existing
  drift engine.
- The "Core-HCM API boundary" mandate (Appendix B p. 84) is mappable to
  canon — the contractor's responsibility ends at the APIM ingress, and the
  adapter formalizes that boundary.
- Sets the pattern for adjacent agency-level API gateways (DHS, Treasury,
  shared services) once they emerge as similarly contractually-mandated
  surfaces.

**Negative**

- One more adapter to keep conformant. APIM's API surface is well-documented
  (Azure Resource Manager + Microsoft Graph), so this is manageable.
- Tier-1 conformance (UIAO_131): activation requires an OPM-issued APIM
  service principal; until that exists, conformance evidence comes from
  Microsoft-attested test fixtures.

**Neutral**

- No effect on the `entra-id` adapter — APIM and Entra play distinct roles
  (gateway vs. IdP) and the two adapters compose, not conflict.

## Alternatives considered

1. **Treat APIM as an instance of the generic `terraform` integration
   adapter.** Rejected — Terraform is the IaC surface for *deploying* APIM
   policy, not the runtime surface for observing it. The two adapters
   compose: Terraform deploys the policy bundle; the APIM adapter observes
   runtime conformance.
2. **Defer to a per-agency adapter when each federal agency stands up its
   own APIM.** Rejected — OPM APIM is named contractually as the **central**
   gateway for the HRIT platform across all agencies. It is a single
   authority, not a fleet.
3. **Push the gateway into the `entra-id` adapter scope.** Rejected — Entra
   issues identities and tokens; APIM enforces token claims at the API
   boundary. Different concerns, different blast radii, different
   conformance contracts.

## Implementation

| File | Change | Status |
|---|---|---|
| `src/uiao/canon/modernization-registry.yaml` | New entry `id: opm-azure-apim` (reserved slot) | done in same PR |
| `src/uiao/canon/specs/application-identity-model.md` | Trust binding paragraph amended (issuance vs. enforcement) — bundled with ADR-051 v1.1 bump | done in same PR |
| `src/uiao/canon/specs/application-identity-onboarding-runbook.md` | §2 Preconditions Authority Plane list amended; version bumped to 1.1 | done in same PR |

## References

- Solicitation 24322626R0007 Amd 4, Appendix B pp. 82, 84
- Q&A #149 — APIM access scope clarification
- UIAO_129 — Application Identity Model
- UIAO_130 — Application Identity Onboarding Runbook
- ADR-051 — SAML trust anchor (companion change)
- ADR-052 — PIV / USAccess adapter (companion change)
- `inbox/HRIT Modernization/HRIT-IAM-Findings.md` §5
