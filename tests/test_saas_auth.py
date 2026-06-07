"""Unit tests for inbound Entra token claim verification.

Signature verification is exercised via the ``insecure_allow_unsigned`` path
and an injected fake verifier — the JWKS/PyJWT path needs network + crypto
and is covered by integration, not unit, tests.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from uiao.saas.auth import EntraTokenVerifier, TokenError

GUID = "12345678-1234-1234-1234-1234567890ab"
AUD = "api://uiao"
ISS = f"https://login.microsoftonline.com/{GUID}/v2.0"


def _segment(obj: dict) -> str:
    raw = json.dumps(obj).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _make_token(**claims) -> str:
    header = _segment({"alg": "none", "typ": "JWT"})
    payload = _segment(claims)
    return f"{header}.{payload}.sig"


def _valid_claims(**overrides) -> dict:
    base = {
        "tid": GUID,
        "aud": AUD,
        "iss": ISS,
        "oid": "user-oid",
        "exp": time.time() + 3600,
        "scp": "Governance.Read Governance.Write",
        "roles": ["UIAO.SaaS.Admin"],
    }
    base.update(overrides)
    return base


def _verifier(**kwargs) -> EntraTokenVerifier:
    defaults = dict(audience=AUD, insecure_allow_unsigned=True)
    defaults.update(kwargs)
    return EntraTokenVerifier(**defaults)


def test_valid_token_parses_claims():
    claims = _verifier().verify(_make_token(**_valid_claims()))
    assert claims.tenant_id == GUID
    assert claims.subject == "user-oid"
    assert "Governance.Read" in claims.scopes
    assert "UIAO.SaaS.Admin" in claims.roles
    assert "UIAO.SaaS.Admin" in claims.principal_scopes


def test_missing_tid_rejected():
    with pytest.raises(TokenError):
        _verifier().verify(_make_token(**_valid_claims(tid="")))


def test_expired_token_rejected():
    with pytest.raises(TokenError):
        _verifier().verify(_make_token(**_valid_claims(exp=time.time() - 3600)))


def test_wrong_audience_rejected():
    with pytest.raises(TokenError):
        _verifier().verify(_make_token(**_valid_claims(aud="api://other")))


def test_wrong_issuer_rejected():
    with pytest.raises(TokenError):
        _verifier().verify(_make_token(**_valid_claims(iss="https://evil.example/v2.0")))


def test_tenant_not_in_allowlist_rejected():
    v = _verifier(allowed_tenants={"99999999-1234-1234-1234-1234567890ab"})
    with pytest.raises(TokenError):
        v.verify(_make_token(**_valid_claims()))


def test_unsigned_rejected_when_not_insecure():
    v = EntraTokenVerifier(audience=AUD, insecure_allow_unsigned=False)
    with pytest.raises(TokenError):
        v.verify(_make_token(**_valid_claims()))


def test_injected_signature_verifier_is_used():
    seen = {}

    def fake(token, *, tenant_id, audience):
        seen["called"] = True
        return _valid_claims()

    v = EntraTokenVerifier(audience=AUD, signature_verifier=fake)
    claims = v.verify(_make_token(**_valid_claims()))
    assert seen.get("called")
    assert claims.tenant_id == GUID


def test_malformed_token_rejected():
    with pytest.raises(TokenError):
        _verifier().verify("not-a-jwt")


def test_unknown_cloud_rejected():
    with pytest.raises(ValueError):
        EntraTokenVerifier(audience=AUD, cloud="mars")
