"""OrgTree drift detection engine (Phase 6, MOD_M / ADR-040).

Implements the six-phase loop MOD_M specifies — Snapshot → Compare →
Classify → Alert → Remediate → Verify — as an **orchestrator** over the
Phase 2–5 modernization adapters. The engine never talks to Graph or
ARM directly; it delegates planning to each phase adapter (which is
already offline-testable), classifies the resulting operations against
the ADR-012 canonical drift taxonomy, and optionally dispatches
remediation through each adapter's ``apply()``.

Design invariants:

* Governance-review op types are **never** auto-remediated. The engine
  honours each adapter's own governance-review set AND the
  ``auto_remediate: false`` flag in the drift-engine config.
* ``halt_on_critical`` — if any finding at or above the configured
  halt level fires during Classify, the Remediate pass is skipped even
  when ``dry_run=False``. Stop-the-line condition for privilege
  escalations.
* ``dry_run=True`` is the default everywhere. Promoting to write-mode
  is an operator decision per scan.

The engine is fully offline-testable: the ``Snapshot`` object is a
pydantic-free dict of pre-fetched tenant state per phase. No live
tenant is required to exercise the full pipeline.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from uiao.modernization.orgtree import (
    DriftEngineConfig,
    OpEntry,
    PhaseConfig,
)
from uiao.modernization.orgtree.drift_engine_config import (
    default_drift_engine_config,
)


logger = logging.getLogger(__name__)


_SEVERITY_RANK = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _at_or_above(sev: str, threshold: str) -> bool:
    return _SEVERITY_RANK.get(sev, 5) <= _SEVERITY_RANK.get(threshold, 5)


# ---------------------------------------------------------------------------
# Snapshot — the input to Compare. One entry per phase; shapes match
# what each phase adapter's plan() expects.
# ---------------------------------------------------------------------------


@dataclass
class PhaseSnapshot:
    """Pre-fetched tenant state for one phase.

    The engine passes the fields of this object straight through to the
    phase adapter's ``plan()`` as keyword arguments. Any extra fields
    are ignored — keeps the engine forward-compatible when an adapter
    adds a new planning input.
    """

    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Snapshot:
    """Per-phase tenant state for a single drift scan."""

    generated_at: str
    by_phase: Dict[str, PhaseSnapshot] = field(default_factory=dict)

    def for_phase(self, name: str) -> PhaseSnapshot:
        return self.by_phase.get(name) or PhaseSnapshot()


# ---------------------------------------------------------------------------
# Findings — the output of Classify. One per planned op that survives
# the severity floor.
# ---------------------------------------------------------------------------


@dataclass
class DriftFinding:
    phase: str
    op: str
    target: str
    reason: str
    drift_class: str
    severity: str
    auto_remediate: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DriftScanReport:
    generated_at: str
    dry_run: bool
    halted: bool
    halt_reason: Optional[str]
    findings: List[DriftFinding] = field(default_factory=list)
    remediation_results: List[Dict[str, Any]] = field(default_factory=list)

    def by_drift_class(self, drift_class: str) -> List[DriftFinding]:
        return [f for f in self.findings if f.drift_class == drift_class]

    def by_severity(self, severity: str) -> List[DriftFinding]:
        return [f for f in self.findings if f.severity == severity]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "dry_run": self.dry_run,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "findings": [f.to_dict() for f in self.findings],
            "remediation_results": self.remediation_results,
        }


# ---------------------------------------------------------------------------
# The orchestrator.
# ---------------------------------------------------------------------------


class OrgTreeDriftEngine:
    """Implements the MOD_M six-phase loop.

    Parameters
    ----------
    config:
        :class:`DriftEngineConfig`. Defaults to the canonical config
        shipped with ``uiao.canon``. The config declares which phases
        participate and how their op types map to drift_class/severity.
    adapter_factory:
        Optional callable ``(PhaseConfig) -> adapter`` used in tests to
        inject pre-built adapters instead of letting the engine import
        the real modules. Defaults to ``_default_adapter_factory``.
    """

    def __init__(
        self,
        config: Optional[DriftEngineConfig] = None,
        adapter_factory: Optional[
            Callable[[PhaseConfig], Any]
        ] = None,
    ) -> None:
        self._config = config or default_drift_engine_config()
        self._adapter_factory = adapter_factory or _default_adapter_factory

    # ------------------------------------------------------------------
    # Phase 1 — Snapshot. The caller assembles a :class:`Snapshot`
    # externally (tests inject pre-baked data; production wires Graph +
    # ARM readers). The engine does not fetch on its own.
    # ------------------------------------------------------------------
    @staticmethod
    def build_snapshot(by_phase: Mapping[str, Mapping[str, Any]]) -> Snapshot:
        return Snapshot(
            generated_at=datetime.now(timezone.utc).isoformat(),
            by_phase={
                name: PhaseSnapshot(kwargs=dict(kwargs or {}))
                for name, kwargs in by_phase.items()
            },
        )

    # ------------------------------------------------------------------
    # Phases 2 + 3 — Compare + Classify.
    # ------------------------------------------------------------------
    def scan(
        self,
        snapshot: Snapshot,
        dry_run: Optional[bool] = None,
    ) -> DriftScanReport:
        """Run Compare + Classify + Alert + (optional) Remediate passes."""
        effective_dry_run = (
            self._config.defaults.dry_run if dry_run is None else dry_run
        )
        report = DriftScanReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            dry_run=effective_dry_run,
            halted=False,
            halt_reason=None,
        )

        # Compare + Classify: run each phase's plan(), translate ops into
        # findings, drop findings below severity_floor. Phases that have
        # no snapshot entry are skipped so a partial scan (e.g. scope one
        # phase in CI) doesn't require stubbing tenant state for the
        # others.
        plans_by_phase: Dict[str, Tuple[PhaseConfig, Any, Any]] = {}
        for phase in self._config.phases:
            if phase.name not in snapshot.by_phase:
                logger.info(
                    "Phase %s has no snapshot entry; skipping", phase.name
                )
                continue
            adapter = self._adapter_factory(phase)
            phase_snap = snapshot.for_phase(phase.name)
            try:
                plan = adapter.plan(**phase_snap.kwargs)
            except TypeError as exc:
                raise DriftEngineError(
                    f"Phase '{phase.name}' adapter refused the snapshot "
                    f"kwargs: {exc}"
                ) from exc
            plans_by_phase[phase.name] = (phase, adapter, plan)
            for op in getattr(plan, "operations", []):
                entry = phase.entry_for(op.op)
                if entry is None:
                    raise DriftEngineError(
                        f"Phase '{phase.name}' produced unmapped op "
                        f"'{op.op}' — update drift-engine-config.yaml"
                    )
                if not _at_or_above(
                    entry.severity,
                    self._config.defaults.severity_floor,
                ):
                    continue
                # Each adapter names the identifying field differently
                # (``target`` in most, ``group_name`` in dynamic-groups).
                # Fall through in preference order so findings always
                # carry a non-empty identifier.
                target = (
                    getattr(op, "target", None)
                    or getattr(op, "group_name", None)
                    or getattr(op, "assignment_name", None)
                    or ""
                )
                report.findings.append(DriftFinding(
                    phase=phase.name,
                    op=op.op,
                    target=str(target),
                    reason=getattr(op, "reason", ""),
                    drift_class=entry.drift_class,
                    severity=entry.severity,
                    auto_remediate=entry.auto_remediate,
                ))

        # Phase 4 — Alert. The findings list IS the alert payload; real
        # wiring (Teams/email) lives outside this module. Consumers
        # subscribe via ``report.findings``.

        # Phase 5 — Remediate. Honours halt_on_critical, the
        # per-op auto_remediate flag, and the dry_run toggle.
        halt_at = self._config.severity_policy.halt_at
        if (
            self._config.defaults.halt_on_critical
            and any(_at_or_above(f.severity, halt_at) for f in report.findings)
        ):
            report.halted = True
            report.halt_reason = (
                f"Severity >= {halt_at} detected — MOD_M §Governance "
                "halt_on_critical=true; remediation pass skipped."
            )
            return report

        for phase_name, (phase, adapter, plan) in plans_by_phase.items():
            # Build a filtered plan that only contains auto-remediable ops;
            # the adapter's own governance-review logic handles the rest
            # but we pre-filter to keep findings deterministic.
            filtered = _filter_plan_for_remediation(plan, phase)
            if not getattr(filtered, "operations", []):
                continue
            apply_report = adapter.apply(filtered, dry_run=effective_dry_run)
            report.remediation_results.append({
                "phase": phase_name,
                "dry_run": effective_dry_run,
                "succeeded": getattr(apply_report, "succeeded", 0),
                "failed": getattr(apply_report, "failed", 0),
                "results": [
                    getattr(r, "__dict__", r)
                    for r in getattr(apply_report, "results", [])
                ],
            })

        # Phase 6 — Verify. Re-snapshot + re-compare is left to the
        # operator (out of scope for v1 orchestrator; test-expensive and
        # Graph/ARM-coupled). A successful remediation + zero-drift
        # rescan is the canonical success signal.
        return report


class DriftEngineError(RuntimeError):
    """Raised when the drift engine encounters an unrecoverable condition."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _default_adapter_factory(phase: PhaseConfig) -> Any:
    """Default factory: import the adapter module and instantiate the class.

    Kept simple — no credential wiring here. Tests pass their own factory.
    """
    module = importlib.import_module(phase.adapter_module)
    cls = getattr(module, phase.adapter_class)
    return cls()


def _filter_plan_for_remediation(plan: Any, phase: PhaseConfig) -> Any:
    """Return a shallow copy of *plan* with only auto_remediate ops kept.

    The plan type varies per phase (DynamicGroupPlan, DelegationPlan,
    DeviceOrgPathPlan, PolicyTargetingPlan). All four expose an
    ``operations`` list. The engine does not reach into phase-specific
    fields beyond ``op`` — any fields the adapter's apply() reads are
    carried through on the original operation objects.
    """
    ops = getattr(plan, "operations", [])
    kept = []
    for op in ops:
        entry = phase.entry_for(op.op)
        if entry is None:
            continue
        if entry.auto_remediate:
            kept.append(op)

    class _FilteredPlan:
        pass

    copy = _FilteredPlan()
    for attr in dir(plan):
        if attr.startswith("_"):
            continue
        try:
            setattr(copy, attr, getattr(plan, attr))
        except AttributeError:
            continue
    copy.operations = kept
    return copy
