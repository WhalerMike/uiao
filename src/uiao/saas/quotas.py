"""
uiao.saas.quotas
---------------
Per-plan service quotas for the multi-tenant SaaS.

Each :class:`~uiao.saas.tenant.TenantPlan` maps to a :class:`PlanQuota` that
caps the resources a tenant on that plan may consume. The headline knob is the
**request rate** (enforced by :mod:`uiao.saas.ratelimit`); the rest are
advisory caps the control plane and governance scheduler read when admitting
work. Quotas are pure data — no I/O, stdlib only — so they import cleanly into
the blocking CI test job and are trivially overridable per deployment.

The defaults are deliberately conservative and easy to reason about; a
deployment overrides them by passing a custom ``quotas`` mapping to
:func:`uiao.saas.ratelimit.TenantRateLimiter` (or by editing
:data:`DEFAULT_QUOTAS` at startup).
"""

from __future__ import annotations

from dataclasses import dataclass

from .tenant import TenantPlan


@dataclass(frozen=True)
class PlanQuota:
    """Resource ceilings for a single commercial plan.

    Attributes
    ----------
    requests_per_minute:
        Sustained inbound data-plane request budget per tenant, per minute.
        ``0`` disables rate limiting for the plan (treated as unlimited).
    burst:
        Extra requests tolerated above the steady rate within a window before
        the limiter rejects (head-room for bursty governance passes).
    max_concurrent_passes:
        Advisory cap on concurrently-running governance passes for the tenant.
    max_evidence_bundles:
        Advisory cap on retained evidence bundles before rotation is required.
    """

    requests_per_minute: int
    burst: int
    max_concurrent_passes: int
    max_evidence_bundles: int

    @property
    def unlimited_rate(self) -> bool:
        """True when this plan is exempt from request-rate limiting."""
        return self.requests_per_minute <= 0

    @property
    def window_limit(self) -> int:
        """Total requests admitted in one rate-limit window (rate + burst)."""
        return self.requests_per_minute + self.burst


#: Default quota table. Tuned so trial is sharply capped, standard/enterprise
#: scale up, and the sovereign (``gov``) plan matches enterprise headroom.
DEFAULT_QUOTAS: dict[TenantPlan, PlanQuota] = {
    TenantPlan.TRIAL: PlanQuota(
        requests_per_minute=60,
        burst=20,
        max_concurrent_passes=1,
        max_evidence_bundles=50,
    ),
    TenantPlan.STANDARD: PlanQuota(
        requests_per_minute=600,
        burst=120,
        max_concurrent_passes=4,
        max_evidence_bundles=1000,
    ),
    TenantPlan.ENTERPRISE: PlanQuota(
        requests_per_minute=3000,
        burst=600,
        max_concurrent_passes=16,
        max_evidence_bundles=10000,
    ),
    TenantPlan.GOV: PlanQuota(
        requests_per_minute=3000,
        burst=600,
        max_concurrent_passes=16,
        max_evidence_bundles=10000,
    ),
}

#: Fallback when a plan is somehow absent from the table — the most
#: conservative ceilings, so an unknown plan never gets unlimited capacity.
FALLBACK_QUOTA = DEFAULT_QUOTAS[TenantPlan.TRIAL]


def quota_for(plan: TenantPlan, *, quotas: dict[TenantPlan, PlanQuota] | None = None) -> PlanQuota:
    """Return the :class:`PlanQuota` for ``plan`` (falls back to TRIAL caps)."""
    table = quotas if quotas is not None else DEFAULT_QUOTAS
    return table.get(plan, FALLBACK_QUOTA)


__all__ = [
    "PlanQuota",
    "DEFAULT_QUOTAS",
    "FALLBACK_QUOTA",
    "quota_for",
]
