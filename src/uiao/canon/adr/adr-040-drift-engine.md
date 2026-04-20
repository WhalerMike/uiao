---
id: ADR-040
title: "OrgTree Drift Detection Engine — Six-Phase Orchestrator"
status: accepted
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
  - security-steward
supersedes: []
related_adrs:
  - ADR-012
  - ADR-033
  - ADR-035
  - ADR-036
  - ADR-037
  - ADR-038
  - ADR-039
canon_refs:
  - MOD_A_OrgPath_Codebook
  - MOD_B_Dynamic_Group_Library
  - MOD_C_Attribute_Mapping_Table
  - MOD_D_Delegation_Matrix_AUs_Roles
  - MOD_M_Drift_Detection_Engine_Specification
  - MOD_N_Execution_Substrate_Integration_Layer
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
---

# ADR-040: OrgTree Drift Detection Engine — Six-Phase Orchestrator

## Status

Accepted

## Context

Phases 2–5 delivered four change-making adapters, each with its own
``plan / apply / reconcile`` shape:

* **Phase 2** — `entra-dynamic-groups` (MOD_B)
* **Phase 3** — `entra-admin-units` (MOD_D)
* **Phase 4** — `entra-device-orgpath` (MOD_C)
* **Phase 5** — `entra-policy-targeting` (MOD_N)

Each adapter diffs one slice of the OrgTree against its canonical
source. MOD_M has described the **continuous observer** that ties them
together since the original scaffold, in six phases: Snapshot, Compare,
Classify, Alert, Remediate, Verify. Before this ADR, nothing tied those
four adapters into a unified drift signal — operators had to run them
one at a time, correlate four separate reports, and decide per-pass
whether to promote to write mode.

Three concrete consequences of that gap:

1. **No single pane of findings.** The ADR-012 canonical drift taxonomy
   (SCHEMA / SEMANTIC / PROVENANCE / AUTHZ / IDENTITY / BOUNDARY) existed
   but no code classified the four adapter op types against it.
2. **No halt-on-critical behaviour.** A tenant-wide (`directoryScopeId=/`)
   role assignment detected by Phase 3 could be in the same CI report
   as routine Phase 2 group creates — with no mechanism to refuse
   remediation while the escalation sits unreviewed.
3. **No canonical op → severity map.** Each adapter labels its own
   phantom ops "governance review", but the severity grading and the
   mapping of op types to drift classes lived only in the adapter
   docstrings.

## Decision

1. Publish the engine's configuration as executable canon at
   `src/uiao/canon/data/orgpath/drift-engine-config.yaml`. The config
   declares:
   - participating phase adapters (module + class);
   - per-op drift_class + severity + auto_remediate flag;
   - global defaults (``dry_run: true``, ``severity_floor``,
     ``halt_on_critical: true``);
   - severity policy (P1–P4 labels + halt threshold).
2. Ship a JSON Schema at
   `src/uiao/schemas/orgpath/drift-engine-config.schema.json` that pins
   the taxonomy enum, severity enum, and governance invariants.
3. Provide the orchestrator at
   `src/uiao/governance/drift_engine.py`. Public surface:
   :class:`OrgTreeDriftEngine` with ``build_snapshot()`` and
   ``scan(snapshot, dry_run)`` methods returning a
   :class:`DriftScanReport` that aggregates findings across all
   participating phases. The engine **never talks to Graph or ARM
   directly** — it delegates planning to each phase adapter (each
   already offline-testable with pre-fetched tenant state).
4. **Remediation policy**, enforced in the orchestrator:
   - ``dry_run=True`` is the default. Writes require an explicit
     per-scan ``dry_run=False``.
   - ``auto_remediate: false`` ops (each adapter's governance-review
     set) are **filtered out of the remediation pass** regardless of
     the dry-run flag. Phantom groups, unscoped role assignments,
     phantom role assignments, phantom device OrgPaths, phantom policy
     assignments, and missing-policy findings never reach the write
     path.
   - ``halt_on_critical`` — when any finding at or above the halt
     severity (``P1`` by default) fires during Classify, the entire
     Remediate pass is skipped. One escalation poisons the whole scan
     until a human resolves it.
5. **Partial scans are supported.** A snapshot missing a phase entry
   skips that phase entirely. Teams can scope a scan to one phase
   (e.g., post-MOD_B PR) without stubbing tenant state for the others.
6. **Unmapped op types raise ``DriftEngineError``.** An adapter that
   emits a new op type (because a new canon rule was added to the
   adapter but not to the engine config) fails loud instead of
   silently dropping the finding. Catches governance wiring gaps at
   CI, not in production.

## Consequences

**Positive**

- Single operator artefact: one ``DriftScanReport`` across all four
  planes, one set of findings, one remediation artefact, one halt
  decision. The MOD_M "Alert" phase is literally ``report.findings``.
- The ADR-012 taxonomy finally has a producer. Every finding carries
  a drift_class field that downstream tooling (dashboards, SIEM, POAMs)
  can aggregate on.
- Halt-on-critical makes stop-the-line governance concrete. An
  unscoped role assignment (MOD_D §Governance Rule 4) halts every
  other remediation — operators can't accidentally auto-fix green
  drift while a red escalation waits for review.
- The engine is fully offline-testable. Snapshots are plain dicts of
  pre-fetched tenant state; the canonical 11-test suite exercises the
  full six-phase loop with no network dependency.
- Adding a new phase is declarative. Register the adapter, add the
  op-type map to the config, done. The engine never hardcodes phase
  names.

**Negative / deferred**

- **Verify is out of scope for v1.** MOD_M's sixth phase
  (re-snapshot + re-scan to confirm remediation took effect) is not
  implemented — doing so would require the engine to talk to Graph/ARM
  to re-read state, which is the read-side work Phase 4.5 / 5.5 still
  owes. For now, a successful remediation + zero-finding rescan (run
  manually) is the canonical success signal.
- **Snapshot fetching is the caller's problem.** The engine consumes
  pre-fetched state; a future follow-up adds Graph + ARM readers so
  ``scan()`` can snapshot on its own given credentials.
- **No alert routing.** MOD_M mentions Teams/email. The engine emits
  findings as structured data; wiring them into M365 notification
  channels is a consumer layer, not part of the engine.
- **No scheduling.** The engine runs one scan per call. Scheduling
  (cron, substrate-drift CI hook) is orthogonal wiring.

## Alternatives considered

- **Build a dedicated drift-observer adapter with its own Graph +
  ARM clients.** Rejected. Duplicating planning logic in a second
  adapter would require two places to fix any drift definition change.
  Orchestrating the existing adapters keeps drift logic DRY and makes
  the four phase adapters the single source of truth for their
  respective invariants.
- **Embed halt_on_critical logic in each adapter.** Rejected. The
  halt condition is a cross-phase concern (phantom AU in MOD_D should
  halt MOD_B remediation too). Only the orchestrator has the view
  needed to enforce it.
- **Classify drift as generic schema diffs.** Rejected. ADR-012 is
  explicit that drift types are semantic (AUTHZ vs IDENTITY vs
  SCHEMA); a generic hash-diff is not enough to route the right
  response.

## Related work

- ADR-012 — canonical drift taxonomy (six classes). This engine is the
  primary producer of taxonomy-classified findings.
- ADR-033 — DRIFT-BOUNDARY class. Reserved for boundary/GCC violations
  emitted by other adapters; not currently produced by any OrgTree
  phase but declared in the taxonomy for forward-compat.
- ADRs 035–039 — the five pre-requisites. This engine composes their
  adapters.
- MOD_M — the canonical specification this ADR implements.
