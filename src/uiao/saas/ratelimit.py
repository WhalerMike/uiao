"""
uiao.saas.ratelimit
------------------
Per-tenant request-rate enforcement for the SaaS data plane.

A :class:`FixedWindowRateLimiter` keeps a per-key counter inside a rolling
fixed window. :class:`TenantRateLimiter` layers the per-plan quota table
(:mod:`uiao.saas.quotas`) on top: each tenant's budget is its plan's
``window_limit`` (steady rate + burst) over ``window_seconds``.

Scope & guarantees
------------------
The limiter is **in-memory and per-replica**: each Container App / ECS replica
enforces its own window. With *N* replicas the effective ceiling is up to *N×*
the per-plan limit — acceptable as a courtesy/abuse guard, and the standard
shape for an L7 limiter. A globally-exact limit requires a shared store
(Redis); that is a deployment swap behind the same :class:`TenantRateLimiter`
interface and is called out as future work in ADR-115.

The clock is injectable (``time.monotonic`` by default) so the window logic is
deterministic under test. The store is plain stdlib — no ``[saas]`` extra — and
the check is a single synchronous critical section (no ``await`` inside), so it
is atomic on the cooperative event loop without a lock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .quotas import DEFAULT_QUOTAS, PlanQuota, quota_for
from .tenant import Tenant, TenantPlan


@dataclass(frozen=True)
class RateLimitDecision:
    """The outcome of a single rate-limit check."""

    allowed: bool
    #: The window request ceiling applied (rate + burst).
    limit: int
    #: Requests remaining in the current window after this check.
    remaining: int
    #: Whole seconds until the current window resets.
    reset_after: int
    #: Seconds the caller should wait before retrying (only when blocked).
    retry_after: int = 0

    def headers(self) -> dict[str, str]:
        """Standard ``RateLimit-*`` response headers (IETF draft shape)."""
        h = {
            "RateLimit-Limit": str(self.limit),
            "RateLimit-Remaining": str(max(self.remaining, 0)),
            "RateLimit-Reset": str(self.reset_after),
        }
        if not self.allowed and self.retry_after > 0:
            h["Retry-After"] = str(self.retry_after)
        return h


class FixedWindowRateLimiter:
    """A fixed-window per-key counter.

    Each key maps to ``(window_start, count)``. A request is admitted while the
    count is below the limit; once the window elapses the counter resets. Keys
    are evicted lazily on access, so a quiet tenant leaves no residue beyond a
    single stale entry until its next request.
    """

    def __init__(
        self,
        *,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window = float(window_seconds)
        self._clock = clock
        self._buckets: dict[str, tuple[float, int]] = {}

    def check(self, key: str, limit: int) -> RateLimitDecision:
        """Admit or reject one request for ``key`` against ``limit``."""
        if limit <= 0:
            # Unlimited plan — always allowed, no bookkeeping.
            return RateLimitDecision(allowed=True, limit=0, remaining=0, reset_after=0)

        now = self._clock()
        start, count = self._buckets.get(key, (now, 0))
        elapsed = now - start
        if elapsed >= self._window:
            # Window expired — start a fresh one for this request.
            start, count = now, 0
            elapsed = 0.0

        reset_after = max(int(round(self._window - elapsed)), 0)

        if count >= limit:
            self._buckets[key] = (start, count)
            return RateLimitDecision(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_after=reset_after,
                retry_after=max(reset_after, 1),
            )

        count += 1
        self._buckets[key] = (start, count)
        return RateLimitDecision(
            allowed=True,
            limit=limit,
            remaining=limit - count,
            reset_after=reset_after,
        )

    def reset(self, key: str | None = None) -> None:
        """Drop one key's window (or all of them) — for tests / admin reset."""
        if key is None:
            self._buckets.clear()
        else:
            self._buckets.pop(key, None)


class TenantRateLimiter:
    """Enforce each tenant's per-plan request budget.

    The budget is the tenant plan's :pyattr:`~uiao.saas.quotas.PlanQuota.window_limit`
    over ``window_seconds``. Tenants whose plan is unlimited
    (``requests_per_minute <= 0``) always pass.
    """

    def __init__(
        self,
        *,
        quotas: dict[TenantPlan, PlanQuota] | None = None,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._quotas = quotas if quotas is not None else DEFAULT_QUOTAS
        self._limiter = FixedWindowRateLimiter(window_seconds=window_seconds, clock=clock)

    def quota(self, plan: TenantPlan) -> PlanQuota:
        return quota_for(plan, quotas=self._quotas)

    def check(self, tenant: Tenant) -> RateLimitDecision:
        """Check ``tenant`` against its plan budget for this window."""
        quota = self.quota(tenant.plan)
        if quota.unlimited_rate:
            return RateLimitDecision(allowed=True, limit=0, remaining=0, reset_after=0)
        return self._limiter.check(tenant.tenant_id, quota.window_limit)

    def reset(self, tenant_id: str | None = None) -> None:
        self._limiter.reset(tenant_id)


__all__ = [
    "RateLimitDecision",
    "FixedWindowRateLimiter",
    "TenantRateLimiter",
]
