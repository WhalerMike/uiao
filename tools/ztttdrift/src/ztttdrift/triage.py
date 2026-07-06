"""Exception-lifecycle triage — the heart of ZTTTdrift.

A maturity assessment tells you an item sits at, say, ``initial`` while your
target is ``advanced``. It does *not* tell you whether that gap is already
governed by a documented, in-date risk-acceptance, whether an acceptance has
quietly lapsed, or whether an old acceptance is now dead weight because the
item has since reached target. Triage answers exactly those, splitting every
**failing** item (assessed stage below its effective target) into three
dispositions:

* ``ACTIONABLE_NEW_DRIFT`` — below target with no acceptance on file. Act now.
* ``LAPSED_ACCEPTANCE`` — below target, an acceptance exists but its expiry
  has passed. Act now (re-review / re-approve / remediate).
* ``GOVERNED_EXCEPTION`` — below target, covered by an in-date acceptance.
  Already governed; suppress from the action list (but keep it visible).

It also surfaces ``retirable`` acceptances: registered exceptions whose item
now meets target, i.e. exceptions that can be cleaned out of the register.
All date math is ``as_of``-injected so results are deterministic and never
drift with the wall clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .models import DEFAULT_TARGET, MaturityItem, MaturityRun, RiskAcceptance, Stage


class Disposition(str, Enum):
    ACTIONABLE_NEW_DRIFT = "actionable_new_drift"
    LAPSED_ACCEPTANCE = "lapsed_acceptance"
    GOVERNED_EXCEPTION = "governed_exception"


#: Dispositions a conmon gate must act on.
ACTIONABLE = frozenset({Disposition.ACTIONABLE_NEW_DRIFT, Disposition.LAPSED_ACCEPTANCE})


@dataclass(frozen=True)
class TriagedItem:
    item: MaturityItem
    target: Stage  # the item's effective target this run was judged against
    disposition: Disposition
    reason: str
    acceptance: RiskAcceptance | None = None

    @property
    def is_actionable(self) -> bool:
        return self.disposition in ACTIONABLE

    def to_dict(self) -> dict:
        return {
            "item_id": self.item.item_id,
            "pillar": self.item.pillar,
            "stage": self.item.stage.value,
            "target_stage": self.target.value,
            "gap": self.target.rank - self.item.stage.rank,
            "disposition": self.disposition.value,
            "reason": self.reason,
            "acceptance": self.acceptance.to_dict() if self.acceptance else None,
        }


@dataclass(frozen=True)
class TriageReport:
    as_of: date
    target: Stage  # the global default target used
    triaged: tuple[TriagedItem, ...]
    retirable: tuple[RiskAcceptance, ...]

    @property
    def actionable(self) -> tuple[TriagedItem, ...]:
        return tuple(t for t in self.triaged if t.is_actionable)

    @property
    def governed(self) -> tuple[TriagedItem, ...]:
        return tuple(t for t in self.triaged if not t.is_actionable)

    def of(self, disposition: Disposition) -> tuple[TriagedItem, ...]:
        return tuple(t for t in self.triaged if t.disposition is disposition)

    @property
    def clean(self) -> bool:
        """True when nothing requires action (the gate-pass condition)."""
        return not self.actionable

    def summary(self) -> dict[str, int]:
        return {
            "failing_total": len(self.triaged),
            "actionable_new_drift": len(self.of(Disposition.ACTIONABLE_NEW_DRIFT)),
            "lapsed_acceptance": len(self.of(Disposition.LAPSED_ACCEPTANCE)),
            "governed_exception": len(self.of(Disposition.GOVERNED_EXCEPTION)),
            "actionable_total": len(self.actionable),
            "retirable_acceptances": len(self.retirable),
        }

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of.isoformat(),
            "target": self.target.value,
            "summary": self.summary(),
            "triaged": [t.to_dict() for t in self.triaged],
            "retirable_acceptances": [a.to_dict() for a in self.retirable],
        }


def _gap_text(item: MaturityItem, target: Stage) -> str:
    return f"stage {item.stage.value} below target {target.value}"


def triage(
    run: MaturityRun,
    acceptances: list[RiskAcceptance],
    *,
    as_of: date,
    target: Stage = DEFAULT_TARGET,
) -> TriageReport:
    """Split a run's below-target items into actionable vs governed, ``as_of`` a date."""
    by_id = {a.item_id: a for a in acceptances}
    items_by_id = run.by_id()

    triaged: list[TriagedItem] = []
    for item in run.failing(target):
        eff = item.effective_target(target)
        acc = by_id.get(item.item_id)
        if acc is None:
            triaged.append(
                TriagedItem(
                    item,
                    eff,
                    Disposition.ACTIONABLE_NEW_DRIFT,
                    f"{_gap_text(item, eff)}; no risk-acceptance on file",
                )
            )
        elif acc.is_expired(as_of):
            triaged.append(
                TriagedItem(
                    item,
                    eff,
                    Disposition.LAPSED_ACCEPTANCE,
                    f"{_gap_text(item, eff)}; risk-acceptance expired {acc.expiry_date.isoformat()}"
                    + (f" ({acc.ticket})" if acc.ticket else ""),
                    acc,
                )
            )
        else:
            triaged.append(
                TriagedItem(
                    item,
                    eff,
                    Disposition.GOVERNED_EXCEPTION,
                    f"{_gap_text(item, eff)}; accepted until {acc.expiry_date.isoformat()}"
                    + (f" ({acc.ticket})" if acc.ticket else ""),
                    acc,
                )
            )

    # An acceptance is retirable when its item now meets target — dead weight
    # the register can shed. (Items absent from the run are left alone: we
    # cannot claim they meet target, only that this run did not assess them.)
    failing_ids = {i.item_id for i in run.failing(target)}
    retirable = tuple(a for a in acceptances if a.item_id not in failing_ids and a.item_id in items_by_id)

    return TriageReport(as_of=as_of, target=target, triaged=tuple(triaged), retirable=retirable)
