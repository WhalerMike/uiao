---
id: ADR-065
title: "HRIT Single-ATO Productization as v0.6.0 Mission Theme"
status: accepted
date: 2026-05-11
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
  - UIAO_144  # HRIT Productization Operational Spec — new spec introduced by this ADR
  - Spec2-D6.1  # Federal HRIT Integration Runbook
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4, PWS §5.1.1 #5 (p. 26) — single ATO covers all agencies"
  - "Solicitation 24322626R0007 Amd 4, Clause 1752.239-74 (p. 107) — OPM ATO process"
  - "Q&A #43 — ATO reciprocity"
  - "Q&A #44 — SSP draft within 30 days, final within 45 days of award"
  - "Q&A #47-48 — single code line, configuration-only differentiation"
---

# ADR-065: HRIT Single-ATO Productization as v0.6.0 Mission Theme

## Renumber and acceptance note (2026-05-11)

This ADR was originally drafted as **ADR-058** (proposed 2026-05-06).
The ADR-058 slot was subsequently claimed by
`adr-058-microsoft-purview-conformance-adapter-coverage.md` (accepted
2026-05-07). To resolve the collision, the present ADR is renumbered to
**ADR-065** (next free slot above ADR-064) and flipped from `proposed`
to `accepted` — backfilled acceptance of the mission theme whose runtime
work shipped in PR #422 ("Claude/v0.6.0 hrit integration") and the
Batch A workstreams referenced in the verification list below.

File history:
- `adr-058-hrit-productization-mission.md` (deleted in the same PR that
  introduced this file)
- Original proposal text retained verbatim below; only frontmatter,
  numeric references (UIAO_143 → UIAO_144), and status changed.

## Status

Accepted.

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

This ADR ratified HRIT Single-ATO Productization as the v0.6.0 mission
theme to close the runtime gap. The work landed in main via
PR #422 (Phase 2 integration), PRs #407/#408/#410/#411/#413 (test
fixes), and supporting Batch A workstream PRs.

## Decision

Adopt **HRIT Single-ATO Productization** as the v0.6.0 mission theme.
Concretely:

1. **Allocate UIAO_144** as the *HRIT Productization Operational Spec*
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
   - Transport plane implementation (ADR-057 numbering pending governance)
   - Per-HRIT-system adapter coverage beyond a reference set

## Consequences

### Canon work in scope (this ADR + UIAO_144)

- ADR-065 (this document)
- UIAO_144 spec (HRIT Productization Operational Spec)
- UIAO_113 v1.2 amendment — adds `ato-decision` + `reciprocity-record` node types
- New schema: `reciprocity-record.schema.json`
- KSI rules: KSI-RECIP-* family

### Runtime work shipped (Batch A — landed in main)

10 parallelizable workstreams covering: schema, OSCAL emitter, CLI,
ConMon SLA, evidence-graph amendment, configuration-latitude drift
detector, fixture, quickstart, tests, KSI rules, narrative doc. See
`inbox/v0.6.0-hrit-productization/03-batch-plan.md` for the workstream
cards. Integration landed via PR #422.

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

### Out-of-band consequences

- The transferable-ATO framing used informally in earlier
  documentation now points to ADR-054 + UIAO_140 + UIAO_144.
- The original `adr-058-hrit-productization-mission.md` file is deleted
  in the same PR that creates this file, to resolve the ADR-058 slot
  collision with `adr-058-microsoft-purview-conformance-adapter-coverage.md`.

## Rejected alternatives

- **Login.gov adapter activation as v0.6.0** — citizen-facing; KYC block
  not yet warm; lower confidence than HRIT productization.
- **Microsoft Tier-1 adapter completion** — narrower; better as a
  parallel batch within HRIT productization.
- **Transport plane (ADR-057 candidate, pending renumber)** — speculative
  doctrine, premises partly answered by federation block; queued.
- **Defer mission theme; accumulate features without theme** — rejected
  because v0.5.0 closed adoption-readiness; v0.6.0 needed a coherent
  external story for the first agency adopter.

## Verification

- [x] UIAO_144 (HRIT Productization Operational Spec) drafted and
      registered in `document-registry.yaml`
- [x] All 10 Batch A workstreams from `03-batch-plan.md` complete
      (landed via PR #422 and supporting PRs)
- [x] Quickstart smoke test passes end-to-end on synthetic fixture
- [x] All 8 blocking CI gates green on v0.6.0 integration tree
- [ ] At least one consuming-agency dry-run validated against OPM-style
      lab tenant (Phase 3 — lab validation; v0.6.1 target)
- [ ] v0.6.0 tag pushed (pending maintainer's local `git push origin v0.6.0`)
