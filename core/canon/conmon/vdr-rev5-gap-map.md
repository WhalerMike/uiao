---
document_id: UIAO_204
title: "UIAO Cross-Walk — FedRAMP VDR Rev5 Open Beta Requirements to UIAO Artifacts"
version: "1.0"
status: Draft
classification: OPERATIONAL
owner: "Michael Stratton"
created_at: "2026-04-18"
updated_at: "2026-04-18"
boundary: "GCC-Moderate"
---

# UIAO Cross-Walk — FedRAMP VDR Rev5 Open Beta Requirements to UIAO Artifacts

> Cross-walks each `VDR-*` requirement/recommendation ID in the FedRAMP **Vulnerability Detection and Response** Rev5 Open Beta process to the UIAO artifact (adapter, pipeline, schema, evidence class, or ADR section) that implements or satisfies it. Authoritative runbook referenced by `ADR-032` on OPT IN. Operational companion to `UIAO_203` (ISCM Strategy).

**Scope:** This document applies only if UIAO **OPTS IN** to the VDR Open Beta per ADR-032. Until adoption, the legacy POA&M-shaped pipeline in `core/CONMON.md` remains authoritative.

**VDR source:** https://fedramp.gov/docs/rev5/balance/vulnerability-detection-and-response/ (page content captured verbatim in ADR-032 context; re-fetched on reference-check per `CONMON.md` §9).

---

## 1. Methodology

Each VDR section becomes a subsection below. Each `VDR-*` ID is listed in a three-column table:

| Col | Meaning |
|---|---|
| **ID** | The VDR requirement or recommendation identifier, exactly as published. |
| **Obligation** | `MUST` / `MUST NOT` / `SHOULD` / `SHOULD NOT` / `MAY` — the exact normative verb used in VDR. |
| **UIAO implementation** | The repo path, ADR section, schema, or pipeline step that implements or is the planned home for this requirement. `PLANNED` means the artifact is named here and will be delivered in a follow-on PR. `N/A` means VDR assigns the requirement to another party (FedRAMP or an Agency). |

**Impact-level applicability.** Every VDR-TFR and VDR-RPT requirement in the published source is tagged `Low / Moderate / High` (all three apply for UIAO's FedRAMP Moderate posture). VDR-EVA / VDR-BST / VDR-CSO requirements apply to all providers. Rows below do not re-state this — assume all rows apply unless the `UIAO implementation` column says otherwise.

---

## 2. FedRAMP's responsibilities (VDR-FRP-*)

These apply to FedRAMP, not to CSPs. UIAO tracks them only to avoid acting on non-UIAO requests inappropriately.

| ID | Obligation | UIAO implementation |
|---|---|---|
| **VDR-FRP-ARP** | `MAY` | N/A — FedRAMP may require additional/alternative vulnerability info as part of a CAP. UIAO will treat such a request as a transformative change trigger (SCR Playbook §Transformative Changes) and process it through `ADR-032` D3 supersession footprint. |
| **VDR-FRP-ADV** | `MAY` | N/A — FedRAMP may request sensitive vulnerability details. UIAO's `CONMON.md` §4 evidence bundles are already SHA-256-integrity-manifested; sharing happens out-of-band via the FedRAMP secure repository, not in-repo. |

---

## 3. General provider responsibilities (VDR-CSO-*)

| ID | Obligation | UIAO implementation |
|---|---|---|
| **VDR-CSO-DET** (Vulnerability Detection) | `MUST` | Implemented via conformance adapters registered in `core/canon/adapter-registry.yaml` (`class: conformance`). Current: ScubaGear (M365 SCuBA baseline). Future: per-platform adapters registered as added. Supplementary detection channels (bug bounty, VDP, supply-chain monitoring, threat intel) are declared in this document §8 below. |
| **VDR-CSO-RES** (Vulnerability Response) | `MUST` | End-to-end pipeline: adapter run → `findings.json` normalization → evaluation enrichment (§4 below) → `tools/conmon/vdr_aggregate.py` (PLANNED) → Monthly Activity Report + machine-readable feed per ADR-032 D5. Partial-mitigation posture encoded in `findings.json` v2 `timeframes.target_mitigation_at`. |
| **VDR-CSO-DOC** (Documentation for Recommendations) | `MUST` | Any UIAO deviation from a VDR `SHOULD` recommendation is documented in-band in this file under the corresponding row. On VDR adoption, UIAO commits to documenting deviations as a required row in §11 (Deviations log). Deviations are part of the authorization data per VDR-CSO-DOC. |

---

## 4. Evaluation (VDR-EVA-*)

Evaluation is the pipeline stage that runs on every finding after detection but before reporting. New in UIAO — does not exist in the pre-VDR `CONMON.md` shape.

| ID | Obligation | UIAO implementation |
|---|---|---|
| **VDR-EVA-ELX** (Evaluate Exploitability) | `MUST` | `findings.json` v2 `evaluation.is_lev` (boolean). Populated by `tools/conmon/evaluator.py` (PLANNED). LEV decisions are captured with rationale in `evaluation.lev_reasoning` (free-text, bounded to 512 chars). |
| **VDR-EVA-EIR** (Evaluate Internet-Reachability) | `MUST` | `findings.json` v2 `evaluation.is_irv` (boolean). The detection context (adapter ID + affected-resource pointer) feeds a per-adapter reachability heuristic declared in the adapter's `canon/adapters/<adapter-id>.md`. |
| **VDR-EVA-EPA** (Estimate Potential Adverse Impact) | `MUST` | `findings.json` v2 `evaluation.potential_adverse_impact` (enum `N1..N5`). Mapping table between ScubaGear native severity (Critical/High/Medium/Low/Info) and `N1..N5` lives in `canon/adapters/scubagear.md` §Evaluation — the adapter specification owns the mapping so it can evolve per-adapter. |
| **VDR-EVA-GRV** (Group Vulnerabilities) | `SHOULD` | `findings.json` v2 `grouping.group_id` (nullable opaque string). Grouping heuristic is adapter-specific; default is null (no grouping). When set, downstream timeframe and reporting logic applies to the group rather than individual findings. |
| **VDR-EVA-EFP** (Evaluate False Positives) | `SHOULD` | `findings.json` v2 `evaluation.is_false_positive` (boolean) + `evaluation.false_positive_reasoning` (free-text). False positives flow through reporting the same as real findings, flagged distinctly per VDR-RPT-VDT. |
| **VDR-EVA-EFA** (Evaluation Factors) | `SHOULD` | `findings.json` v2 `evaluation.factors` (object keyed by VDR's 8 factors: criticality, reachability, exploitability, detectability, prevalence, privilege, proximate_vulnerabilities, known_threats; each value 0–10 scale). Default unpopulated; populated when LEV/IRV evaluations require rationale. |

---

## 5. Best practices (VDR-BST-*)

| ID | Obligation | UIAO implementation |
|---|---|---|
| **VDR-BST-DFR** (Design For Resilience) | `SHOULD` | Architectural — `docs/docs/00_CorePrinciples.qmd` already encodes SSOT + drift-detection + canon-anchored evidence as design defaults. No additional VDR-specific artifact required; this is satisfied by the substrate architecture. |
| **VDR-BST-ADT** (Automate Detection) | `SHOULD` | Satisfied. All detection is via GitHub Actions workflows (`conformance-run.yml`, `conmon-scheduled.yml`) — zero manual detection in the pipeline. |
| **VDR-BST-DAC** (Detect After Changes) | `SHOULD` | Implemented via `conmon-aggregate.yml` trigger on `push` to `evidence/conformance/**/findings.json` (`CONMON.md` §5.3) plus the `modernization-completed` `repository_dispatch` event (`CONMON.md` §5.1). Post-VDR: the same triggers fire the VDR evaluator pipeline. |
| **VDR-BST-MSP** (Maintain Security) | `SHOULD NOT` | Posture statement. UIAO does not weaken tenant security to enable scanning — service-principal authentication is scoped to Graph read scopes only (`CONMON.md` §10 item C5). This row is satisfied by non-action. |
| **VDR-BST-AKE** (Avoid KEVs) | `SHOULD NOT` | Pre-deployment check. PLANNED: `tools/conmon/kev_gate.py` — queries the CISA KEV catalog API and rejects any modernization adapter run that would deploy a resource with a KEV. Integrated into the modernization adapter workflow template. |
| **VDR-BST-SIR** (Sampling) | `MAY` | Sampling is per-adapter. `canon/adapters/<adapter-id>.md` declares sampling policy (full sweep vs. representative sample) per information-resource class. Default: full sweep (non-sampled). |

---

## 6. Timeframes (VDR-TFR-*)

The heart of VDR. Replaces the monthly-POA&M cadence in `CONMON.md` §7. All rows apply at Low / Moderate / High.

| ID | Obligation | UIAO implementation |
|---|---|---|
| **VDR-TFR-MHR** (Monthly Activity Report) | `MUST` | Output: `evidence/vdr-reports/monthly/YYYY-MM.md`. Generator: `tools/conmon/vdr_aggregate.py --monthly` (PLANNED). Consumers: agency AO, FedRAMP PMO. Template includes VDR-RPT-VDT and VDR-RPT-AVI content. |
| **VDR-TFR-MAV** (Mark Accepted Vulnerabilities) | `MUST` | 192-day cutoff enforced by `vdr_aggregate.py`. At T+192d unresolved, `findings.json` `accepted.is_accepted` flips to `true` and `accepted.explanation` is required (population gated at report-generation time — unpopulated → report fails, hard block). |
| **VDR-TFR-KEV** (Remediate KEVs) | `SHOULD` | Tracked against CISA BOD 22-01 due dates. KEV-matched findings get an additional field `evaluation.kev_due_date` (copied from CISA catalog). `vdr_aggregate.py` raises a regression issue on T-3d approach and on missed due date. |
| **VDR-TFR-MRH** (Historical Activity — machine-readable) | `SHOULD` | Output: `evidence/vdr-reports/machine/current.json` (append-only). Served via GitHub raw content URL in the interim; API endpoint reserved for Phase 3+. Updated at least monthly per the persistent requirement. |
| **VDR-TFR-PSD** (Persistent Sample Detection) | `SHOULD` | `cron: '0 2 * * 1'` on `conmon-sampled.yml` (PLANNED) — weekly Monday 02:00 UTC, scoped to adapters whose `canon/adapters/<id>.md` declares `sampling: true`. |
| **VDR-TFR-PDD** (Persistent Drift Detection) | `SHOULD` | Existing monthly cadence (`cron: '0 2 1 * *'` in `conmon-scheduled.yml`, `CONMON.md` §5.2). Resources likely to drift = everything in `modernization-registry.yaml` plus tenant-configuration surfaces per adapter declaration. |
| **VDR-TFR-PCD** (Persistent Complete Detection) | `SHOULD` | New: `conmon-complete.yml` (PLANNED) — `cron: '0 3 1 */6 *'` twice a year on 1 Jan + 1 Jul. Scopes adapters whose `canon/adapters/<id>.md` declares `drift-likely: false`. Extended evidence retention (5 years) per `VDR-RPT-PER` needs. |
| **VDR-TFR-EVU** (Evaluate Vulnerabilities Quickly) | `SHOULD` | 7-day SLA from detection to evaluation. Enforced by `vdr_aggregate.py --overdue-check` run via `conmon-aggregate.yml`. Breach raises a `conmon/overdue-evaluation` GitHub issue. |
| **VDR-TFR-PVR** (Mitigation and Remediation Expectations) | `SHOULD` | Matrix table below, verbatim from VDR. Enforced by `vdr_aggregate.py`. Overdue findings surface both in the machine-readable feed and as `conmon/overdue-remediation` GitHub issues. |
| **VDR-TFR-RMN** (Remaining Vulnerabilities) | `SHOULD` | Findings below the matrix thresholds are mitigated during routine operations per UIAO-CSP judgment. No automated enforcement. Captured in the Monthly Activity Report high-level overview. |
| **VDR-TFR-IRI** (Internet-Reachable Incidents) | `MAY` | UIAO elects to treat LEV+IRV+N4/N5 findings as security incidents until partial mitigation to N3 or below. Routed through the CONMON.md §Incident-communications pattern. Deviation from `MAY` documented here: **adopted**, not deviated. |
| **VDR-TFR-NRI** (Non-Internet-Reachable Incidents) | `MAY` | UIAO elects to treat LEV+NIRV+N5 findings as security incidents until partial mitigation to N4 or below. Same routing as VDR-TFR-IRI. |

### 6.1 Timeframe matrix (VDR-TFR-PVR, verbatim)

Days from evaluation by `[LEV+IRV | LEV+NIRV | NLEV] × [N5..N2]`:

| Potential Adverse Impact | LEV + IRV | LEV + NIRV | NLEV |
|---|---|---|---|
| N5 | 4 | 8 | 32 |
| N4 | 8 | 32 | 64 |
| N3 | 32 | 64 | 192 |
| N2 | 96 | 160 | 192 |

N1 is unbounded — UIAO applies VDR-TFR-RMN (Remaining Vulnerabilities) for N1.

---

## 7. Reporting (VDR-RPT-*)

| ID | Obligation | UIAO implementation |
|---|---|---|
| **VDR-RPT-PER** (Persistent Reporting) | `MUST` | `evidence/vdr-reports/machine/current.json` plus the Monthly Activity Report. Both are authorization data and flow through the FedRAMP Authorization Data Sharing (ADS) process on adoption. |
| **VDR-RPT-NID** (Responsible Disclosure) | `MUST NOT` | Encoded as a policy gate in `vdr_aggregate.py` — sensitive exploitation details are filtered out of the machine-readable feed based on a per-adapter `sensitive-fields` list declared in `canon/adapters/<id>.md`. |
| **VDR-RPT-VDT** (Vulnerability Details) | `MUST` | `findings.json` v2 fields map 1:1 to VDR-RPT-VDT's 11 required fields: tracking ID (`id`), time/source of detection (`detected_at`/`detector`), evaluation time (`evaluated_at`), IRV flag, LEV flag, historical + current adverse-impact (`evaluation.potential_adverse_impact_history[]` + `evaluation.potential_adverse_impact`), time/level of each completed impact reduction, estimated next-reduction time/target, overdue flag, supplementary info (`supplementary`), final disposition (`disposition`). |
| **VDR-RPT-AVI** (Accepted Vulnerability Info) | `MUST` | Subset of VDR-RPT-VDT fields plus mandatory `accepted.explanation`. Enforced at report-generation time (see VDR-TFR-MAV). |
| **VDR-RPT-HLO** (High-Level Overviews) | `SHOULD` | Monthly Activity Report §High-level overview section — covers VDP, bug bounty, pen-test, assessments per month. Data sources: `inbox/vulnerability-programs.yaml` (PLANNED) + the adapter-declared supplementary channels in §8 below. |
| **VDR-RPT-RPD** (Responsible Public Disclosure) | `MAY` | Governed by `docs/findings/README.md`'s class contract — findings published under `docs/findings/` are explicitly redacted of exploitation details per VDR-RPT-NID. Public disclosure is an opt-in editorial decision per finding. |

---

## 8. Supplementary detection channels (UIAO-declared)

Per VDR-CSO-DET and VDR-RPT-HLO, UIAO declares the following supplementary detection channels:

| Channel | Status | Owner | Output route |
|---|---|---|---|
| Coordinated Vulnerability Disclosure (VDP) | Per `SECURITY.md` | `owner` field of `SECURITY.md` | Findings land in `docs/findings/` per `docs/findings/README.md` class contract |
| Bug bounty | Not in place | TBD | PLANNED — decision tracked as a new open item in `CONMON.md` §10 on VDR adoption |
| Supply chain monitoring | Dependabot — active | Dependabot | GitHub security advisories + Dependabot PRs |
| Threat intelligence | Not in place | TBD | PLANNED — open item on VDR adoption |
| Penetration testing | Annual by 3PAO | 3PAO (TBD) | 3PAO SAR via the FedRAMP secure repository |

---

## 9. Agency guidance (VDR-AGM-*)

These apply to **agencies** reusing UIAO's FedRAMP authorization, not to UIAO. Tracked here so UIAO knows what agencies SHOULD and SHOULD NOT do, and so UIAO's communications to agency customers align.

| ID | Obligation | UIAO posture |
|---|---|---|
| **VDR-AGM-RVR** (Review Vulnerability Reports) | `SHOULD` (agency) | UIAO provides both a human-readable Monthly Activity Report and a machine-readable feed (VDR-TFR-MHR / VDR-TFR-MRH) sized for automated agency-side processing. |
| **VDR-AGM-MAP** (Maintain Agency POA&M) | `SHOULD` (agency) | Agency-side. UIAO provides the data; agency maintains any agency-side POA&M. UIAO does not duplicate the agency's POA&M inside the UIAO repo. |
| **VDR-AGM-DRE** (Do Not Request Extra Info) | `SHOULD NOT` (agency) | UIAO expects agency requests to be bounded by the VDR-required fields. Extra-info requests outside that bound are routed through FedRAMP per VDR-AGM-NFR. |
| **VDR-AGM-NFR** (Notify FedRAMP) | `MUST` (agency) | Agency-side. UIAO logs any extra-info request received + any FedRAMP notification acknowledgement in the monthly report's high-level overview for traceability. |

---

## 10. Gap summary — what's missing from UIAO on OPT IN

Everything tagged `PLANNED` above. Collated for the follow-on PR sequence:

1. **`core/schemas/findings/findings.schema.json`** — defines `findings.json` v2 (VDR-EVA fields, `timeframes`, `accepted`, `grouping`).
2. **`tools/conmon/evaluator.py`** — populates `evaluation.*` fields per adapter run.
3. **`tools/conmon/vdr_aggregate.py`** — monthly/machine reports, overdue checks, accepted-state transitions, regression issues.
4. **`tools/conmon/kev_gate.py`** — VDR-BST-AKE pre-deployment check.
5. **`.github/workflows/conmon-sampled.yml`** — weekly VDR-TFR-PSD runs.
6. **`.github/workflows/conmon-complete.yml`** — semi-annual VDR-TFR-PCD runs.
7. **`canon/adapters/<id>.md` per-adapter VDR metadata block** — sampling policy, drift-likely flag, sensitive-fields list, severity→`N1..N5` mapping, reachability heuristic.
8. **`inbox/vulnerability-programs.yaml`** — VDR-RPT-HLO data source for VDP/bug-bounty/pen-test summaries.
9. **New open items C9+ in `CONMON.md` §10** — bug-bounty decision, threat-intel channel decision, severity-mapping ratification per adapter.

---

## 11. Deviations log

Per VDR-CSO-DOC. Empty on creation.

| Date | VDR ID | Recommendation (verbatim) | UIAO deviation | Reason | Owner |
|---|---|---|---|---|---|
| _(none)_ | | | | | |

---

## 12. References

- FedRAMP Rev5 Balance — Vulnerability Detection and Response (Open Beta) — https://fedramp.gov/docs/rev5/balance/vulnerability-detection-and-response/
- `core/canon/adr/adr-032-fedramp-vdr-rev5-open-beta.md` — adoption decision
- `core/canon/conmon/iscm-strategy.md` (UIAO_203) — strategy
- `core/CONMON.md` — legacy ConMon operational companion (partially superseded on VDR adoption per ADR-032 D3)
- FedRAMP Continuous Monitoring Playbook v1.0 (2025-11-17) — `core/compliance/reference/fedramp-conmon-playbook/FedRAMP_Continuous_Monitoring_Playbook.pdf`
- NIST SP 800-137 — `core/compliance/reference/nist-sp-800-137/NIST.SP.800-137.pdf`
- CISA BOD 22-01 (KEV catalog) — CISA.gov
- `core/canon/adapter-registry.yaml` — conformance adapters (detection surface)
- `core/canon/modernization-registry.yaml` — change-making adapters (VDR-BST-AKE scope)
- `docs/findings/README.md` — governance-findings class (VDR-RPT-RPD channel)
- `SECURITY.md` — VDP contact

---

## 13. Change log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-18 | 1.0 | Initial draft (status `Draft`). Cross-walks all 30 VDR-* IDs (FRP-2, CSO-3, EVA-6, BST-6, TFR-12, RPT-6, AGM-4 — minus 3 AGM-only IDs that don't apply to UIAO as CSP) to UIAO artifacts. Nine PLANNED artifacts enumerated in §10 for the VDR-adoption follow-on PR sequence. Deviations log empty on creation. | Claude (Cowork, session `claude/fedramp-continuous-monitoring-WXbxO`) |

