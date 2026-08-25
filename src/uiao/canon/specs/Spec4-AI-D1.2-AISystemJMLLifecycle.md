---
document_id: UIAO_197
title: "AI System JML Lifecycle — Joiner, Mover, and Leaver Events for Federal AI System Identities"
version: "1.0"
status: Draft
owner: governance-steward
created_at: "2026-06-19"
updated_at: "2026-06-19"
canon_adrs:
  - ADR-114   # AI System JML Lifecycle — governing ADR
  - ADR-112   # Federal AI Use Case Governance — source of lifecycle triggers
  - ADR-003   # Human JML — structural model this spec extends
  - ADR-092   # Active Governance — actuation ladder
  - ADR-059   # SailPoint adapter family — sailpoint-machine-identity slot
  - ADR-040   # Drift engine — finding routing
  - ADR-012   # Canonical drift taxonomy
publish_to_site: true
---

# UIAO_197 — AI System JML Lifecycle

## Overview

Every human identity governed by UIAO passes through three lifecycle events:
joiner (hire), mover (role or bureau change), leaver (separation). Those events
are the spine of every provisioning workflow, access review cycle, and
deprovisioning automation in ADR-003.

Federal AI systems deployed under OMB M-25-21 are identity subjects in UIAO's
machine-identity surface (UIAO_196). They need the same lifecycle model. The
source of truth is not an HR system — it is the OMB Annual AI Use Case
Inventory. The `development_stage` field drives the event translation; diffs
between annual inventory vintages drive event detection.

This spec defines:

- the three JML event types for AI system identities
- the field changes that trigger each event
- the governance actions each event requires
- one new drift finding type: `DRIFT-COMPLIANCE::ai-staleness`
- the Python interface in `uiao.governance.ai_inventory.jml`

The governing ADR is **ADR-114**. This spec provides the operational schema
detail that ADR-114's doctrine section leaves implicit.

---

## 1. Event Type Definitions

### 1.1 ai-system.joiner

**Trigger:** A system's `development_stage` first appears as `pilot` or
`deployed` in the current inventory vintage, with no record of that system
in the prior vintage at the same or later stage.

**Meaning:** The system has crossed the authorization threshold. It is now an
active identity subject in the machine-identity surface and must have an
OrgPath record, a named owner, and a credential lifecycle entry.

**Required governance actions (in sequence):**

| Step | Action | Posture |
|---|---|---|
| J-1 | Derive OrgPath from `agency` + `agency_bureau` (UIAO_196 §2) | PER_POLICY — auto-stamp when both fields present |
| J-2 | Stamp `AISystemRecord` in the machine-identity surface | PER_POLICY |
| J-3 | Assign bureau governance contact as credential owner (from `contact_email`) | NEVER_AUTOFIX — owner must be confirmed by a human |
| J-4 | Set credential rotation schedule per bureau tier | PER_POLICY — inherited from OrgPath node |
| J-5 | Create credential lifecycle entry in IGA platform | PER_POLICY (L3 when SailPoint adapter active) |
| J-6 | Enqueue initial access review within 30 days | PER_POLICY |
| J-7 | If `ato_status ≠ YES` and `agent_class = AGENTIC` → emit `DRIFT-COMPLIANCE::ai-agentic-ungoverned` (P1) | — |
| J-8 | If `orgpath = None` → emit `DRIFT-IDENTITY::ai-no-orgpath` (P2) | — |

**Pilot vs. deployed distinction:**

- **Pilot joiner:** Credential scope is limited to pilot environment only.
  Expiry is set to pilot end date. Rotation clock starts at issuance.
- **Deployed joiner:** Full production credential with bureau-standard rotation
  cadence and scope matching the ATO authorization boundary.

---

### 1.2 ai-system.mover

**Trigger:** A system already in the live population (`development_stage ∈
{pilot, deployed}`) has one or more of the following fields change between
inventory vintages:

| Field | Governance implication |
|---|---|
| `contact_email` | Credential owner changes — re-assign in IGA |
| `agency_bureau` | OrgPath changes — re-derive and re-stamp |
| `agent_class` | Classification changes — may escalate to P1 path |
| `is_high_impact` | Newly True → elevate credential tier and rotation cadence |
| `ato_status` | Changes to `NO` → ATO gap finding; changes to `YES` → close prior finding |
| `development_stage` | `pilot` → `deployed` → mover event (scope expansion) |

**Required governance actions per changed field:**

| Changed field | Action | Posture |
|---|---|---|
| `agency_bureau` | Re-derive OrgPath; re-stamp record; notify prior and new bureau governance contacts | PER_POLICY |
| `contact_email` | Re-assign IGA credential owner to new contact; notify prior owner | NEVER_AUTOFIX — new owner must confirm |
| `agent_class` → `AGENTIC` | Escalate to P1 governance path; require declared governance mode (L1 minimum per ADR-092 §4) | NEVER_AUTOFIX |
| `is_high_impact` → True | Elevate credential tier; accelerate rotation cadence to privileged-service-account schedule; trigger immediate access review | PER_POLICY |
| `ato_status` → NO | Emit `DRIFT-COMPLIANCE::ai-ato-gap` (P2) | NEVER_AUTOFIX |
| `ato_status` → YES | Close any open `ai-ato-gap` finding; reset rotation clock if credential is unchanged | PER_POLICY |
| `development_stage` pilot → deployed | Expand credential scope to production boundary; remove pilot expiry; confirm ATO is `YES` | NEVER_AUTOFIX (scope expansion requires human sign-off) |

A single inventory diff can produce multiple changed fields for the same system.
All applicable mover actions fire independently; they are not mutually exclusive.

---

### 1.3 ai-system.leaver

**Trigger:** Any of:
- `development_stage` changes to `retired` in the current vintage
- `development_stage` changes to `cancelled`
- System is present in prior vintage but **absent** from current vintage
  (candidate leaver — requires human confirmation before deprovisioning)
- System has been in `paused` stage for > 90 consecutive days

**Required governance actions (8-step sequence with timelines):**

| Step | Action | Timeline | Posture |
|---|---|---|---|
| L-1 | Alert credential owner and bureau governance contact | T+0 | PER_POLICY |
| L-2 | Freeze new permission grants on all credentials | T+0 | PER_POLICY |
| L-3 | Export full audit trail to evidence bundle | T+7 days | PER_POLICY |
| L-4 | Revoke API keys and OAuth client credentials | T+14 days | NEVER_AUTOFIX (human must confirm revocation) |
| L-5 | Rotate or revoke service account credentials | T+14 days | NEVER_AUTOFIX |
| L-6 | Remove system from active access review queues | T+14 days | PER_POLICY |
| L-7 | Archive OrgPath record (queryable but no longer active) | T+30 days | PER_POLICY |
| L-8 | Emit closed-loop evidence to ATO record and UIAO evidence fabric | T+30 days | PER_POLICY |

**Absent-from-inventory handling:**

A system that disappears from the inventory without a `retired` stage entry is
a candidate leaver, not a confirmed leaver. Two possibilities:
1. The agency retired the system and stopped reporting it (governance failure)
2. The agency reorganized its reporting and the system continues under a
   different use-case ID

The scanner flags the system with `DRIFT-COMPLIANCE::ai-staleness` (§4) and
routes to the bureau governance contact for disposition. Steps L-1 and L-2 fire
immediately; steps L-3 through L-8 are held pending human confirmation.

**Ghost credential risk:**

The most common leaver failure mode is steps L-4 and L-5 never executing
because no one was notified of the retirement. UIAO_197 closes this by making
L-1 (notification) a PER_POLICY automated action that fires at T+0 when the
vintage diff detects the retirement — regardless of whether anyone in the
agency manually initiates the deprovisioning process.

---

## 2. Event Detection: Vintage Diff Algorithm

Event detection compares the current inventory vintage against the prior
vintage using `omg_id` as the stable cross-year key.

```
for each record in current_vintage:
    prior = lookup(record.omg_id, prior_vintage)

    if prior is None:
        if record.development_stage in {PILOT, DEPLOYED}:
            emit joiner(record)          # new system entering active population
    else:
        changed = diff_fields(prior, record)
        if changed:
            emit mover(record, changed)  # existing system with field changes

for each record in prior_vintage:
    current = lookup(record.omg_id, current_vintage)
    if current is None:
        emit candidate_leaver(record)    # absent from new vintage

    if current.development_stage == RETIRED and prior.development_stage != RETIRED:
        emit leaver(record)              # explicit retirement in new vintage
```

`diff_fields` checks only the seven mover-trigger fields listed in §1.2. Other
field changes (e.g., `use_case_name`, `vendor_name`) are recorded in the event
but do not trigger governance actions.

---

## 3. Python Interface

```python
from uiao.governance.ai_inventory.jml import (
    detect_events,
    JMLEvent,
    JMLEventType,
)

events = detect_events(
    current_vintage=current_records,   # list[AISystemRecord]
    prior_vintage=prior_records,       # list[AISystemRecord] | None
)

for event in events:
    print(event.event_type)            # JMLEventType.JOINER / MOVER / LEAVER
    print(event.record.identity_label) # system name
    print(event.changed_fields)        # list[str] — mover only
    print(event.actions)               # list[JMLAction] — required governance steps
    print(event.findings)              # list[Finding] — drift findings emitted
```

**`JMLEvent` fields:**

| Field | Type | Description |
|---|---|---|
| `event_type` | `JMLEventType` | `JOINER`, `MOVER`, or `LEAVER` |
| `record` | `AISystemRecord` | Current-vintage record |
| `prior_record` | `AISystemRecord \| None` | Prior-vintage record (None for joiners) |
| `changed_fields` | `list[str]` | Fields that changed (mover only) |
| `actions` | `list[JMLAction]` | Governance actions required |
| `findings` | `list[Finding]` | Drift findings emitted by this event |
| `candidate_leaver` | `bool` | True when system absent from vintage (pending confirmation) |

**`JMLAction` fields:**

| Field | Type | Description |
|---|---|---|
| `step` | `str` | Step code (J-1, M-3, L-4, …) |
| `description` | `str` | Human-readable action description |
| `posture` | `Posture` | PER_POLICY or NEVER_AUTOFIX |
| `timeline_days` | `int \| None` | Days from event detection (leaver steps only) |
| `requires_confirmation` | `bool` | True when NEVER_AUTOFIX |

---

## 4. New Drift Finding: ai-staleness

```
DRIFT-COMPLIANCE::ai-staleness
```

**Trigger:** A live system (`development_stage ∈ {pilot, deployed}`) has had
no mover event detected across the last 365+ days of vintage diffs — its
inventory record has not changed in any mover-trigger field.

**Meaning:** The system's governance record may be stale. An AI system that
has not changed in over a year in any governance-relevant field is either:
- genuinely stable (acceptable — staleness finding is informational), or
- not being updated when changes occur (governance failure — the inventory
  record no longer reflects reality)

The finding prompts the bureau governance contact to confirm the record is
current.

| Property | Value |
|---|---|
| Drift class | `DRIFT-COMPLIANCE::ai-staleness` |
| Severity | P3 |
| Posture | PER_POLICY |
| Threshold | 365 days since last mover event (or since joiner if no movers recorded) |
| Remediation | Bureau governance contact confirms or updates the inventory record |
| Auto-close | Yes — closes automatically when any mover event is detected |

P3 is informational: it does not block certification and does not trigger the
drift gate halt. It surfaces in the findings report and routes to the governance
contact for disposition.

---

## 5. Relationship to Human JML (ADR-003)

| Dimension | Human JML (ADR-003) | AI System JML (UIAO_197) |
|---|---|---|
| Event source | HR system of record (ADR-088) | OMB Annual AI Use Case Inventory |
| Joiner trigger | Hire record | `development_stage` first enters `pilot` or `deployed` |
| Mover trigger | HR transfer / role change | Field change in mover-trigger set |
| Leaver trigger | Separation record | `development_stage = retired` or absent from vintage |
| Owner identity | Employee (person) | Bureau governance contact (person) |
| Credential type | User account, PIV binding | Service account, managed identity, API key |
| Rotation policy | PIV / password policy | Bureau service-account standard (inherited from OrgPath node) |
| Deprovisioning authority | HR-triggered, automated | NEVER_AUTOFIX steps require human confirmation |
| Staleness signal | HR record mismatch | No mover event in 365 days |

The structural model is identical. The source, trigger, and credential type
differ because the identity population differs. The governance logic — assign
owner, set rotation, review access, deprovision on exit, detect staleness —
is the same.

---

## 6. Actuation Levels

Per ADR-092, all JML actions in UIAO_197 operate at L1 (observe and alert)
by default. Promotion to higher actuation levels requires a governance-board
decision:

| Action category | Default level | Maximum without board decision |
|---|---|---|
| Drift finding emission | L1 | L1 |
| Owner notification | L1 | L2 (advise) |
| Credential scope freeze (L-2) | L1 alert | L3 (gated — requires human confirm) |
| Credential revocation (L-4, L-5) | L1 alert | L3 (gated — requires human confirm) |
| OrgPath re-stamp (J-1, J-2) | L2 | L2 |
| IGA platform write (J-5, L-6) | L3 (gated) | L3 |

No UIAO_197 action operates at L4 (autonomous) for any leaver step. Credential
revocation is always gated on human confirmation regardless of actuation level.

---

## 7. Evidence Produced

Each JML event produces an evidence bundle entry:

| Evidence artifact | Contents | NIST controls |
|---|---|---|
| `jml-event-log.json` | Timestamped event record: event type, system, changed fields, actions taken, findings emitted | AC-2, IA-4, CA-7 |
| `jml-action-log.json` | Per-action execution record: step code, timestamp, actor (human / system), outcome | AC-2(3), AC-2(7) |
| `machine-identity-lifecycle-state.json` | Current lifecycle state for all governed AI systems: stage, last event, next review date, open findings | CM-8, IA-2 |

The `to_json()` method on `JMLEventSet` produces an ODR-compatible JSON
payload for ingestion by the evidence fabric (ADR-006, ADR-016).

---

## 8. Integration with UIAO_196

UIAO_197 extends UIAO_196 without modifying it. The `AISystemRecord` schema
is unchanged. UIAO_197 adds:

- a vintage-diff layer that reads two `list[AISystemRecord]` and produces
  `list[JMLEvent]`
- the `JMLEvent`, `JMLAction`, and `JMLEventSet` types
- the `DRIFT-COMPLIANCE::ai-staleness` finding type (added to `drift.py`)
- the `jml.py` module in `uiao.governance.ai_inventory`

UIAO_196 `scan_inventory()` continues to operate independently. For a full
lifecycle scan, callers run both:

```python
scan_result  = scan_inventory(current_csv, known_registry_ids=...)
event_result = detect_events(current_vintage=scan_result.records,
                             prior_vintage=prior_records)
```

---

## Appendix A — Implementation file layout

```
src/uiao/governance/ai_inventory/
    jml.py          # JMLEventType, JMLEvent, JMLAction, JMLEventSet, detect_events()
    drift.py        # add DRIFT_AI_STALENESS constant and finding_staleness()

tests/governance/ai_inventory/
    test_jml.py     # joiner / mover / leaver detection; staleness threshold; candidate leaver
```

No changes to `schema.py` or `scanner.py`.
