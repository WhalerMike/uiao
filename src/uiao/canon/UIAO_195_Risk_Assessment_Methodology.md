---
document_id: UIAO_195
title: "UIAO Risk Assessment Methodology (NIST SP 800-30 Rev 1)"
version: "0.1"
status: Draft
owner: Michael Stratton
created_at: "2026-06-19"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO Risk Assessment Methodology (NIST SP 800-30 Rev 1)

> **Status: Draft / template.** Canonical scoring methodology backing the
> Risk Assessment (RA) control family. `RA-3` asserts that "risk assessment
> methodology aligns with NIST SP 800-30 Rev 1"
> ([`RA-3.yml`](data/control-library/ra/RA-3.yml), `PARAM-RA-003-003`); until
> this document existed, that methodology lived only in an external SharePoint
> location, leaving the assertion without a canonical source (an SSOT /
> `DRIFT-PROVENANCE` gap per [AGENTS.md operating principles](../../../AGENTS.md)).
> This document **is** that source: the qualitative likelihood × impact scoring
> matrix, the threat and vulnerability taxonomies, and the risk-determination
> rubric that `RA-3` cites. Bracketed `[PLACEHOLDER]` fields are completed per
> authorizing agency.

## Purpose

Establish the single canonical methodology by which risk to a UIAO Governance
OS deployment is **identified, analyzed, scored, and prioritized**, so that a
risk rating recorded anywhere in the substrate (the ServiceNow GRC Risk
Register, a POA&M item, an SSP risk narrative) traces to one published scale
rather than to an analyst's discretion. The methodology aligns with **NIST SP
800-30 Rev 1** (*Guide for Conducting Risk Assessments*) and feeds the control
selection, continuous-monitoring, and POA&M processes already canonized
elsewhere in the corpus.

This is a **compliance** artifact, co-equal with the governance corpus: it
operationalizes the RA control family rather than describing substrate
internals. It does not introduce doctrine — it makes explicit a methodology the
RA controls already require — so it is registered as canon without a dedicated
ADR, consistent with the UIAO_185–192 compliance-template series.

## Scope and applicability

| In scope | Out of scope |
|---|---|
| Risk to the UIAO information system: confidentiality, integrity, availability of the governance substrate and the identity/telemetry/policy data it processes | Enterprise/mission risk outside the system boundary (handled by the agency risk-management strategy, `PM-9`) |
| The three-tier framing of NIST SP 800-39 as the *context* for system-tier assessment | Privacy risk determination — see [UIAO_192](UIAO_192_Privacy_Impact_Assessment.md) (PT family) |
| Supplier/component risk *scoring* (the scale is shared) | Supply-chain process — see [UIAO_191](UIAO_191_Supply_Chain_Risk_Management_Plan.md) (`SR` family) |
| Identity-specific risk inputs | Identity risk *model* internals — see [UIAO_170](UIAO_170_Identity_Risk_Scoring_Model.md) |

## Assessment process (NIST SP 800-30 Rev 1 §3)

The methodology follows the four-step process of the standard:

1. **Prepare** — establish the assessment scope, the system boundary (inherited
   from the `RA-2` security categorization), assumptions, and the information
   and threat sources to be used.
2. **Conduct** — identify threat sources and events, identify vulnerabilities
   and predisposing conditions, determine **likelihood**, determine **impact**,
   and determine **risk** as the combination of the two (the matrices in the
   sections below).
3. **Communicate** — disseminate results to the AO, ISSO, System Owner, and
   CISO (`RA-3` `PARAM-RA-003-002`) via the risk register and the SSP risk
   narrative.
4. **Maintain** — keep the assessment current through continuous monitoring
   ([UIAO_190](UIAO_190_Continuous_Monitoring_Strategy.md), `CA-7`) and
   re-assess at least annually or on significant change (`RA-3`
   `PARAM-RA-003-001`).

## §1 — Threat sources and threat events (SP 800-30 Rev 1 Appendix D / E)

Threat **sources** are characterized by type and, for adversarial sources, by
capability, intent, and targeting. Threat **events** are the actions a source
takes. UIAO seeds these from Microsoft Sentinel threat-intelligence feeds and
MITRE ATT&CK technique mapping (`RA-3` narrative), then records them against the
following taxonomy.

| Source class | Characterization | UIAO input |
|---|---|---|
| Adversarial | Capability × Intent × Targeting (Appendix D, Tables D-3…D-5) | Sentinel TI, MITRE ATT&CK, CyberArk privileged-access analytics |
| Accidental | Range of effect of an erroneous action | ServiceNow incident history, change records |
| Structural | Equipment / software / control failure | Defender for Cloud posture, drift findings (`src/uiao/governance/drift.py`) |
| Environmental | Natural or infrastructure outage | Inherited infrastructure availability posture |

Threat events are rated for **relevance** (Appendix E, Table E-4: Confirmed →
Expected → Anticipated → Predicted → Possible → Not Applicable). Only events of
*Possible* relevance or higher enter the likelihood determination.

## §2 — Vulnerabilities and predisposing conditions (Appendix F)

Vulnerabilities are identified from Microsoft Defender for Cloud
recommendations, `RA-5` vulnerability scanning, and substrate drift findings.
Each is rated for **severity** (Very Low → Very High) using the pervasiveness of
the weakness and the exposure created by predisposing conditions (e.g., a
control not yet adopted at the relevant ADR-076 tier is a predisposing
condition that raises exposure). Severity and pervasiveness feed the likelihood
determination in §3.

## §3 — Likelihood determination (Appendix G)

Likelihood is assessed in two parts and combined, per the standard:

- **Likelihood of initiation/occurrence** — for adversarial events, a function
  of source capability and intent against the targeted system; for
  non-adversarial events, the expected frequency.
- **Likelihood of resulting in adverse impact** — given initiation, the
  probability the event succeeds against the vulnerability, accounting for
  in-place controls.

The two combine into an **overall likelihood** on the shared five-level scale.
The semi-quantitative anchors (Appendix G, Table G-2 / the Appendix I value
scale) are retained so a register entry can carry either the qualitative band
or its representative value:

| Qualitative | Semi-quantitative value | Description |
|---|---|---|
| Very High | 96–100 (10) | Almost certain to occur and succeed |
| High | 80–95 (8) | Highly likely |
| Moderate | 21–79 (5) | Somewhat likely |
| Low | 5–20 (2) | Unlikely |
| Very Low | 0–4 (0) | Highly unlikely |

## §4 — Impact determination (Appendix H)

Impact is the magnitude of harm from a successful threat event. The impact
**level is inherited from the `RA-2` security categorization** (FIPS 199
confidentiality/integrity/availability levels) rather than re-derived, so the
risk assessment and the categorization cannot disagree —
[UIAO_185](UIAO_185_System_Security_Plan_Template.md) §3 holds the categorization
of record. Harm types (Appendix H, Table H-2) span operations, assets,
individuals, other organizations, and the Nation; the representative scale
mirrors §3.

| Qualitative | Semi-quantitative value | Description |
|---|---|---|
| Very High | 96–100 (10) | Multiple severe or catastrophic adverse effects |
| High | 80–95 (8) | Severe or catastrophic adverse effect |
| Moderate | 21–79 (5) | Serious adverse effect |
| Low | 5–20 (2) | Limited adverse effect |
| Very Low | 0–4 (0) | Negligible adverse effect |

## §5 — Risk determination: the likelihood × impact matrix (Appendix I)

Risk is the combination of overall likelihood (§3) and impact (§4), read off
the matrix below — UIAO's canonical reproduction of **NIST SP 800-30 Rev 1
Table I-2** (*Assessment Scale — Level of Risk*). This is the heatmap of
record: every risk rating in the ServiceNow GRC Risk Register
([`RA-3.yml`](data/control-library/ra/RA-3.yml)) is the cell where its assessed
likelihood row meets its impact column. Rows are **likelihood**; columns are
**impact**.

| Likelihood ↓ / Impact → | Very Low | Low | Moderate | High | Very High |
|---|---|---|---|---|---|
| **Very High** | Very Low | Low | Moderate | High | **Very High** |
| **High** | Very Low | Low | Moderate | High | **Very High** |
| **Moderate** | Very Low | Low | Moderate | Moderate | High |
| **Low** | Very Low | Low | Low | Low | Moderate |
| **Very Low** | Very Low | Very Low | Very Low | Low | Low |

The resulting **risk level** drives disposition urgency:

| Risk level | Disposition |
|---|---|
| **Very High** | Unacceptable. Immediate executive attention; do not operate without remediation or a formal, time-bound risk acceptance by the AO. |
| **High** | Remediate on a priority schedule; tracked as a high-priority POA&M item. |
| **Moderate** | Remediate on the standard POA&M schedule or document a justified acceptance. |
| **Low** | Track; remediate opportunistically. |
| **Very Low** | Monitor; ordinarily accepted. |

## §6 — Risk response (SP 800-30 feeds SP 800-39 §2.3)

Each determined risk receives a documented response — **accept, mitigate,
transfer, or avoid** (the four responses named in the `RA-3` narrative) — with a
risk owner assigned in the ServiceNow GRC Risk Register. Risks dispositioned to
**mitigate** open a Plan of Action and Milestones item
([UIAO_189](UIAO_189_POAM_Template.md), `CA-5`) carrying the milestone dates,
responsible party, and completion status. **Accept** decisions at Moderate or
above require AO sign-off recorded against the register entry. The residual risk
after response is re-scored on the same matrix and recorded as the
**residual-risk** value.

## §7 — Cadence, dissemination, and maintenance

Assessments are conducted at least **annually** or upon significant system
change, new threat intelligence, or a security incident (`RA-3`
`PARAM-RA-003-001`). Results are disseminated to the **AO, ISSO, System Owner,
and CISO** (`RA-3` `PARAM-RA-003-002`) through the Executive Dashboard and
formal risk briefings. Between assessments, continuous monitoring
([UIAO_190](UIAO_190_Continuous_Monitoring_Strategy.md), `CA-7`) surfaces risk
changes — including substrate drift findings — that trigger re-scoring without
waiting for the annual cycle.

## §8 — Control and artifact traceability

| Concern | Authoritative source |
|---|---|
| Risk assessment control (cites this methodology) | [`RA-3.yml`](data/control-library/ra/RA-3.yml) |
| Risk assessment policy & procedures | [`RA-1.yml`](data/control-library/ra/RA-1.yml) |
| Impact level (FIPS 199 categorization) | [`RA-2.yml`](data/control-library/ra/RA-2.yml) → [UIAO_185](UIAO_185_System_Security_Plan_Template.md) §3 |
| Vulnerability inputs | [`RA-5.yml`](data/control-library/ra/RA-5.yml) |
| Remediation tracking (POA&M) | [UIAO_189](UIAO_189_POAM_Template.md) (`CA-5`) |
| Risk monitoring between assessments | [UIAO_190](UIAO_190_Continuous_Monitoring_Strategy.md) (`CA-7`) |
| Supply-chain risk (shared scale) | [UIAO_191](UIAO_191_Supply_Chain_Risk_Management_Plan.md) (`SR`) |
| Privacy risk (separate determination) | [UIAO_192](UIAO_192_Privacy_Impact_Assessment.md) (PT) |
| Enterprise risk-management strategy | `PM-9` (agency-level) |

## References

- NIST SP 800-30 Rev 1 — *Guide for Conducting Risk Assessments* (methodology, Appendices D–I)
- NIST SP 800-39 — *Managing Information Security Risk* (three-tier risk-management context)
- FIPS 199 / NIST SP 800-60 Vol. II — security categorization (impact source, via `RA-2`)
- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP (risk narrative, categorization of record)
- [UIAO_189](UIAO_189_POAM_Template.md) — POA&M Template (`CA-5`)
- [UIAO_190](UIAO_190_Continuous_Monitoring_Strategy.md) — Continuous Monitoring Strategy (`CA-7`)
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — Gap Closure Register (Workstream A)
