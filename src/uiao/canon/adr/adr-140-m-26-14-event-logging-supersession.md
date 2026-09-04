---
id: ADR-140
title: "OMB M-26-14 Event-Logging Supersession — Retiring the M-21-31 EL0–EL3 Tiers from Live Claims"
status: PROPOSED
date: 2026-09-04
deciders:
  - governance-steward
  - conmon-steward
  - Michael Stratton
extends: []
supersedes: []
tags:
  - omb-m-26-14
  - omb-m-21-31
  - event-logging
  - telemetry
  - retention
  - au-11
  - conmon
  - compliance-spine
canon_refs:
  - UIAO_174
related_findings:
  - FINDING-PGM-004
related_discussions:
  - https://www.whitehouse.gov/omb/information-for-agencies/memoranda/
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-140-m-26-14-event-logging-supersession.html
---

# ADR-140: OMB M-26-14 Event-Logging Supersession — Retiring the M-21-31 EL0–EL3 Tiers from Live Claims

## Status

**PROPOSED — 2026-09-04.** OMB Memorandum **M-26-14**, *Ensuring
Effective and Efficient Agency Logging and Network Visibility*
(22 May 2026), rescinds **OMB M-21-31** outright. The environmental fact
is recorded in
[FINDING-PGM-004](../../../../docs/findings/omb-m-26-14-rescinds-m-21-31-event-logging.qmd);
this ADR is the substrate's decision in response.

### Status history

| Date | Status | Note |
|---|---|---|
| 2026-09-04 | PROPOSED | Initial landing from the 3–4 September 2026 corpus assessment and Requirements Register. Promotion to ACCEPTED gated on direct retrieval of the M-26-14 text (§Ratification gate). |

## Context

M-21-31 has been the substrate's event-logging authority since the
compliance spine was first authored. It sits in
`orgcomp-compliance-spine.yml` as the authority driver `omb-m-21-31` on
the **AU-2**, **AU-3**, **AU-12** and **SI-4** control rows, which means
it propagates into every generated authorities table, and it is cited in
the SIEM telemetry-emission guides, the ConMon gap roadmap and the
whitepaper corpus.

The rescission is not a renaming. Three things moved:

1. **EL0–EL3 no longer exist.** A five-level maturity model (0
   Ineffective through 4 Optimal) replaces them, **scored to the lowest
   watermark** — one deficient category caps the score. The tier
   vocabulary has no issuing authority behind it any more.
2. **Scope moved from enumerated tiers to risk**, via Critical Event
   Monitoring and a Threat-Informed Risk Framework.
3. **Retention was re-parameterised** to six months actively searchable
   and one year retrievable, against the twelve-months-active figure the
   substrate's AU-11 narratives were written to.

The corpus assessment of 3 September 2026 found M-21-31 cited in the
present tense in 46 files, 71 days after it stopped being in force, and
identified this as one of four "single-lookup kill" citations — an error
a federal reviewer finds in one search and which ends the review at the
point it is found.

## Decision

**D1 — The spine authority driver moves.** `omb-m-21-31` is replaced by
`omb-m-26-14` in `orgcomp-compliance-spine.yml`, on every control row
that carried it (AU-2 ×3, AU-3, AU-12, SI-4). The generated authorities
tables are regenerated from the spine; they are not hand-edited.

**D2 — EL0–EL3 vocabulary is retired from live claims.** No artifact
emits, and no document asserts in the present tense, an "EL0"/"EL1"/
"EL2"/"EL3" event-logging tier. Where a maturity position must be
stated, it is stated against M-26-14's five-level model and named as
such, including the lowest-watermark scoring rule, which is the part a
reader will otherwise assume works like an average.

**D3 — Retention is re-parameterised.** AU-11 and audit-retention
narratives state **six months actively searchable and one year
retrievable** as the federal floor, sourced to M-26-14. Where the
substrate's own operational target is longer, it is labelled as the
program's target rather than as the federal requirement — the same
discipline ADR-111 applies to SLA tiers.

**D4 — Deadlines are cited in relative form only.** M-26-14's milestones
are anchored to the publication of CISA's Logging Reference Architecture
(August 2026): plans at +90 days, maturity levels at +120 / +180 / +320
days. **No document converts these to a fixed calendar date.** A derived
date presented as if the memo stated it is the failure mode this
decision exists to prevent, and it is the specific error the assessment's
own adversarial pass caught in its first draft.

M-26-14's milestones are therefore **deliberately not registered** in
`orgcomp-authority-deadlines.yml`. That registry is calendar-date-keyed
by construction — every entry carries a `date`, and
`check_authority_deadlines.py` reads `entry["date"]` unconditionally to
assert that prose naming the event carries that date. Registering a
derived date there would make the consistency gate *require* the fixed
form and bless the exact error this decision forbids. A relative
deadline cannot be expressed honestly in a calendar registry, and the
right response is to leave it out and say so, not to launder the
derivation through a `note:` field the gate does not read. Extending the
registry to carry anchor-plus-offset entries is the follow-up; until
then, M-26-14's schedule is governed by this ADR and by
FINDING-PGM-004, not by the gate.

**D5 — Historical citations are preserved, not swept.** A past-tense
citation describing what M-21-31 required, as the predecessor of the
current regime, is correct and stays. The charter provenance records and
the dated corpus-sweep findings artifacts are **not** rewritten: they are
a dated disclosure record, and editing them to say something their author
did not say at that date destroys the record's value. Only present-tense
live citations move.

## Consequences

**Positive.** The four control rows that drive every generated
authorities table now name an instrument that is in force. The
lowest-watermark scoring rule is stated where the tier vocabulary used
to sit, which is a stronger claim than EL3 ever was — it tells a reader
that one weak category caps the agency, which is the operationally
important property.

**Negative / accepted cost.** The retention change is a **loosening** of
the active-search floor (twelve months to six) and a tightening of the
retrievable horizon. Any gap analysis that scored an environment against
"12 months active" re-scores, and some gaps close on paper without
anything in the environment changing. That is a real reporting
discontinuity and it must be disclosed where it occurs rather than
silently absorbed.

**Unresolved.** The substrate does not yet model CEM/THIRF scoping, and
this ADR does not introduce it. Until it does, documents state the
five-level maturity model and the retention floor, and are silent on
risk-based scope selection rather than inventing a mapping.

## Ratification gate

Promotion from PROPOSED to ACCEPTED requires:

1. Direct retrieval of the **M-26-14 text**, confirming the rescission
   sentence, the five-level model, the lowest-watermark rule and the
   six-month/one-year retention figures. The corpus assessment could not
   reach whitehouse.gov or cisa.gov from an automated client, so every
   figure in D3 currently rests on a secondary source.
2. Direct retrieval of **CISA's Logging Reference Architecture**,
   confirming its publication date — which is the anchor every deadline
   in D4 is measured from, and therefore the single fact that makes the
   relative-deadline form usable at all.
3. A decision on whether CEM/THIRF scoping is modelled in the substrate
   or explicitly declared out of scope.
