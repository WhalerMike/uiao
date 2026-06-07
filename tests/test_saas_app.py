"""Integration tests: tenant-resolution middleware + control-plane API.

Uses the FastAPI TestClient with an in-memory repository and unsigned-token
mode so no network / crypto / database is required.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

pytest.importorskip("httpx")
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from uiao.saas import InMemoryTenantRepository, attach_saas  # noqa: E402
from uiao.saas.settings import SaasSettings  # noqa: E402
from uiao.saas.tenant import Tenant, TenantStatus  # noqa: E402

TENANT = "12345678-1234-1234-1234-1234567890ab"
PUBLISHER = "aaaaaaaa-1111-2222-3333-444444444444"
AUD = "api://uiao"


def _token(tid: str, *, roles=None, exp_offset=3600) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = {
        "tid": tid,
        "aud": AUD,
        "iss": f"https://login.microsoftonline.com/{tid}/v2.0",
        "oid": "caller",
        "exp": time.time() + exp_offset,
    }
    if roles:
        payload["roles"] = roles
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"


def _bearer(tid: str, **kw) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(tid, **kw)}"}


def _settings() -> SaasSettings:
    return SaasSettings(
        api_audience=AUD,
        publisher_tenant_id=PUBLISHER,
        app_client_id="client-123",
        insecure_allow_unsigned_tokens=True,
        provisioning_enabled=True,
    )


def _make_client(repo: InMemoryTenantRepository) -> TestClient:
    app = FastAPI()

    @app.get("/api/v1/ping")
    async def ping(request: Request) -> dict[str, str]:
        return {"tenant": request.state.tenant.tenant_id}

    attach_saas(app, settings=_settings(), repository=repo)
    return TestClient(app)


# --------------------------------------------------------------------------
# Data-plane tenant resolution
# --------------------------------------------------------------------------
def test_healthz_is_public():
    client = _make_client(InMemoryTenantRepository())
    assert client.get("/healthz").status_code == 200


def test_no_token_is_401():
    client = _make_client(InMemoryTenantRepository())
    assert client.get("/api/v1/ping").status_code == 401


def test_unknown_tenant_is_403():
    client = _make_client(InMemoryTenantRepository())
    resp = client.get("/api/v1/ping", headers=_bearer(TENANT))
    assert resp.status_code == 403
    assert resp.json()["error"] == "tenant_not_onboarded"


def test_suspended_tenant_is_403():
    repo = InMemoryTenantRepository(
        [Tenant(tenant_id=TENANT).with_status(TenantStatus.ACTIVE).with_status(TenantStatus.SUSPENDED, reason="x")]
    )
    client = _make_client(repo)
    resp = client.get("/api/v1/ping", headers=_bearer(TENANT))
    assert resp.status_code == 403
    assert resp.json()["error"] == "tenant_not_active"


def test_active_tenant_resolves():
    repo = InMemoryTenantRepository([Tenant(tenant_id=TENANT).with_status(TenantStatus.ACTIVE)])
    client = _make_client(repo)
    resp = client.get("/api/v1/ping", headers=_bearer(TENANT))
    assert resp.status_code == 200
    assert resp.json()["tenant"] == TENANT
    assert resp.headers["x-uiao-tenant"] == TENANT


# --------------------------------------------------------------------------
# Control plane
# --------------------------------------------------------------------------
def test_control_requires_admin_role():
    client = _make_client(InMemoryTenantRepository())
    # publisher tenant token WITHOUT the admin role
    resp = client.post("/control/v1/tenants", json={"tenant_id": TENANT}, headers=_bearer(PUBLISHER))
    assert resp.status_code == 403


def test_control_rejects_non_publisher():
    client = _make_client(InMemoryTenantRepository())
    resp = client.post(
        "/control/v1/tenants",
        json={"tenant_id": TENANT},
        headers=_bearer(TENANT, roles=["UIAO.SaaS.Admin"]),
    )
    assert resp.status_code == 401  # not from publisher tenant -> allowlist reject


def test_onboard_then_lifecycle():
    repo = InMemoryTenantRepository()
    client = _make_client(repo)
    admin = _bearer(PUBLISHER, roles=["UIAO.SaaS.Admin"])

    # Onboard
    resp = client.post("/control/v1/tenants", json={"tenant_id": TENANT, "display_name": "Acme"}, headers=admin)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["tenant"]["status"] == "active"
    assert "adminconsent" in body["admin_consent_url"]
    assert body["stamp_steps"]

    # Duplicate onboard -> 409
    assert client.post("/control/v1/tenants", json={"tenant_id": TENANT}, headers=admin).status_code == 409

    # List + get
    assert len(client.get("/control/v1/tenants", headers=admin).json()) == 1
    assert client.get(f"/control/v1/tenants/{TENANT}", headers=admin).json()["tenant_id"] == TENANT

    # Suspend -> data plane blocked
    assert (
        client.post(f"/control/v1/tenants/{TENANT}/suspend", json={"reason": "billing"}, headers=admin).status_code
        == 200
    )

    # Resume
    assert client.post(f"/control/v1/tenants/{TENANT}/resume", json={}, headers=admin).json()["status"] == "active"

    # Deprovision
    dep = client.request("DELETE", f"/control/v1/tenants/{TENANT}", headers=admin)
    assert dep.status_code == 200
    assert client.get(f"/control/v1/tenants/{TENANT}", headers=admin).json()["status"] == "deprovisioned"


def test_get_missing_tenant_404():
    client = _make_client(InMemoryTenantRepository())
    admin = _bearer(PUBLISHER, roles=["UIAO.SaaS.Admin"])
    assert client.get(f"/control/v1/tenants/{TENANT}", headers=admin).status_code == 404
