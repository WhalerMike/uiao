"""Continuous monitoring — the time dimension ScubaGear (and single-run triage) omit.

ScubaGear is point-in-time and :mod:`scubadrift.triage` decides a single run.
Continuous-monitoring programs need more: a durable *history* across runs, the
*age* of each open finding measured against a remediation deadline, and a
*periodic report* an ISSO/AO can act on. This module adds exactly that, on top
of the same triage core.

Federal context this **supports** (it does not, by itself, certify compliance):

* **CISA BOD 25-01** — recurring automated SCuBA assessment and reporting.
* **NIST SP 800-137 (ISCM)** / **NIST 800-53 CA-7** — ongoing assessment, trend,
  and a defined monitoring frequency.
* **FedRAMP ConMon** — POA&M remediation timelines by risk. The default SLA
  windows below (High 30 / Moderate 90 / Low 180 days) mirror the common
  FedRAMP figures; they are **defaults you must confirm** against your
  authorizing official's requirements, and are overridable.

Everything is ``as_of``-injected and history-file-driven, so it stays
deterministic and replayable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

from .models import RiskAcceptance, ScubaRun
from .triage import ACTIONABLE, triage

# --- SLA policy ------------------------------------------------------------

#: FedRAMP-style remediation windows in days, by risk tier. Defaults — confirm
#: against your authorization's ConMon requirements before relying on them.
DEFAULT_SLA_WINDOWS: dict[str, int] = {"high": 30, "moderate": 90, "low": 180}

#: Map a SCuBA Criticality ("Shall"/"Should"/"May") to a risk tier.
CRITICALITY_TIER: dict[str, str] = {"shall": "high", "should": "moderate", "may": "low"}


def tier_for(criticality: str) -> str:
    """Risk tier for a SCuBA criticality; unknown criticalities default to moderate."""
    return CRITICALITY_TIER.get((criticality or "").strip().lower(), "moderate")


# --- History ledger --------------------------------------------------------


@dataclass(frozen=True)
class HistoryFinding:
    policy_id: str
    criticality: str
    disposition: str

    def to_dict(self) -> dict:
        return {"policy_id": self.policy_id, "criticality": self.criticality, "disposition": self.disposition}

    @property
    def is_actionable(self) -> bool:
        return self.disposition in {d.value for d in ACTIONABLE}


@dataclass(frozen=True)
class HistoryEntry:
    """One recorded assessment: its date, provenance, counts, and findings."""

    as_of: date
    run_timestamp: str
    product: str
    tenant_id: str
    counts: dict[str, int]
    findings: tuple[HistoryFinding, ...]

    def actionable_ids(self) -> set[str]:
        return {f.policy_id for f in self.findings if f.is_actionable}

    def failing_ids(self) -> set[str]:
        return {f.policy_id for f in self.findings}

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of.isoformat(),
            "run_timestamp": self.run_timestamp,
            "product": self.product,
            "tenant_id": self.tenant_id,
            "counts": self.counts,
            "findings": [f.to_dict() for f in self.findings],
        }

    @classmethod
    def from_dict(cls, d: dict) -> HistoryEntry:
        return cls(
            as_of=date.fromisoformat(d["as_of"]),
            run_timestamp=d.get("run_timestamp", ""),
            product=d.get("product", ""),
            tenant_id=d.get("tenant_id", ""),
            counts=dict(d.get("counts", {})),
            findings=tuple(
                HistoryFinding(f["policy_id"], f.get("criticality", ""), f["disposition"])
                for f in d.get("findings", [])
            ),
        )


def record_run(
    run: ScubaRun,
    acceptances: list[RiskAcceptance],
    *,
    as_of: date,
    include_warnings: bool = False,
) -> HistoryEntry:
    """Triage a run and distill it into a history entry."""
    report = triage(run, acceptances, as_of=as_of, include_warnings=include_warnings)
    findings = tuple(
        HistoryFinding(t.policy.policy_id, t.policy.criticality, t.disposition.value) for t in report.triaged
    )
    return HistoryEntry(
        as_of=as_of,
        run_timestamp=run.timestamp,
        product=run.product,
        tenant_id=run.tenant_id,
        counts=report.summary(),
        findings=findings,
    )


@dataclass
class History:
    """An ordered ledger of :class:`HistoryEntry`, persisted as JSON Lines."""

    entries: list[HistoryEntry] = field(default_factory=list)

    def append(self, entry: HistoryEntry) -> None:
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.as_of)

    @property
    def latest(self) -> HistoryEntry | None:
        return self.entries[-1] if self.entries else None

    @property
    def previous(self) -> HistoryEntry | None:
        return self.entries[-2] if len(self.entries) >= 2 else None

    def first_seen(self, policy_id: str) -> date | None:
        """Earliest date this policy appears failing in the ledger."""
        seen = [e.as_of for e in self.entries if policy_id in e.failing_ids()]
        return min(seen) if seen else None

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.write_text("".join(json.dumps(e.to_dict(), sort_keys=True) + "\n" for e in self.entries), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> History:
        p = Path(path)
        if not p.exists():
            return cls()
        entries = [
            HistoryEntry.from_dict(json.loads(line))
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        entries.sort(key=lambda e: e.as_of)
        return cls(entries=entries)


# --- SLA / aging -----------------------------------------------------------


class SlaStatus(str, Enum):
    ON_TRACK = "on_track"
    DUE_SOON = "due_soon"  # within 20% of the window
    OVERDUE = "overdue"


@dataclass(frozen=True)
class SlaFinding:
    policy_id: str
    criticality: str
    tier: str
    disposition: str
    first_seen: date
    age_days: int
    window_days: int
    status: SlaStatus

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "criticality": self.criticality,
            "tier": self.tier,
            "disposition": self.disposition,
            "first_seen": self.first_seen.isoformat(),
            "age_days": self.age_days,
            "window_days": self.window_days,
            "status": self.status.value,
        }


def _status(age: int, window: int) -> SlaStatus:
    if age > window:
        return SlaStatus.OVERDUE
    if age >= window * 0.8:
        return SlaStatus.DUE_SOON
    return SlaStatus.ON_TRACK


def sla_findings(
    history: History,
    *,
    as_of: date,
    windows: dict[str, int] | None = None,
) -> list[SlaFinding]:
    """Age every actionable finding in the latest entry against its SLA window.

    Governed exceptions are excluded — their clock is the acceptance expiry, not
    a remediation deadline.
    """
    windows = windows or DEFAULT_SLA_WINDOWS
    latest = history.latest
    if latest is None:
        return []
    out: list[SlaFinding] = []
    for f in latest.findings:
        if not f.is_actionable:
            continue
        first = history.first_seen(f.policy_id) or latest.as_of
        tier = tier_for(f.criticality)
        window = windows.get(tier, windows.get("moderate", 90))
        age = (as_of - first).days
        out.append(
            SlaFinding(f.policy_id, f.criticality, tier, f.disposition, first, age, window, _status(age, window))
        )
    out.sort(key=lambda s: (s.status is not SlaStatus.OVERDUE, -s.age_days))
    return out


# --- Period report ---------------------------------------------------------


@dataclass(frozen=True)
class ConMonReport:
    period_start: date | None
    period_end: date
    posture: dict[str, int]
    new_actionable: tuple[str, ...]
    resolved_actionable: tuple[str, ...]
    sla: tuple[SlaFinding, ...]

    @property
    def overdue(self) -> tuple[SlaFinding, ...]:
        return tuple(s for s in self.sla if s.status is SlaStatus.OVERDUE)

    @property
    def due_soon(self) -> tuple[SlaFinding, ...]:
        return tuple(s for s in self.sla if s.status is SlaStatus.DUE_SOON)

    @property
    def clean(self) -> bool:
        """No actionable findings and no SLA breach."""
        return self.posture.get("actionable_total", 0) == 0 and not self.overdue

    def framework_alignment(self) -> dict[str, str]:
        return {
            "CISA BOD 25-01": "recurring SCuBA assessment recorded to a durable history ledger",
            "NIST SP 800-137 (ISCM)": "ongoing assessment with trend and defined monitoring frequency",
            "NIST 800-53 CA-7": "continuous monitoring: status over time, not a point-in-time check",
            "FedRAMP ConMon": "open findings aged against remediation SLA windows (defaults High 30 / Moderate 90 / Low 180)",
        }

    def to_dict(self) -> dict:
        return {
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat(),
            "posture": self.posture,
            "trend": {
                "new_actionable": list(self.new_actionable),
                "resolved_actionable": list(self.resolved_actionable),
            },
            "sla": {
                "overdue": [s.to_dict() for s in self.overdue],
                "due_soon": [s.to_dict() for s in self.due_soon],
                "all": [s.to_dict() for s in self.sla],
            },
            "clean": self.clean,
            "framework_alignment": self.framework_alignment(),
        }


def build_report(
    history: History,
    *,
    as_of: date,
    windows: dict[str, int] | None = None,
) -> ConMonReport:
    """Build a periodic continuous-monitoring report from the ledger."""
    latest = history.latest
    if latest is None:
        raise ValueError("cannot build a ConMon report from an empty history")
    prev = history.previous
    latest_ids = latest.actionable_ids()
    prev_ids = prev.actionable_ids() if prev else set()
    return ConMonReport(
        period_start=prev.as_of if prev else None,
        period_end=latest.as_of,
        posture=dict(latest.counts),
        new_actionable=tuple(sorted(latest_ids - prev_ids)),
        resolved_actionable=tuple(sorted(prev_ids - latest_ids)),
        sla=tuple(sla_findings(history, as_of=as_of, windows=windows)),
    )
