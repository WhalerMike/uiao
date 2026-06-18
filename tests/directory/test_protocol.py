"""LDAPv3 protocol parse/serialize tests (ADR-100)."""

from __future__ import annotations

import pytest

from uiao.directory import ber, protocol


def _bind_request(message_id: int, version: int, name: str, password: str) -> bytes:
    op = ber.encode_sequence(
        [
            ber.encode_integer(version),
            ber.encode_octet_string(name),
            ber.encode_octet_string(password, tag=protocol.AUTH_SIMPLE),
        ],
        tag=protocol.APP_BIND_REQUEST,
    )
    return ber.encode_sequence([ber.encode_integer(message_id), op])


def _search_request(message_id: int, base: str, scope: int, filt: bytes, attributes: list[str]) -> bytes:
    op = ber.encode_sequence(
        [
            ber.encode_octet_string(base),
            ber.encode_enumerated(scope),
            ber.encode_enumerated(0),
            ber.encode_integer(0),
            ber.encode_integer(0),
            ber.encode_boolean(False),
            filt,
            ber.encode_sequence([ber.encode_octet_string(a) for a in attributes]),
        ],
        tag=protocol.APP_SEARCH_REQUEST,
    )
    return ber.encode_sequence([ber.encode_integer(message_id), op])


def _equality(attr: str, value: str) -> bytes:
    return ber.encode_tlv(protocol.FILTER_EQUALITY, ber.encode_octet_string(attr) + ber.encode_octet_string(value))


def test_parse_bind_request() -> None:
    req = protocol.parse_message(_bind_request(1, 3, "cn=admin", "secret"))
    assert isinstance(req, protocol.BindRequest)
    assert (req.message_id, req.version, req.name, req.password) == (1, 3, "cn=admin", "secret")


def test_parse_anonymous_bind() -> None:
    req = protocol.parse_message(_bind_request(1, 3, "", ""))
    assert isinstance(req, protocol.BindRequest)
    assert req.name == "" and req.password == ""


def test_parse_unbind_request() -> None:
    op = ber.encode_null(tag=protocol.APP_UNBIND_REQUEST)
    msg = ber.encode_sequence([ber.encode_integer(7), op])
    req = protocol.parse_message(msg)
    assert isinstance(req, protocol.UnbindRequest)
    assert req.message_id == 7


def test_parse_present_filter() -> None:
    filt = ber.encode_octet_string("objectClass", tag=protocol.FILTER_PRESENT)
    req = protocol.parse_message(_search_request(2, "dc=x", 2, filt, []))
    assert isinstance(req, protocol.SearchRequest)
    assert req.scope == protocol.Scope.WHOLE_SUBTREE
    assert req.filter.kind == "present"
    assert req.filter.attribute == "objectClass"


def test_parse_and_filter_with_equality() -> None:
    filt = ber.encode_tlv(
        protocol.FILTER_AND,
        _equality("objectClass", "person") + _equality("uiaoOrgPathDepartment", "IT"),
    )
    req = protocol.parse_message(_search_request(3, "ou=people,dc=x", 1, filt, ["cn"]))
    assert req.filter.kind == "and"
    assert {c.attribute for c in req.filter.children} == {"objectClass", "uiaoOrgPathDepartment"}
    assert req.attributes == ("cn",)


def test_parse_substrings_filter() -> None:
    sub_seq = ber.encode_sequence(
        [
            ber.encode_octet_string("al", tag=protocol.SUB_INITIAL),
            ber.encode_octet_string("gov", tag=protocol.SUB_FINAL),
        ]
    )
    filt = ber.encode_tlv(protocol.FILTER_SUBSTRINGS, ber.encode_octet_string("cn") + sub_seq)
    req = protocol.parse_message(_search_request(4, "dc=x", 2, filt, []))
    assert req.filter.kind == "substrings"
    assert req.filter.initial == "al"
    assert req.filter.final == "gov"


def test_unsupported_op_raises() -> None:
    # ModifyRequest [APPLICATION 6] is not implemented.
    op = ber.encode_sequence([], tag=ber.APPLICATION | ber.CONSTRUCTED | 6)
    msg = ber.encode_sequence([ber.encode_integer(9), op])
    with pytest.raises(protocol.UnsupportedOperation):
        protocol.parse_message(msg)


def test_unsupported_auth_raises() -> None:
    # An unrecognised authentication choice (neither simple [0] nor SASL [3])
    # is rejected; here a made-up [5] context tag.
    op = ber.encode_sequence(
        [
            ber.encode_integer(3),
            ber.encode_octet_string(""),
            ber.encode_octet_string("x", tag=ber.CONTEXT | 5),
        ],
        tag=protocol.APP_BIND_REQUEST,
    )
    msg = ber.encode_sequence([ber.encode_integer(1), op])
    with pytest.raises(protocol.UnsupportedOperation):
        protocol.parse_message(msg)


def test_encode_bind_response_round_trips() -> None:
    raw = protocol.encode_bind_response(5, protocol.ResultCode.SUCCESS)
    envelope, _ = ber.read_tlv(raw)
    mid, op = ber.read_children(envelope.content)
    assert ber.decode_integer(mid.content) == 5
    assert op.tag == protocol.APP_BIND_RESPONSE
    code = ber.read_children(op.content)[0]
    assert ber.decode_integer(code.content) == int(protocol.ResultCode.SUCCESS)


def _sasl_bind(message_id: int, mechanism: str, credentials: bytes | None) -> bytes:
    sasl_fields = [ber.encode_octet_string(mechanism)]
    if credentials is not None:
        sasl_fields.append(ber.encode_octet_string(credentials))
    auth = ber.encode_sequence(sasl_fields, tag=protocol.AUTH_SASL)
    op = ber.encode_sequence([ber.encode_integer(3), ber.encode_octet_string(""), auth], tag=protocol.APP_BIND_REQUEST)
    return ber.encode_sequence([ber.encode_integer(message_id), op])


def test_parse_sasl_bind_request() -> None:
    req = protocol.parse_message(_sasl_bind(1, "GSSAPI", b"\x60\x01\x02"))
    assert isinstance(req, protocol.SaslBindRequest)
    assert req.mechanism == "GSSAPI"
    assert req.credentials == b"\x60\x01\x02"


def test_parse_sasl_bind_without_credentials() -> None:
    req = protocol.parse_message(_sasl_bind(1, "GSSAPI", None))
    assert isinstance(req, protocol.SaslBindRequest)
    assert req.credentials is None


def test_encode_bind_response_with_server_sasl_creds_round_trips() -> None:
    raw = protocol.encode_bind_response(2, protocol.ResultCode.SASL_BIND_IN_PROGRESS, server_sasl_creds=b"\xaa\xbb")
    envelope, _ = ber.read_tlv(raw)
    _, op = ber.read_children(envelope.content)
    assert op.tag == protocol.APP_BIND_RESPONSE
    parts = ber.read_children(op.content)
    assert ber.decode_integer(parts[0].content) == int(protocol.ResultCode.SASL_BIND_IN_PROGRESS)
    creds = next(p for p in parts if p.tag == protocol.SERVER_SASL_CREDS)
    assert creds.content == b"\xaa\xbb"


def test_parse_starttls_extended_request() -> None:
    op = ber.encode_sequence(
        [ber.encode_octet_string(protocol.STARTTLS_OID, tag=protocol.EXT_REQUEST_NAME)],
        tag=protocol.APP_EXTENDED_REQUEST,
    )
    msg = ber.encode_sequence([ber.encode_integer(8), op])
    req = protocol.parse_message(msg)
    assert isinstance(req, protocol.ExtendedRequest)
    assert req.message_id == 8
    assert req.request_name == protocol.STARTTLS_OID


def test_extended_request_without_name_is_protocol_error() -> None:
    op = ber.encode_sequence([], tag=protocol.APP_EXTENDED_REQUEST)
    msg = ber.encode_sequence([ber.encode_integer(1), op])
    with pytest.raises(protocol.ProtocolError):
        protocol.parse_message(msg)


def test_encode_extended_response_with_name_round_trips() -> None:
    raw = protocol.encode_extended_response(9, protocol.ResultCode.SUCCESS, response_name=protocol.STARTTLS_OID)
    envelope, _ = ber.read_tlv(raw)
    mid, op = ber.read_children(envelope.content)
    assert ber.decode_integer(mid.content) == 9
    assert op.tag == protocol.APP_EXTENDED_RESPONSE
    parts = ber.read_children(op.content)
    assert ber.decode_integer(parts[0].content) == int(protocol.ResultCode.SUCCESS)
    name = next(p for p in parts if p.tag == protocol.EXT_RESPONSE_NAME)
    assert ber.decode_octet_string(name.content) == protocol.STARTTLS_OID


def test_encode_extended_response_refusal_omits_name() -> None:
    raw = protocol.encode_extended_response(9, protocol.ResultCode.UNWILLING_TO_PERFORM)
    envelope, _ = ber.read_tlv(raw)
    _, op = ber.read_children(envelope.content)
    parts = ber.read_children(op.content)
    assert all(p.tag != protocol.EXT_RESPONSE_NAME for p in parts)


def test_encode_search_result_entry_round_trips() -> None:
    entry = protocol.Entry(dn="cn=alice,dc=x", attributes={"cn": ["alice"], "uiaoOrgPathRegion": ["NCR"]})
    raw = protocol.encode_search_result_entry(6, entry)
    envelope, _ = ber.read_tlv(raw)
    _, op = ber.read_children(envelope.content)
    assert op.tag == protocol.APP_SEARCH_RESULT_ENTRY
    dn_tlv, attrs_tlv = ber.read_children(op.content)
    assert ber.decode_octet_string(dn_tlv.content) == "cn=alice,dc=x"
    attr_names = {
        ber.decode_octet_string(ber.read_children(a.content)[0].content) for a in ber.read_children(attrs_tlv.content)
    }
    assert attr_names == {"cn", "uiaoOrgPathRegion"}
