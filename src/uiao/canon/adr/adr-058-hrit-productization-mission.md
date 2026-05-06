---
id: ADR-058
title: "HRIT Single-ATO Productization as v0.6.0 Mission Theme"
status: proposed
date: 2026-05-06
deciders:
  - governance-steward
  - oscal-engineer
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-051  # SAML Trust Anchor — observable upstream contract
  - ADR-052  # PIV / USAccess — observable upstream contract
  - ADR-053  # OPM Azure APIM — observable upstream contract
  - ADR-054  # Single-ATO Reciprocity Model — runtime contract this ADR ratifies
  - ADR-055  # KYC / Customer Identity (sibling theme, complementary)
  - ADR-056  # Login.gov Federation (sibling, not blocking)
canon_refs:
  - UIAO_112  # Multi-Tenant Isolation — amended by ADR-054
  - UIAO_113  # Evidence Graph — v1.2 amendment in scope
  - UIAO_140  # Single-ATO Reciprocity Model
  - UIAO_141  # Customer Identity Model
  - UIAO_143  # HRIT Productization Operational Spec — new spec introduced by this ADR
  - Spec2-D6.1  # Federal HRIT Integration Runbook
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4, PWS §5.1.1 #5 (p. 26) — single ATO covers all agencies"
  - "Solicitation 24322626R0007 Amd 4, Clause 1752.239-74 (p. 107) — OPM ATO process"
  - "Q&A #43 — ATO reciprocity"
  - "Q&A #44 — SSP draft within 30 days, final within 45 days of award"
  - "Q&A #47-48 — single code line, configuration-only differentiation"
---

# ADR-058: HRIT Single-ATO Productization as v0.6.0 Mission Theme

## Status

Proposed.

## Context

ADR-054 + UIAO_140 ratified the **Single-ATO Reciprocity Model** on
2026-05-04 — one SSP, one ATO, N consuming agencies under reciprocity.
Anchored to OPM Solicitation 24322626R0007 (single OPM ATO covers all
~24 CFO-Act agencies). Spec2-D6.1 enumerates the twelve federal HRIT
systems that constitute the integration surface.

ADR-054 §Implementation table (lines 157–164) **explicitly defers** the
runtime work to follow-on PRs:

- `src/uiao/oscal/reciprocity_record.py` emitter
- Reciprocity-record JSON Schema
- Evidence-graph node types for `ato-decision` + `reciprocity-record`
  events (UIAO_113 v1.2 amendment)
- Per-consuming-agency reciprocity bundle aggregation
- ConMon SLA enforcement (30-day draft / 45-day final SSP, 30-day
  reauthorization window)
- Reciprocity acceptance CLI command
- Configuration-latitude drift enforcement (DRIFT-SCHEMA finding)
- Tests (happy-path + lapsed-ATO + configuration-latitude drift)
- Quickstart + reference fixture for OPM-style three-agency scenario

The doctrine layer is complete; the runtime layer is sparse and the
schema layer has the consumption-registry foundation but not the
reciprocity-record artifact schema.

The next release — v0.6.0 — needs a coherent mission theme. Five
candidates were surveyed in
`inbox/v0.6.0-roadmap-reconciliation-2026-05-05.md` §5:

1. HRIT Single-ATO Productization
2. Login.gov Adapter Activation
3. KYC / Customer Identity Adapter
4. Microsoft Tier-1 Adapter Completion
5. Transport Plane Implementation (ADR-057, speculative)

This ADR ratifies **option 1** as the v0.6.0 mission theme.

## Decision

Adopt **HRIT Single-ATO Productization** as the v0.6.0 mission theme.
Concretely:

1. **Allocate UIAO_143** as the *HRIT Productization Operational Spec*
   under `src/uiao/canon/specs/hrit-productization.md`. Operational
   counterpart to UIAO_140 (model) and Spec2-D6.1 (federal-integration
   runbook).

2. **Close every deferred item from ADR-054 §Implementation** as a
   parallelizable Batch A. Ten file-scoped workstreams enumerated in
   `inbox/v0.6.0-hrit-productization/03-batch-plan.md`.

3. **Acceptance for v0.6.0 release** (binding):
   - `uiao reciprocity onboard-agency` CLI command produces a signed
     reciprocity-record artifact
   - Reciprocity-record validates against new
     `src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`
   - Evidence graph v1.2 includes `ato-decision` and `reciprocity-record`
     event node types
   - `uiao conmon ato-cadence-check` enforces 30/45-day SSP cadence and
     30-day reauthorization SLA
   - Configuration outside the SSP-enumerated latitude table emits a
     `DRIFT-SCHEMA` finding
   - Per-agency reciprocity bundle aggregation produces a self-verifying
     artifact a consuming agency AO can validate without UIAO platform
     access
   - Quickstart walks a stranger end-to-end against a synthetic
     "OPM + Treasury + IRS" three-agency fixture in under 15 minutes
   - 8 blocking CI gates remain green (ruff, mypy strict, pytest,
     schema validation, substrate drift, metadata validator, adapter
     conformance, quarto)

4. **Lane discipline.** Phase 0 of HRIT productization treats ADR-051
   (SAML), ADR-052 (PIV), and ADR-053 (APIM) as *observable upstream
   contracts*. UIAO consumes their assertions and emits evidence about
   them; UIAO never issues SAML, never provisions PIV, never operates
   APIM. Any PR that crosses that line is rejected at review.

5. **Out of scope for v0.6.0** (deliberate):
   - Login.gov adapter implementation (ADR-056 Stage 3)
   - KYC adapter implementation (ADR-055)
   - Microsoft Tier-1 adapter completion (#299 follow-on)
   - Transport plane implementation (ADR-057, speculative)
   - Per-HRIT-system adapter coverage beyond a reference set

## Consequences

### Canon work in scope (this ADR + UIAO_143)

- ADR-058 (this document)
- UIAO_143 spec (HRIT Productization Operational Spec)
- UIAO_113 v1.2 amendment — adds `ato-decision` + `reciprocity-record` node types
- New schema: `reciprocity-record.schema.json`
- KSI rules: KSI-RECIP-* family

### Runtime work in scope (Batch A)

10 parallelizable workstreams covering: schema, OSCAL emitter, CLI,
ConMon SLA, evidence-graph amendment, configuration-latitude drift
detector, fixture, quickstart, tests, KSI rules, narrative doc. See
`inbox/v0.6.0-hrit-productization/03-batch-plan.md` for the full
workstream cards.

### Federation block — observable, not implementable

ADR-051/052/053 surfaces are observed via existing telemetry adapters:
- SAML assertions captured via SIEM ingestion (when that adapter activates)
- PIV cert chains observed at TLS endpoints
- APIM logs ingested as telemetry

No new adapter code in v0.6.0 for these. Phase 1 of each ADR's own
activation work is independent.

### CI consequences

- Schema-validation row added for `reciprocity-record.schema.json`
- Adapter-conformance row added for HRIT reference fixture
- Substrate-drift extended to surface configuration-latitude findings at P1

### Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| OPM solicitation requirements drift before v0.6.0 cuts | Medium | Re-anchor on Solicitation 24322626R0007 Amd 4 only; later amendments handled in v0.6.x |
| Reciprocity-record schema diverges from FedRAMP RFC eventual ratification | Medium | Cite ADR-043 pathway-1/pathway-2 model; mark fields advisory until RFC ratifies |
| Configuration-latitude drift triggers false positives on lab fixtures | Low | Latitude table starts permissive; tighten via PR after lab validation |
| Login.gov / KYC theme advocates pull priority | Medium | This ADR commits one theme; sibling themes remain valid for v0.7.0 |

### Out-of-band consequences

- The ADR index (`canon/adr/index.md`) needs a refresh to include
  ADR-032 through ADR-058 — pre-existing housekeeping debt.
- The transferable-ATO framing used informally in earlier
  documentation now points to ADR-054 + UIAO_140 + UIAO_143.

## Rejected alternatives

- **Login.gov adapter activation as v0.6.0** — citizen-facing; KYC block
  not yet warm; lower confidence than HRIT productization.
- **Microsoft Tier-1 adapter completion** — narrower; better as a
  parallel batch within HRIT productization (e.g., ServiceNow as a
  downstream consumer of reciprocity records).
- **Transport plane (ADR-057)** — speculative doctrine, premises partly
  answered by federation block; queued for later.
- **Defer mission theme; accumulate features without theme** — rejected
  because v0.5.0 closed adoption-readiness; v0.6.0 needs a coherent
  external story for the first agency adopter.

## Verification

Acceptance of ADR-058 is a doctrinal commitment; verification is the
existence and integrity of the downstream artifacts:

- [ ] UIAO_143 (HRIT Productization Operational Spec) drafted and
      registered in `document-registry.yaml`
- [ ] All 10 Batch A workstreams from `03-batch-plan.md` complete
- [ ] Quickstart smoke test passes end-to-end on synthetic fixture
- [ ] All 8 blocking CI gates green
- [ ] At least one consuming-agency dry-run validated against OPM-style
      lab tenant (Phase 3 — lab validation)
- [ ] CHANGELOG entry composed and v0.6.0 tag pushed
