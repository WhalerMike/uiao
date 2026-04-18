---
title: "ADR-032: FedRAMP Vulnerability Detection and Response (VDR) Rev5 Open Beta Adoption"
adr: "ADR-032"
status: PROPOSED
date: "2026-04-18"
deciders: ["Michael Stratton"]
tags: ["fedramp", "conmon", "vdr", "20x", "vulnerability-management", "poam"]
---

# ADR-032: FedRAMP Vulnerability Detection and Response (VDR) Rev5 Open Beta Adoption

## Status

PROPOSED — 2026-04-18

Awaiting: (a) user decision on opt-in; (b) FedRAMP sign-up form submission by 2026-02-02 if opting in; (c) full-requirements plan by the Open Beta close on 2026-05-22.

## Context

FedRAMP published the **Vulnerability Detection and Response** (VDR) process as an Optional Open Beta under the Rev5 Balance Improvement Releases. Effective dates per FedRAMP:

- **Open Beta begins:** 2026-02-02 (sign-up required — Google Form URL published on the VDR process page).
- **Requirements deadline:** 2026-05-22 (providers MUST plan to address all requirements and recommendations by this date).
- **Effective applicability:** Optional for Rev5 Authorized providers.

VDR defines minimum vulnerability-management requirements that cloud service providers must meet to be FedRAMP Authorized while allowing flexibility in implementation. The process introduces a machine-readable ongoing-reporting model layered over the existing Authorization Data Sharing (ADS) pipeline.

### What VDR supersedes

The published VDR text is explicit (emphasis ours):

> All existing FedRAMP requirements, including control statements, standards, and other guidelines that reference **vulnerability scanning or formal Plans of Action and Milestones (POA&Ms)**, are superseded by this process and MAY be ignored by providers of cloud service offerings that have met the requirements to adopt this process with approval by FedRAMP.

This directly targets `CONMON.md` sections built on the pre-VDR FedRAMP Continuous Monitoring Playbook v1.0 (2025-11-17): POA&M-shaped outputs (§§2.5, 3 `outputs: poam-csv`, 4.3, 5.3, 7) and monthly scan cadence (§§2.3, 2.4).

### Core VDR constructs absent from current UIAO canon

The VDR process introduces taxonomy and timeframe machinery that has no counterpart in `CONMON.md` as of today:

- **Likely Exploitable Vulnerability (LEV)**, **Internet-Reachable Vulnerability (IRV)**, **Known Exploited Vulnerability (KEV)**, **Accepted Vulnerability**, **False Positive Vulnerability** — defined terms.
- **Potential Adverse Impact ratings N1–N5** — agency-impact ladder; supersedes CVSS/NVD severity framing in `core/CONMON.md` §7.1.
- **Timeframe matrix** (VDR-TFR-PVR) — days-from-evaluation for mitigation/remediation indexed by `[LEV+IRV | LEV+NIRV | NLEV] × [N2..N5]`, replacing the Playbook's monthly POA&M cadence.
- **Persistent Detection cadences** — 7-day samples (VDR-TFR-PSD), 30-day drift (VDR-TFR-PDD), 6-month complete (VDR-TFR-PCD) — replace the `0 2 1 * *` monthly cron in `CONMON.md` §3.
- **192-day accepted-vulnerability cutoff** (VDR-TFR-MAV) — governs the `accepted` state transition.
- **Monthly Activity Report** (VDR-TFR-MHR) + **Persistent Reporting** (VDR-RPT-PER) — human-readable + machine-readable reporting, subject to the ADS process, replacing the POA&M CSV handoff to USDA Connect.gov (per `CONMON.md` §7.2) for adopters.

### UIAO posture check (as of this ADR)

A cross-walk of all 30 VDR-* requirement IDs against `core/`, `docs/`, and `impl/` on `main@8bd87f9` returned **zero matches**. No `VDR-*`, `LEV`, `IRV`, `KEV`, `NIRV`, `NLEV`, `N1..N5`, or `192 days` references exist anywhere in canon. The traditional Playbook model is the only posture in place.

### Why this ADR

Adopting VDR is a canon-affecting decision that:

1. Rewrites significant portions of `core/CONMON.md` (operational companion to the legacy Playbook model).
2. Introduces new operational canon (VDR gap-map, ISCM strategy — see UIAO_203 and UIAO_204).
3. Changes the ongoing-reporting pathway (ADS feed vs. POA&M CSV to Connect.gov).
4. Creates a hard deadline (2026-02-02 sign-up) that bounds the decision window.

The decision cannot ride silently on a PR; it needs an append-only governance record.

## Decision

### D1. Adoption posture

**UNDECIDED pending user ruling.** Two options framed:

- **OPT IN.** Submit the VDR Open Beta sign-up form before 2026-02-02. Commit to addressing all VDR requirements and recommendations by 2026-05-22. Expect that post-adoption, VDR's supersession clause retires the POA&M-to-Connect.gov pipeline described in `CONMON.md` §7.2 for UIAO and replaces it with the ADS-linked Monthly Activity Report and Persistent Reporting feeds.
- **OPT OUT.** Continue operating under the traditional FedRAMP ConMon Playbook v1.0 (2025-11-17) model. Accept that the VDR machinery — taxonomy, N1–N5 impact, LEV/IRV/NIRV timeframes, KEV-catalog adherence — will not be expressed in UIAO canon.

The remaining decisions (D2–D5) are conditional on OPT IN.

### D2. Canon artifact allocation

On adoption, three canon artifacts are created and maintained:

| Artifact | Path | Doc ID | Role |
|---|---|---|---|
| This ADR | `core/canon/adr/adr-032-fedramp-vdr-rev5-open-beta.md` | ADR-032 | Governance decision record |
| ISCM strategy | `core/canon/conmon/iscm-strategy.md` | **UIAO_203** | Closes open item C2 from `CONMON.md` §10 (800-137 §3.1); frames UIAO's monitoring strategy under VDR + 800-137 |
| VDR gap map | `core/canon/conmon/vdr-rev5-gap-map.md` | **UIAO_204** | Cross-walks each `VDR-*` requirement ID to UIAO artifacts (adapters, pipelines, evidence classes) |

Both operational artifacts land under a new `core/canon/conmon/` directory. Classification `OPERATIONAL` per metadata schema v1 (runtime/process artifacts; not source-of-truth canon).

### D3. `CONMON.md` supersession pattern

On adoption, `core/CONMON.md` does **not** get deleted. Instead, each VDR-affected section gets a **supersession header** of the form:

> **SUPERSEDED-ON-ADOPTION (2026-04-18, ADR-032).** Content retained for historical record and for the fallback case if VDR Open Beta participation is suspended. Live operational guidance is in `core/canon/conmon/vdr-rev5-gap-map.md` (UIAO_204).

Affected sections (by current `CONMON.md` heading):

- §2.5 Respond to findings (POA&M monthly cadence)
- §3 Conformance Adapter schema — `outputs: poam-csv` field and `retention-years` alignment
- §4.3 POA&M row shape
- §5.3 `conmon-aggregate.yml` — POA&M feed step
- §6 Significant Change Request playbook — keeps SCR concept, rewrites POA&M attachments
- §7 POA&M feed (the entire section)

Supersession is **conditional on FedRAMP acceptance into the Open Beta**. Until acceptance letter is in hand, the traditional model remains authoritative.

### D4. Evidence-schema changes

The normalized `findings.json` (current `CONMON.md` §4.2) gains VDR-aligned fields:

- `evaluation`: `{ is_lev: bool, is_irv: bool, is_kev: bool, potential_adverse_impact: "N1"|"N2"|"N3"|"N4"|"N5" }`
- `timeframes`: `{ detected_at, evaluated_at, target_mitigation_at, next_reduction_at, overdue: bool }`
- `accepted`: `{ is_accepted: bool, accepted_at, explanation }` (populated when mitigation not completed within 192 days)
- `grouping`: optional opaque group-id per VDR-EVA-GRV (Group Vulnerabilities)

Schema lives at `core/schemas/findings/findings.schema.json` (new, to be created in a follow-on PR).

### D5. Reporting pipeline

Two outputs replace the monthly `poam-YYYY-MM.csv`:

- **Monthly Activity Report** (VDR-TFR-MHR) — human-readable Markdown at `evidence/vdr-reports/monthly/YYYY-MM.md`.
- **Machine-readable feed** (VDR-TFR-MRH / VDR-RPT-PER) — persistent JSON stream at `evidence/vdr-reports/machine/current.json`, updated at least monthly, subject to the FedRAMP ADS process.

Both generated by `tools/conmon/vdr_aggregate.py` (new, follow-on PR). The POA&M CSV generator is kept but no longer wired into CI triggers for VDR-adopted cloud service offerings.

## Consequences

### If OPT IN

- **Positive:** Machine-readable posture feed aligns with UIAO's OSCAL-native evidence model (`VISION.md` pillar 4). VDR's evaluation discipline (VDR-EVA-*) is a natural fit for UIAO's adapter taxonomy. KEV tracking integrates with the KSI engine.
- **Negative:** Open Beta is pre-GA — requirements may shift before 2026-05-22. Sign-up is public; other agencies can see UIAO's participation.
- **Operational:** The `findings.json` contract changes in v2; all downstream consumers (`dashboard/conmon-dashboard.json`, `tools/conmon/aggregate.py`) need updates. Effort estimate: one working session to draft, plus follow-on PRs for schema, pipeline, and CONMON.md supersession.

### If OPT OUT

- **Positive:** No canon churn; existing posture stable.
- **Negative:** UIAO's VDR story lags the FedRAMP curve. If VDR becomes mandatory post-Beta (2026-05-22+ likely), the canon update becomes urgent rather than planned.

## Alternatives considered

- **Partial adoption (cherry-pick VDR taxonomy without Open Beta sign-up).** Rejected: VDR's supersession clause and ADS feed require formal participation. Cherry-picking the taxonomy without participation creates canon that claims compliance without the certification pathway.
- **Wait for VDR GA.** Rejected: the Open Beta is explicitly the path to influence the final requirement set. Early participation is also the path to agency-customer signaling (per VDR's competitive-marketplace framing).

## References

- FedRAMP Rev5 Balance Improvement Releases — Vulnerability Detection and Response process (https://fedramp.gov/docs/rev5/balance/vulnerability-detection-and-response/)
- FedRAMP Continuous Monitoring Playbook v1.0 (2025-11-17) — `core/compliance/reference/fedramp-conmon-playbook/FedRAMP_Continuous_Monitoring_Playbook.pdf`
- NIST SP 800-137 — `core/compliance/reference/nist-sp-800-137/NIST.SP.800-137.pdf`
- CISA BOD 22-01 (KEV catalog) — referenced by VDR-TFR-KEV
- OMB Memorandum M-24-15 §IV(a) — agency notification duty to FedRAMP
- 44 USC § 3613(e) — Presumption of Adequacy
- `core/CONMON.md` v0.1.0 — current (pre-VDR) operational canon
- `core/canon/adr/adr-025-continuous-monitoring-program.md` — ConMon program architecture
- `core/canon/adr/adr-028-monorepo-consolidation-gos-integration.md` — retires federal/commercial firewall
- `core/canon/document-registry.yaml` — UIAO_203 + UIAO_204 allocations

## Change log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-18 | 0.1.0 | Initial draft. PROPOSED status. Frames adoption decision; allocates UIAO_203 (ISCM strategy) and UIAO_204 (VDR gap map); defines supersession pattern for `CONMON.md`; outlines evidence-schema and reporting-pipeline changes conditional on OPT IN. | Claude (Cowork, session `claude/fedramp-continuous-monitoring-WXbxO`) |
