"""Unit tests for per-plan quotas and the tenant rate limiter.

Pure stdlib + pydantic — no FastAPI / network / database. The limiter clock is
injected so window expiry is deterministic.
"""

from __future__ import annotations

from uiao.saas.quotas import DEFAULT_QUOTAS, FALLBACK_QUOTA, PlanQuota, quota_for
from uiao.saas.ratelimit import FixedWindowRateLimiter, TenantRateLimiter
from uiao.saas.tenant import Tenant, TenantPlan, TenantStatus

TENANT = "12345678-1234-1234-1234-1234567890ab"


# --------------------------------------------------------------------------
# Quotas
# --------------------------------------------------------------------------
def test_every_plan_has_a_quota():
    for plan in TenantPlan:
        assert isinstance(quota_for(plan), PlanQuota)


def test_quota_ordering_is_monotonic():
    trial = quota_for(TenantPlan.TRIAL).requests_per_minute
    standard = quota_for(TenantPlan.STANDARD).requests_per_minute
    enterprise = quota_for(TenantPlan.ENTERPRISE).requests_per_minute
    assert trial < standard < enterprise


def test_window_limit_is_rate_plus_burst():
    q = quota_for(TenantPlan.TRIAL)
    assert q.window_limit == q.requests_per_minute + q.burst


def test_fallback_is_trial_for_unknown_plan():
    assert quota_for(TenantPlan.TRIAL, quotas={}) is FALLBACK_QUOTA


def test_unlimited_rate_flag():
    assert not quota_for(TenantPlan.TRIAL).unlimited_rate
    assert PlanQuota(0, 0, 1, 1).unlimited_rate


# --------------------------------------------------------------------------
# FixedWindowRateLimiter
# --------------------------------------------------------------------------
class _Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_fixed_window_admits_up_to_limit_then_blocks():
    clock = _Clock()
    rl = FixedWindowRateLimiter(window_seconds=60, clock=clock)
    for i in range(3):
        d = rl.check("k", limit=3)
        assert d.allowed
        assert d.remaining == 2 - i
    blocked = rl.check("k", limit=3)
    assert not blocked.allowed
    assert blocked.remaining == 0
    assert blocked.retry_after >= 1


def test_fixed_window_resets_after_window():
    clock = _Clock()
    rl = FixedWindowRateLimiter(window_seconds=60, clock=clock)
    rl.check("k", limit=1)
    assert not rl.check("k", limit=1).allowed
    clock.t += 61  # advance past the window
    assert rl.check("k", limit=1).allowed


def test_zero_limit_is_unlimited():
    rl = FixedWindowRateLimiter(window_seconds=60, clock=_Clock())
    for _ in range(1000):
        assert rl.check("k", limit=0).allowed


def test_keys_are_isolated():
    rl = FixedWindowRateLimiter(window_seconds=60, clock=_Clock())
    rl.check("a", limit=1)
    assert not rl.check("a", limit=1).allowed
    assert rl.check("b", limit=1).allowed  # different key unaffected


def test_decision_headers():
    rl = FixedWindowRateLimiter(window_seconds=60, clock=_Clock())
    d = rl.check("k", limit=5)
    h = d.headers()
    assert h["RateLimit-Limit"] == "5"
    assert h["RateLimit-Remaining"] == "4"
    assert "Retry-After" not in h
    # Exhaust and confirm Retry-After appears on the blocked decision.
    for _ in range(4):
        rl.check("k", limit=5)
    assert "Retry-After" in rl.check("k", limit=5).headers()


# --------------------------------------------------------------------------
# TenantRateLimiter (plan-aware)
# --------------------------------------------------------------------------
def _tenant(plan: TenantPlan) -> Tenant:
    return Tenant(tenant_id=TENANT, plan=plan).with_status(TenantStatus.ACTIVE)


def test_tenant_limiter_uses_plan_window_limit():
    clock = _Clock()
    trl = TenantRateLimiter(window_seconds=60, clock=clock)
    tenant = _tenant(TenantPlan.TRIAL)
    limit = quota_for(TenantPlan.TRIAL).window_limit
    allowed = sum(1 for _ in range(limit) if trl.check(tenant).allowed)
    assert allowed == limit
    assert not trl.check(tenant).allowed


def test_tenant_limiter_unlimited_plan_passes(monkeypatch):
    # Build a custom table where ENTERPRISE is unlimited.
    quotas = dict(DEFAULT_QUOTAS)
    quotas[TenantPlan.ENTERPRISE] = PlanQuota(0, 0, 99, 99)
    trl = TenantRateLimiter(quotas=quotas, window_seconds=60, clock=_Clock())
    tenant = _tenant(TenantPlan.ENTERPRISE)
    for _ in range(10_000):
        assert trl.check(tenant).allowed


def test_tenant_limiter_reset():
    trl = TenantRateLimiter(window_seconds=60, clock=_Clock())
    tenant = _tenant(TenantPlan.TRIAL)
    for _ in range(quota_for(TenantPlan.TRIAL).window_limit):
        trl.check(tenant)
    assert not trl.check(tenant).allowed
    trl.reset(tenant.tenant_id)
    assert trl.check(tenant).allowed
