---
adr_id: adr-114
title: "AI System JML Lifecycle — Joiner, Mover, and Leaver Events for Federal AI System Identities"
status: PROPOSED
decided: 2026-06-19
deciders: Michael Stratton
updated: 2026-06-19
next_review: 2026-12-19
review_trigger: M-25-21 is superseded or amended; OMB publishes a 2026 inventory with changed schema; SailPoint machine-identity adapter promotes from reserved to active; ADR-016 (human JML) is substantially revised; a new federal mandate imposes AI credential lifecycle obligations; UIAO_197 version increments
impact: "Extends UIAO's human JML model (ADR-016) to federal AI system identities, using the OMB Annual AI Use Case Inventory as the source of lifecycle events. Defines three event types — ai-system.joiner (pilot/deployed first appearance), ai-system.mover (governance-relevant field change), ai-system.leaver (retirement or inventory removal). Defines an 8-step deprovisioning sequence that closes the ghost-credential gap. Adds DRIFT-COMPLIANCE::ai-staleness (P3) for records with no mover event in 365+ days. Doctrine plus implementation — lands jml.py and test_jml.py."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-114-ai-system-jml-lifecycle.html
---

# ADR-114: AI System JML Lifecycle — Joiner, Mover, and Leaver Events for Federal AI System Identities

## Status

**PROPOSED** — 2026-06-19.

This ADR is doctrine plus implementation. It closes the lifecycle gap left open
by ADR-112: ADR-112 named federal AI systems as identity subjects; this ADR
defines the lifecycle events that govern them from first deployment to
credential revocation on retirement.

## Context

### The gap ADR-112 left open

ADR-112 established that every deployed or piloted federal AI system is an
identity subject in UIAO's machine-identity surface. It named the OMB Annual AI
Use Case Inventory as the authoritative discovery feed. It defined six drift
finding types for identity governance gaps.

What ADR-112 did not define is what happens over time. An identity subject is
not a static record. It joins the environment, changes roles and bureaus, and
eventually exits. Without lifecycle events, governance of AI system identities
is a point-in-time scan — useful for finding gaps, but blind to the transitions
that create gaps in the first place.

ADR-016 solved this for human identities: joiner, mover, leaver. The HR system
is the source of truth; it fires events; UIAO acts on them. The model is well
understood and has been operational for years.

Federal AI systems have no HR system. Until OMB began publishing the Federal AI
Use Case Inventory, they had no equivalent source of lifecycle events at all.
The `development_stage` field and annual vintage diffs are the HR system
equivalent for the AI identity population.

### The ghost credential problem

The most common governance failure for AI system identities is not the missing
ATO — it is the orphaned credential after the system retires. A service account
or API key created for an AI system at deployment time persists indefinitely
unless someone actively revokes it. That requires knowing the system retired,
knowing the credential exists, and taking a manual action. None of those three
things happen reliably without a lifecycle trigger.

The 2025 OMB inventory already contains `development_stage = retired` entries.
Those entries are reporting actions, not deprovisioning actions. The ghost
credential problem is the gap between the two: retirement in the inventory does
not automatically revoke the credential the system was running under.

This ADR closes that gap by making `development_stage = retired` a structured
lifecycle event — the leaver trigger — that initiates an 8-step deprovisioning
sequence.

### Why the human JML model applies

The human JML model works because it separates the *source of truth* (HR system)
from the *identity substrate* (Active Directory, Entra, UIAO) and defines the
translation from HR events to identity operations. The source changes; the model
is consistent.

For AI systems, the source of truth is the OMB inventory, not an HR system. The
translation layer is different — `development_stage` instead of hire/transfer/
termination records. The model is the same: a source fires an event; UIAO
translates it into identity operations; the credential lifecycle reflects the
system's actual state.

| Human JML | AI System JML |
|---|---|
| HR hire record → joiner | `development_stage` first = `pilot`/`deployed` → joiner |
| HR transfer record → mover | Governance field change between vintages → mover |
| HR separation record → leaver | `development_stage = retired` or absent from vintage → leaver |
| Employee account | Service account / managed identity / API key |
| Manager assigns owner | Bureau governance contact assigned from `contact_email` |
| AD deprovisioning on leaver | Credential revocation 8-step sequence |

## Decision

Five positions.

### 1. The OMB Annual AI Use Case Inventory is the JML event source for federal AI system identities

For the federal vertical, UIAO **MUST** treat inventory vintage diffs as the
primary source of JML events for AI system identities. Specifically:

- A system that appears in the current vintage at `development_stage ∈ {pilot,
  deployed}` with no prior-vintage record at the same stage is a **joiner**.
- A system that appears in both vintages with any change in the seven
  mover-trigger fields is a **mover**.
- A system that transitions to `development_stage = retired` or disappears from
  the inventory is a **leaver** (confirmed) or **candidate leaver** (absent
  without a retirement record).

The diff key is `omg_id` — the stable cross-year identifier in the OMB inventory.

### 2. Each event type has a defined set of required governance actions

The full governance action set for each event type is specified in UIAO_197 §1.
The binding obligations are:

**Joiner (8 steps J-1 through J-8):**
- OrgPath must be derived and stamped before any other action.
- Owner must be confirmed by a human; it cannot be auto-assigned.
- Pilot and deployed joiners have different credential scope constraints.
- If OrgPath cannot be derived, `DRIFT-IDENTITY::ai-no-orgpath` fires immediately.

**Mover (field-specific actions):**
- `agency_bureau` change → OrgPath re-derivation is mandatory.
- `contact_email` change → new owner must confirm; prior owner must be notified.
- `agent_class → AGENTIC` → escalation to P1 governance path; declared
  governance mode required (L1 minimum per ADR-092 §4).
- `development_stage: pilot → deployed` → scope expansion requires human
  sign-off; not PER_POLICY auto.

**Leaver (8 steps L-1 through L-8, with timelines):**
- Steps L-1 (alert) and L-2 (freeze new grants) fire at T+0 automatically.
- Steps L-4 and L-5 (credential revocation) are **NEVER_AUTOFIX** — a human
  must confirm before any credential is revoked, regardless of actuation level.
- Steps L-3, L-6, L-7, L-8 are PER_POLICY; they execute automatically within
  their timeline windows once L-1 through L-5 are satisfied.

### 3. DRIFT-COMPLIANCE::ai-staleness is added to the drift taxonomy

A live AI system with no mover event detected in 365+ days of vintage diffs is
classified as `DRIFT-COMPLIANCE::ai-staleness` (P3, PER_POLICY). This is the
AI identity equivalent of an HR record that has not been updated despite
organizational changes — a signal that the inventory record may no longer
reflect the system's actual governance state.

P3 is informational: it does not block certification and does not trigger the
drift gate halt. It auto-closes when any mover event is detected.

### 4. No UIAO_197 action operates at L4 for credential revocation

Credential revocation (leaver steps L-4 and L-5) is always gated on human
confirmation, regardless of ADR-092 actuation level. The actuation ceiling for
revocation is L3 (gated actuation with human approval). This constraint is
permanent and **cannot** be overridden by a governance-board decision to elevate
the overall actuation level.

The rationale: a false positive on a leaver event (e.g., an absent-from-vintage
record that was not actually retired) combined with L4 autonomous revocation
would deprovision a live system's credentials without any human review. The
blast radius of that error exceeds the efficiency gain of full automation.

### 5. Candidate leavers require human confirmation before deprovisioning proceeds beyond L-2

A system absent from the current vintage without an explicit `retired` stage
entry is a candidate leaver — the absence may indicate retirement, reporting
failure, or a use-case ID change. Steps L-1 and L-2 fire immediately (the
system's credentials are frozen for new grants). Steps L-3 through L-8 are
held pending a human disposition: confirmed retirement (proceed), or confirmed
continuation (close the candidate-leaver finding and re-onboard if needed).

## Consequences

**Positive.**

- The ghost-credential gap is closed by construction: `development_stage =
  retired` in any OMB vintage triggers L-1 (alert) at T+0, making the
  deprovisioning sequence deterministic rather than dependent on institutional
  memory.
- The lifecycle model is structurally identical to ADR-016 (human JML), which
  means governance teams already familiar with human identity lifecycle
  management can apply the same mental model to AI system identities.
- `DRIFT-COMPLIANCE::ai-staleness` provides a proactive signal for records that
  may have decayed — catching drift in the governance record itself, not just
  in the credential state.
- The candidate-leaver pattern handles the real-world case where agencies
  retire systems without updating the inventory, providing a governance trigger
  from an absence rather than requiring an explicit retirement action.
- ADR-112's finding set is extended with one new finding type
  (`ai-staleness`) without modifying UIAO_196's schema — UIAO_197 and UIAO_196
  are composable.

**Negative / costs.**

- Vintage diffs require storing prior-vintage records. The machine-identity
  surface must maintain a vintage archive (at minimum: the most recent prior
  vintage) to enable diff-based event detection.
- Candidate-leaver disposition requires human action. In a large agency with
  many systems absent from a new vintage (e.g., due to reporting changes), the
  disposition queue could be substantial.
- The 365-day staleness threshold is conservative. A system that genuinely has
  not changed in a year is not necessarily ungoverned — P3 severity and
  PER_POLICY posture reflect this.
- Ghost-credential detection between vintages (a system still live operationally
  but missing from the inventory) is not possible from the vintage diff alone;
  it requires the `sailpoint-machine-identity` adapter's continuous telemetry.

**Neutral.**

- Does not change UIAO_196's `AISystemRecord` schema.
- Does not change ADR-112's six drift finding types; adds one new type.
- Does not change ADR-016 (human JML); the two models are parallel, not merged.
- Adds `jml.py` to `uiao.governance.ai_inventory`; no existing modules change.

## Implementation

The implementation spec is **UIAO_197** (`Spec4-AI-D1.2-AISystemJMLLifecycle.md`).
It defines the complete Python interface, the vintage diff algorithm, all event
type fields, and the evidence artifacts produced.

New files:

```
src/uiao/governance/ai_inventory/jml.py
tests/governance/ai_inventory/test_jml.py
```

Modified files:

```
src/uiao/governance/ai_inventory/drift.py    # add DRIFT_AI_STALENESS + finding_staleness()
```

No changes to `schema.py` or `scanner.py`.

## References

- [ADR-012](adr-012-canonical-drift-taxonomy.md) — canonical drift taxonomy; `DRIFT-COMPLIANCE::ai-staleness` extends it
- [ADR-016](adr-016-jml-lifecycle.md) — human JML; structural model this ADR extends to AI system identities
- [ADR-040](adr-040-drift-engine.md) — drift engine; P3 findings routing
- [ADR-059](adr-059-sailpoint-adapter-family.md) — sailpoint adapter family; continuous telemetry between vintages
- [ADR-088](adr-088-hr-as-orgtree-truth-source.md) — HR as OrgTree source; contrasted with OMB inventory as AI identity source
- [ADR-092](adr-092-active-governance.md) — active governance; L0–L4 actuation ladder; L4 ceiling on credential revocation
- [ADR-112](adr-112-federal-ai-usecase-governance.md) — Federal AI Use Case Governance; governing ADR for UIAO_196; this ADR extends it with lifecycle
- [UIAO_196](../specs/Spec4-AI-D1.1-AISystemIdentityRecord.md) — AI System Identity Record; schema this lifecycle governs
- [UIAO_197](../specs/Spec4-AI-D1.2-AISystemJMLLifecycle.md) — AI System JML Lifecycle specification; implementation detail for this ADR
- OMB M-25-21 — *Accelerating Federal Use of AI: Innovation, Governance, and Public Trust*, 2025
- OMB 2025 Federal AI Use Case Inventory — `github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory`
