"""SASL mechanisms for the Active Governance Directory (ADR-101).

ADR-101 permits the AGD to authenticate LDAP clients via SASL with exactly
one mechanism — **GSSAPI** (Kerberos, RFC 4752) — and only as *gate-only
ticket validation*: the AGD accepts a service ticket the incumbent KDC
issued, using its own service keytab, to decide read scope. It is **not** a
credential authority — it never issues tickets, runs an AS/TGS, or stores
user secrets (ADR-101 §2 / §4 boundary table).

This module is mechanism-agnostic: a :class:`SaslMechanism` is a small
multi-step state machine (``step(token) -> SaslResult``) that the server
drives across one or more ``saslBindInProgress`` round-trips. The GSSAPI
adapter is lazy-imported behind the ``[kerberos]`` optional extra, so the
core AGD stays pure-stdlib and import never hard-requires ``gssapi``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass


class SaslError(Exception):
    """Raised when a SASL exchange cannot proceed (bad token, missing dep)."""


@dataclass(frozen=True)
class SaslResult:
    """The outcome of one :meth:`SaslMechanism.step`.

    * ``done=False`` — the exchange continues; ``response_token`` is sent to
      the client in a ``saslBindInProgress`` BindResponse.
    * ``done=True, success=True`` — authentication succeeded; ``principal`` is
      the validated client identity (the KDC's assertion) and gates read
      scope. ``response_token`` may carry a final server token.
    * ``done=True, success=False`` — authentication failed; ``message``
      explains why and the bind is answered ``invalidCredentials``.
    """

    done: bool
    success: bool = False
    response_token: bytes | None = None
    principal: str | None = None
    message: str = ""

    @classmethod
    def challenge(cls, token: bytes) -> SaslResult:
        return cls(done=False, response_token=token)

    @classmethod
    def ok(cls, principal: str, token: bytes | None = None) -> SaslResult:
        return cls(done=True, success=True, principal=principal, response_token=token)

    @classmethod
    def fail(cls, message: str) -> SaslResult:
        return cls(done=True, success=False, message=message)


class SaslMechanism(ABC):
    """One in-progress SASL authentication, driven a step at a time."""

    #: The mechanism's registered SASL name (e.g. ``"GSSAPI"``).
    name: str

    @abstractmethod
    def step(self, token: bytes | None) -> SaslResult:
        """Consume the client's token; return the next :class:`SaslResult`."""
        raise NotImplementedError


# A factory makes a fresh per-connection mechanism instance (SASL state is
# per-bind, never shared across connections).
SaslMechanismFactory = Callable[[], SaslMechanism]


# ---------------------------------------------------------------------------
# GSSAPI (Kerberos) — RFC 4752, gate-only ticket validation (ADR-101)
# ---------------------------------------------------------------------------
# Security-layer bitmask advertised after the context is established. The AGD
# offers "no security layer" only (bit 0x01): integrity/confidentiality are
# the channel's job (run StartTLS/LDAPS, ADR-100 §4), and a security layer
# would put the AGD inline on the data stream — beyond the gate-only role.
_QOP_NONE = 0x01
_MAX_BUFFER = 0  # no security layer => no negotiated buffer


class GssapiMechanism(SaslMechanism):
    """GSSAPI acceptor: validate the client's Kerberos ticket, no more.

    Holds only the AGD's **own** service credentials (its keytab, via the
    default acceptor credential). It accepts the security context the client
    presents, extracts the initiator principal as the KDC's assertion, and
    negotiates the auth-only (no-security-layer) exchange. It never acquires
    initiator credentials, issues tickets, or touches user secrets.
    """

    name = "GSSAPI"

    def __init__(self, service_name: str | None = None) -> None:
        try:
            import gssapi
        except ImportError as exc:  # pragma: no cover - exercised without [kerberos]
            raise SaslError("GSSAPI SASL requires the 'gssapi' package — install the '[kerberos]' extra") from exc
        self._gssapi = gssapi
        creds = None
        if service_name is not None:
            name = gssapi.Name(service_name, name_type=gssapi.NameType.hostbased_service)
            creds = gssapi.Credentials(name=name, usage="accept")
        # When service_name is None, the default acceptor credential (the host
        # keytab's ldap/<host> entry) is used — the standard service posture.
        self._context = gssapi.SecurityContext(creds=creds, usage="accept")
        self._principal: str | None = None
        self._phase = "context"

    def step(self, token: bytes | None) -> SaslResult:
        if self._phase == "context":
            return self._step_context(token)
        return self._step_security_layer(token)

    def _step_context(self, token: bytes | None) -> SaslResult:
        if token is None:
            return SaslResult.fail("GSSAPI bind requires an initial client token")
        out = self._context.step(token)
        if not self._context.complete:
            return SaslResult.challenge(out or b"")
        # Context established — the initiator name is the KDC's assertion.
        self._principal = str(self._context.initiator_name)
        # Advertise auth-only (no security layer): GSS_Wrap a 4-byte token of
        # {qop bitmask, 3-byte max buffer} (RFC 4752 §3.1).
        advert = bytes([_QOP_NONE]) + _MAX_BUFFER.to_bytes(3, "big")
        wrapped = self._context.wrap(advert, encrypt=False)
        self._phase = "security_layer"
        return SaslResult.challenge(wrapped.message)

    def _step_security_layer(self, token: bytes | None) -> SaslResult:
        if token is None:
            return SaslResult.fail("GSSAPI security-layer step requires a client token")
        unwrapped = self._context.unwrap(token).message
        if len(unwrapped) < 4:
            return SaslResult.fail("malformed GSSAPI security-layer response")
        if not (unwrapped[0] & _QOP_NONE):
            return SaslResult.fail("client did not accept the no-security-layer option")
        assert self._principal is not None
        return SaslResult.ok(self._principal)
