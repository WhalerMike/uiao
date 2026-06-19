"""
uiao.saas.aws_pg_auth
--------------------
Passwordless (AWS IAM) authentication for the Postgres tenant registry — the
AWS analogue of :mod:`uiao.saas.pg_auth` (ADR-117).

Amazon RDS for PostgreSQL accepts a short-lived **IAM authentication token** as
the connection password. The ECS task role is granted ``rds-db:connect`` on the
database user, so the SaaS app connects with no long-lived database password —
the same posture ADR-116 established on Azure, via the same SQLAlchemy
``do_connect`` seam (:func:`uiao.saas.pg_auth.apply_token_auth`).

``rds.generate_db_auth_token`` is a *local* request-signing operation (no
network round-trip) that yields a token valid for ~15 minutes.
:class:`RdsIamTokenProvider` caches it and regenerates before expiry. The
generator is injectable, so the cache/refresh logic is unit-tested with a fake
and a fake clock; ``boto3`` is **lazy-imported** only when no generator is
supplied, keeping this module in the ``[api]`` CI job.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

#: RDS IAM auth tokens are valid for 15 minutes from signing.
RDS_IAM_TOKEN_TTL_SECONDS = 900.0

#: Signs an IAM auth token: (hostname, port, username, region) -> token.
TokenGenerator = Callable[[str, int, str, str], str]


@dataclass(frozen=True)
class _Cached:
    token: str
    expires_at: float


class RdsIamTokenProvider:
    """Mint + cache a short-lived RDS IAM auth token (the connection password).

    Because ``generate_db_auth_token`` does not return an expiry, the provider
    tracks issuance against :data:`RDS_IAM_TOKEN_TTL_SECONDS` and regenerates
    once the token is within ``refresh_margin`` seconds of expiry.
    """

    def __init__(
        self,
        *,
        hostname: str,
        username: str,
        region: str,
        port: int = 5432,
        generate: TokenGenerator | None = None,
        ttl: float = RDS_IAM_TOKEN_TTL_SECONDS,
        refresh_margin: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not hostname or not username or not region:
            raise ValueError("hostname, username and region are required for RDS IAM auth")
        if refresh_margin < 0:
            raise ValueError("refresh_margin must be non-negative")
        if refresh_margin >= ttl:
            raise ValueError("refresh_margin must be smaller than the token ttl")
        self._hostname = hostname
        self._username = username
        self._region = region
        self._port = port
        self._generate = generate
        self._ttl = ttl
        self._margin = refresh_margin
        self._clock = clock
        self._cached: _Cached | None = None

    def _sign(self) -> str:
        if self._generate is not None:
            return self._generate(self._hostname, self._port, self._username, self._region)
        # Lazy import: only deployments using IAM auth need boto3 (the [aws]
        # extra). Tests inject ``generate``.
        import boto3

        client = boto3.client("rds", region_name=self._region)
        token: str = client.generate_db_auth_token(
            DBHostname=self._hostname,
            Port=self._port,
            DBUsername=self._username,
            Region=self._region,
        )
        return token

    def token(self) -> str:
        """Return a currently-valid IAM token, regenerating if near expiry."""
        now = self._clock()
        cached = self._cached
        if cached is not None and cached.expires_at - self._margin > now:
            return cached.token
        token = self._sign()
        self._cached = _Cached(token=token, expires_at=now + self._ttl)
        return token

    def invalidate(self) -> None:
        """Drop the cached token so the next :meth:`token` regenerates."""
        self._cached = None


__all__ = [
    "RDS_IAM_TOKEN_TTL_SECONDS",
    "TokenGenerator",
    "RdsIamTokenProvider",
]
