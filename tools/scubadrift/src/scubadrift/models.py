"""Core data model for ScubaDrift.

ScubaGear (CISA's sanctioned M365 assessment tool) emits a point-in-time
result set: one row per policy with a Pass/Fail/Warning/Manual/N/A verdict.
ScubaDrift consumes that verdict set and layers on the three things ScubaGear
does not track: run-to-run drift, exception (risk-acceptance) lifecycle, and a
CI/conmon gate. These are the value objects those layers operate on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum


class Result(str, Enum):
    """A ScubaGear policy verdict, normalized to a closed vocabulary."""

    PASS = "Pass"
    FAIL = "Fail"
    WARNING = "Warning"
    MANUAL = "Manual"
    NA = "N/A"
    OMITTED = "Omitted"
    UNKNOWN = "Unknown"

    @classmethod
    def parse(cls, raw: str | None) -> Result:
        text = (raw or "").strip().lower()
        if text in ("pass", "passed"):
            return cls.PASS
        if text in ("fail", "failed"):
            return cls.FAIL
        if text in ("warning", "warn"):
            return cls.WARNING
        if text == "manual":
            return cls.MANUAL
        if text.replace(".", "").replace(" ", "").startswith("na") or text.startswith("n/a"):
            return cls.NA
        if text == "omitted":
            return cls.OMITTED
        return cls.UNKNOWN


#: Verdicts that count as a compliance failure by default. ``WARNING`` is
#: promoted into this set only when the caller opts in (``include_warnings``);
#: ``MANUAL``/``N/A``/``OMITTED`` are never auto-actionable.
FAILING = frozenset({Result.FAIL})
FAILING_WITH_WARNINGS = frozenset({Result.FAIL, Result.WARNING})


@dataclass(frozen=True)
class PolicyResult:
    """One evaluated policy from a ScubaGear run."""

    policy_id: str
    result: Result
    criticality: str = ""
    description: str = ""
    details: str = ""

    def is_failing(self, include_warnings: bool = False) -> bool:
        failing = FAILING_WITH_WARNINGS if include_warnings else FAILING
        return self.result in failing

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "result": self.result.value,
            "criticality": self.criticality,
            "description": self.description,
            "details": self.details,
        }


@dataclass(frozen=True)
class ScubaRun:
    """A single ScubaGear assessment: metadata plus its policy results."""

    product: str
    tenant_id: str
    timestamp: str
    scubagear_version: str
    baseline_version: str
    results: tuple[PolicyResult, ...]

    @property
    def when(self) -> datetime:
        """Best-effort parse of the run timestamp (UTC, epoch on failure)."""
        raw = (self.timestamp or "").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return datetime.fromtimestamp(0, tz=timezone.utc)

    def by_id(self) -> dict[str, PolicyResult]:
        return {p.policy_id: p for p in self.results}

    def failing(self, include_warnings: bool = False) -> tuple[PolicyResult, ...]:
        return tuple(p for p in self.results if p.is_failing(include_warnings))

    def to_dict(self) -> dict:
        return {
            "product": self.product,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp,
            "scubagear_version": self.scubagear_version,
            "baseline_version": self.baseline_version,
            "results": [p.to_dict() for p in self.results],
        }


@dataclass(frozen=True)
class RiskAcceptance:
    """A governed exception: a documented, time-boxed acceptance of a failure."""

    policy_id: str
    justification: str
    approved_by: str
    approved_date: date
    expiry_date: date
    ticket: str = ""

    def is_expired(self, as_of: date) -> bool:
        return as_of > self.expiry_date

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "justification": self.justification,
            "approved_by": self.approved_by,
            "approved_date": self.approved_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "ticket": self.ticket,
        }
