"""Unit tests for the distributed (shared-store) rate limiter (ADR-118).

Pure stdlib — the window store is in-process with an injected clock, so no
Redis is needed. Mirrors test_saas_quotas' coverage of the in-process limiter.
"""

from __future__ import annotations

import asyncio

from uiao.saas.quotas import quota_for
from uiao.saas.ratelimit import DistributedTenantRateLimiter, InMemoryWindowStore, PlanQuota
from uiao.saas.tenant import Tenant, TenantPlan, TenantStatus

TENANT = "12345678-1234-1234-1234-1234567890ab"


def _run(coro):
    return asyncio.run(coro)


class _Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def _tenant(plan: TenantPlan) -> Tenant:
    return Tenant(tenant_id=TENANT, plan=plan).with_status(TenantStatus.ACTIVE)


# --------------------------------------------------------------------------
# InMemoryWindowStore
# --------------------------------------------------------------------------
def test_window_store_counts_and_resets():
    clock = _Clock()
    store = InMemoryWindowStore(clock=clock)
    c1, _ = _run(store.hit("k", 60))
    c2, reset = _run(store.hit("k", 60))
    assert (c1, c2) == (1, 2)
    assert 0 < reset <= 60
    clock.t += 61  # window elapses
    c3, _ = _run(store.hit("k", 60))
    assert c3 == 1  # fresh window


def test_window_store_keys_isolated():
    store = InMemoryWindowStore(clock=_Clock())
    _run(store.hit("a", 60))
    cb, _ = _run(store.hit("b", 60))
    assert cb == 1


# --------------------------------------------------------------------------
# DistributedTenantRateLimiter
# --------------------------------------------------------------------------
def test_allows_up_to_window_limit_then_blocks():
    clock = _Clock()
    rl = DistributedTenantRateLimiter(InMemoryWindowStore(clock=clock), window_seconds=60)
    tenant = _tenant(TenantPlan.TRIAL)
    limit = quota_for(TenantPlan.TRIAL).window_limit

    allowed = 0
    last = None
    for _ in range(limit):
        last = _run(rl.check(tenant))
        assert last.allowed
        allowed += 1
    assert allowed == limit
    assert last.limit == limit and last.remaining == 0

    blocked = _run(rl.check(tenant))
    assert not blocked.allowed
    assert blocked.remaining == 0
    assert blocked.retry_after >= 1


def test_window_reset_restores_budget():
    clock = _Clock()
    rl = DistributedTenantRateLimiter(InMemoryWindowStore(clock=clock), window_seconds=60)
    tenant = _tenant(TenantPlan.TRIAL)
    for _ in range(quota_for(TenantPlan.TRIAL).window_limit):
        _run(rl.check(tenant))
    assert not _run(rl.check(tenant)).allowed
    clock.t += 61
    assert _run(rl.check(tenant)).allowed


def test_unlimited_plan_never_touches_store():
    class _ExplodingStore:
        async def hit(self, key, window_seconds):  # pragma: no cover - must not run
            raise AssertionError("unlimited plan must not hit the store")

    quotas = dict.fromkeys(TenantPlan, PlanQuota(0, 0, 1, 1))  # all unlimited
    rl = DistributedTenantRateLimiter(_ExplodingStore(), quotas=quotas)
    assert _run(rl.check(_tenant(TenantPlan.ENTERPRISE))).allowed


def test_remaining_decrements():
    rl = DistributedTenantRateLimiter(InMemoryWindowStore(clock=_Clock()), window_seconds=60)
    tenant = _tenant(TenantPlan.STANDARD)
    limit = quota_for(TenantPlan.STANDARD).window_limit
    first = _run(rl.check(tenant))
    second = _run(rl.check(tenant))
    assert first.remaining == limit - 1
    assert second.remaining == limit - 2
