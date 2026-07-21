"""Route-level auth posture for the FastAPI app (repo-review round 2).

Two hardening changes are pinned here:

1. The FedRAMP router (`/api/v1/fedramp`) carries the shared fail-closed
   bearer gate (`require_auditor`) at the mount, like `/api/auditor`.
2. The IIS Windows-identity headers (`X-IIS-WindowsAuthUser`,
   `Remote-User`, `X-Auth-User`) are client-forgeable and must be
   ignored unless the deployment opts in via
   ``UIAO_API_WINDOWS_AUTH_TRUSTED`` (set by
   deploy/windows-server/web.config, where IIS owns every request).
   Without the opt-in, a forged header must NOT authenticate.

The lifespan is intentionally not entered (no ``with`` block): startup
needs live Entra configuration these tests don't have and don't need.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("msal")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from uiao.api.app import app  # noqa: E402

FORGED_IIS_HEADERS = {"X-IIS-WindowsAuthUser": "CORP\\forged-admin"}
SURVEY_BODY = {"ldap_server": "dc01.example.gov", "base_dn": "DC=example,DC=gov"}


@pytest.fixture
def client() -> TestClient:
    # raise_server_exceptions=False: handlers that need lifespan state
    # (e.g. /health reads app.state.token_provider) 500 instead of
    # erroring the test — these tests only discriminate 401 vs not-401.
    return TestClient(app, raise_server_exceptions=False)


def test_health_stays_anonymous(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code != 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/fedramp/status",
        "/api/v1/fedramp/ksi/completeness",
        "/api/v1/fedramp/evidence",
        "/api/v1/fedramp/drift",
    ],
)
def test_fedramp_gets_require_bearer(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 401, path


def test_fedramp_dryrun_requires_bearer(client: TestClient) -> None:
    response = client.post("/api/v1/fedramp/dryrun")
    assert response.status_code == 401


def test_fedramp_accepts_a_dev_bearer(client: TestClient, monkeypatch) -> None:
    """conftest defaults UIAO_API_AUTH_MODE=insecure-dev; the gate must
    pass a non-empty bearer through to the handler (any non-401 outcome —
    the handler itself may still 4xx/5xx on missing evidence dirs)."""
    monkeypatch.setenv("UIAO_API_AUTH_MODE", "insecure-dev")
    response = client.get(
        "/api/v1/fedramp/status",
        headers={"Authorization": "Bearer dev-token"},
    )
    assert response.status_code != 401


def test_survey_rejects_forged_iis_headers_by_default(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("UIAO_API_WINDOWS_AUTH_TRUSTED", raising=False)
    monkeypatch.delenv("REMOTE_USER", raising=False)
    response = client.post(
        "/api/v1/survey/run",
        json=SURVEY_BODY,
        headers=FORGED_IIS_HEADERS,
    )
    assert response.status_code == 401


def test_survey_honors_headers_only_when_deployment_opts_in(client: TestClient, monkeypatch) -> None:
    """With the IIS opt-in set, the same header authenticates (the request
    then proceeds to the LDAP layer, which fails for other reasons here —
    anything but 401 proves the auth layer accepted the identity)."""
    monkeypatch.setenv("UIAO_API_WINDOWS_AUTH_TRUSTED", "1")
    response = client.post(
        "/api/v1/survey/run",
        json=SURVEY_BODY,
        headers=FORGED_IIS_HEADERS,
    )
    assert response.status_code != 401
