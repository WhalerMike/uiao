"""Tests for the shared fail-closed bearer auth dependency (routes/_auth.py)."""

from __future__ import annotations

import base64
import json
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import uiao.api.routes._auth as auth_mod
from uiao.saas.auth import EntraTokenVerifier

TENANT = "11111111-2222-3333-4444-555555555555"
AUDIENCE = "api://uiao-governance"


def _b64url(obj: dict) -> str:
    raw = json.dumps(obj).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _jwt(payload: dict) -> str:
    return f"{_b64url({'alg': 'RS256', 'typ': 'JWT'})}.{_b64url(payload)}.fakesig"


def _claims(**overrides) -> dict:
    payload = {
        "tid": TENANT,
        "aud": AUDIENCE,
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "exp": time.time() + 3600,
        "sub": "subject-guid",
        "oid": "object-guid",
    }
    payload.update(overrides)
    return payload


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def entra_mode(monkeypatch):
    monkeypatch.setenv("UIAO_API_AUTH_MODE", "entra")
    monkeypatch.delenv("UIAO_API_AUTH_AUDIENCE", raising=False)
    monkeypatch.delenv("UIAO_API_AUTH_REQUIRED_ROLES", raising=False)


@pytest.fixture
def unsigned_verifier(monkeypatch, entra_mode):
    """Inject a claims-only verifier so tests never hit the network JWKS path."""
    verifier = EntraTokenVerifier(audience=AUDIENCE, insecure_allow_unsigned=True)
    monkeypatch.setattr(auth_mod, "_build_verifier", lambda: verifier)
    return verifier


class TestFailClosedDefaults:
    def test_missing_credentials_is_401(self):
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(None)
        assert exc.value.status_code == 401

    def test_entra_is_the_default_mode(self, monkeypatch):
        monkeypatch.delenv("UIAO_API_AUTH_MODE", raising=False)
        monkeypatch.delenv("UIAO_API_AUTH_AUDIENCE", raising=False)
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds("anything"))
        assert exc.value.status_code == 503  # unconfigured, not silently accepted

    def test_unconfigured_audience_is_503(self, entra_mode):
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds(_jwt(_claims())))
        assert exc.value.status_code == 503
        assert "UIAO_API_AUTH_AUDIENCE" in exc.value.detail

    def test_opaque_token_is_401_not_auditor(self, entra_mode, monkeypatch):
        monkeypatch.setenv("UIAO_API_AUTH_AUDIENCE", AUDIENCE)
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds("not-a-jwt"))
        assert exc.value.status_code == 401

    def test_unknown_mode_is_503(self, monkeypatch):
        monkeypatch.setenv("UIAO_API_AUTH_MODE", "bogus")
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds("token"))
        assert exc.value.status_code == 503


class TestEntraClaimsPath:
    def test_valid_claims_return_subject(self, unsigned_verifier):
        subject = auth_mod.require_auditor(_creds(_jwt(_claims())))
        assert subject == "object-guid"  # oid preferred over sub

    def test_expired_token_is_401(self, unsigned_verifier):
        token = _jwt(_claims(exp=time.time() - 3600))
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds(token))
        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail

    def test_wrong_audience_is_401(self, unsigned_verifier):
        token = _jwt(_claims(aud="api://someone-else"))
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds(token))
        assert exc.value.status_code == 401

    def test_missing_tenant_is_401(self, unsigned_verifier):
        payload = _claims()
        del payload["tid"]
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds(_jwt(payload)))
        assert exc.value.status_code == 401

    def test_wrong_issuer_is_401(self, unsigned_verifier):
        token = _jwt(_claims(iss="https://evil.example.com/v2.0"))
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds(token))
        assert exc.value.status_code == 401


class TestRoleEnforcement:
    def test_required_role_present_passes(self, unsigned_verifier, monkeypatch):
        monkeypatch.setenv("UIAO_API_AUTH_REQUIRED_ROLES", "UIAO.Viewer,UIAO.Auditor")
        token = _jwt(_claims(roles=["UIAO.Auditor"]))
        assert auth_mod.require_auditor(_creds(token)) == "object-guid"

    def test_required_role_missing_is_403(self, unsigned_verifier, monkeypatch):
        monkeypatch.setenv("UIAO_API_AUTH_REQUIRED_ROLES", "UIAO.Auditor")
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds(_jwt(_claims())))
        assert exc.value.status_code == 403


class TestInsecureDevMode:
    def test_opaque_token_accepted(self, monkeypatch):
        monkeypatch.setenv("UIAO_API_AUTH_MODE", "insecure-dev")
        assert auth_mod.require_auditor(_creds("test-token")) == "auditor"

    def test_jwt_subject_extracted(self, monkeypatch):
        monkeypatch.setenv("UIAO_API_AUTH_MODE", "insecure-dev")
        assert auth_mod.require_auditor(_creds(_jwt(_claims(sub="dev-user")))) == "dev-user"


class TestTenantAllowlist:
    def test_disallowed_tenant_is_401(self, entra_mode, monkeypatch):
        verifier = EntraTokenVerifier(
            audience=AUDIENCE,
            allowed_tenants={"99999999-0000-0000-0000-000000000000"},
            insecure_allow_unsigned=True,
        )
        monkeypatch.setattr(auth_mod, "_build_verifier", lambda: verifier)
        with pytest.raises(HTTPException) as exc:
            auth_mod.require_auditor(_creds(_jwt(_claims())))
        assert exc.value.status_code == 401
        assert "allowlist" in exc.value.detail
