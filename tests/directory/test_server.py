"""End-to-end LDAP server tests over a real asyncio socket (ADR-100).

These drive the server through an actual TCP connection using BER messages
the test encodes itself, exercising the framing reader, bind policy, and
search path together. No third-party LDAP client is required.
"""

from __future__ import annotations

import asyncio

from uiao.directory import ber, protocol
from uiao.directory.dit import build_directory
from uiao.directory.server import LdapServer

PRINCIPALS = [
    {"principal_id": "alice@uiao.gov", "principal_type": "user", "attributes": {"extensionAttribute2": "IT"}},
    {"principal_id": "bob@uiao.gov", "principal_type": "user", "attributes": {"extensionAttribute2": "HR"}},
]


def _bind(message_id: int, name: str, password: str, version: int = 3) -> bytes:
    op = ber.encode_sequence(
        [
            ber.encode_integer(version),
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


async def _read_message(reader: asyncio.StreamReader) -> protocol.ber.TLV:
    first = await reader.readexactly(1)
    len_octet = await reader.readexactly(1)
    if len_octet[0] < 0x80:
        body_len = len_octet[0]
        header = first + len_octet
    else:
        rest = await reader.readexactly(len_octet[0] & 0x7F)
        body_len = int.from_bytes(rest, "big")
        header = first + len_octet + rest
    body = await reader.readexactly(body_len)
    tlv, _ = ber.read_tlv(header + body)
    return tlv


def _result_code(envelope: ber.TLV) -> int:
    _, op = ber.read_children(envelope.content)
    return ber.decode_integer(ber.read_children(op.content)[0].content)


async def _run_session(server: LdapServer, requests: list[bytes]) -> list[ber.TLV]:
    srv = await asyncio.start_server(server.handle_connection, "127.0.0.1", 0)
    host, port = srv.sockets[0].getsockname()[:2]
    responses: list[ber.TLV] = []
    async with srv:
        reader, writer = await asyncio.open_connection(host, port)
        for req in requests:
            writer.write(req)
        await writer.drain()
        # Half-close the write side so the server sees EOF after the last
        # request and closes the connection — otherwise both ends block on
        # read when the session omits an explicit UnbindRequest.
        writer.write_eof()
        # Read responses until the server closes (EOF -> IncompleteReadError).
        try:
            while True:
                responses.append(await _read_message(reader))
        except asyncio.IncompleteReadError:
            pass
        writer.close()
    return responses


def test_anonymous_bind_then_subtree_search() -> None:
    server = LdapServer(directory=build_directory(PRINCIPALS))
    requests = [
        _bind(1, "", ""),
        _search_present(2, "dc=agd,dc=uiao,dc=gov"),
        ber.encode_sequence([ber.encode_integer(3), ber.encode_null(tag=protocol.APP_UNBIND_REQUEST)]),
    ]
    responses = asyncio.run(_run_session(server, requests))
    # bindResponse + 4 searchResultEntry (base, people, alice, bob) + searchResultDone.
    tags = [r and ber.read_children(r.content)[1].tag for r in responses]
    assert tags[0] == protocol.APP_BIND_RESPONSE
    assert _result_code(responses[0]) == int(protocol.ResultCode.SUCCESS)
    entries = [t for t in tags if t == protocol.APP_SEARCH_RESULT_ENTRY]
    assert len(entries) == 4
    assert tags[-1] == protocol.APP_SEARCH_RESULT_DONE


def test_simple_bind_rejects_bad_credentials() -> None:
    server = LdapServer(directory=build_directory(PRINCIPALS), credentials={"cn=admin": "right"})
    responses = asyncio.run(_run_session(server, [_bind(1, "cn=admin", "wrong")]))
    assert _result_code(responses[0]) == int(protocol.ResultCode.INVALID_CREDENTIALS)


def test_simple_bind_accepts_good_credentials() -> None:
    server = LdapServer(directory=build_directory(PRINCIPALS), credentials={"cn=admin": "right"})
    responses = asyncio.run(_run_session(server, [_bind(1, "cn=admin", "right")]))
    assert _result_code(responses[0]) == int(protocol.ResultCode.SUCCESS)


def test_non_v3_bind_is_protocol_error() -> None:
    server = LdapServer(directory=build_directory(PRINCIPALS))
    responses = asyncio.run(_run_session(server, [_bind(1, "", "", version=2)]))
    assert _result_code(responses[0]) == int(protocol.ResultCode.PROTOCOL_ERROR)


def test_size_limit_truncates_and_reports() -> None:
    server = LdapServer(directory=build_directory(PRINCIPALS), size_limit=2)
    responses = asyncio.run(_run_session(server, [_search_present(1, "dc=agd,dc=uiao,dc=gov")]))
    tags = [ber.read_children(r.content)[1].tag for r in responses]
    assert tags.count(protocol.APP_SEARCH_RESULT_ENTRY) == 2
    assert tags[-1] == protocol.APP_SEARCH_RESULT_DONE


def _modify(message_id: int, dn: str) -> bytes:
    # A well-formed ModifyRequest the read projection must refuse, not service.
    op = ber.encode_sequence(
        [ber.encode_octet_string(dn), ber.encode_sequence([])],
        tag=protocol.APP_MODIFY_REQUEST,
    )
    return ber.encode_sequence([ber.encode_integer(message_id), op])


def test_unsupported_write_op_is_refused_without_dropping_connection() -> None:
    # A write op must come back as unwillingToPerform on the matching
    # response type, and the connection must survive so the following
    # search still succeeds (ADR-100: refuse, don't drop).
    server = LdapServer(directory=build_directory(PRINCIPALS))
    requests = [
        _modify(1, "cn=alice-uiao.gov,ou=people,dc=agd,dc=uiao,dc=gov"),
        _search_present(2, "dc=agd,dc=uiao,dc=gov"),
    ]
    responses = asyncio.run(_run_session(server, requests))
    refusal = responses[0]
    assert ber.read_children(refusal.content)[1].tag == protocol.APP_MODIFY_RESPONSE
    assert _result_code(refusal) == int(protocol.ResultCode.UNWILLING_TO_PERFORM)
    later_tags = [ber.read_children(r.content)[1].tag for r in responses[1:]]
    assert protocol.APP_SEARCH_RESULT_ENTRY in later_tags
    assert later_tags[-1] == protocol.APP_SEARCH_RESULT_DONE


def test_search_missing_base_returns_no_such_object() -> None:
    # A base object absent from the tree is noSuchObject (RFC 4511 §4.5.3),
    # not success/0 entries.
    server = LdapServer(directory=build_directory(PRINCIPALS))
    responses = asyncio.run(_run_session(server, [_search_present(1, "ou=ghosts,dc=agd,dc=uiao,dc=gov")]))
    tags = [ber.read_children(r.content)[1].tag for r in responses]
    assert tags.count(protocol.APP_SEARCH_RESULT_ENTRY) == 0
    assert tags[-1] == protocol.APP_SEARCH_RESULT_DONE
    assert _result_code(responses[-1]) == int(protocol.ResultCode.NO_SUCH_OBJECT)


def _entry_attr_names(envelope: ber.TLV) -> set[str]:
    """Attribute names carried by a SearchResultEntry envelope."""
    _, op = ber.read_children(envelope.content)
    _dn, attrs_seq = ber.read_children(op.content)
    return {
        ber.decode_octet_string(ber.read_children(a.content)[0].content) for a in ber.read_children(attrs_seq.content)
    }


def _entry_dn(envelope: ber.TLV) -> str:
    _, op = ber.read_children(envelope.content)
    dn_tlv, _attrs = ber.read_children(op.content)
    return ber.decode_octet_string(dn_tlv.content)


# A principal whose facets include the default-sensitive clearance + cost-center.
CLEARED = [
    {
        "principal_id": "alice@uiao.gov",
        "principal_type": "user",
        "attributes": {"extensionAttribute2": "IT", "extensionAttribute5": "CC-4200", "extensionAttribute9": "Secret"},
    },
]


def test_anonymous_search_redacts_sensitive_facets() -> None:
    server = LdapServer(directory=build_directory(CLEARED))
    responses = asyncio.run(_run_session(server, [_search_present(1, "dc=agd,dc=uiao,dc=gov")]))
    alice = next(r for r in responses if _is_entry(r) and "alice" in _entry_dn(r))
    names = _entry_attr_names(alice)
    assert "uiaoOrgPathClearanceLevel" not in names
    assert "uiaoOrgPathCostCenter" not in names
    assert "uiaoOrgPathDepartment" in names  # non-sensitive facet still visible


def test_authenticated_search_reveals_sensitive_facets() -> None:
    server = LdapServer(directory=build_directory(CLEARED), credentials={"cn=admin": "pw"})
    requests = [_bind(1, "cn=admin", "pw"), _search_present(2, "dc=agd,dc=uiao,dc=gov")]
    responses = asyncio.run(_run_session(server, requests))
    alice = next(r for r in responses if _is_entry(r) and "alice" in _entry_dn(r))
    names = _entry_attr_names(alice)
    assert "uiaoOrgPathClearanceLevel" in names
    assert "uiaoOrgPathCostCenter" in names


def _is_entry(envelope: ber.TLV) -> bool:
    return ber.read_children(envelope.content)[1].tag == protocol.APP_SEARCH_RESULT_ENTRY


def _starttls(message_id: int) -> bytes:
    op = ber.encode_sequence(
        [ber.encode_octet_string(protocol.STARTTLS_OID, tag=protocol.EXT_REQUEST_NAME)],
        tag=protocol.APP_EXTENDED_REQUEST,
    )
    return ber.encode_sequence([ber.encode_integer(message_id), op])


def test_starttls_refused_when_not_configured() -> None:
    # No tls_context -> StartTLS is refused (unwillingToPerform) but the
    # connection survives so a following search still works.
    server = LdapServer(directory=build_directory(PRINCIPALS))
    requests = [_starttls(1), _search_present(2, "dc=agd,dc=uiao,dc=gov")]
    responses = asyncio.run(_run_session(server, requests))
    ack_op = ber.read_children(responses[0].content)[1]
    assert ack_op.tag == protocol.APP_EXTENDED_RESPONSE
    assert ber.decode_integer(ber.read_children(ack_op.content)[0].content) == int(
        protocol.ResultCode.UNWILLING_TO_PERFORM
    )
    later = [ber.read_children(r.content)[1].tag for r in responses[1:]]
    assert protocol.APP_SEARCH_RESULT_ENTRY in later


def test_unknown_extended_op_is_protocol_error() -> None:
    op = ber.encode_sequence(
        [ber.encode_octet_string("1.2.3.4.5", tag=protocol.EXT_REQUEST_NAME)],
        tag=protocol.APP_EXTENDED_REQUEST,
    )
    msg = ber.encode_sequence([ber.encode_integer(1), op])
    server = LdapServer(directory=build_directory(PRINCIPALS))
    responses = asyncio.run(_run_session(server, [msg]))
    ack_op = ber.read_children(responses[0].content)[1]
    assert ack_op.tag == protocol.APP_EXTENDED_RESPONSE
    assert ber.decode_integer(ber.read_children(ack_op.content)[0].content) == int(protocol.ResultCode.PROTOCOL_ERROR)


def test_search_existing_base_no_match_is_success() -> None:
    # Base exists but the filter matches nothing -> success, 0 entries.
    server = LdapServer(directory=build_directory(PRINCIPALS))
    eq = ber.encode_tlv(
        protocol.FILTER_EQUALITY,
        ber.encode_octet_string("uiaoOrgPathRegion") + ber.encode_octet_string("NOWHERE"),
    )
    op = ber.encode_sequence(
        [
            ber.encode_octet_string("dc=agd,dc=uiao,dc=gov"),
            ber.encode_enumerated(int(protocol.Scope.WHOLE_SUBTREE)),
            ber.encode_enumerated(0),
            ber.encode_integer(0),
            ber.encode_integer(0),
            ber.encode_boolean(False),
            eq,
            ber.encode_sequence([]),
        ],
        tag=protocol.APP_SEARCH_REQUEST,
    )
    msg = ber.encode_sequence([ber.encode_integer(1), op])
    responses = asyncio.run(_run_session(server, [msg]))
    tags = [ber.read_children(r.content)[1].tag for r in responses]
    assert tags.count(protocol.APP_SEARCH_RESULT_ENTRY) == 0
    assert _result_code(responses[-1]) == int(protocol.ResultCode.SUCCESS)
