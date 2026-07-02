"""Exception-lifecycle triage — the heart of ScubaDrift.

ScubaGear tells you a policy failed. It does *not* tell you whether that
failure is already governed by a documented, in-date risk-acceptance, whether
an acceptance has quietly lapsed, or whether an old acceptance is now dead
weight because the policy passes again. Triage answers exactly those, splitting
every failing policy into three dispositions:

* ``ACTIONABLE_NEW_DRIFT`` — failing with no acceptance on file. Act now.
* ``LAPSED_ACCEPTANCE`` — failing, an acceptance exists but its expiry has
  passed. Act now (re-review / re-approve / remediate).
* ``GOVERNED_EXCEPTION`` — failing, covered by an in-date acceptance. Already
  governed; suppress from the action list (but keep it visible).

It also surfaces ``retirable`` acceptances: registered exceptions whose policy
now passes (or is absent), i.e. exceptions that can be cleaned out of the
register. All date math is ``as_of``-injected so results are deterministic and
never drift with the wall clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .models import PolicyResult, RiskAcceptance, ScubaRun


class Disposition(str, Enum):
    ACTIONABLE_NEW_DRIFT = "actionable_new_drift"
    LAPSED_ACCEPTANCE = "lapsed_acceptance"
    GOVERNED_EXCEPTION = "governed_exception"


#: Dispositions a conmon gate must act on.
ACTIONABLE = frozenset({Disposition.ACTIONABLE_NEW_DRIFT, Disposition.LAPSED_ACCEPTANCE})


@dataclass(frozen=True)
class TriagedPolicy:
    policy: PolicyResult
    disposition: Disposition
    reason: str
    acceptance: RiskAcceptance | None = None

    @property
    def is_actionable(self) -> bool:
        return self.disposition in ACTIONABLE

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy.policy_id,
            "criticality": self.policy.criticality,
            "result": self.policy.result.value,
            "disposition": self.disposition.value,
            "reason": self.reason,
            "acceptance": self.acceptance.to_dict() if self.acceptance else None,
        }


@dataclass(frozen=True)
class TriageReport:
    as_of: date
    triaged: tuple[TriagedPolicy, ...]
    retirable: tuple[RiskAcceptance, ...]

    @property
    def actionable(self) -> tuple[TriagedPolicy, ...]:
        return tuple(t for t in self.triaged if t.is_actionable)

    @property
    def governed(self) -> tuple[TriagedPolicy, ...]:
        return tuple(t for t in self.triaged if not t.is_actionable)

    def of(self, disposition: Disposition) -> tuple[TriagedPolicy, ...]:
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
            "summary": self.summary(),
            "triaged": [t.to_dict() for t in self.triaged],
            "retirable_acceptances": [a.to_dict() for a in self.retirable],
        }


def triage(
    run: ScubaRun,
    acceptances: list[RiskAcceptance],
    *,
    as_of: date,
    include_warnings: bool = False,
) -> TriageReport:
    """Split a run's failures into actionable vs governed, ``as_of`` a date."""
    by_id = {a.policy_id: a for a in acceptances}
    results_by_id = run.by_id()

    triaged: list[TriagedPolicy] = []
    for policy in run.failing(include_warnings):
        acc = by_id.get(policy.policy_id)
        if acc is None:
            triaged.append(TriagedPolicy(policy, Disposition.ACTIONABLE_NEW_DRIFT, "no risk-acceptance on file"))
        elif acc.is_expired(as_of):
            triaged.append(
                TriagedPolicy(
                    policy,
                    Disposition.LAPSED_ACCEPTANCE,
                    f"risk-acceptance expired {acc.expiry_date.isoformat()}"
                    + (f" ({acc.ticket})" if acc.ticket else ""),
                    acc,
                )
            )
        else:
            triaged.append(
                TriagedPolicy(
                    policy,
                    Disposition.GOVERNED_EXCEPTION,
                    f"accepted until {acc.expiry_date.isoformat()}" + (f" ({acc.ticket})" if acc.ticket else ""),
                    acc,
                )
            )

    # An acceptance is retirable when its policy is no longer failing (passing,
    # N/A, or gone from the run) — dead weight the register can shed.
    failing_ids = {p.policy_id for p in run.failing(include_warnings)}
    retirable = tuple(acc for acc in acceptances if acc.policy_id not in failing_ids and acc.policy_id in results_by_id)

    return TriageReport(as_of=as_of, triaged=tuple(triaged), retirable=retirable)
