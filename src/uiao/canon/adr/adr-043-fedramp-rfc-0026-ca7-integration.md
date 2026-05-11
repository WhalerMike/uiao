---
id: ADR-043
title: "FedRAMP RFC-0026 (CA-7 Continuous Monitoring Expectations) — UIAO Integration"
status: ACCEPTED
date: 2026-04-21
accepted_date: 2026-04-27
deciders:
  - governance-steward
  - conmon-steward
  - Michael Stratton
extends:
  - ADR-025
supersedes: []
tags:
  - fedramp
  - rfc-0026
  - ca-7
  - continuous-monitoring
  - vdr
  - ccm
  - conmon
  - oscal
  - bod-25-01
  - scubagear
canon_refs:
  - UIAO_002
  - UIAO_003
  - UIAO_110
  - UIAO_132
related_discussions:
  - https://github.com/FedRAMP/community/discussions/130
---

# ADR-043: FedRAMP RFC-0026 (CA-7 Continuous Monitoring Expectations) — UIAO Integration

## Status

**ACCEPTED — 2026-04-27.** RFC-0026's public comment period closed
**2026-04-22**. The FedRAMP 20x assessment companion note
(`inbox/New_FedRAMP_Boundary/FedRAMP_20x_Assessment_and_Implications.docx`,
§1.3) and `src/uiao/canon/data/fedramp-20x.yml` (`deployment_surfaces`
block, `rev5-balance-improvement-releases`) confirm that the Rev5 Balance
Improvement Releases — including **Vulnerability Detection and Response**
(the modernized pathway for RV5-CA07-VLN) and **Collaborative Continuous
Monitoring** (the modernized pathway for RV5-CA07-CCM) — are now
published at [fedramp.gov/docs/rev5/balance/](https://www.fedramp.gov/docs/rev5/balance/)
as opt-in updates to existing Rev5-authorized packages. Both ratification
gates (stable Balance Improvement Release state + corresponding FedRAMP
Marketplace guidance) are satisfied.

The pathway commitments below transition from **intent** to **obligation**
on this ratification. The Notice 0009 deadlines (CCM BIR mandatory
2027-04-01; VDR BIR mandatory 2027-07-01) and the RFC-0026 enforcement
schedule (gradual adoption end of June 2026; grace period through
2026-12-31; enforcement 2027-01-01) carry forward unchanged.

### Status history

| Date | Status | Note |
|---|---|---|
| 2026-04-21 | PROPOSED | Initial landing during RFC-0026 public comment period. |
| 2026-04-27 | ACCEPTED | Comment period closed 2026-04-22. Rev5 Balance Improvement Releases for VDR and CCM published; ratification gates satisfied. Anchor evidence: `inbox/New_FedRAMP_Boundary/FedRAMP_20x_Assessment_and_Implications.docx` §1.3 and `canon/data/fedramp-20x.yml` `deployment_surfaces`. |

## Context

### The RFC

FedRAMP RFC-0026 (`FedRAMP/community` discussion #130, opened April 2026,
comment period closing 2026-04-22) updates the CA-7 Continuous Monitoring
control for all Rev5 baselines. It replaces Joint Authorization Board
guidance rescinded by OMB M-24-15 with two paired requirements and, for each
requirement, two parallel **pathways** — a modernized pathway anchored in an
upcoming "Balance Improvement Release" and a traditional pathway that
preserves the existing monthly cadence.

| Requirement id | Name | Pathway 1 (modernized) | Pathway 2 (traditional) |
|---|---|---|---|
| RV5-CA07-VLN | Vulnerability Reporting | Implement Vulnerability Detection and Response (VDR) Balance Improvement Release | Share monthly OS / Database / Web App / Container / Service Configuration scans **and** monthly POA&M updates **and** annual Independent Assessor scans |
| RV5-CA07-CCM | Collaborative Continuous Monitoring | Implement Collaborative Continuous Monitoring Balance Improvement Release | Host monthly ConMon meetings open to all agency customers per the Rev5 ConMon Playbook |

Effective dates per the RFC: gradual adoption begins **end of June 2026**, a
grace period runs through **2026-12-31**, and enforcement begins
**2027-01-01**. Corrective action follows a five-strike ladder culminating in
marketplace de-listing, with a 12-month reset clock after each failure.

### Interlocking deadlines from FedRAMP Notice 0009

RFC-0026's pathway posture (D1 below) is intentionally dual-track: UIAO runs
Pathway 2 (traditional) at enforcement start and commits to migrate to
Pathway 1 (modernized) when the Balance Improvement Releases publish.
FedRAMP Notice 0009 — *Balance Improvement Release adoption schedule* —
constrains that migration with two hard dates that fall *inside* the
RFC-0026 enforcement window, meaning Pathway-1 migration is not indefinitely
deferrable:

| Date | Notice 0009 event | UIAO implication |
|---|---|---|
| 2027-04-01 | CCM BIR adoption mandatory | Pathway-1 RV5-CA07-CCM adapter (`ccm-bir`) must be active or the `conmon-aggregate.yml` readiness gate fires 90 days prior (2027-01-01) |
| 2027-06-01 | VDR adoption mandatory | Pathway-1 RV5-CA07-VLN adapter (`vdr-bir`) must be active or the readiness gate fires 90 days prior (2027-03-02) |

The adapter-registry entries for `ccm-bir` and `vdr-bir` (RESERVED as of
this ADR) encode `notice-0009-mandatory-by` dates in their
`fedramp-rfc-0026` advisory block; the script
`scripts/conmon/migration_readiness.py` consumes those dates plus the
`status` field and opens a governance issue inside the 90-day lead
window if the pathway transition hasn't started.

### Where UIAO already stands

UIAO is a FedRAMP-Moderate governance substrate whose entire operating model
is organized around continuous monitoring. The substrate already:

- Anchors ConMon policy in ADR-025, NIST SP 800-137 Appendix D's eleven
  security automation domains, and FedRAMP ConMon Playbook v1.0
  (2025-11-17) — see `src/uiao/canon/compliance/reference/fedramp-conmon-playbook/`.
- Ships a conformance-adapter class with four CA-7-tagged slots
  (`scubagear`, `vuln-scan`, `stig-compliance`, `patch-state`) already
  registered in `src/uiao/canon/adapter-registry.yaml`.
- Runs three ConMon CI workflows (`conformance-run.yml`,
  `conmon-scheduled.yml`, `conmon-aggregate.yml`) that fan out monthly and
  roll up POA&M CSV + dashboard JSON per ADR-025 D3.
- Defines a five-class drift taxonomy (UIAO_110) that spans the
  point-in-time-to-continuous gap the RFC is designed to close.
- Emits OSCAL-native evidence (SSP, SAR, POA&M) through its governance
  plane — directly addressing the RFC's machine-readable security-data
  priority.

### Why this ADR exists now

The repo owner commented on RFC-0026 flagging the intersection with CISA
BOD 25-01 and the gap between point-in-time SCuBA assessments and
continuous drift detection. RFC-0026's traditional pathway bakes in a
monthly cadence that UIAO's ConMon Playbook alignment already targets; the
modernized pathway depends on the VDR/CCM Balance Improvement Releases,
which are not yet published. UIAO therefore has to (a) commit, in writing,
to the default pathway it will run on day one; (b) name the trigger that
will move it to the modernized pathway once the Balance Improvement
Releases ship; and (c) close the explicit gaps other commenters
(`vedigaurav`, `lewisrcombs78`, `CSP-AB`, `lrSpriggs`) identified so that
UIAO adopters inherit answers rather than re-litigating them.

## Decision

### D1. Pathway posture is dual-track by default

UIAO runs **Pathway 2 (traditional) on both requirements at the effective
date** because it is the pathway whose deliverables already exist: monthly
scan sharing, monthly POA&M, annual IA scan, monthly ConMon meeting.
UIAO pre-wires Pathway 1 (modernized) as a **planned migration** gated on
the publication of the VDR and CCM Balance Improvement Releases. The
pathway-selection field is recorded per-adapter in
`canon/adapter-registry.yaml` (see D4) and per-program in `UIAO_132`.

### D2. RV5-CA07-VLN is satisfied by the existing vulnerability-telemetry fan-out

The traditional pathway deliverables map onto existing UIAO artifacts:

- **Monthly OS / DB / Web App / Container / Service Configuration scans** →
  produced by the reserved `vuln-scan` conformance adapter
  (`canon/adapter-registry.yaml`, automation-domain
  `vulnerability-management`) plus the `scubagear` configuration scan and
  the reserved `stig-compliance` and `patch-state` slots. Scan
  frequency is driven by `conmon-scheduled.yml`.
- **Monthly POA&M update** → produced by `conmon-aggregate.yml` emitting
  POA&M CSV per the current FedRAMP POA&M template and the Connect.gov
  submission folder naming required by the RFC.
- **Annual Independent Assessor scans** → continues to route through the
  Phase 1 3PAO engagement described in ADR-025 D5 and `CONMON.md` §8.

UIAO additionally commits to the **72-hour timeliness SLA for critical
findings** requested by `vedigaurav` and `lrSpriggs` during comment, even
though the RFC does not yet mandate it; the SLA is enforced in
`conmon-aggregate.yml` via severity-gated issue creation.

### D3. RV5-CA07-CCM is satisfied by the monthly ConMon meeting cadence plus OSCAL evidence drop

The traditional pathway requires hosting monthly agency-open ConMon
meetings. UIAO commits to:

- A standing monthly ConMon meeting slot, with agenda, attendee list,
  and recording/minutes cited in the POA&M evidence pack that
  `conmon-aggregate.yml` emits.
- Pre-meeting evidence drop to Connect.gov in OSCAL JSON — SSP, SAR,
  POA&M — via the generators referenced in UIAO_110.
- Agency-consumption interface: agency customers read the same
  machine-readable feeds UIAO emits for its own drift ledger, so the
  "adequate authorization data" gap `vedigaurav` flagged is answered by
  pointing at the OSCAL drop rather than bespoke reporting.

### D4. Adapter-registry extension: `fedramp-rfc-0026` block

Every conformance adapter whose `controls` list contains `CA-7` gains an
advisory `fedramp-rfc-0026` block of the following shape (added under the
existing `notes` free-text, not as a new schema-enforced field — see
Consequences §N1):

```
fedramp-rfc-0026:
  requirement: RV5-CA07-VLN | RV5-CA07-CCM
  pathway: pathway-2-traditional
  planned-pathway: pathway-1-modernized
  pathway-transition-trigger: "Publication of the VDR Balance Improvement Release"
  adr: ADR-043
```

The advisory block is consumed by UIAO_132 and by the `conmon-aggregate`
workflow's dashboard JSON; it is not yet promoted into
`adapter-registry.schema.json` because RFC-0026 is still PROPOSED
upstream. Schema promotion is gated on RFC-0026 ratification (Promotion
Checklist §P3).

### D5. Corrective-action posture

UIAO adopts the RFC's five-strike ladder verbatim **with one addition**:
a self-imposed **45-day internal cure window** before the first strike
fires, aligned with `lrSpriggs`'s comment. The internal cure is tracked
in `docs/docs/conmon-corrective-action-playbook.qmd` (stub created
alongside this ADR) and is independent of the FedRAMP-issued strike
clock — it exists solely so UIAO catches its own drift before a PMO
notification.

### D6. Explicit position on `WhalerMike`'s BOD 25-01 comment

The repo owner's RFC comment flagged that point-in-time SCuBA
assessments are insufficient for continuous drift detection. UIAO's
answer: `scubagear` remains a point-in-time assessor, but its output is
consumed by the Drift Engine (UIAO_110), which materializes SCuBA drift
as `DRIFT-SEMANTIC` and `DRIFT-POLICY` findings between runs. The drift
ledger — not the SCuBA run — is what satisfies RV5-CA07-VLN's continuity
obligation for M365-SCuBA-scoped controls. BOD 25-01 scope is called out
explicitly in UIAO_132.

## Consequences

### Positive

- UIAO has a written answer to every CA-7 obligation RFC-0026 imposes
  before the 2027-01-01 enforcement date, and a migration plan to the
  modernized pathway that does not require a rewrite.
- Every RFC-era deliverable (monthly scans, monthly POA&M, annual IA
  scan, monthly meeting, OSCAL drop) is already produced by existing
  substrate — this ADR is mostly bookkeeping over code that already
  runs.
- The drift-ledger answer to BOD 25-01 closes the gap the repo owner
  raised in comment without waiting on the VDR release.

### Negative / deferred

- **N1. Schema drift risk.** The `fedramp-rfc-0026` block in
  `adapter-registry.yaml` is a conventional key in the `notes` free-text
  body today. If RFC-0026 ratifies in a shape incompatible with this
  convention, schema promotion will require a registry migration.
- **N2. Pathway-1 readiness.** The VDR and CCM Balance Improvement
  Releases are unpublished at ADR date. UIAO cannot pre-build against
  them; a later ADR will supersede D1–D3 once the releases land.
- **N3. Connect.gov integration.** UIAO does not yet have a Connect.gov
  submission automation — today's POA&M drop is manual. A follow-up is
  tracked in UIAO_132 §Open items.
- **N4. 72-hour critical-finding SLA is self-imposed.** If RFC-0026
  ratifies with a stricter SLA, severity gates in `conmon-aggregate.yml`
  must tighten.

## Alternatives considered

- **Commit to Pathway 1 (modernized) as the default.** Rejected: the
  VDR/CCM Balance Improvement Releases are not yet published and their
  deliverable contracts are not specified in enough detail to pre-build
  against.
- **Defer the ADR until RFC-0026 ratifies.** Rejected: the RFC comment
  window closes 2026-04-22 and the effective date is 2026-06-30.
  UIAO's default pathway needs to be on paper before the enforcement
  clock starts, even if the ADR is PROPOSED rather than ACCEPTED.
- **Roll the content into a revised ADR-025.** Rejected per CR-003
  (ADR-025 is immutable once decisions are made). Additive ADR with an
  `extends: ADR-025` link is the correct shape.
- **Treat RFC-0026 as pure documentation and skip the adapter-registry
  touchpoint.** Rejected: the whole point of UIAO's registry is
  machine-readable traceability from canon to the workflow that emits
  evidence; if CA-7 pathways are not registered, the CI dashboard
  cannot tell an auditor which pathway a given scan satisfies.

## Promotion checklist

Before this ADR can move from `PROPOSED` to `ACCEPTED`:

- [ ] RFC-0026 has been ratified upstream (or explicitly superseded by
      a later FedRAMP RFC) — check `FedRAMP/community` discussion #130
      and the FedRAMP Marketplace guidance.
- [ ] The VDR and CCM Balance Improvement Releases are published and
      their deliverable contracts have been reviewed against this
      ADR's D1–D3.
- [ ] `UIAO_132` has been promoted from DRAFT to Current and has a
      fully populated Pathway-1 migration plan.
- [ ] `adapter-registry.schema.json` has been updated to schema-enforce
      the `fedramp-rfc-0026` block (P3 above).
- [ ] The Connect.gov submission automation described in N3 has a
      tracked owner and a tentative delivery date.

## Related work

- ADR-025 — Continuous Monitoring Program and Customer Documentation
  Platform Architecture (the architectural substrate this ADR extends).
- ADR-040 — Drift Engine (consumes conformance-adapter output and
  materializes SCuBA drift between runs, per D6).
- UIAO_002 — SCuBA Technical Specification (scope for the drift-based
  continuity answer in D6).
- UIAO_110 — Drift Engine Specification.
- UIAO_132 — FedRAMP RFC-0026 CA-7 Pathway Integration (the
  operational companion to this ADR, authored alongside it).
- `src/uiao/canon/compliance/reference/fedramp-rfc-0026/` — RFC
  provenance stub with upstream URL, retrieval date, and the comment
  thread reference.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 2026-04-21 | Drafted during RFC-0026 comment window | Automation |
| 0.2 | 2026-04-23 | Added interlocking FedRAMP Notice 0009 deadlines (CCM BIR 2027-04-01, VDR 2027-06-01) and the `ccm-bir` / `vdr-bir` adapter-registry slots they drive. Paired with `scripts/conmon/migration_readiness.py` and the new E8 enhancement in `docs/docs/uiao-rfc-0026-roadmap.md`. | Automation |

