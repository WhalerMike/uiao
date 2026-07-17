"""Shared bearer-token auth dependency for the governance / auditor routers.

Verification is fail-closed and mode-selected via ``UIAO_API_AUTH_MODE``:

- ``entra`` (default) — the token must be a valid Entra ID JWT: RS256
  signature against the issuing tenant's JWKS, plus ``exp``/``nbf``/``aud``/
  ``iss``/``tid`` claim checks, all delegated to
  :class:`uiao.saas.auth.EntraTokenVerifier`. Server-side configuration:

  - ``UIAO_API_AUTH_AUDIENCE`` (required) — the API's App ID URI / audience.
  - ``UIAO_API_AUTH_TENANTS`` (optional) — comma-separated tenant-id
    allowlist; unset accepts any tenant that passes issuer validation.
  - ``UIAO_API_AUTH_CLOUD`` (optional) — ``commercial`` (default, also
    serves GCC-Moderate per ADR-033), ``gcc-high``, or ``dod``.
  - ``UIAO_API_AUTH_REQUIRED_ROLES`` (optional) — comma-separated app
    roles (e.g. ``UIAO.Viewer,UIAO.Auditor``); when set, the token must
    carry at least one, else 403.

  Missing configuration is a 503, an unverifiable token is a 401 — never a
  silent pass-through.

- ``insecure-dev`` — accepts any non-empty bearer token (the pre-hardening
  development behavior). Must be opted into explicitly; local dev and the
  test suite only.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from uiao.saas.auth import (
    EntraTokenVerifier,
    SignatureVerifier,
    TokenError,
    decode_unverified_claims,
)

_bearer = HTTPBearer(auto_error=False)

_MODE_ENV = "UIAO_API_AUTH_MODE"
_AUDIENCE_ENV = "UIAO_API_AUTH_AUDIENCE"
_TENANTS_ENV = "UIAO_API_AUTH_TENANTS"
_CLOUD_ENV = "UIAO_API_AUTH_CLOUD"
_ROLES_ENV = "UIAO_API_AUTH_REQUIRED_ROLES"

_verifier_cache: dict[tuple[str, str, str], EntraTokenVerifier] = {}


def _lazy_jwks(cloud: str) -> SignatureVerifier:
    """JWKS verifier that defers the PyJWT import until first verification.

    Keeps ``uiao.api`` importable without ``pyjwt`` installed; the missing
    dependency surfaces as a 503 on the first authenticated request instead
    of an import-time crash of the whole service.
    """
    real: SignatureVerifier | None = None

    def _verify(token: str, *, tenant_id: str, audience: str) -> dict[str, object]:
        nonlocal real
        if real is None:
            from uiao.saas.auth import jwks_verifier

            real = jwks_verifier(cloud)
        return real(token, tenant_id=tenant_id, audience=audience)

    return _verify


def _build_verifier() -> EntraTokenVerifier:
    audience = os.environ.get(_AUDIENCE_ENV, "").strip()
    if not audience:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"API auth is not configured: set {_AUDIENCE_ENV} (and optionally "
                f"{_TENANTS_ENV}/{_CLOUD_ENV}), or set {_MODE_ENV}=insecure-dev "
                "for local development only."
            ),
        )
    cloud = os.environ.get(_CLOUD_ENV, "commercial").strip() or "commercial"
    tenants_raw = os.environ.get(_TENANTS_ENV, "").strip()
    key = (audience, cloud, tenants_raw)
    verifier = _verifier_cache.get(key)
    if verifier is None:
        allowed = {t.strip() for t in tenants_raw.split(",") if t.strip()} or None
        try:
            verifier = EntraTokenVerifier(
                audience=audience,
                cloud=cloud,
                allowed_tenants=allowed,
                signature_verifier=_lazy_jwks(cloud),
            )
        except ValueError as exc:  # unknown cloud
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"API auth misconfigured: {exc}",
            ) from exc
        _verifier_cache[key] = verifier
    return verifier


def _dev_subject(token: str) -> str:
    """Best-effort subject extraction for insecure-dev mode (pre-hardening behavior)."""
    try:
        payload = decode_unverified_claims(token)
        return str(payload.get("sub", payload.get("oid", "auditor")))
    except TokenError:
        return "auditor"


def require_auditor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """Validate a Bearer token and return the verified subject claim."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required. Role: UIAO.Viewer or UIAO.Auditor",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    mode = os.environ.get(_MODE_ENV, "entra").strip().lower() or "entra"

    if mode == "insecure-dev":
        return _dev_subject(token)

    if mode != "entra":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unrecognized {_MODE_ENV}={mode!r}; expected 'entra' or 'insecure-dev'.",
        )

    verifier = _build_verifier()
    try:
        claims = verifier.verify(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT signature verification requires pyjwt[crypto]; pip install 'uiao[api]'.",
        ) from exc

    roles_raw = os.environ.get(_ROLES_ENV, "").strip()
    if roles_raw:
        required = {r.strip() for r in roles_raw.split(",") if r.strip()}
        if required and not (claims.principal_scopes & required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token lacks a required role (one of: {', '.join(sorted(required))}).",
            )
    return claims.subject or "unknown"


__all__ = ["require_auditor"]
