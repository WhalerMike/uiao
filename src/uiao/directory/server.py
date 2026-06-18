"""Async LDAPv3 server for the Active Governance Directory (ADR-100).

A pure-``asyncio`` TCP server that answers the AGD's read surface:
``BIND`` (anonymous + simple), ``SEARCH`` (base / one-level / subtree),
and ``UNBIND``. It is in-path on the LDAP request path — the data-plane
position ADR-100 sanctions as an exception to ADR-092 §1 — but it remains
a **read projection**: there is no add/modify/delete op, so the in-path
server can never mutate the governance substrate.

Authentication policy for this first increment:

* **anonymous bind** (empty DN + empty password) — always succeeds and
  yields the full read-only projection;
* **simple bind** — succeeds only when the credentials match an entry in
  an operator-supplied ``credentials`` map (``{bind_dn: password}``);
  otherwise ``invalidCredentials``.

Kerberos/SASL, StartTLS, and write ops are explicitly out of scope and
roadmapped in ADR-100 — unsupported ops answer ``unwillingToPerform``
without dropping the connection.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from dataclasses import dataclass, field

from uiao.directory import ber, protocol
from uiao.directory.dit import Directory
from uiao.directory.policy import ReadPolicy, default_read_policy
from uiao.directory.sasl import SaslError, SaslMechanism, SaslMechanismFactory

logger = logging.getLogger("uiao.directory.server")

# Soft cap so a `(objectClass=*)` subtree sweep cannot return unbounded
# entries; overridable per server. A 0 size_limit means "server decides".
_DEFAULT_SIZE_LIMIT = 500


@dataclass
class LdapServer:
    """An LDAPv3 read projection of a :class:`Directory`."""

    directory: Directory
    credentials: dict[str, str] = field(default_factory=dict)
    size_limit: int = _DEFAULT_SIZE_LIMIT
    read_policy: ReadPolicy = field(default_factory=default_read_policy)
    # When set, the server offers StartTLS (RFC 4511 §4.14) so a client on the
    # plaintext port can upgrade the connection in-band. Distinct from the
    # ``ssl_context`` passed to :meth:`serve`, which is LDAPS-on-connect.
    tls_context: ssl.SSLContext | None = None
    # SASL mechanisms offered (name -> per-connection factory), ADR-101. Empty
    # by default; populate with {"GSSAPI": GssapiMechanism} to offer Kerberos.
    sasl_mechanisms: dict[str, SaslMechanismFactory] = field(default_factory=dict)

    # -- bind policy --------------------------------------------------------
    def _authenticate(self, name: str, password: str) -> protocol.ResultCode:
        if not name and not password:
            return protocol.ResultCode.SUCCESS  # anonymous
        if self.credentials.get(name) == password and password != "":
            return protocol.ResultCode.SUCCESS
        return protocol.ResultCode.INVALID_CREDENTIALS

    # -- per-request handlers ----------------------------------------------
    def process_bind(self, req: protocol.BindRequest) -> tuple[bytes, bool]:
        """Return the bind response and whether the connection is now authed.

        A successful *anonymous* bind (empty name/password) leaves the
        connection unauthenticated; only a successful *simple* bind against
        a known credential authenticates it (and thus unlocks sensitive
        facets via :attr:`read_policy`). A failed bind drops the connection
        back to anonymous (RFC 4511 §4.2.1).
        """
        if req.version != 3:
            response = protocol.encode_bind_response(
                req.message_id,
                protocol.ResultCode.PROTOCOL_ERROR,
                f"only LDAPv3 is supported (got v{req.version})",
            )
            return response, False
        code = self._authenticate(req.name, req.password)
        authenticated = code == protocol.ResultCode.SUCCESS and bool(req.name) and req.password != ""
        return protocol.encode_bind_response(req.message_id, code), authenticated

    def handle_bind(self, req: protocol.BindRequest) -> bytes:
        """Bind response only (see :meth:`process_bind` for the auth state)."""
        return self.process_bind(req)[0]

    def handle_sasl_bind(
        self, req: protocol.SaslBindRequest, session: SaslMechanism | None
    ) -> tuple[bytes, bool, str | None, SaslMechanism | None]:
        """Advance a (possibly multi-step) SASL bind (ADR-101).

        Returns ``(response, authenticated, principal, session)``. While the
        exchange is in progress the response is ``saslBindInProgress`` and the
        live ``session`` is handed back to drive the next round-trip; on
        completion the session is cleared. Gate-only: success sets read scope
        via the validated ``principal``, never a write capability.
        """
        if req.version != 3:
            response = protocol.encode_bind_response(
                req.message_id,
                protocol.ResultCode.PROTOCOL_ERROR,
                f"only LDAPv3 is supported (got v{req.version})",
            )
            return response, False, None, None

        factory = self.sasl_mechanisms.get(req.mechanism)
        if factory is None:
            response = protocol.encode_bind_response(
                req.message_id,
                protocol.ResultCode.AUTH_METHOD_NOT_SUPPORTED,
                f"unsupported SASL mechanism '{req.mechanism}'",
            )
            return response, False, None, None

        # A fresh exchange starts a new mechanism instance; a continuation
        # reuses the in-progress one (state is per-bind, never shared).
        if session is None or session.name != req.mechanism:
            try:
                session = factory()
            except SaslError as exc:
                response = protocol.encode_bind_response(
                    req.message_id, protocol.ResultCode.AUTH_METHOD_NOT_SUPPORTED, str(exc)
                )
                return response, False, None, None

        try:
            result = session.step(req.credentials)
        except SaslError as exc:
            response = protocol.encode_bind_response(req.message_id, protocol.ResultCode.OPERATIONS_ERROR, str(exc))
            return response, False, None, None

        if not result.done:
            response = protocol.encode_bind_response(
                req.message_id,
                protocol.ResultCode.SASL_BIND_IN_PROGRESS,
                server_sasl_creds=result.response_token or b"",
            )
            return response, False, None, session
        if result.success:
            response = protocol.encode_bind_response(
                req.message_id, protocol.ResultCode.SUCCESS, server_sasl_creds=result.response_token
            )
            return response, True, result.principal, None
        response = protocol.encode_bind_response(
            req.message_id, protocol.ResultCode.INVALID_CREDENTIALS, result.message
        )
        return response, False, None, None

    def handle_search(self, req: protocol.SearchRequest, *, authenticated: bool = False) -> list[bytes]:
        # The base object must exist for any scope (RFC 4511 §4.5.3); a base
        # that exists but matches nothing is success/0 entries, not noSuchObject.
        if not self.directory.contains(req.base_object):
            return [
                protocol.encode_search_result_done(
                    req.message_id,
                    protocol.ResultCode.NO_SUCH_OBJECT,
                    message=f"base object '{req.base_object}' does not exist",
                )
            ]
        out: list[bytes] = []
        matched = self.directory.search(req.base_object, req.scope, req.filter)
        effective_limit = min(filter_positive(req.size_limit), self.size_limit) or self.size_limit
        truncated = False
        for entry in matched:
            if len(out) >= effective_limit:
                truncated = True
                break
            # Project to the requested attributes, then redact sensitive
            # facets for anonymous binds (ADR-100 §5 per-bind read scoping).
            scoped = self.read_policy.apply(_project(entry, req.attributes), authenticated=authenticated)
            out.append(protocol.encode_search_result_entry(req.message_id, scoped))
        code = protocol.ResultCode.SUCCESS
        message = "" if not truncated else f"sizeLimit {effective_limit} reached"
        out.append(protocol.encode_search_result_done(req.message_id, code, message))
        return out

    # -- extended ops (StartTLS) -------------------------------------------
    async def _handle_extended(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        req: protocol.ExtendedRequest,
        *,
        tls_active: bool,
        peer: object,
    ) -> bool:
        """Service an ExtendedRequest. Returns True iff a StartTLS upgrade happened.

        Only StartTLS (RFC 4511 §4.14) is recognised. Anything else, or
        StartTLS when no ``tls_context`` is configured / TLS is already up,
        is refused with a non-success ExtendedResponse and no responseName.
        """
        if req.request_name != protocol.STARTTLS_OID:
            writer.write(
                protocol.encode_extended_response(
                    req.message_id, protocol.ResultCode.PROTOCOL_ERROR, message="unsupported extended operation"
                )
            )
            return False
        if self.tls_context is None:
            writer.write(
                protocol.encode_extended_response(
                    req.message_id, protocol.ResultCode.UNWILLING_TO_PERFORM, message="StartTLS is not configured"
                )
            )
            return False
        if tls_active:
            writer.write(
                protocol.encode_extended_response(
                    req.message_id, protocol.ResultCode.OPERATIONS_ERROR, message="TLS is already established"
                )
            )
            return False
        # ``StreamWriter.start_tls`` is the in-band upgrade primitive — but it
        # only exists on Python 3.11+. On 3.10 (still in ``requires-python``)
        # there is no public way to upgrade an existing stream, so refuse
        # rather than crash; LDAPS-on-connect remains available there.
        start_tls = getattr(writer, "start_tls", None)
        if start_tls is None:  # pragma: no cover - exercised only on Python 3.10
            writer.write(
                protocol.encode_extended_response(
                    req.message_id,
                    protocol.ResultCode.UNWILLING_TO_PERFORM,
                    message="StartTLS requires Python 3.11+ (use LDAPS-on-connect)",
                )
            )
            return False
        # Acknowledge first, then perform the in-band handshake (RFC 4511
        # §4.14.2): the success response is the last thing sent in the clear.
        writer.write(
            protocol.encode_extended_response(
                req.message_id, protocol.ResultCode.SUCCESS, response_name=protocol.STARTTLS_OID
            )
        )
        await writer.drain()
        try:
            await start_tls(self.tls_context)
        except (ssl.SSLError, OSError) as exc:
            # The handshake failed after we acknowledged; the connection is no
            # longer usable in either mode (RFC 4511 §4.14.2). Drop it.
            logger.warning("StartTLS handshake failed from %s: %s", peer, exc)
            raise ConnectionResetError("StartTLS handshake failed") from exc
        logger.info("StartTLS upgrade completed for %s", peer)
        return True

    # -- connection loop ----------------------------------------------------
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        logger.info("AGD connection from %s", peer)
        # Connections start anonymous; a successful simple/SASL bind flips this.
        authenticated = False
        sasl_session: SaslMechanism | None = None  # in-progress multi-step SASL bind
        tls_active = writer.get_extra_info("ssl_object") is not None  # LDAPS-on-connect
        try:
            while True:
                data = await _read_one_message(reader)
                if data is None:
                    break
                try:
                    req = protocol.parse_message(data)
                except protocol.UnsupportedOperation as exc:
                    # A read projection services no write op — refuse it with
                    # unwillingToPerform (keyed to the request) and keep the
                    # connection open, per ADR-100.
                    refusal = protocol.encode_unwilling_response(exc.message_id, exc.op_tag, str(exc))
                    if refusal is not None:
                        writer.write(refusal)
                        await writer.drain()
                        logger.info("refused unsupported op from %s: %s", peer, exc)
                    else:
                        logger.warning("dropped uncorrelatable unsupported op from %s: %s", peer, exc)
                    continue
                except protocol.ProtocolError as exc:
                    logger.warning("protocol error from %s: %s", peer, exc)
                    break

                if isinstance(req, protocol.UnbindRequest):
                    break
                if isinstance(req, protocol.BindRequest):
                    response, authenticated = self.process_bind(req)
                    sasl_session = None  # a simple bind clears any SASL exchange
                    writer.write(response)
                elif isinstance(req, protocol.SaslBindRequest):
                    response, authenticated, principal, sasl_session = self.handle_sasl_bind(req, sasl_session)
                    if authenticated:
                        logger.info("SASL %s bind authenticated %s as %s", req.mechanism, peer, principal)
                    writer.write(response)
                elif isinstance(req, protocol.SearchRequest):
                    for chunk in self.handle_search(req, authenticated=authenticated):
                        writer.write(chunk)
                elif isinstance(req, protocol.ExtendedRequest):
                    upgraded = await self._handle_extended(reader, writer, req, tls_active=tls_active, peer=peer)
                    if upgraded:
                        # StartTLS discards any prior authentication state
                        # (RFC 4513 §3.1.1): the connection is anonymous again.
                        tls_active, authenticated = True, False
                await writer.drain()
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()
            logger.info("AGD connection closed: %s", peer)

    async def serve(
        self,
        host: str = "127.0.0.1",
        port: int = 1389,
        *,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        """Run the server until cancelled.

        When ``ssl_context`` is supplied the listener is LDAPS-on-connect
        (TLS wraps the socket immediately, the conventional ``ldaps://``
        deployment) — the transport-security control ADR-100 §4 requires
        before the AGD may leave loopback. StartTLS (the in-band upgrade
        extended op) remains roadmap.
        """
        server = await asyncio.start_server(self.handle_connection, host, port, ssl=ssl_context)
        sockets = ", ".join(str(s.getsockname()) for s in (server.sockets or ()))
        scheme = "ldaps" if ssl_context else "ldap"
        logger.info("Active Governance Directory listening on %s (%s)", sockets, scheme)
        async with server:
            await server.serve_forever()


def build_server_tls_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    """Build a server-side TLS context for LDAPS from a cert + key (PEM)."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


def filter_positive(value: int) -> int:
    """A SearchRequest size_limit of 0 means "no client limit"."""
    return value if value > 0 else 1 << 62


def _project(entry: protocol.Entry, requested: tuple[str, ...]) -> protocol.Entry:
    """Restrict an entry to the requested attributes (empty/`*` = all)."""
    if not requested or "*" in requested:
        return entry
    wanted = {a.lower() for a in requested}
    attrs = {name: vals for name, vals in entry.attributes.items() if name.lower() in wanted}
    return protocol.Entry(dn=entry.dn, attributes=attrs)


async def _read_one_message(reader: asyncio.StreamReader) -> bytes | None:
    """Read exactly one BER ``LDAPMessage`` envelope, or None at EOF."""
    first = await reader.read(1)
    if not first:
        return None
    if first[0] != ber.TAG_SEQUENCE:
        # Not an LDAPMessage SEQUENCE — unrecoverable framing.
        raise protocol.ProtocolError("LDAPMessage must start with a SEQUENCE tag")
    len_first = await reader.readexactly(1)
    header = first + len_first
    if len_first[0] < 0x80:
        body_len = len_first[0]
    else:
        num = len_first[0] & 0x7F
        len_rest = await reader.readexactly(num)
        header += len_rest
        body_len = int.from_bytes(len_rest, "big")
    body = await reader.readexactly(body_len)
    return header + body
