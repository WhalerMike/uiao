# Proposed Canon Additions — KYC / Customer Identity Block

> **Status:** DRAFT — `inbox/` content, not canon. The four artifacts below
> form one tightly-coupled canon block; they're best promoted together rather
> than incrementally.
>
> **Created:** 2026-05-05
>
> **Source mandate:** User-stated architectural intent (2026-05-04) —
> *"KYC implemented as an important Customer protocol both as a Federal
> Agencie's support for external customers, as well as for Agencies to be a
> SSOT for things like SSA # and other info to other agencies, States,
> Employers, and etc. Agencies are both Vendors and Customers of each
> other."*
>
> Plus: OMB M-19-17 (federal customer ICAM), OMB M-22-09 (Federal Zero
> Trust Strategy), Privacy Act of 1974, CMPPA of 1988, NIST SP 800-63-3.

---

## What this bundle is

Four canon artifacts that together establish the **Customer Identity
Canon Block** — UIAO's first-class model for citizen / business / cross-
agency identity flows. Companion to the workforce-identity block
(UIAO_129 + UIAO_130 + ADR-051..054 + UIAO_140 already in canon via PR
#312).

These are drafts because canon edits flow through the canon-change process
declared in `AGENTS.md` and repo invariant **I5**:

> **I5. Canon changes flow through the canon-change process.** Adding,
> modifying, retiring, or superseding anything under `src/uiao/canon/`
> requires a new UIAO_NNN allocation in `document-registry.yaml` (for
> new docs), a new ADR in `src/uiao/canon/adr/` (for doctrinal changes),
> and governance review.

These drafts have **not** been allocated their final IDs — the placeholder
references (UIAO_141, UIAO_142, ADR-055) are the suggested next sequential
numbers as of 2026-05-05.

---

## The four artifacts

| File | Role |
|---|---|
| [`UIAO_141-customer-identity-model.md`](UIAO_141-customer-identity-model.md) | Declarative spec for the Customer Identity Record (CIR) primitive — six required bindings: canonical identifier, IAL, AAL, FAL, authority of record, reciprocal-consumption entitlement |
| [`UIAO_142-customer-kyc-runbook.md`](UIAO_142-customer-kyc-runbook.md) | Operational runbook for inbound KYC, outbound KYC, reciprocity provisioning, and drift detection |
| [`ADR-055-customer-identity-canon-block.md`](ADR-055-customer-identity-canon-block.md) | The doctrinal ADR — establishes the canon block, allocates UIAO_141 / UIAO_142, registers 12 adapter slots, amends UIAO_113 + UIAO_120 |
| (within the ADR) Adapter-slot manifest | 10 conformance + 2 modernization reserved slots for federal authorities of record (SSA, IRS, GSA, USCIS, e-Verify, OFAC, DMV, DCSA, VA, vitals, Login.gov, ID.me) |

The companion findings document is one level up at
[`../KYC-Customer-Protocol-Findings.md`](../KYC-Customer-Protocol-Findings.md)
— read it first if you want the full scoping context.

---

## What this bundle does NOT do

- **Does not modify** `src/uiao/canon/` or any of the registries. That is a
  governance-board action at promotion time, not an inbox-draft action.
- **Does not allocate** UIAO_NNN identifiers or the ADR-NNN number. Those
  are registry-steward decisions at merge time. The placeholder identifiers
  (UIAO_141, UIAO_142, ADR-055) are next-available as of 2026-05-05 and may
  shift if other PRs land first.
- **Does not implement** any adapter code. All twelve adapter slots are
  `status: reserved`; activation requires per-adapter ADRs modeled on
  ADR-035.
- **Does not write the new `reciprocal-consumption-registry.yaml`.** ADR-055
  introduces the registry path and JSON Schema; the initial registry file
  is empty (no entitlements yet).
- **Does not draft per-engagement runbooks.** UIAO_142 is the generic
  runbook. Engagement-specific runbooks (e.g., a Login.gov citizen-portal
  integration runbook, paralleling Spec2-D3.x for HRIT) are follow-ups.
- **Does not amend Truth Fabric appendix B-02.** The `identity_type` enum
  stays as-is; KYC operates as a refinement layer, not a replacement.

---

## Dependency order at promotion time

If split into commits, suggested order:

```
1. UIAO_141 + UIAO_142 + ADR-055 + document-registry.yaml
2. reciprocal-consumption-registry.yaml + JSON Schema
3. adapter-registry.yaml + modernization-registry.yaml (12 slot additions)
4. (optional) UIAO_113 + UIAO_120 amendments
```

Each commit is independently reviewable; the bundle as a whole is what
closes the gap.

---

## Post-merge follow-ups (out of scope for this bundle)

- **Per-adapter activation ADRs** — one per authority of record when an
  agency engagement requires it. Likely first: Login.gov (federation
  issuer), then SSA Consent-Based SSN Verification or IRS Income
  Verification Express Service.
- **OSCAL emitters** — `customer-identity-record` and
  `reciprocity-attribute-record` artifact types in `src/uiao/oscal/`.
  Separate PR after canon is stable.
- **PII minimization architecture** — selective disclosure, attribute-based
  credentials, zero-knowledge proofs ("over 18", "US citizen") for
  privacy-preserving customer flows. Worth a dedicated UIAO_NNN spec.
- **Login.gov-specific integration runbook** — Spec3-D6.x candidate,
  paralleling the HRIT Spec2-D3.x for federated citizen authentication.
- **State-level reciprocity governance** — federal-state attribute exchange
  has its own legal frame. Separate spec once the federal-side block is
  stable.
- **Employer-facing reciprocity** — e-Verify, W-2 reporting, work-
  authorization. Tied to NFC/SSA but with employer-specific compliance
  constraints.
- **Continuous evaluation / continuous vetting** — security-clearance
  modernization layer that consumes inter-agency attributes ongoing.

## Tie-back to existing canon

| Existing canon | KYC tie-in |
|---|---|
| UIAO_129 §2 binding #4 — SAML 2.0 added by ADR-051 | KYC reuses SAML for citizen-portal federation; FAL-2 IdPs (Login.gov, ID.me) federate via SAML to consuming agencies |
| ADR-052 — PIV/USAccess | Federal employees authenticate via PIV; **external customers** authenticate via Login.gov / ID.me / agency portals — different trust anchors, same trust-anchor binding model |
| UIAO_140 — Single-ATO Reciprocity | UIAO_140 reciprocity is *authorization-level*; UIAO_141/142 reciprocity is *attribute-level*. Same doctrine, different scope. |
| ADR-053 — OPM Azure APIM | Pattern for inter-agency API gateway; KYC peer-to-peer attribute exchange will likely use similar gateways operated by each authority of record |
| UIAO_113 — Evidence Graph | Customer Identity Records and reciprocity events emit to the same graph as workforce events; UIAO_113 v1.1 amendment enumerates the new event types |
| UIAO_120 — Zero-Trust Integration Layer | UIAO_120 v1.1 amendment recognizes the customer-identity surface as a peer to the workforce-identity surface |
| Truth Fabric `b-02-identity-anchoring.md` | The `identity_type` enum stays (person/device/service/organization); KYC operates as a refinement on `person` and `organization` records |
| Spec2-D3.x — HR-driven IAM | Workforce customer onboarding; KYC is external customer onboarding. Distinct flows, parallel architecture. |
