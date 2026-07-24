"""Core data model for ZTTTdrift.

A Zero Trust maturity self-assessment (Microsoft ZTTT, a CISA ZTMM v2.0
self-assessment worksheet, or similar) emits a point-in-time result set: one
row per assessed item with a *maturity stage* rather than a pass/fail verdict.
ZTTTdrift consumes that result set — normalized to the versioned
``ztttdrift-input/1.0`` contract — and layers on the three things the
assessment itself does not track: run-to-run drift, exception
(risk-acceptance) lifecycle, and a CI/conmon gate. These are the value objects
those layers operate on.

Stages follow the CISA Zero Trust Maturity Model v2.0 four-stage scale, which
is **ordered**::

    traditional (0) < initial (1) < advanced (2) < optimal (3)

The parenthesized rank is also the numeric score used for per-pillar trend
averaging in :mod:`ztttdrift.conmon`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class Stage(str, Enum):
    """A ZTMM v2.0 maturity stage — an ordered, closed vocabulary."""

    TRADITIONAL = "traditional"
    INITIAL = "initial"
    ADVANCED = "advanced"
    OPTIMAL = "optimal"

    @property
    def rank(self) -> int:
        """Ordinal position (and conmon score): traditional=0 ... optimal=3."""
        return _STAGE_RANK[self]

    @classmethod
    def parse(cls, raw: str | None) -> Stage:
        text = (raw or "").strip().lower()
        try:
            return cls(text)
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(f"unknown maturity stage {raw!r} (expected one of: {valid})") from None


_STAGE_RANK: dict[Stage, int] = {Stage.TRADITIONAL: 0, Stage.INITIAL: 1, Stage.ADVANCED: 2, Stage.OPTIMAL: 3}

#: The default gate target when neither the item nor the CLI says otherwise.
DEFAULT_TARGET = Stage.ADVANCED

#: The six CISA ZTMM v2.0 pillars (five pillars + the cross-cutting capabilities),
#: in canonical order. Pillar names in the input contract must match one of these
#: (case-insensitively); they are normalized to this spelling.
PILLARS: tuple[str, ...] = (
    "Identity",
    "Devices",
    "Networks",
    "Applications and Workloads",
    "Data",
    "Cross-Cutting",
)

_PILLAR_BY_LOWER: dict[str, str] = {p.lower(): p for p in PILLARS}


def normalize_pillar(raw: str) -> str:
    """Return the canonical pillar spelling, or raise ``ValueError``."""
    canonical = _PILLAR_BY_LOWER.get((raw or "").strip().lower())
    if canonical is None:
        raise ValueError(f"unknown pillar {raw!r} (expected one of: {', '.join(PILLARS)})")
    return canonical


@dataclass(frozen=True)
class MaturityItem:
    """One assessed item from a maturity run."""

    item_id: str
    pillar: str
    stage: Stage
    title: str = ""
    target_stage: Stage | None = None

    def effective_target(self, default_target: Stage) -> Stage:
        """The item's own target if declared, else the global default."""
        return self.target_stage or default_target

    def is_failing(self, default_target: Stage) -> bool:
        """An item FAILS when its assessed stage is below its effective target."""
        return self.stage.rank < self.effective_target(default_target).rank

    def gap(self, default_target: Stage) -> int:
        """How many stages below target (0 or negative when at/above target)."""
        return self.effective_target(default_target).rank - self.stage.rank

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "pillar": self.pillar,
            "stage": self.stage.value,
            "title": self.title,
            "target_stage": self.target_stage.value if self.target_stage else None,
        }


@dataclass(frozen=True)
class MaturityRun:
    """A single maturity assessment: metadata plus its per-item stages."""

    assessed_at: date
    source: str
    items: tuple[MaturityItem, ...]

    def by_id(self) -> dict[str, MaturityItem]:
        return {i.item_id: i for i in self.items}

    def failing(self, default_target: Stage) -> tuple[MaturityItem, ...]:
        return tuple(i for i in self.items if i.is_failing(default_target))

    def to_dict(self) -> dict:
        return {
            "assessed_at": self.assessed_at.isoformat(),
            "source": self.source,
            "items": [i.to_dict() for i in self.items],
        }


@dataclass(frozen=True)
class RiskAcceptance:
    """A governed exception: a documented, time-boxed acceptance of a below-target item."""

    item_id: str
    justification: str
    approved_by: str
    approved_date: date
    expiry_date: date
    ticket: str = ""

    def is_expired(self, as_of: date) -> bool:
        return as_of > self.expiry_date

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "justification": self.justification,
            "approved_by": self.approved_by,
            "approved_date": self.approved_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "ticket": self.ticket,
        }
