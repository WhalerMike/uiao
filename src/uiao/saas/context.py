"""
uiao.saas.context
----------------
Per-request tenant binding via :class:`contextvars.ContextVar`.

The tenant-resolution middleware sets the current :class:`TenantContext` at
the start of each request and clears it when the request completes. Any code
deep in the call stack — adapters, governance passes, evidence writers — can
call :func:`require_current_tenant` to discover whose data it is operating
on, without threading the tenant through every signature.

``ContextVar`` is task-local, so concurrent requests served by the same
worker never see each other's tenant.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field

from .tenant import Tenant


@dataclass(frozen=True)
class TenantContext:
    """The resolved tenant plus the authenticated principal for a request."""

    tenant: Tenant
    #: ``sub``/``oid`` of the calling principal.
    subject: str = ""
    #: OAuth2 scopes / app roles granted on the inbound token.
    scopes: frozenset[str] = field(default_factory=frozenset)

    @property
    def tenant_id(self) -> str:
        return self.tenant.tenant_id

    @property
    def namespace(self) -> str:
        return self.tenant.data_namespace

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


_current: ContextVar[TenantContext | None] = ContextVar("uiao_saas_tenant", default=None)


def set_current_tenant(context: TenantContext) -> Token[TenantContext | None]:
    """Bind ``context`` as the current tenant; returns a reset token."""
    return _current.set(context)


def clear_current_tenant(token: Token[TenantContext | None] | None = None) -> None:
    """Clear the bound tenant. Pass the token from :func:`set_current_tenant`."""
    if token is not None:
        _current.reset(token)
    else:
        _current.set(None)


def get_current_tenant() -> TenantContext | None:
    """Return the current tenant context, or ``None`` outside a request."""
    return _current.get()


def require_current_tenant() -> TenantContext:
    """Return the current tenant context or raise if none is bound."""
    ctx = _current.get()
    if ctx is None:
        raise LookupError(
            "no tenant bound to the current context — this code path must run "
            "inside a tenant-resolved request, or set one explicitly for tests"
        )
    return ctx


__all__ = [
    "TenantContext",
    "set_current_tenant",
    "clear_current_tenant",
    "get_current_tenant",
    "require_current_tenant",
]
