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
:class:`TenantRateLimiter` is **in-memory and per-replica**: each Container App
/ ECS replica enforces its own window. With *N* replicas the effective ceiling
is up to *N×* the per-plan limit — acceptable as a courtesy/abuse guard, and the
standard shape for an L7 limiter.

For a **globally-exact** limit across replicas, :class:`DistributedTenantRateLimiter`
runs the same per-plan logic over a shared :class:`WindowStore` — a Redis-backed
counter (:class:`RedisWindowStore`) in production, an in-process
:class:`InMemoryWindowStore` for tests/single-node. It is a drop-in behind the
same ``check(tenant) -> RateLimitDecision`` contract (ADR-118); the tenant
middleware awaits the result when it is a coroutine, so either limiter slots in
without further change. ``redis`` is lazy-imported behind the ``[redis]`` extra,
so importing this module never requires it.

The clock is injectable (``time.monotonic`` by default) so the window logic is
deterministic under test. The in-process store is plain stdlib — no extra — and
its check is a single synchronous critical section (no ``await`` inside), so it
is atomic on the cooperative event loop without a lock.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

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


# --------------------------------------------------------------------------
# Distributed (shared-store) limiter — globally-exact across replicas (ADR-118)
# --------------------------------------------------------------------------
class WindowStore(Protocol):
    """A shared fixed-window counter keyed by tenant.

    :meth:`hit` atomically increments the counter for ``key`` within the current
    window and returns ``(count_after_increment, seconds_until_reset)``.
    """

    async def hit(self, key: str, window_seconds: float) -> tuple[int, int]: ...


class InMemoryWindowStore:
    """Async, single-process :class:`WindowStore` — tests and single-node use.

    Counts every hit (including ones the limiter will reject), matching the
    Redis store's semantics, so the two are interchangeable in tests.
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._buckets: dict[str, tuple[float, int]] = {}

    async def hit(self, key: str, window_seconds: float) -> tuple[int, int]:
        now = self._clock()
        start, count = self._buckets.get(key, (now, 0))
        elapsed = now - start
        if elapsed >= window_seconds:
            start, count = now, 0
            elapsed = 0.0
        count += 1
        self._buckets[key] = (start, count)
        reset_after = max(int(round(window_seconds - elapsed)), 0)
        return count, reset_after

    async def reset(self, key: str | None = None) -> None:
        if key is None:
            self._buckets.clear()
        else:
            self._buckets.pop(key, None)


class RedisWindowStore:
    """Redis-backed :class:`WindowStore` — globally exact across replicas.

    Uses the canonical fixed-window pattern: ``INCR`` the per-tenant key, set an
    ``EXPIRE`` on the first hit of a window, and read the remaining ``TTL``.
    ``redis.asyncio`` is imported lazily (the ``[redis]`` extra); a client may be
    injected for tests.
    """

    def __init__(self, url: str = "", *, client: Any = None, key_prefix: str = "uiao:rl:") -> None:
        self._url = url
        self._client = client
        self._prefix = key_prefix

    def _redis(self) -> Any:
        if self._client is None:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]  # lazy: [redis] extra

            self._client = aioredis.from_url(self._url)
        return self._client

    async def hit(self, key: str, window_seconds: float) -> tuple[int, int]:
        r = self._redis()
        full_key = f"{self._prefix}{key}"
        window = int(math.ceil(window_seconds))
        count = int(await r.incr(full_key))
        if count == 1:
            await r.expire(full_key, window)
            ttl = window
        else:
            ttl = int(await r.ttl(full_key))
            if ttl < 0:  # key without TTL (lost EXPIRE) — re-arm defensively
                await r.expire(full_key, window)
                ttl = window
        return count, ttl


class DistributedTenantRateLimiter:
    """Enforce each tenant's per-plan budget over a shared :class:`WindowStore`.

    Same contract as :class:`TenantRateLimiter` (``check(tenant)`` →
    :class:`RateLimitDecision`) but **async**, so the count is exact across all
    replicas sharing the store. Unlimited plans short-circuit without touching
    the store.
    """

    def __init__(
        self,
        store: WindowStore,
        *,
        quotas: dict[TenantPlan, PlanQuota] | None = None,
        window_seconds: float = 60.0,
    ) -> None:
        self._store = store
        self._quotas = quotas if quotas is not None else DEFAULT_QUOTAS
        self._window = float(window_seconds)

    def quota(self, plan: TenantPlan) -> PlanQuota:
        return quota_for(plan, quotas=self._quotas)

    async def check(self, tenant: Tenant) -> RateLimitDecision:
        quota = self.quota(tenant.plan)
        if quota.unlimited_rate:
            return RateLimitDecision(allowed=True, limit=0, remaining=0, reset_after=0)
        limit = quota.window_limit
        count, reset_after = await self._store.hit(tenant.tenant_id, self._window)
        if count > limit:
            return RateLimitDecision(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_after=reset_after,
                retry_after=max(reset_after, 1),
            )
        return RateLimitDecision(
            allowed=True,
            limit=limit,
            remaining=limit - count,
            reset_after=reset_after,
        )


__all__ = [
    "RateLimitDecision",
    "FixedWindowRateLimiter",
    "TenantRateLimiter",
    "WindowStore",
    "InMemoryWindowStore",
    "RedisWindowStore",
    "DistributedTenantRateLimiter",
]
