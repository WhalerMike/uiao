"""LDAPS (TLS-on-connect) round-trip test for the AGD (ADR-100 §4).

Generates a throwaway self-signed cert with ``cryptography`` (skipped if
unavailable), serves the projection over TLS, and drives a real TLS client
through bind + subtree search — proving the transport-security control
ADR-100 §4 requires before the AGD may leave loopback actually works on
the wire.
"""

from __future__ import annotations

import asyncio
import datetime
import ssl
from pathlib import Path

import pytest

from uiao.directory import ber, protocol
from uiao.directory.dit import build_directory
from uiao.directory.server import LdapServer, build_server_tls_context

pytest.importorskip("cryptography")

PRINCIPALS = [{"principal_id": "alice@uiao.gov", "principal_type": "user", "attributes": {"extensionAttribute2": "IT"}}]


def _self_signed(tmp_path: Path) -> tuple[Path, Path]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


def _bind(message_id: int, name: str, password: str) -> bytes:
    op = ber.encode_sequence(
        [
            ber.encode_integer(3),
            ber.encode_octet_string(name),
            ber.encode_octet_string(password, tag=protocol.AUTH_SIMPLE),
        ],
        tag=protocol.APP_BIND_REQUEST,
    )
    return ber.encode_sequence([ber.encode_integer(message_id), op])


def _search_present(message_id: int, base: str) -> bytes:
    filt = ber.encode_octet_string("objectClass", tag=protocol.FILTER_PRESENT)
    op = ber.encode_sequence(
        [
            ber.encode_octet_string(base),
            ber.encode_enumerated(int(protocol.Scope.WHOLE_SUBTREE)),
            ber.encode_enumerated(0),
            ber.encode_integer(0),
            ber.encode_integer(0),
            ber.encode_boolean(False),
            filt,
            ber.encode_sequence([]),
        ],
        tag=protocol.APP_SEARCH_REQUEST,
    )
    return ber.encode_sequence([ber.encode_integer(message_id), op])


async def _read_message(reader: asyncio.StreamReader) -> ber.TLV:
    first = await reader.readexactly(1)
    len_octet = await reader.readexactly(1)
    if len_octet[0] < 0x80:
        header, body_len = first + len_octet, len_octet[0]
    else:
        rest = await reader.readexactly(len_octet[0] & 0x7F)
        header, body_len = first + len_octet + rest, int.from_bytes(rest, "big")
    tlv, _ = ber.read_tlv(header + await reader.readexactly(body_len))
    return tlv


async def _tls_round_trip(server: LdapServer, server_ctx: ssl.SSLContext, cert: Path) -> list[ber.TLV]:
    srv = await asyncio.start_server(server.handle_connection, "127.0.0.1", 0, ssl=server_ctx)
    host, port = srv.sockets[0].getsockname()[:2]
    client_ctx = ssl.create_default_context()
    client_ctx.check_hostname = False  # round-trip proof; we trust the cert directly
    client_ctx.load_verify_locations(str(cert))
    responses: list[ber.TLV] = []
    async with srv:
        reader, writer = await asyncio.open_connection(host, port, ssl=client_ctx)
        # SSL transports cannot half-close, so end with an explicit unbind.
        for req in [
            _bind(1, "", ""),
            _search_present(2, "dc=agd,dc=uiao,dc=gov"),
            ber.encode_sequence([ber.encode_integer(3), ber.encode_null(tag=protocol.APP_UNBIND_REQUEST)]),
        ]:
            writer.write(req)
        await writer.drain()
        try:
            while True:
                responses.append(await _read_message(reader))
        except asyncio.IncompleteReadError:
            pass
        writer.close()
    return responses


def test_ldaps_round_trip(tmp_path: Path) -> None:
    cert, key = _self_signed(tmp_path)
    server_ctx = build_server_tls_context(str(cert), str(key))
    server = LdapServer(directory=build_directory(PRINCIPALS))
    responses = asyncio.run(_tls_round_trip(server, server_ctx, cert))
    tags = [ber.read_children(r.content)[1].tag for r in responses]
    assert tags[0] == protocol.APP_BIND_RESPONSE
    assert protocol.APP_SEARCH_RESULT_ENTRY in tags
    assert tags[-1] == protocol.APP_SEARCH_RESULT_DONE


def _starttls(message_id: int) -> bytes:
    op = ber.encode_sequence(
        [ber.encode_octet_string(protocol.STARTTLS_OID, tag=protocol.EXT_REQUEST_NAME)],
        tag=protocol.APP_EXTENDED_REQUEST,
    )
    return ber.encode_sequence([ber.encode_integer(message_id), op])


async def _starttls_round_trip(server: LdapServer, cert: Path) -> list[ber.TLV]:
    srv = await asyncio.start_server(server.handle_connection, "127.0.0.1", 0)
    host, port = srv.sockets[0].getsockname()[:2]
    client_ctx = ssl.create_default_context()
    client_ctx.check_hostname = False
    client_ctx.load_verify_locations(str(cert))
    responses: list[ber.TLV] = []
    async with srv:
        reader, writer = await asyncio.open_connection(host, port)
        # 1) Ask for StartTLS in the clear and read the extendedResp ack.
        writer.write(_starttls(1))
        await writer.drain()
        ack = await _read_message(reader)
        responses.append(ack)
        # 2) Upgrade the client side in-band, then run LDAP over TLS.
        await writer.start_tls(client_ctx, server_hostname="localhost")
        for req in [
            _bind(2, "", ""),
            _search_present(3, "dc=agd,dc=uiao,dc=gov"),
            ber.encode_sequence([ber.encode_integer(4), ber.encode_null(tag=protocol.APP_UNBIND_REQUEST)]),
        ]:
            writer.write(req)
        await writer.drain()
        try:
            while True:
                responses.append(await _read_message(reader))
        except asyncio.IncompleteReadError:
            pass
        writer.close()
    return responses


def test_starttls_round_trip(tmp_path: Path) -> None:
    cert, key = _self_signed(tmp_path)
    server = LdapServer(directory=build_directory(PRINCIPALS))
    server.tls_context = build_server_tls_context(str(cert), str(key))
    responses = asyncio.run(_starttls_round_trip(server, cert))
    # First response is the StartTLS ack (extendedResp, success, in the clear).
    ack = responses[0]
    ack_op = ber.read_children(ack.content)[1]
    assert ack_op.tag == protocol.APP_EXTENDED_RESPONSE
    assert ber.decode_integer(ber.read_children(ack_op.content)[0].content) == int(protocol.ResultCode.SUCCESS)
    # The bind + search that follow ran over the now-encrypted channel.
    later = [ber.read_children(r.content)[1].tag for r in responses[1:]]
    assert protocol.APP_BIND_RESPONSE in later
    assert protocol.APP_SEARCH_RESULT_ENTRY in later
    assert later[-1] == protocol.APP_SEARCH_RESULT_DONE
