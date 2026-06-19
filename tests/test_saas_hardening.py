"""Integration tests for the SaaS hardening layer: RFC 9457 problem+json,
per-plan rate limiting, the audit endpoint, and the readiness probe.

Uses the FastAPI TestClient with an in-memory repository and unsigned-token
mode (no network / crypto / database).
"""

from __future__ import annotations

import base64
import json
import time

import pytest

pytest.importorskip("httpx")
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from uiao.saas import InMemoryTenantRepository, TenantRateLimiter, attach_saas  # noqa: E402
from uiao.saas.errors import PROBLEM_MEDIA_TYPE  # noqa: E402
from uiao.saas.quotas import quota_for  # noqa: E402
from uiao.saas.settings import SaasSettings  # noqa: E402
from uiao.saas.tenant import Tenant, TenantPlan, TenantStatus  # noqa: E402

TENANT = "12345678-1234-1234-1234-1234567890ab"
PUBLISHER = "aaaaaaaa-1111-2222-3333-444444444444"
AUD = "api://uiao"


def _token(tid: str, *, roles=None) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = {
        "tid": tid,
        "aud": AUD,
        "iss": f"https://login.microsoftonline.com/{tid}/v2.0",
        "oid": "caller",
        "exp": time.time() + 3600,
    }
    if roles:
        payload["roles"] = roles
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"


def _bearer(tid: str, **kw) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(tid, **kw)}"}


def _settings(**overrides) -> SaasSettings:
    base = dict(
        api_audience=AUD,
        publisher_tenant_id=PUBLISHER,
        app_client_id="client-123",
        insecure_allow_unsigned_tokens=True,
        provisioning_enabled=True,
    )
    base.update(overrides)
    return SaasSettings(**base)


def _make_client(repo, *, settings=None, rate_limiter=None) -> TestClient:
    app = FastAPI()

    @app.get("/api/v1/ping")
    async def ping(request: Request) -> dict[str, str]:
        return {"tenant": request.state.tenant.tenant_id}

    attach_saas(app, settings=settings or _settings(), repository=repo, rate_limiter=rate_limiter)
    return TestClient(app, raise_server_exceptions=True)


# --------------------------------------------------------------------------
# RFC 9457 problem+json
# --------------------------------------------------------------------------
def test_data_plane_error_is_problem_json():
    client = _make_client(InMemoryTenantRepository())
    resp = client.get("/api/v1/ping", headers=_bearer(TENANT))
    assert resp.status_code == 403
    assert resp.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = resp.json()
    assert body["status"] == 403
    assert body["title"] == "Forbidden"
    assert body["error"] == "tenant_not_onboarded"  # stable machine code preserved
    assert body["instance"] == "/api/v1/ping"
    assert body["tenant"] == TENANT


def test_control_plane_error_is_problem_json():
    client = _make_client(InMemoryTenantRepository())
    admin = _bearer(PUBLISHER, roles=["UIAO.SaaS.Admin"])
    resp = client.get(f"/control/v1/tenants/{TENANT}", headers=admin)
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = resp.json()
    assert body["status"] == 404
    assert body["error"] == "not_found"
    assert "instance" in body


def test_missing_bearer_is_problem_json_401():
    client = _make_client(InMemoryTenantRepository())
    resp = client.get("/api/v1/ping")
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


# --------------------------------------------------------------------------
# Per-plan rate limiting
# --------------------------------------------------------------------------
class _Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def _active(plan: TenantPlan) -> InMemoryTenantRepository:
    return InMemoryTenantRepository([Tenant(tenant_id=TENANT, plan=plan).with_status(TenantStatus.ACTIVE)])


def test_rate_limit_blocks_after_budget_and_sets_headers():
    clock = _Clock()
    limiter = TenantRateLimiter(window_seconds=60, clock=clock)
    repo = _active(TenantPlan.TRIAL)
    client = _make_client(repo, rate_limiter=limiter)

    budget = quota_for(TenantPlan.TRIAL).window_limit
    last = None
    for _ in range(budget):
        last = client.get("/api/v1/ping", headers=_bearer(TENANT))
        assert last.status_code == 200
    assert last.headers["RateLimit-Limit"] == str(budget)

    blocked = client.get("/api/v1/ping", headers=_bearer(TENANT))
    assert blocked.status_code == 429
    assert blocked.json()["error"] == "rate_limited"
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.headers["RateLimit-Remaining"] == "0"

    # Advancing past the window restores the budget.
    clock.t += 61
    assert client.get("/api/v1/ping", headers=_bearer(TENANT)).status_code == 200


def test_rate_limit_headers_on_success():
    client = _make_client(_active(TenantPlan.STANDARD), rate_limiter=TenantRateLimiter(clock=_Clock()))
    resp = client.get("/api/v1/ping", headers=_bearer(TENANT))
    assert resp.status_code == 200
    assert "RateLimit-Remaining" in resp.headers


def test_rate_limiting_disabled_when_no_limiter():
    # settings.rate_limiting_enabled drives auto-construction; pass it off and
    # inject nothing → no limiter, unlimited requests.
    repo = _active(TenantPlan.TRIAL)
    client = _make_client(repo, settings=_settings(rate_limiting_enabled=False))
    for _ in range(quota_for(TenantPlan.TRIAL).window_limit + 10):
        assert client.get("/api/v1/ping", headers=_bearer(TENANT)).status_code == 200


# --------------------------------------------------------------------------
# Audit endpoint
# --------------------------------------------------------------------------
def test_audit_endpoint_lists_lifecycle_events():
    client = _make_client(InMemoryTenantRepository())
    admin = _bearer(PUBLISHER, roles=["UIAO.SaaS.Admin"])
    client.post("/control/v1/tenants", json={"tenant_id": TENANT, "display_name": "Acme"}, headers=admin)
    client.post(f"/control/v1/tenants/{TENANT}/suspend", json={"reason": "billing"}, headers=admin)

    resp = client.get("/control/v1/audit", headers=admin)
    assert resp.status_code == 200
    events = resp.json()
    assert {e["action"] for e in events} == {"onboard", "suspend"}
    assert all(e["actor"] for e in events)  # admin subject recorded

    scoped = client.get("/control/v1/audit", params={"tenant_id": TENANT}, headers=admin)
    assert all(e["tenant_id"] == TENANT for e in scoped.json())


def test_audit_endpoint_requires_admin():
    client = _make_client(InMemoryTenantRepository())
    assert client.get("/control/v1/audit", headers=_bearer(PUBLISHER)).status_code == 403


# --------------------------------------------------------------------------
# Readiness probe
# --------------------------------------------------------------------------
def test_readyz_ok():
    client = _make_client(InMemoryTenantRepository())
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_readyz_degraded_when_registry_unreachable():
    class _BrokenRepo(InMemoryTenantRepository):
        async def ping(self) -> bool:
            return False

    client = _make_client(_BrokenRepo())
    resp = client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"
