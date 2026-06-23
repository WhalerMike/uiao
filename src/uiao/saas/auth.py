"""
uiao.saas.auth
-------------
Inbound Entra ID (Azure AD) bearer-token verification for the multi-tenant
data plane.

A SaaS request arrives with a JWT minted by the *customer's* tenant for the
UIAO API audience. Verification has two halves:

1. **Signature** — validated against the issuing tenant's JWKS. This requires
   network + crypto and is delegated to a pluggable
   :class:`SignatureVerifier`; the production implementation
   (:func:`jwks_verifier`) is lazy-imported so PyJWT/cryptography are only
   needed when actually verifying signatures (the ``[saas]`` extra).
2. **Claims** — ``exp`` not passed, ``aud`` matches the API audience, ``iss``
   is a Microsoft identity-platform v2 issuer for an allowed tenant, and a
   ``tid`` (tenant id) is present. This half is pure-stdlib and fully tested.

For local dev / tests, ``insecure_allow_unsigned=True`` skips the signature
check (claims are still validated).
"""

from __future__ import annotations

import base64
import binascii
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

#: Microsoft identity platform v2 issuer template. ``{tid}`` is the tenant id.
ISSUER_V2_TEMPLATES = {
    "commercial": "https://login.microsoftonline.com/{tid}/v2.0",
    "gcc-high": "https://login.microsoftonline.us/{tid}/v2.0",
    "dod": "https://login.microsoftonline.us/{tid}/v2.0",
}


class TokenError(Exception):
    """Raised when an inbound token fails verification."""


@dataclass(frozen=True)
class Claims:
    """The verified, relevant subset of an Entra access-token's claims."""

    tenant_id: str
    subject: str
    audience: str
    issuer: str
    scopes: frozenset[str] = field(default_factory=frozenset)
    roles: frozenset[str] = field(default_factory=frozenset)
    raw: dict[str, object] = field(default_factory=dict)

    @property
    def principal_scopes(self) -> frozenset[str]:
        """Delegated scopes (``scp``) unioned with app roles (``roles``)."""
        return self.scopes | self.roles


class SignatureVerifier(Protocol):
    """Validates a token's signature and returns its decoded payload."""

    def __call__(self, token: str, *, tenant_id: str, audience: str) -> dict[str, object]: ...


def _b64url_json(segment: str) -> dict[str, object]:
    """Decode a base64url JWT segment into a JSON object."""
    padded = segment + "=" * (-len(segment) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        obj = json.loads(decoded)
    except (binascii.Error, ValueError, json.JSONDecodeError) as exc:
        raise TokenError(f"malformed JWT segment: {exc}") from exc
    if not isinstance(obj, dict):
        raise TokenError("JWT segment is not a JSON object")
    return obj


def decode_unverified_claims(token: str) -> dict[str, object]:
    """Decode the payload of a JWT *without* verifying its signature."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("token is not a well-formed JWT (expected 3 segments)")
    return _b64url_json(parts[1])


def _as_str_set(value: object) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset(value.split())
    if isinstance(value, (list, tuple)):
        return frozenset(str(v) for v in value)
    return frozenset()


class EntraTokenVerifier:
    """Verifies inbound Entra access tokens for the SaaS data plane."""

    def __init__(
        self,
        *,
        audience: str,
        cloud: str = "commercial",
        allowed_tenants: set[str] | None = None,
        signature_verifier: SignatureVerifier | None = None,
        insecure_allow_unsigned: bool = False,
        leeway_seconds: int = 60,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if cloud not in ISSUER_V2_TEMPLATES:
            raise ValueError(f"unknown cloud {cloud!r}; expected one of {sorted(ISSUER_V2_TEMPLATES)}")
        self._audience = audience
        self._cloud = cloud
        self._allowed_tenants = allowed_tenants
        self._signature_verifier = signature_verifier
        self._insecure_allow_unsigned = insecure_allow_unsigned
        self._leeway = leeway_seconds
        self._clock = clock

    def expected_issuer(self, tenant_id: str) -> str:
        return ISSUER_V2_TEMPLATES[self._cloud].format(tid=tenant_id)

    def verify(self, token: str) -> Claims:
        """Verify ``token`` and return its :class:`Claims`, or raise."""
        unverified = decode_unverified_claims(token)
        tenant_id = str(unverified.get("tid", "")).strip()
        if not tenant_id:
            raise TokenError("token has no 'tid' (tenant id) claim")

        if self._allowed_tenants is not None and tenant_id not in self._allowed_tenants:
            raise TokenError(f"tenant {tenant_id} is not in the issuer allowlist")

        # --- Signature ----------------------------------------------------
        if self._signature_verifier is not None:
            payload = self._signature_verifier(token, tenant_id=tenant_id, audience=self._audience)
        elif self._insecure_allow_unsigned:
            payload = unverified
        else:
            raise TokenError("no signature verifier configured and insecure_allow_unsigned is off — refusing token")

        self._validate_claims(payload, tenant_id)
        return self._to_claims(payload, tenant_id)

    def _validate_claims(self, payload: dict[str, object], tenant_id: str) -> None:
        now = self._clock()
        exp = payload.get("exp")
        if isinstance(exp, (int, float)) and now > float(exp) + self._leeway:
            raise TokenError("token has expired")
        nbf = payload.get("nbf")
        if isinstance(nbf, (int, float)) and now + self._leeway < float(nbf):
            raise TokenError("token is not yet valid (nbf)")

        aud = payload.get("aud")
        audiences = {aud} if isinstance(aud, str) else set(aud) if isinstance(aud, (list, tuple)) else set()
        if self._audience and self._audience not in audiences:
            raise TokenError(f"token audience {audiences} does not include {self._audience!r}")

        iss = str(payload.get("iss", ""))
        expected = self.expected_issuer(tenant_id)
        if iss and iss != expected:
            raise TokenError(f"token issuer {iss!r} does not match expected {expected!r}")

    @staticmethod
    def _to_claims(payload: dict[str, object], tenant_id: str) -> Claims:
        subject = str(payload.get("oid", payload.get("sub", "")))
        return Claims(
            tenant_id=tenant_id,
            subject=subject,
            audience=str(payload.get("aud", "")),
            issuer=str(payload.get("iss", "")),
            scopes=_as_str_set(payload.get("scp")),
            roles=_as_str_set(payload.get("roles")),
            raw=payload,
        )


def jwks_verifier(cloud: str = "commercial", *, timeout: int = 5) -> SignatureVerifier:
    """Return a production JWKS-backed signature verifier.

    Lazy-imports ``PyJWT`` (the ``[saas]`` extra). Fetches the issuing
    tenant's signing keys from the OpenID configuration and validates the
    RS256 signature. Keys are cached per-tenant by PyJWT's ``PyJWKClient``.
    """
    import jwt  # type: ignore[import-untyped]
    from jwt import PyJWKClient

    base = {
        "commercial": "https://login.microsoftonline.com",
        "gcc-high": "https://login.microsoftonline.us",
        "dod": "https://login.microsoftonline.us",
    }[cloud]
    _clients: dict[str, PyJWKClient] = {}

    def _verify(token: str, *, tenant_id: str, audience: str) -> dict[str, object]:
        client = _clients.get(tenant_id)
        if client is None:
            client = PyJWKClient(f"{base}/{tenant_id}/discovery/v2.0/keys", timeout=timeout)
            _clients[tenant_id] = client
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(  # type: ignore[no-any-return]
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            options={"verify_exp": True},
        )

    return _verify


__all__ = [
    "Claims",
    "EntraTokenVerifier",
    "SignatureVerifier",
    "TokenError",
    "decode_unverified_claims",
    "jwks_verifier",
]
