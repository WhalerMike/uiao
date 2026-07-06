"""Continuous monitoring — the time dimension a single assessment (and single-run triage) omit.

A maturity self-assessment is point-in-time and :mod:`ztttdrift.triage`
decides a single run. Continuous-monitoring programs need more: a durable
*history* across runs, a per-pillar *maturity trend*, the *age* of each open
gap measured against a remediation deadline, and a *periodic report* an
ISSO/AO can act on. This module adds exactly that, on top of the same triage
core.

Per-pillar trend uses the ordinal stage scores documented on
:class:`ztttdrift.models.Stage` — ``traditional=0, initial=1, advanced=2,
optimal=3`` — averaged over every item assessed in the pillar (not just the
failing ones), so a pillar's score moves whenever any of its items does.

Federal context this **supports** (it does not, by itself, certify compliance):

* **CISA BOD 25-01** — recurring automated secure-configuration assessment and
  reporting; the same ledger discipline applied to Zero Trust maturity.
* **NIST SP 800-137 (ISCM)** / **NIST 800-53 CA-7** — ongoing assessment,
  trend, and a defined monitoring frequency.
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

from .models import DEFAULT_TARGET, MaturityRun, RiskAcceptance, Stage
from .triage import ACTIONABLE, triage

# --- SLA policy ------------------------------------------------------------

#: FedRAMP-style remediation windows in days, by risk tier. Defaults — confirm
#: against your authorization's ConMon requirements before relying on them.
DEFAULT_SLA_WINDOWS: dict[str, int] = {"high": 30, "moderate": 90, "low": 180}


def tier_for_gap(gap: int) -> str:
    """Risk tier for a stage gap (effective target rank minus assessed rank).

    Two or more stages below target is a **high**-tier gap (e.g. ``traditional``
    against an ``advanced`` target), one stage below is **moderate**, and
    anything at or above target is **low** (it should never be actionable).
    """
    if gap >= 2:
        return "high"
    if gap == 1:
        return "moderate"
    return "low"


# --- History ledger --------------------------------------------------------


@dataclass(frozen=True)
class HistoryFinding:
    item_id: str
    pillar: str
    stage: str
    gap: int
    disposition: str

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "pillar": self.pillar,
            "stage": self.stage,
            "gap": self.gap,
            "disposition": self.disposition,
        }

    @property
    def is_actionable(self) -> bool:
        return self.disposition in {d.value for d in ACTIONABLE}


@dataclass(frozen=True)
class HistoryEntry:
    """One recorded assessment: its date, provenance, counts, pillar scores, findings."""

    as_of: date
    assessed_at: str
    source: str
    target: str
    counts: dict[str, int]
    pillar_scores: dict[str, float]
    findings: tuple[HistoryFinding, ...]

    def actionable_ids(self) -> set[str]:
        return {f.item_id for f in self.findings if f.is_actionable}

    def failing_ids(self) -> set[str]:
        return {f.item_id for f in self.findings}

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of.isoformat(),
            "assessed_at": self.assessed_at,
            "source": self.source,
            "target": self.target,
            "counts": self.counts,
            "pillar_scores": self.pillar_scores,
            "findings": [f.to_dict() for f in self.findings],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        return cls(
            as_of=date.fromisoformat(d["as_of"]),
            assessed_at=d.get("assessed_at", ""),
            source=d.get("source", ""),
            target=d.get("target", ""),
            counts=dict(d.get("counts", {})),
            pillar_scores={str(k): float(v) for k, v in d.get("pillar_scores", {}).items()},
            findings=tuple(
                HistoryFinding(
                    f["item_id"], f.get("pillar", ""), f.get("stage", ""), int(f.get("gap", 0)), f["disposition"]
                )
                for f in d.get("findings", [])
            ),
        )


def pillar_scores(run: MaturityRun) -> dict[str, float]:
    """Average stage score per pillar over every assessed item (0.0–3.0)."""
    ranks: dict[str, list[int]] = {}
    for item in run.items:
        ranks.setdefault(item.pillar, []).append(item.stage.rank)
    return {pillar: round(sum(rs) / len(rs), 2) for pillar, rs in sorted(ranks.items())}


def record_run(
    run: MaturityRun,
    acceptances: list[RiskAcceptance],
    *,
    as_of: date,
    target: Stage = DEFAULT_TARGET,
) -> HistoryEntry:
    """Triage a run and distill it into a history entry."""
    report = triage(run, acceptances, as_of=as_of, target=target)
    findings = tuple(
        HistoryFinding(
            t.item.item_id,
            t.item.pillar,
            t.item.stage.value,
            t.target.rank - t.item.stage.rank,
            t.disposition.value,
        )
        for t in report.triaged
    )
    return HistoryEntry(
        as_of=as_of,
        assessed_at=run.assessed_at.isoformat(),
        source=run.source,
        target=target.value,
        counts=report.summary(),
        pillar_scores=pillar_scores(run),
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

    def first_seen(self, item_id: str) -> date | None:
        """Earliest date this item appears failing in the ledger."""
        seen = [e.as_of for e in self.entries if item_id in e.failing_ids()]
        return min(seen) if seen else None

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.write_text("".join(json.dumps(e.to_dict(), sort_keys=True) + "\n" for e in self.entries), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "History":
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
    item_id: str
    pillar: str
    tier: str
    disposition: str
    first_seen: date
    age_days: int
    window_days: int
    status: SlaStatus

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "pillar": self.pillar,
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

    Governed exceptions are excluded — their clock is the acceptance expiry,
    not a remediation deadline. The tier comes from the stage gap
    (:func:`tier_for_gap`): the further below target, the shorter the window.
    """
    windows = windows or DEFAULT_SLA_WINDOWS
    latest = history.latest
    if latest is None:
        return []
    out: list[SlaFinding] = []
    for f in latest.findings:
        if not f.is_actionable:
            continue
        first = history.first_seen(f.item_id) or latest.as_of
        tier = tier_for_gap(f.gap)
        window = windows.get(tier, windows.get("moderate", 90))
        age = (as_of - first).days
        out.append(SlaFinding(f.item_id, f.pillar, tier, f.disposition, first, age, window, _status(age, window)))
    out.sort(key=lambda s: (s.status is not SlaStatus.OVERDUE, -s.age_days))
    return out


# --- Period report ---------------------------------------------------------


@dataclass(frozen=True)
class ConMonReport:
    period_start: date | None
    period_end: date
    posture: dict[str, int]
    pillar_trend: dict[str, dict]
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
            "CISA BOD 25-01": "recurring automated assessment recorded to a durable history ledger",
            "NIST SP 800-137 (ISCM)": "ongoing assessment with trend and defined monitoring frequency",
            "NIST 800-53 CA-7": "continuous monitoring: maturity status over time, not a point-in-time check",
            "FedRAMP ConMon": "open gaps aged against remediation SLA windows (defaults High 30 / Moderate 90 / Low 180)",
        }

    def to_dict(self) -> dict:
        return {
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat(),
            "posture": self.posture,
            "pillar_trend": self.pillar_trend,
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


def _pillar_trend(latest: HistoryEntry, prev: HistoryEntry | None) -> dict[str, dict]:
    trend: dict[str, dict] = {}
    prev_scores = prev.pillar_scores if prev else {}
    for pillar, score in sorted(latest.pillar_scores.items()):
        before = prev_scores.get(pillar)
        trend[pillar] = {
            "score": score,
            "previous": before,
            "delta": round(score - before, 2) if before is not None else None,
        }
    return trend


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
        pillar_trend=_pillar_trend(latest, prev),
        new_actionable=tuple(sorted(latest_ids - prev_ids)),
        resolved_actionable=tuple(sorted(prev_ids - latest_ids)),
        sla=tuple(sla_findings(history, as_of=as_of, windows=windows)),
    )
