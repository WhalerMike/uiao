"""Identity-plane resolver — pluggable per adapter manifest.

Per ADR-072 §3, the runtime identity validator delegates resolution to
an `IdentityPlaneResolver` declared in the adapter's manifest. The
default is `EntraIDResolver`. Federal-only deployments can swap in
`LoginGovResolver`, `PIVResolver`, or a custom resolver without
touching the sink.

This file is a DRAFT skeleton. Promotion to
`src/uiao/identity/resolver.py` happens when ADR-072 is ACCEPTED.
"""

from __future__ import annotations

import abc
import functools
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import ClassVar, Optional


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resolution result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionResult:
    """Outcome of an identity-plane resolution.

    `resolved=True` means the principal exists and is in a state the
    substrate considers valid for emission (active, not disabled, not
    pending deletion). `resolved=False` means the principal could not
    be found or is in a state that DOES NOT permit emission; the
    `reason` field carries the human-readable cause.
    """

    issuer_identity: str
    resolved: bool
    principal_display: Optional[str] = None
    reason: Optional[str] = None
    resolved_at: Optional[str] = None


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------


class IdentityPlaneResolver(abc.ABC):
    """Abstract base for identity-plane resolvers.

    Concrete subclasses bind to a specific identity plane (Entra ID,
    Login.gov, PIV/USAccess, federal IdP). The plug-point is the
    adapter manifest's `identity_resolver:` field, which carries a
    `module:ClassName` reference.

    Subclasses MUST be safe to construct without network access; the
    network call happens in `resolve()`. This lets the sink construct
    a resolver during init and surface configuration errors at startup
    rather than at first emission.
    """

    #: Stable identifier; matches the value used in adapter manifests.
    RESOLVER_ID: ClassVar[str] = "base"

    #: Time-to-live for positive resolutions in seconds. Subclasses can
    #: override to match their identity plane's expected churn rate.
    CACHE_TTL_SECONDS: ClassVar[int] = 5 * 60

    def __init__(self, *, config: Optional[dict] = None) -> None:
        if self.RESOLVER_ID == "base":
            raise TypeError(
                "IdentityPlaneResolver subclasses MUST override RESOLVER_ID"
            )
        self._config = config or {}
        self._cache: dict[str, tuple[datetime, ResolutionResult]] = {}
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, issuer_identity: str) -> ResolutionResult:
        """Resolve an issuer identity, honoring the LRU cache."""
        now = datetime.now(timezone.utc)
        ttl = timedelta(seconds=self.CACHE_TTL_SECONDS)

        with self._cache_lock:
            cached = self._cache.get(issuer_identity)
            if cached is not None and now - cached[0] < ttl:
                return cached[1]

        result = self._resolve_uncached(issuer_identity)

        with self._cache_lock:
            self._cache[issuer_identity] = (now, result)

        return result

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def _resolve_uncached(self, issuer_identity: str) -> ResolutionResult:
        """Perform the actual identity-plane lookup.

        Subclasses implement the network call to the identity plane.
        Returns a `ResolutionResult` with `resolved=True` iff the
        principal exists and is in an emission-valid state.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# EntraIDResolver — default
# ---------------------------------------------------------------------------


class EntraIDResolver(IdentityPlaneResolver):
    """Default resolver — looks up issuer_identity as an Entra ID object ID.

    Phase 2 ships the skeleton with a stubbed lookup; the real
    Graph-API call is wired in PR-2a (paired with the resolver
    registration in the sink). The stub returns `resolved=True` for
    any non-empty issuer_identity that looks like a UUID, so the
    rest of the validator chain can be unit-tested without a live
    tenant.
    """

    RESOLVER_ID = "entra-id"

    def _resolve_uncached(self, issuer_identity: str) -> ResolutionResult:
        # Phase 2 STUB — real implementation calls
        # GET https://graph.microsoft.com/v1.0/directoryObjects/{id}
        # and checks accountEnabled + onPremisesSyncEnabled.
        if not issuer_identity:
            return ResolutionResult(
                issuer_identity=issuer_identity,
                resolved=False,
                reason="issuer_identity is empty",
            )
        if not _looks_like_uuid(issuer_identity):
            return ResolutionResult(
                issuer_identity=issuer_identity,
                resolved=False,
                reason="issuer_identity is not a valid Entra ID object ID (UUID)",
            )
        return ResolutionResult(
            issuer_identity=issuer_identity,
            resolved=True,
            principal_display=f"entra:{issuer_identity}",
            resolved_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# Resolver registry — manifest plug-point
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=64)
def load_resolver(resolver_ref: str) -> IdentityPlaneResolver:
    """Load a resolver by `module:ClassName` reference.

    Adapter manifests declare a resolver as
    `identity_resolver: "uiao.identity.resolver:EntraIDResolver"`. The
    sink calls this function with that string at emit time; an LRU
    cache ensures each resolver class is instantiated at most once per
    process.

    A manifest without `identity_resolver:` resolves to the default
    `EntraIDResolver`. A reference that fails to import raises
    `RuntimeError` synchronously, surfacing the configuration error
    rather than failing on every emission.
    """
    if not resolver_ref:
        return EntraIDResolver()

    if ":" not in resolver_ref:
        raise RuntimeError(
            f"identity_resolver {resolver_ref!r} must be of the form 'module:ClassName'"
        )

    module_path, class_name = resolver_ref.split(":", 1)
    try:
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"identity_resolver {resolver_ref!r} could not be loaded: {exc}"
        ) from exc

    if not issubclass(cls, IdentityPlaneResolver):
        raise RuntimeError(
            f"identity_resolver {resolver_ref!r} does not subclass IdentityPlaneResolver"
        )
    return cls()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


import re

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _looks_like_uuid(value: str) -> bool:
    return bool(_UUID_PATTERN.match(value))
