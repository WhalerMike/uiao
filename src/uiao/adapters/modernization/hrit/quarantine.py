"""
hrit/quarantine.py
------------------
UIAO Modernization Adapter: HR-feed quarantine gate for OrgPath placement.

``extract_hrit_record_inventory`` (``inventory.py``) resolves each inbound HR
record to an OrgPath and emits ``DRIFT-IDENTITY`` when the organizational
fields exist but resolve to nothing. That is necessary but not sufficient: an
HR feed can also deliver rows that are *structurally* resolvable yet unsafe to
provision from — a snapshot that went stale, a row with no placement fields at
all, or a "move" that relocates a person implausibly far across the org in a
single sync. Provisioning (or de-provisioning) from any of those silently
propagates a bad feed into Entra.

This module is the **quarantine gate** that sits between the HR inventory and
the provisioning middleware (Spec2-D3.2). It inspects the resolved records and
*holds* — does not provision — any record that trips one of three checks:

  * **Staleness** (``DRIFT-PROVENANCE``) — the record's ``extracted_at`` is
    older than the freshness bound, so the snapshot may no longer reflect the
    system of record. A stale snapshot must not drive joiner/mover/leaver.
  * **Null placement** (``DRIFT-IDENTITY``) — every organizational field
    (``department``, ``division``, ``organization_code``, ``cost_center``) is
    empty, so there is nothing to place on. Distinct from the inventory's
    unresolved-OrgPath finding, where the fields are present but miss the
    codebook.
  * **Improbable delta** (``DRIFT-SEMANTIC``) — the record's new OrgPath
    diverges from the person's prior placement by more than a plausible move:
    the top-level org changed, too many path segments changed at once, or the
    depth jumped too far. A legitimate mover shifts within a shared ancestor;
    a whole-org jump in one feed sync is far more likely a bad row.

A quarantined record is not a rejection — it is a **hold for human review**
before it reaches the provisioning pipeline, the same governance-review posture
the drift engine uses elsewhere. The gate is deterministic and side-effect
free: it reads records + a prior-placement map + the current time and returns a
report; the caller decides what to do with the held set.

Drift-class mapping follows ``docs/docs/16_DriftDetectionStandard.qmd`` and the
inventory adapter's own mapping table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Mapping, Optional, Sequence

from .inventory import DriftFinding, HRRecord

# ------------------------------------------------------------------
# Quarantine reason codes — stable identifiers used in decisions and
# surfaced in the report summary.
# ------------------------------------------------------------------
QUARANTINE_STALE: str = "STALE"
QUARANTINE_NULL_PLACEMENT: str = "NULL_PLACEMENT"
QUARANTINE_IMPROBABLE_DELTA: str = "IMPROBABLE_DELTA"
_VALID_QUARANTINE_REASONS: tuple[str, ...] = (
    QUARANTINE_STALE,
    QUARANTINE_NULL_PLACEMENT,
    QUARANTINE_IMPROBABLE_DELTA,
)

# Drift class + severity per reason (see module docstring).
_REASON_DRIFT_CLASS: dict[str, str] = {
    QUARANTINE_STALE: "DRIFT-PROVENANCE",
    QUARANTINE_NULL_PLACEMENT: "DRIFT-IDENTITY",
    QUARANTINE_IMPROBABLE_DELTA: "DRIFT-SEMANTIC",
}
_REASON_SEVERITY: dict[str, str] = {
    QUARANTINE_STALE: "P2",
    QUARANTINE_NULL_PLACEMENT: "P1",
    QUARANTINE_IMPROBABLE_DELTA: "P2",
}


@dataclass(frozen=True)
class QuarantineConfig:
    """Tunable thresholds for the quarantine gate.

    ``max_age_hours`` bounds snapshot freshness (staleness check).
    ``orgpath_delimiter`` is the OrgPath segment separator; a single
    trailing delimiter is tolerated (OrgPath prefixes carry it).
    ``max_changed_segments`` and ``max_depth_jump`` bound how far a move
    may travel before it is treated as improbable; ``top_level_change_is_improbable``
    flags any change to the root org segment as improbable regardless of
    the numeric thresholds.
    """

    max_age_hours: float = 48.0
    orgpath_delimiter: str = "/"
    max_changed_segments: int = 2
    max_depth_jump: int = 2
    top_level_change_is_improbable: bool = True


@dataclass(frozen=True)
class QuarantineDecision:
    """The gate's decision for one HR record."""

    employee_id: str
    quarantined: bool
    reasons: tuple[str, ...] = ()
    findings: tuple[DriftFinding, ...] = ()


@dataclass
class QuarantineReport:
    """Aggregate result of a quarantine-gate pass.

    ``decisions`` carries one entry per input record (in input order).
    ``held`` is the subset of employee_ids that were quarantined — the
    records the caller must NOT provision without review. ``findings`` is
    every drift finding flattened for merge into the parent report.
    """

    decisions: list[QuarantineDecision] = field(default_factory=list)
    held: list[str] = field(default_factory=list)
    findings: list[DriftFinding] = field(default_factory=list)

    @property
    def evaluated_count(self) -> int:
        return len(self.decisions)

    @property
    def held_count(self) -> int:
        return len(self.held)

    @property
    def cleared_count(self) -> int:
        return self.evaluated_count - self.held_count

    def reason_counts(self) -> dict[str, int]:
        """Count of held records by quarantine reason (a record may count in more than one)."""
        counts = {r: 0 for r in _VALID_QUARANTINE_REASONS}
        for d in self.decisions:
            for r in d.reasons:
                counts[r] += 1
        return counts


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------
def _parse_iso(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp (accepting a trailing 'Z') to aware UTC.

    Returns None when the value is empty or unparseable — the caller treats
    an unparseable ``extracted_at`` as its own provenance problem rather than
    raising, so one bad row cannot abort the whole gate pass.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _segments(orgpath: str, delimiter: str) -> list[str]:
    """Split an OrgPath into non-empty segments, tolerating a trailing delimiter."""
    return [s for s in orgpath.split(delimiter) if s]


def _has_placement_fields(record: HRRecord) -> bool:
    """True when at least one organizational placement field is populated."""
    return any(
        (v or "").strip()
        for v in (
            record.department,
            record.division,
            record.organization_code,
            record.cost_center,
        )
    )


def _improbable_delta(prior: str, current: str, config: QuarantineConfig) -> Optional[str]:
    """Return a human-readable reason if prior->current is an improbable move, else None."""
    delim = config.orgpath_delimiter
    old = _segments(prior, delim)
    new = _segments(current, delim)
    if not old or not new or old == new:
        return None

    common = 0
    for a, b in zip(old, new, strict=False):
        if a == b:
            common += 1
        else:
            break

    if config.top_level_change_is_improbable and common == 0:
        return (
            f"top-level org changed ('{old[0]}' -> '{new[0]}'); a cross-organization "
            "move in a single feed sync is more likely a bad row than a real transfer"
        )

    changed = max(len(old), len(new)) - common
    if changed > config.max_changed_segments:
        return f"{changed} OrgPath segments changed at once (threshold {config.max_changed_segments})"

    depth_jump = abs(len(new) - len(old))
    if depth_jump > config.max_depth_jump:
        return (
            f"OrgPath depth jumped by {depth_jump} levels ({len(old)} -> {len(new)}; threshold {config.max_depth_jump})"
        )
    return None


# ------------------------------------------------------------------
# Gate entry point
# ------------------------------------------------------------------
def evaluate_hr_quarantine(
    records: Sequence[HRRecord],
    *,
    now: str,
    prior_placements: Optional[Mapping[str, str]] = None,
    config: Optional[QuarantineConfig] = None,
) -> QuarantineReport:
    """Run the quarantine gate over a set of resolved HR records.

    Parameters
    ----------
    records:
        HR records as produced by ``extract_hrit_record_inventory`` (each
        carries ``resolved_orgpath`` when the inventory could place it).
    now:
        Current time as an ISO-8601 timestamp; the staleness check measures
        ``now - extracted_at`` against ``config.max_age_hours``. Passed in
        (never read from the clock here) so the gate is deterministic and
        replayable in evidence.
    prior_placements:
        Optional map of ``employee_id -> prior OrgPath``. When a record's
        ``employee_id`` is present here and its ``resolved_orgpath`` differs,
        the improbable-delta check runs. Absent entries skip that check (a
        joiner has no prior placement).
    config:
        Threshold overrides; defaults are conservative (see ``QuarantineConfig``).

    Returns
    -------
    QuarantineReport
        One decision per record, the held employee_id set, and the flattened
        drift findings for merge into the parent report.
    """
    cfg = config or QuarantineConfig()
    priors = prior_placements or {}
    now_dt = _parse_iso(now)
    report = QuarantineReport()
    seq = 0

    for record in records:
        reasons: list[str] = []
        findings: list[DriftFinding] = []

        # 1. Staleness — snapshot older than the freshness bound.
        extracted_dt = _parse_iso(record.extracted_at)
        if now_dt is not None and extracted_dt is not None:
            age = now_dt - extracted_dt
            if age > timedelta(hours=cfg.max_age_hours):
                age_hours = age.total_seconds() / 3600.0
                seq += 1
                reasons.append(QUARANTINE_STALE)
                findings.append(
                    _finding(
                        QUARANTINE_STALE,
                        seq,
                        record.employee_id,
                        f"HR record snapshot is {age_hours:.1f}h old (extracted_at "
                        f"'{record.extracted_at}'), exceeding the {cfg.max_age_hours:.0f}h "
                        "freshness bound. A stale snapshot must not drive provisioning; "
                        "hold until a fresh extract confirms the record.",
                    )
                )

        # 2. Null placement — no organizational field to place on.
        if not _has_placement_fields(record):
            seq += 1
            reasons.append(QUARANTINE_NULL_PLACEMENT)
            findings.append(
                _finding(
                    QUARANTINE_NULL_PLACEMENT,
                    seq,
                    record.employee_id,
                    "HR record carries no organizational placement fields "
                    "(department, division, organization_code, cost_center all empty); "
                    "there is nothing to bind an OrgPath to. Hold for HR data correction "
                    "before provisioning.",
                )
            )

        # 3. Improbable delta — implausible move versus prior placement.
        prior = priors.get(record.employee_id)
        current = record.resolved_orgpath
        if prior and current:
            why = _improbable_delta(prior, current, cfg)
            if why is not None:
                seq += 1
                reasons.append(QUARANTINE_IMPROBABLE_DELTA)
                findings.append(
                    _finding(
                        QUARANTINE_IMPROBABLE_DELTA,
                        seq,
                        record.employee_id,
                        f"OrgPath move from '{prior}' to '{current}' is improbable: {why}. "
                        "Hold for review — an improbable placement delta is more often a "
                        "bad HR feed row than a real transfer.",
                    )
                )

        quarantined = bool(reasons)
        report.decisions.append(
            QuarantineDecision(
                employee_id=record.employee_id,
                quarantined=quarantined,
                reasons=tuple(reasons),
                findings=tuple(findings),
            )
        )
        if quarantined:
            report.held.append(record.employee_id)
            report.findings.extend(findings)

    return report


def _finding(reason: str, seq: int, employee_id: str, detail: str) -> DriftFinding:
    """Build a DriftFinding for a quarantine reason (GOV-HRQ-NNN error codes)."""
    return DriftFinding(
        drift_class=_REASON_DRIFT_CLASS[reason],
        severity=_REASON_SEVERITY[reason],
        path=employee_id,
        detail=detail,
        error_code=f"GOV-HRQ-{seq:03d}",
        object_type="HRRecord",
    )
