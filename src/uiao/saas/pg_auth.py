"""
uiao.saas.pg_auth
----------------
Passwordless (Microsoft Entra) authentication for the Postgres tenant registry.

Azure Database for PostgreSQL Flexible Server accepts a short-lived Entra
access token *as the connection password*. Binding the SaaS managed identity
as the server's Entra administrator (see ``deploy/azure/bicep/modules/
postgres.bicep``) lets the Container App connect with **no long-lived database
password** — the single highest-value secret in the deployment disappears
(ADR-116).

This module is deliberately dependency-light:

* :class:`EntraPostgresTokenProvider` — caches an OSSRDBMS access token and
  refreshes it before expiry. Its token *acquirer* is injectable, so the
  caching/refresh logic is unit-tested with a fake credential and a fake clock;
  the real :class:`azure.identity.DefaultAzureCredential` is **lazy-imported**
  only when no acquirer is supplied. Nothing here imports ``azure`` or
  ``sqlalchemy`` at module load, so it is import-safe in the ``[api]``-only CI
  job, exactly like the rest of :mod:`uiao.saas`.
* :func:`apply_entra_auth` — wires the provider into a SQLAlchemy *async*
  engine via the ``do_connect`` event, so every new asyncpg connection is
  issued a freshly-minted token. SQLAlchemy is lazy-imported here too.

The token endpoint differs per sovereign cloud, so :func:`ossrdbms_scope_for`
maps the UIAO ``cloud`` setting to the correct ``ossrdbms-aad`` audience.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

#: OSSRDBMS token audience for Azure commercial (also GCC-Moderate, ADR-033).
OSSRDBMS_SCOPE_COMMERCIAL = "https://ossrdbms-aad.database.windows.net/.default"
#: OSSRDBMS token audience for the US sovereign clouds (GCC-High / DoD).
OSSRDBMS_SCOPE_USGOV = "https://ossrdbms-aad.database.usgovcloudapi.net/.default"


def ossrdbms_scope_for(cloud: str) -> str:
    """Return the OSSRDBMS token scope for a UIAO ``cloud`` value."""
    return OSSRDBMS_SCOPE_USGOV if cloud in ("gcc-high", "dod") else OSSRDBMS_SCOPE_COMMERCIAL


class _AccessToken(Protocol):
    """Structural type matching ``azure.core.credentials.AccessToken``."""

    token: str
    expires_on: int  # epoch seconds


#: A token acquirer maps a scope to an object exposing ``token`` + ``expires_on``.
TokenAcquirer = Callable[[str], _AccessToken]


@dataclass(frozen=True)
class _Cached:
    token: str
    expires_on: float


class EntraPostgresTokenProvider:
    """Cache + refresh an Entra access token used as the Postgres password.

    The token is reused until it is within ``refresh_margin`` seconds of
    expiry, then re-acquired. This keeps token acquisition off the hot path of
    every connection while never presenting a (nearly) expired token.
    """

    def __init__(
        self,
        *,
        acquire: TokenAcquirer | None = None,
        scope: str = OSSRDBMS_SCOPE_COMMERCIAL,
        refresh_margin: float = 300.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if refresh_margin < 0:
            raise ValueError("refresh_margin must be non-negative")
        self._acquire = acquire
        self._scope = scope
        self._margin = refresh_margin
        self._clock = clock
        self._cached: _Cached | None = None

    @property
    def scope(self) -> str:
        return self._scope

    def _acquire_token(self) -> _AccessToken:
        if self._acquire is not None:
            return self._acquire(self._scope)
        # Lazy import: only deployments that actually use passwordless auth
        # need azure-identity (the [saas] extra). Tests inject ``acquire``.
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        acquired: _AccessToken = credential.get_token(self._scope)
        return acquired

    def token(self) -> str:
        """Return a currently-valid access token, refreshing if near expiry."""
        now = self._clock()
        cached = self._cached
        if cached is not None and cached.expires_on - self._margin > now:
            return cached.token
        acquired = self._acquire_token()
        self._cached = _Cached(token=acquired.token, expires_on=float(acquired.expires_on))
        return self._cached.token

    def invalidate(self) -> None:
        """Drop the cached token so the next :meth:`token` re-acquires."""
        self._cached = None


class _TokenProvider(Protocol):
    """Anything that can mint a current connection token (the password)."""

    def token(self) -> str: ...


def apply_token_auth(async_engine: Any, provider: _TokenProvider, *, username: str = "") -> None:
    """Make ``async_engine`` authenticate each new connection with a token.

    Registers a ``do_connect`` listener on the engine's underlying sync engine
    that injects a fresh token (from ``provider.token()``) as the connection
    password — and, when given, ``username`` as the connection user. SQLAlchemy
    is imported lazily so this module stays free of the ``[saas]`` extra at
    import time.

    The provider is duck-typed: both :class:`EntraPostgresTokenProvider` (Azure)
    and :class:`uiao.saas.aws_pg_auth.RdsIamTokenProvider` (AWS) satisfy it, so
    the same connection seam serves passwordless auth on either cloud.
    """
    from sqlalchemy import event

    @event.listens_for(async_engine.sync_engine, "do_connect")
    def _provide_token(_dialect, _conn_rec, _cargs, cparams):  # type: ignore[no-untyped-def]
        cparams["password"] = provider.token()
        if username:
            cparams["user"] = username
        # Return None → SQLAlchemy proceeds with the (mutated) cparams.
        return None


#: Backwards-compatible alias (ADR-116 shipped ``apply_entra_auth``).
apply_entra_auth = apply_token_auth


__all__ = [
    "OSSRDBMS_SCOPE_COMMERCIAL",
    "OSSRDBMS_SCOPE_USGOV",
    "ossrdbms_scope_for",
    "TokenAcquirer",
    "EntraPostgresTokenProvider",
    "apply_token_auth",
    "apply_entra_auth",
]
