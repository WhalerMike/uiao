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
from dataclasses import dataclass, field

from uiao.directory import ber, protocol
from uiao.directory.dit import Directory

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

    # -- bind policy --------------------------------------------------------
    def _authenticate(self, name: str, password: str) -> protocol.ResultCode:
        if not name and not password:
            return protocol.ResultCode.SUCCESS  # anonymous
        if self.credentials.get(name) == password and password != "":
            return protocol.ResultCode.SUCCESS
        return protocol.ResultCode.INVALID_CREDENTIALS

    # -- per-request handlers ----------------------------------------------
    def handle_bind(self, req: protocol.BindRequest) -> bytes:
        if req.version != 3:
            return protocol.encode_bind_response(
                req.message_id,
                protocol.ResultCode.PROTOCOL_ERROR,
                f"only LDAPv3 is supported (got v{req.version})",
            )
        code = self._authenticate(req.name, req.password)
        return protocol.encode_bind_response(req.message_id, code)

    def handle_search(self, req: protocol.SearchRequest) -> list[bytes]:
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
            out.append(protocol.encode_search_result_entry(req.message_id, _project(entry, req.attributes)))
        code = protocol.ResultCode.SUCCESS
        message = "" if not truncated else f"sizeLimit {effective_limit} reached"
        out.append(protocol.encode_search_result_done(req.message_id, code, message))
        return out

    # -- connection loop ----------------------------------------------------
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        logger.info("AGD connection from %s", peer)
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
                    writer.write(self.handle_bind(req))
                elif isinstance(req, protocol.SearchRequest):
                    for chunk in self.handle_search(req):
                        writer.write(chunk)
                await writer.drain()
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()
            logger.info("AGD connection closed: %s", peer)

    async def serve(self, host: str = "127.0.0.1", port: int = 1389) -> None:
        """Run the server until cancelled."""
        server = await asyncio.start_server(self.handle_connection, host, port)
        sockets = ", ".join(str(s.getsockname()) for s in (server.sockets or ()))
        logger.info("Active Governance Directory listening on %s", sockets)
        async with server:
            await server.serve_forever()


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
