---
title: "Phase 3 — Remediation Contract on Findings + Router + OSCAL Integration"
status: DRAFT
date: 2026-05-15
owner: Michael Stratton
depends_on: Phase 0 (ADR-070 ACCEPTED), Phase 1 (ADR-071 ACCEPTED), Phase 2 (ADR-072 ACCEPTED)
related_strategy: "Whitepaper TARGET → SHIPPED plan (governance-os whitepaper §3)"
---

# Phase 3 — Remediation Contract + Router + OSCAL Integration

Phase 2 ships runtime drift detection. Phase 3 takes findings the rest
of the way — every finding (substrate-walker hygiene AND runtime sink)
carries the §4 remediation contract from
[`16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd),
and a shared `RemediationRouter` dispatches each finding to one of four
handlers (halt | fix | flag | log).

This is the last engineering phase before the whitepaper marketing flip
in Phase 4.

## Three-axis change

Phase 3 changes three things in parallel:

| Axis | Today | After Phase 3 |
|---|---|---|
| `DriftFinding` shape | 5-field dataclass (drift_class, severity, path, detail, subkind) | 14-field dataclass with §4 remediation contract carried inline |
| Routing | None — findings just sit in reports / event logs | `RemediationRouter` dispatches each finding to halt / fix / flag / log handler |
| OSCAL bundle | Snapshot or event-log assembly; runtime findings invisible to assessor | `--include-runtime-findings` flag pulls runtime findings in as Component Definition observations |

The current state is **three separate `DriftFinding` classes** in the
substrate:

1. [`src/uiao/substrate/walker.py`](../../../src/uiao/substrate/walker.py) — canon-hygiene findings (`subkind="hygiene"`)
2. [`src/uiao/governance/drift_engine.py`](../../../src/uiao/governance/drift_engine.py) — OrgTree six-phase orchestrator
3. [`inbox/drafts/phase1-emit-hook-and-evidence-capture/provenance_sink.py`](../phase1-emit-hook-and-evidence-capture/provenance_sink.py) — runtime sink (`subkind="runtime"`)

Per the strategy memo, **Phase 3 does NOT refactor the OrgTree engine.**
It promotes the substrate-walker and runtime-sink classes to a shared
canonical `DriftFinding` at `src/uiao/models/drift_finding.py` and
leaves OrgTree's `DriftFinding` as a peer class. Phase 5 (future
cleanup) unifies all three.

## What Phase 3 does NOT do

- **No OrgTree engine refactor.** Stays peer; documented as a known
  duplication.
- **No auto-remediation framework.** The `fix` handler dispatches to
  adapter-specific apply() functions that already exist; Phase 3 only
  routes, it does not implement fixes for adapters that don't have one.
- **No POA&M redesign.** The `flag` handler writes a `POAMEntry` using
  the existing [`src/uiao/models/poam.py`](../../../src/uiao/models/poam.py)
  model; no schema changes.
- **No `RemediationStatus` lifecycle workflow.** The router writes
  findings into POA&M `Open` state and stops; the existing POA&M
  generator owns the lifecycle.

## What's in this folder

| File | Purpose | Lands at |
|---|---|---|
| [adr-073-remediation-contract-and-router.md](adr-073-remediation-contract-and-router.md) | Records the three-axis change; commits to NOT refactoring OrgTree in this phase; pins the four router-handler types | `src/uiao/canon/adr/` |
| [drift_finding.py](drift_finding.py) | Canonical `DriftFinding` dataclass with §4 remediation contract fields; subsumes the walker and sink classes | `src/uiao/models/drift_finding.py` |
| [remediation_router.py](remediation_router.py) | `RemediationRouter` + four handler implementations (`halt` / `fix` / `flag` / `log`) | `src/uiao/governance/router.py` |
| [oscal_runtime_findings.diff.md](oscal_runtime_findings.diff.md) | Diff sketch for the OSCAL generator's `--include-runtime-findings` mode | Inline in `src/uiao/generators/oscal.py` |
| [walker_and_sink_consolidation.diff.md](walker_and_sink_consolidation.diff.md) | How the walker and runtime sink both adopt the canonical class; back-compat via re-exports | Inline in `src/uiao/substrate/walker.py` + `src/uiao/telemetry/provenance.py` |

## Promotion plan

Phase 3 ships as **two sub-PRs** for blast-radius control:

1. **PR-3a — Canonical DriftFinding + router (no OSCAL change).**
   Promote the shared class, route walker + sink findings, ship the
   four handlers. Walker and sink emit findings carrying the §4
   contract; nothing else changes for assessors yet.
2. **PR-3b — OSCAL `--include-runtime-findings` flag.** Adds the bundle-
   integration mode. Default off; flips on for the next ATO package
   regeneration after assessor sign-off.

Each PR is independently mergeable. PR-3a unblocks Phase 4's
whitepaper flip; PR-3b is the assessor-facing surface.

## Exit criteria

Phase 3 is complete when:

1. ADR-073 ACCEPTED.
2. `src/uiao/models/drift_finding.py` is the canonical class; walker
   and sink both use it.
3. `RemediationRouter` is registered into the substrate boot sequence;
   it consumes every finding emitted by walker + sink.
4. CI tests pass:
   - A P1 finding produces `remediation_action="halt"` and an
     escalation_path entry on the finding.
   - A deterministic P2 finding (auto-remediatable drift class) produces
     `remediation_action="fix"` and `auto_remediated=True`.
   - A non-deterministic P2 finding produces `remediation_action="flag"`
     and writes a POAMEntry to the configured POA&M store.
   - A P4 finding produces `remediation_action="log"` and no further
     action.
5. OSCAL bundle regeneration with `--include-runtime-findings`
   produces a Component Definition that carries runtime findings as
   observations under `_UIAO_RUNTIME_NS`.

## Cross-references

- [`inbox/drafts/phase0-runtime-provenance-envelope/`](../phase0-runtime-provenance-envelope/) — typed envelope
- [`inbox/drafts/phase1-emit-hook-and-evidence-capture/`](../phase1-emit-hook-and-evidence-capture/) — emit hook + event log
- [`inbox/drafts/phase2-runtime-drift-validators/`](../phase2-runtime-drift-validators/) — runtime validators
- [`docs/docs/16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd) — §3 severity model + §4 remediation contract (promoted by this phase)
- [`src/uiao/models/poam.py`](../../../src/uiao/models/poam.py) — POAMEntry / RemediationMilestone / RemediationStatus the `flag` handler writes to
- [`src/uiao/governance/drift_engine.py`](../../../src/uiao/governance/drift_engine.py) — OrgTree engine; NOT refactored in this phase (documented Phase 5 follow-on)
- [`src/uiao/generators/oscal.py`](../../../src/uiao/generators/oscal.py) — OSCAL generator extended with runtime-findings mode
