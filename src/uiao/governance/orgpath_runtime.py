"""OrgPath Governance Runtime — the runnable governance loop (UIAO_174 / UIAO_163).

This module turns the one-shot :py:class:`~uiao.governance.drift_engine.DriftEngine`
into a *named, runnable* governance runtime: a single composition that an
operator (or the CLI / API) can start against a tenant snapshot and get back
a self-describing governance report plus a stream of governance-telemetry
events (UIAO_174).

What it composes
----------------
1. **Codebook** (UIAO_151) — the per-facet SSOT, loaded from canon by default.
2. **Phase 5 adapters** — the Entra dynamic-group / admin-unit / policy-target
   adapters (ADR-084 §C4). Each is transport-injected; with ``transport=None``
   (the runtime default) every ``apply()`` is write-free, so the runtime is
   fully offline-testable and dry-run-safe out of the box.
3. **DriftEngine** — the six-phase Snapshot → Compare → Classify → Alert →
   Remediate → Verify loop (UIAO_163 v2.0).

What it adds on top of ``DriftEngine``
--------------------------------------
* A **named entrypoint** (:py:meth:`OrgPathGovernanceRuntime.govern`) that an
  operator can actually run — no Python glue required.
* **Governance telemetry** — emits UIAO_174 events (``SnapshotCreated``,
  ``DriftDetected``, ``DriftRemediated``, ``EscalationTriggered``) so the run
  is observable, not just a return value.
* A **single report object** (:py:class:`GovernanceReport`) bundling the drift
  scan, the telemetry, and a rollup summary, with ``to_dict()`` for pipelines.

Design invariants (inherited from ADR-084 §C5 via the engine)
-------------------------------------------------------------
* ``dry_run=True`` is the default. Promotion to write-mode is a per-run
  operator decision.
* Governance-review op verbs (phantom / rebind) are never auto-remediated.
* ``halt_on_critical`` stops the line on codebook-integrity (P1) findings;
  the runtime surfaces that as an ``EscalationTriggered`` event.

The runtime never talks to Graph or ARM itself — all transport lives in the
adapters, behind the ``transport`` seam, exactly as the engine requires.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from uiao.governance.drift_engine import Adapter, DriftEngine, DriftScanReport
from uiao.modernization.orgtree.codebook import Codebook, default_codebook
from uiao.modernization.orgtree.drift_engine_config import (
    DriftEngineConfig,
    default_drift_engine_config,
)
from uiao.modernization.orgtree.types import (
    AdminUnitSnapshot,
    GroupSnapshot,
    PolicyTargetSnapshot,
    PrincipalSnapshot,
    Snapshot,
)

# Type aliases for the injectable, test-deterministic seams.
IdFactory = Callable[[], str]
Clock = Callable[[], str]


def _default_id() -> str:
    return uuid.uuid4().hex


def _default_clock() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# GovernanceEvent — one UIAO_174 governance-telemetry event
# ---------------------------------------------------------------------------

# The UIAO_174 event types this runtime emits. The full UIAO_174 vocabulary is
# larger (15 types); the runtime emits the subset its loop can authoritatively
# attest to. Others (SLABreached, MigrationPhaseCompleted, …) are emitted by
# their owning subsystems, not the drift loop.
EVENT_SNAPSHOT_CREATED = "SnapshotCreated"
EVENT_DRIFT_DETECTED = "DriftDetected"
EVENT_DRIFT_REMEDIATED = "DriftRemediated"
EVENT_ESCALATION_TRIGGERED = "EscalationTriggered"


@dataclass(frozen=True)
class GovernanceEvent:
    """One governance-telemetry event (UIAO_174 §Event Schema).

    ``event_id`` is a per-event UUID; ``event_type`` is one of the
    ``EVENT_*`` constants; ``payload`` carries the type-specific body.
    """

    event_id: str
    event_type: str
    timestamp: str
    snapshot_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "timestamp": self.timestamp,
            "snapshotId": self.snapshot_id,
            "payload": dict(self.payload),
        }


# ---------------------------------------------------------------------------
# GovernanceReport — the single object one govern() run returns
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GovernanceReport:
    """Bundles the drift scan, the telemetry stream, and a rollup summary.

    This is the runtime's deliverable: everything an operator or a
    downstream pipeline needs from one governance pass, in one object.
    """

    scan: DriftScanReport
    events: tuple[GovernanceEvent, ...]

    @property
    def snapshot_id(self) -> str:
        return self.scan.snapshot_id

    @property
    def generated_at(self) -> str:
        return self.scan.generated_at

    @property
    def dry_run(self) -> bool:
        return self.scan.dry_run

    @property
    def halted(self) -> bool:
        return self.scan.halted

    @property
    def drift_count(self) -> int:
        return self.scan.finding_count

    @property
    def severity_counts(self) -> Mapping[str, int]:
        return self.scan.severity_counts

    @property
    def remediated_count(self) -> int:
        """Operations actually dispatched across every adapter (0 in dry-run)."""
        return sum(r.sent_count for r in self.scan.apply_results.values())

    @property
    def planned_count(self) -> int:
        """Operations the adapters would dispatch (planned, pre-apply)."""
        return sum(r.planned_count for r in self.scan.apply_results.values())

    def events_of_type(self, event_type: str) -> tuple[GovernanceEvent, ...]:
        return tuple(e for e in self.events if e.event_type == event_type)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at,
            "dry_run": self.dry_run,
            "halted": self.halted,
            "drift_count": self.drift_count,
            "severity_counts": dict(self.severity_counts),
            "planned_count": self.planned_count,
            "remediated_count": self.remediated_count,
            "findings": [f.to_dict() for f in self.scan.findings],
            "apply_results": {
                name: {
                    "planned": r.planned_count,
                    "sent": r.sent_count,
                    "skipped": r.skipped_count,
                    "errors": r.error_count,
                    "dry_run": r.dry_run,
                }
                for name, r in self.scan.apply_results.items()
            },
            "events": [e.to_dict() for e in self.events],
        }


# ---------------------------------------------------------------------------
# Snapshot (de)serialization — bridges JSON inputs to the engine's Snapshot
# ---------------------------------------------------------------------------


class SnapshotError(ValueError):
    """Raised when a snapshot payload cannot be parsed into a ``Snapshot``."""


def snapshot_from_dict(payload: Mapping[str, Any]) -> Snapshot:
    """Build a :py:class:`Snapshot` from a plain dict (e.g. parsed JSON).

    Recognised keys (all optional except an implied non-empty body):
    ``generated_at`` (ISO-8601; defaults to now), ``principals``,
    ``groups``, ``admin_units``, ``policy_targets``. Each list element is a
    dict matching the corresponding ``*Snapshot`` dataclass fields.
    """
    if not isinstance(payload, Mapping):
        raise SnapshotError("snapshot payload must be a mapping")

    generated_at = payload.get("generated_at") or _default_clock()

    try:
        principals = tuple(
            PrincipalSnapshot(
                principal_id=p["principal_id"],
                principal_type=p.get("principal_type", "user"),
                attributes=dict(p.get("attributes", {})),
            )
            for p in payload.get("principals", [])
        )
        groups = tuple(
            GroupSnapshot(
                object_id=g.get("object_id", ""),
                name=g["name"],
                membership_rule=g.get("membership_rule", ""),
                group_type=g.get("group_type", "Security"),
            )
            for g in payload.get("groups", [])
        )
        admin_units = tuple(
            AdminUnitSnapshot(
                object_id=a.get("object_id", ""),
                name=a["name"],
                membership_rule=a.get("membership_rule", ""),
                restricted_management=bool(a.get("restricted_management", False)),
            )
            for a in payload.get("admin_units", [])
        )
        policy_targets = tuple(
            PolicyTargetSnapshot(
                assignment_id=t.get("assignment_id", ""),
                policy_definition_id=t.get("policy_definition_id", ""),
                scope_rule=t.get("scope_rule", ""),
            )
            for t in payload.get("policy_targets", [])
        )
    except (KeyError, TypeError) as exc:
        raise SnapshotError(f"malformed snapshot element: {exc}") from exc

    return Snapshot(
        generated_at=generated_at,
        principals=principals,
        groups=groups,
        admin_units=admin_units,
        policy_targets=policy_targets,
    )


# ---------------------------------------------------------------------------
# OrgPathGovernanceRuntime — the runnable governance loop
# ---------------------------------------------------------------------------


class OrgPathGovernanceRuntime:
    """The runnable OrgPath governance loop.

    Compose with a :py:class:`Codebook`, a mapping of adapter name → Phase 5
    adapter, and a :py:class:`DriftEngineConfig`; call :py:meth:`govern` with a
    :py:class:`Snapshot` to execute one full governance pass and get back a
    :py:class:`GovernanceReport` (drift scan + UIAO_174 telemetry + summary).

    Defaults are detection-only and dry-run-safe: with no adapters the runtime
    classifies drift and emits telemetry without planning any writes. Use
    :py:meth:`with_canon_adapters` to wire the canonical Phase 5 adapter set
    (still write-free until a transport is injected and ``dry_run=False``).
    """

    def __init__(
        self,
        codebook: Codebook | None = None,
        adapters: Mapping[str, Adapter] | None = None,
        config: DriftEngineConfig | None = None,
        *,
        id_factory: IdFactory = _default_id,
        clock: Clock = _default_clock,
    ) -> None:
        self.codebook = codebook or default_codebook()
        self.config = config or default_drift_engine_config()
        self.engine = DriftEngine(self.codebook, dict(adapters or {}), self.config)
        self._id = id_factory
        self._clock = clock

    @classmethod
    def with_canon_adapters(
        cls,
        codebook: Codebook | None = None,
        config: DriftEngineConfig | None = None,
        *,
        id_factory: IdFactory = _default_id,
        clock: Clock = _default_clock,
    ) -> OrgPathGovernanceRuntime:
        """Build a runtime wired with the canonical snapshot-driven adapters.

        Loads the dynamic-group / admin-unit / policy-target libraries from
        canon (UIAO_152/154/155 data) and constructs their Entra adapters with
        ``transport=None`` — planning is pure and no writes occur until an
        operator injects a transport and promotes ``dry_run=False``.

        The device-plane adapter is intentionally omitted: it consumes
        operator-supplied ``DeviceFacetAssignment`` inputs rather than a tenant
        snapshot, so it has nothing to plan in the snapshot-driven loop.
        """
        # Imported lazily so a missing optional canon data file (or a future
        # adapter-extra split) can't break the detection-only default path.
        from uiao.adapters.entra_admin_units import EntraAdminUnitAdapter
        from uiao.adapters.entra_dynamic_groups import EntraDynamicGroupAdapter
        from uiao.adapters.entra_policy_targeting import EntraPolicyTargetAdapter
        from uiao.modernization.orgtree.admin_units import load_admin_unit_registry
        from uiao.modernization.orgtree.dynamic_groups import load_dynamic_group_library
        from uiao.modernization.orgtree.policy_targeting import load_policy_target_library

        cb = codebook or default_codebook()
        adapters: dict[str, Adapter] = {
            "dynamic_groups": EntraDynamicGroupAdapter(load_dynamic_group_library(cb)),
            "admin_units": EntraAdminUnitAdapter(load_admin_unit_registry(cb)),
            "policy_targeting": EntraPolicyTargetAdapter(load_policy_target_library(cb)),
        }
        return cls(cb, adapters, config, id_factory=id_factory, clock=clock)

    def govern(self, snapshot: Snapshot, *, dry_run: bool | None = None) -> GovernanceReport:
        """Run one governance pass and return the report + telemetry.

        Emits a ``SnapshotCreated`` event, runs the drift engine, emits one
        ``DriftDetected`` per finding and one ``DriftRemediated`` per actually
        dispatched operation, and an ``EscalationTriggered`` event if the
        engine halted on a critical (P1) finding.
        """
        events: list[GovernanceEvent] = []
        scan = self.engine.run(snapshot, dry_run=dry_run)
        sid = scan.snapshot_id

        events.append(
            self._event(
                EVENT_SNAPSHOT_CREATED,
                sid,
                {
                    "generated_at": scan.generated_at,
                    "principals": len(snapshot.principals),
                    "groups": len(snapshot.groups),
                    "admin_units": len(snapshot.admin_units),
                    "policy_targets": len(snapshot.policy_targets),
                    "dry_run": scan.dry_run,
                },
            )
        )

        for finding in scan.findings:
            events.append(
                self._event(
                    EVENT_DRIFT_DETECTED,
                    sid,
                    {
                        "target": finding.target,
                        "facet": finding.facet,
                        "drift_class": finding.drift_class,
                        "drift_category": finding.drift_category,
                        "severity": finding.severity,
                        "auto_remediate": finding.auto_remediate,
                        "reason": finding.reason,
                    },
                )
            )

        for adapter_name, result in scan.apply_results.items():
            for op in result.sent:
                events.append(
                    self._event(
                        EVENT_DRIFT_REMEDIATED,
                        sid,
                        {
                            "adapter": adapter_name,
                            "op": op.op,
                            "facet": op.facet,
                            "target": op.target,
                        },
                    )
                )

        if scan.halted:
            events.append(
                self._event(
                    EVENT_ESCALATION_TRIGGERED,
                    sid,
                    {
                        "reason": "halt_on_critical fired — codebook-integrity / "
                        "critical finding present; remediation suppressed.",
                        "halt_on_critical": self.config.halt_on_critical,
                        "severity_counts": dict(scan.severity_counts),
                    },
                )
            )

        return GovernanceReport(scan=scan, events=tuple(events))

    def _event(self, event_type: str, snapshot_id: str, payload: Mapping[str, Any]) -> GovernanceEvent:
        return GovernanceEvent(
            event_id=self._id(),
            event_type=event_type,
            timestamp=self._clock(),
            snapshot_id=snapshot_id,
            payload=dict(payload),
        )
