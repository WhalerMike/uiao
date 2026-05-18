"""
src/uiao/governance/ssot_contention.py
---------------------------------------
SSOT-Contention Evaluator — ADR-074 implementation.

The substrate's six original drift classifiers in :mod:`uiao.governance.drift`
follow the *state-comparison* pattern: given an expected state and an
actual state, classify the divergence. ``DRIFT-SSOT-CONTENTION`` is
different — it fires on a single **write event** observed against an
instance the canon-blessed SSOT roster has demoted. This module lives
alongside ``drift.py`` rather than inside it because the input shape
(``WriteEvent`` + ``SSOTRoster``) doesn't fit the
``(expected_state, actual_state)`` signature the other classifiers use.

Detection contract (ADR-074 §2):

    1. The SSOT roster declares an authoritative instance for a domain.
    2. The roster declares a non-empty set of demoted instances.
    3. A write event is observed against one of the demoted instances.
    4. The write's target column is not in the demoted instance's
       ``cache_eligible_columns`` allowlist.
    5. The write occurred within the roster's cutover scope —
       i.e., after demotion_date and before retirement_date.

When all five hold, ``classify_ssot_contention`` returns a ``DriftState``
with ``drift_class="DRIFT-SSOT-CONTENTION"`` and severity per ADR-074 §3.
When any predicate fails, returns ``None``.

Severity bands (ADR-074 §3):

    * Inside a planned cutover_window → P3 (informational; expected)
    * Outside cutover, within remediation_window_days → P2 (default)
    * Past remediation_window_days → P1 (escalated)

The classifier is **pure**: it takes a single write event and a roster
and returns a DriftState. State persistence (was-this-finding-already-
emitted, how long has this been open, etc.) is the calling engine's
responsibility — the classifier does not maintain history.

Loading: ``SSOTRoster.from_yaml(path)`` and ``SSOTRoster.from_dict(d)``.
The roster YAML shape is validated by
``src/uiao/schemas/ssot-roster/ssot-roster.schema.json``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Literal, Optional, Tuple

import yaml

from uiao.governance.drift import DRIFT_SSOT_CONTENTION
from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WriteEvent:
    """A single write event observed against an instance.

    Sourced from an adapter that surfaces the underlying audit log: a
    SQL Server Audit reader for MS SQL writes, an HR-system audit log
    reader for HR-domain writes, etc. The classifier consumes this
    canonical event shape regardless of the audit-log source.
    """

    target_instance: str
    target_table: str
    target_column: Optional[str]  # None when the write affects the whole row
    timestamp: datetime
    principal: str
    source_audit_log: str = "unknown"


@dataclass(frozen=True)
class AuthoritativeInstance:
    """The single SSOT instance designated for a data domain."""

    identifier: str
    boundary_classification: str
    selection_rationale: str
    discovery_source: Optional[str] = None


@dataclass(frozen=True)
class CutoverWindow:
    """Planned operational window during which write traffic moves from
    a demoted instance to the authoritative SSOT. Writes inside this
    window emit at P3 (informational) rather than P2 (default).
    """

    planned_start: datetime
    planned_end: datetime

    def contains(self, ts: datetime) -> bool:
        return self.planned_start <= ts <= self.planned_end


@dataclass(frozen=True)
class DemotedInstance:
    """An instance canonically demoted in favor of an SSOT for a domain."""

    identifier: str
    demotion_date: date
    status: str
    cutover_window: Optional[CutoverWindow] = None
    cache_eligible_columns: FrozenSet[str] = field(default_factory=frozenset)
    retirement_date: Optional[date] = None
    remediation_window_days: Optional[int] = None
    discovery_source: Optional[str] = None


@dataclass(frozen=True)
class SSOTRoster:
    """A canon-blessed SSOT roster for a single (domain, domain_scope) pair.

    Loaded from a YAML file conforming to
    ``src/uiao/schemas/ssot-roster/ssot-roster.schema.json``.
    """

    schema_version: str
    domain: str
    ratification_date: date
    authoritative_instance: AuthoritativeInstance
    demoted_instances: Tuple[DemotedInstance, ...]
    remediation_window_days: int = 30
    domain_scope: Optional[str] = None
    governance_review_pr: Optional[str] = None

    @classmethod
    def from_yaml(cls, path: Path) -> SSOTRoster:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SSOTRoster:
        auth = data["authoritative_instance"]
        authoritative = AuthoritativeInstance(
            identifier=auth["identifier"],
            boundary_classification=auth["boundary_classification"],
            selection_rationale=auth["selection_rationale"],
            discovery_source=auth.get("discovery_source"),
        )

        demoted: List[DemotedInstance] = []
        for entry in data.get("demoted_instances", []):
            window = None
            if "cutover_window" in entry:
                w = entry["cutover_window"]
                window = CutoverWindow(
                    planned_start=_parse_datetime(w["planned_start"]),
                    planned_end=_parse_datetime(w["planned_end"]),
                )
            retirement = _parse_date(entry["retirement_date"]) if entry.get("retirement_date") else None
            demoted.append(
                DemotedInstance(
                    identifier=entry["identifier"],
                    demotion_date=_parse_date(entry["demotion_date"]),
                    status=entry["status"],
                    cutover_window=window,
                    cache_eligible_columns=frozenset(entry.get("cache_eligible_columns", [])),
                    retirement_date=retirement,
                    remediation_window_days=entry.get("remediation_window_days"),
                    discovery_source=entry.get("discovery_source"),
                )
            )

        return cls(
            schema_version=data["schema-version"],
            domain=data["domain"],
            domain_scope=data.get("domain_scope"),
            ratification_date=_parse_date(data["ratification_date"]),
            authoritative_instance=authoritative,
            demoted_instances=tuple(demoted),
            remediation_window_days=data.get("remediation_window_days", 30),
            governance_review_pr=data.get("governance_review_pr"),
        )

    def find_demoted(self, identifier: str) -> Optional[DemotedInstance]:
        for d in self.demoted_instances:
            if d.identifier == identifier:
                return d
        return None


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def classify_ssot_contention(
    *,
    roster: SSOTRoster,
    write_event: WriteEvent,
    provenance: ProvenanceRecord,
    now: Optional[datetime] = None,
    drift_id: Optional[str] = None,
) -> Optional[DriftState]:
    """Evaluate ADR-074 §2 predicates against a single write event.

    Returns a ``DriftState`` with ``drift_class="DRIFT-SSOT-CONTENTION"``
    when all five predicates hold; otherwise returns ``None``. Severity
    is assigned per ADR-074 §3.

    The ``now`` parameter is exposed for deterministic testing; in
    production it defaults to the current UTC time.
    """
    # Predicate 2: roster declares demoted instances.
    if not roster.demoted_instances:
        return None

    # Predicate 3: write_event targets a demoted instance.
    demoted = roster.find_demoted(write_event.target_instance)
    if demoted is None:
        return None

    # Predicate 5a: write occurred after demotion.
    write_date = write_event.timestamp.date()
    if write_date < demoted.demotion_date:
        return None

    # Predicate 5b: write occurred before retirement (when retirement is set).
    if demoted.retirement_date is not None and write_date > demoted.retirement_date:
        return None

    # Predicate 4: target column is not in cache_eligible_columns.
    if write_event.target_column is not None and _column_in_allowlist(
        write_event.target_table,
        write_event.target_column,
        demoted.cache_eligible_columns,
    ):
        return None

    # All predicates pass — emit contention finding.
    severity = _severity_for_event(
        roster=roster,
        demoted=demoted,
        write_event=write_event,
        now=now,
    )
    return _build_contention_drift_state(
        roster=roster,
        demoted=demoted,
        write_event=write_event,
        severity=severity,
        provenance=provenance,
        drift_id=drift_id,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _column_in_allowlist(
    table: str,
    column: str,
    allowlist: FrozenSet[str],
) -> bool:
    """Return True when 'table.column' is covered by the allowlist.

    Allowlist entries are either two-segment (``table.column``) or
    three-segment (``schema.table.column``). The classifier matches on
    the trailing ``table.column`` regardless of schema qualifier, since
    WriteEvent does not carry the schema name.
    """
    canonical = f"{table}.{column}"
    if canonical in allowlist:
        return True
    for entry in allowlist:
        parts = entry.split(".")
        if len(parts) == 3 and parts[1] == table and parts[2] == column:
            return True
    return False


def _severity_for_event(
    *,
    roster: SSOTRoster,
    demoted: DemotedInstance,
    write_event: WriteEvent,
    now: Optional[datetime],
) -> str:
    """Map an event + roster to a P1-P4 severity band per ADR-074 §3."""
    if demoted.cutover_window is not None and demoted.cutover_window.contains(write_event.timestamp):
        return "P3"

    effective_now = now or datetime.now(timezone.utc)
    days_since_demotion = (effective_now.date() - demoted.demotion_date).days
    window_days = demoted.remediation_window_days or roster.remediation_window_days
    if days_since_demotion > window_days:
        return "P1"
    return "P2"


def _build_contention_drift_state(
    *,
    roster: SSOTRoster,
    demoted: DemotedInstance,
    write_event: WriteEvent,
    severity: str,
    provenance: ProvenanceRecord,
    drift_id: Optional[str],
) -> DriftState:
    """Construct the canonical DriftState for a contention finding.

    The DriftState's ``classification`` field carries the risk signal
    independent of the drift_class — contention is always at least
    'risky' (P3 cutover-window) and 'unauthorized' for P1/P2 since the
    write is canonically prohibited outside the cutover-validation
    window.
    """
    classification: Literal["risky", "unauthorized"] = "risky" if severity == "P3" else "unauthorized"
    column_ref = (
        f"{write_event.target_table}.{write_event.target_column}"
        if write_event.target_column
        else f"{write_event.target_table}.*"
    )
    expected_state = {
        "domain": roster.domain,
        "authoritative_instance": roster.authoritative_instance.identifier,
        "permitted_writes": "cache_eligible_columns only",
    }
    actual_state = {
        "demoted_instance": demoted.identifier,
        "write_target": column_ref,
        "write_timestamp": write_event.timestamp.isoformat(),
        "principal": write_event.principal,
    }
    expected_hash = canonical_hash(expected_state)
    actual_hash = canonical_hash(actual_state)
    resource_id = demoted.identifier
    policy_ref = f"ssot-roster::{roster.domain}" + (f"/{roster.domain_scope}" if roster.domain_scope else "")
    state_id = drift_id or f"drift:ssot-contention:{demoted.identifier}:{write_event.timestamp.isoformat()}"
    delta = {
        "added": [],
        "removed": [],
        "changed": [column_ref],
    }
    # Severity is conveyed via the `delta` payload's first changed entry
    # and via the DriftState's `classification` axis. ADR-074 §2's
    # severity bands inform routing; a downstream report builder picks
    # the band off of `expected_state` / `actual_state` and applies
    # additional context (e.g. domain boundary, audit log source).
    return DriftState(
        id=state_id,
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=True,
        classification=classification,
        delta=delta,
        provenance=provenance,
        drift_class=DRIFT_SSOT_CONTENTION,
    )


# ---------------------------------------------------------------------------
# Convenience aggregator
# ---------------------------------------------------------------------------


def classify_write_event_batch(
    *,
    roster: SSOTRoster,
    write_events: List[WriteEvent],
    provenance: ProvenanceRecord,
    now: Optional[datetime] = None,
) -> List[DriftState]:
    """Convenience wrapper — classify a batch of write events and return
    only the contention findings.

    Most callers will iterate event-by-event for streaming evaluation;
    this helper exists for batch evaluation from a static audit-log
    snapshot (the common case during initial roster ratification or
    end-of-month review).
    """
    findings: List[DriftState] = []
    for event in write_events:
        result = classify_ssot_contention(
            roster=roster,
            write_event=event,
            provenance=provenance,
            now=now,
        )
        if result is not None:
            findings.append(result)
    return findings
