"""LDAPv3 protocol messages for the Active Governance Directory (RFC 4511).

Parses the inbound ``protocolOp`` subset the AGD answers — ``BindRequest``,
``SearchRequest``, ``UnbindRequest`` — and serializes the responses
(``BindResponse``, ``SearchResultEntry``, ``SearchResultDone``). The
search ``Filter`` choice is modelled as a small algebraic tree
(:class:`Filter`) so :mod:`uiao.directory.dit` can evaluate it against a
projected entry.

Out of scope for this first increment (ADR-100 roadmap): modify/add/
delete/compare write ops, SASL/StartTLS, controls, paged results, and
the extensible-match filter choice. Unsupported protocol ops are
surfaced as :class:`UnsupportedOperation` so the server answers
``unwillingToPerform`` rather than dropping the connection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from uiao.directory import ber

# --- Application tags (RFC 4511 §4.1.1) ------------------------------------
APP_BIND_REQUEST = ber.APPLICATION | ber.CONSTRUCTED | 0  # 0x60
APP_BIND_RESPONSE = ber.APPLICATION | ber.CONSTRUCTED | 1  # 0x61
APP_UNBIND_REQUEST = ber.APPLICATION | 2  # 0x42 (primitive, NULL)
APP_SEARCH_REQUEST = ber.APPLICATION | ber.CONSTRUCTED | 3  # 0x63
APP_SEARCH_RESULT_ENTRY = ber.APPLICATION | ber.CONSTRUCTED | 4  # 0x64
APP_SEARCH_RESULT_DONE = ber.APPLICATION | ber.CONSTRUCTED | 5  # 0x65

# Write/compare/extended request tags — never serviced (read projection,
# ADR-100), but recognised so the server can refuse them with
# ``unwillingToPerform`` keyed to the matching response type rather than
# silently dropping the request.
APP_MODIFY_REQUEST = ber.APPLICATION | ber.CONSTRUCTED | 6  # 0x66
APP_MODIFY_RESPONSE = ber.APPLICATION | ber.CONSTRUCTED | 7  # 0x67
APP_ADD_REQUEST = ber.APPLICATION | ber.CONSTRUCTED | 8  # 0x68
APP_ADD_RESPONSE = ber.APPLICATION | ber.CONSTRUCTED | 9  # 0x69
APP_DEL_REQUEST = ber.APPLICATION | 10  # 0x4a (primitive, LDAPDN)
APP_DEL_RESPONSE = ber.APPLICATION | ber.CONSTRUCTED | 11  # 0x6b
APP_MODIFY_DN_REQUEST = ber.APPLICATION | ber.CONSTRUCTED | 12  # 0x6c
APP_MODIFY_DN_RESPONSE = ber.APPLICATION | ber.CONSTRUCTED | 13  # 0x6d
APP_COMPARE_REQUEST = ber.APPLICATION | ber.CONSTRUCTED | 14  # 0x6e
APP_COMPARE_RESPONSE = ber.APPLICATION | ber.CONSTRUCTED | 15  # 0x6f
APP_EXTENDED_REQUEST = ber.APPLICATION | ber.CONSTRUCTED | 23  # 0x77
APP_EXTENDED_RESPONSE = ber.APPLICATION | ber.CONSTRUCTED | 24  # 0x78

# --- Authentication choice (context tags inside BindRequest) ---------------
AUTH_SIMPLE = ber.CONTEXT | 0  # [0] simple password (primitive)

# --- Filter choice context tags (RFC 4511 §4.5.1) --------------------------
FILTER_AND = ber.CONTEXT | ber.CONSTRUCTED | 0
FILTER_OR = ber.CONTEXT | ber.CONSTRUCTED | 1
FILTER_NOT = ber.CONTEXT | ber.CONSTRUCTED | 2
FILTER_EQUALITY = ber.CONTEXT | ber.CONSTRUCTED | 3
FILTER_SUBSTRINGS = ber.CONTEXT | ber.CONSTRUCTED | 4
FILTER_PRESENT = ber.CONTEXT | 7  # [7] AttributeDescription (primitive)

# Substring component tags (inside the substrings SEQUENCE OF CHOICE).
SUB_INITIAL = ber.CONTEXT | 0
SUB_ANY = ber.CONTEXT | 1
SUB_FINAL = ber.CONTEXT | 2


class ResultCode(IntEnum):
    """The LDAP result codes the AGD emits (RFC 4511 §4.1.9)."""

    SUCCESS = 0
    OPERATIONS_ERROR = 1
    PROTOCOL_ERROR = 2
    NO_SUCH_OBJECT = 32
    INVALID_CREDENTIALS = 49
    UNWILLING_TO_PERFORM = 53


class Scope(IntEnum):
    """SearchRequest scope (RFC 4511 §4.5.1.2)."""

    BASE_OBJECT = 0
    SINGLE_LEVEL = 1
    WHOLE_SUBTREE = 2


class ProtocolError(ValueError):
    """Raised when an inbound message is structurally invalid."""


class UnsupportedOperation(ProtocolError):
    """Raised for a well-formed but unsupported protocol op.

    Carries the originating ``message_id`` and request ``op_tag`` so the
    server can answer ``unwillingToPerform`` keyed to the request (RFC 4511
    §4.2) instead of dropping the connection.
    """

    def __init__(self, message: str, *, message_id: int = 0, op_tag: int = 0) -> None:
        super().__init__(message)
        self.message_id = message_id
        self.op_tag = op_tag


# ---------------------------------------------------------------------------
# Filter model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Filter:
    """A node in the search-filter tree.

    ``kind`` is one of ``and`` / ``or`` / ``not`` / ``equality`` /
    ``present`` / ``substrings``. The remaining fields are populated per
    kind: ``children`` for and/or/not; ``attribute`` for every leaf;
    ``value`` for equality; ``initial`` / ``any`` / ``final`` for
    substrings.
    """

    kind: str
    attribute: str = ""
    value: str = ""
    children: tuple[Filter, ...] = ()
    initial: str | None = None
    any: tuple[str, ...] = ()
    final: str | None = None


# ---------------------------------------------------------------------------
# Inbound message dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BindRequest:
    message_id: int
    version: int
    name: str
    password: str


@dataclass(frozen=True)
class SearchRequest:
    message_id: int
    base_object: str
    scope: Scope
    size_limit: int
    filter: Filter
    attributes: tuple[str, ...]


@dataclass(frozen=True)
class UnbindRequest:
    message_id: int


@dataclass(frozen=True)
class ExtendedRequest:
    """An LDAPv3 ExtendedRequest ([APPLICATION 23], RFC 4511 §4.12).

    Only the ``request_name`` OID is decoded — that is all the AGD needs to
    recognise StartTLS (:data:`STARTTLS_OID`). ``request_value`` is carried
    verbatim for completeness.
    """

    message_id: int
    request_name: str
    request_value: bytes | None = None


# The StartTLS extended-operation OID (RFC 4511 §4.14.1 / RFC 2830).
STARTTLS_OID = "1.3.6.1.4.1.1466.20037"

# ExtendedRequest field tags (context-specific, primitive).
EXT_REQUEST_NAME = ber.CONTEXT | 0  # [0] requestName  LDAPOID
EXT_REQUEST_VALUE = ber.CONTEXT | 1  # [1] requestValue OCTET STRING
EXT_RESPONSE_NAME = ber.CONTEXT | 10  # [10] responseName LDAPOID


@dataclass(frozen=True)
class Entry:
    """A directory entry to serialize into a SearchResultEntry."""

    dn: str
    attributes: dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Inbound parsing
# ---------------------------------------------------------------------------
def parse_message(data: bytes) -> BindRequest | SearchRequest | UnbindRequest | ExtendedRequest:
    """Parse one complete ``LDAPMessage`` envelope into a request object."""
    envelope, _ = ber.read_tlv(data)
    if envelope.tag != ber.TAG_SEQUENCE:
        raise ProtocolError("LDAPMessage must be a SEQUENCE")
    parts = ber.read_children(envelope.content)
    if len(parts) < 2:
        raise ProtocolError("LDAPMessage requires messageID and protocolOp")
    if parts[0].tag != ber.TAG_INTEGER:
        raise ProtocolError("messageID must be an INTEGER")
    message_id = ber.decode_integer(parts[0].content)
    op = parts[1]

    if op.tag == APP_BIND_REQUEST:
        return _parse_bind(message_id, op)
    if op.tag == APP_SEARCH_REQUEST:
        return _parse_search(message_id, op)
    if op.tag == APP_UNBIND_REQUEST:
        return UnbindRequest(message_id=message_id)
    if op.tag == APP_EXTENDED_REQUEST:
        return _parse_extended(message_id, op)
    raise UnsupportedOperation(
        f"protocolOp tag 0x{op.tag:02x} is not supported",
        message_id=message_id,
        op_tag=op.tag,
    )


def _parse_extended(message_id: int, op: ber.TLV) -> ExtendedRequest:
    parts = ber.read_children(op.content)
    if not parts or parts[0].tag != EXT_REQUEST_NAME:
        raise ProtocolError("ExtendedRequest requires a requestName [0]")
    request_name = ber.decode_octet_string(parts[0].content)
    request_value = None
    for extra in parts[1:]:
        if extra.tag == EXT_REQUEST_VALUE:
            request_value = extra.content
    return ExtendedRequest(message_id=message_id, request_name=request_name, request_value=request_value)


def _parse_bind(message_id: int, op: ber.TLV) -> BindRequest:
    parts = ber.read_children(op.content)
    if len(parts) < 3:
        raise ProtocolError("BindRequest requires version, name, authentication")
    version = ber.decode_integer(parts[0].content)
    name = ber.decode_octet_string(parts[1].content)
    auth = parts[2]
    if auth.tag != AUTH_SIMPLE:
        raise UnsupportedOperation(
            "only simple authentication is supported",
            message_id=message_id,
            op_tag=APP_BIND_REQUEST,
        )
    return BindRequest(
        message_id=message_id,
        version=version,
        name=name,
        password=ber.decode_octet_string(auth.content),
    )


def _parse_search(message_id: int, op: ber.TLV) -> SearchRequest:
    parts = ber.read_children(op.content)
    if len(parts) < 8:
        raise ProtocolError("SearchRequest requires eight components")
    base_object = ber.decode_octet_string(parts[0].content)
    scope = Scope(ber.decode_integer(parts[1].content))
    size_limit = ber.decode_integer(parts[3].content)
    try:
        search_filter = _parse_filter(parts[6])
    except UnsupportedOperation as exc:
        # Re-key an unsupported filter choice to the search so the server
        # can answer searchResultDone(unwillingToPerform) for this message.
        raise UnsupportedOperation(str(exc), message_id=message_id, op_tag=APP_SEARCH_REQUEST) from exc
    attributes = tuple(ber.decode_octet_string(a.content) for a in ber.read_children(parts[7].content))
    return SearchRequest(
        message_id=message_id,
        base_object=base_object,
        scope=scope,
        size_limit=size_limit,
        filter=search_filter,
        attributes=attributes,
    )


def _parse_filter(tlv: ber.TLV) -> Filter:
    if tlv.tag == FILTER_PRESENT:
        return Filter(kind="present", attribute=ber.decode_octet_string(tlv.content))
    if tlv.tag in (FILTER_AND, FILTER_OR):
        children = tuple(_parse_filter(c) for c in ber.read_children(tlv.content))
        return Filter(kind="and" if tlv.tag == FILTER_AND else "or", children=children)
    if tlv.tag == FILTER_NOT:
        inner, _ = ber.read_tlv(tlv.content)
        return Filter(kind="not", children=(_parse_filter(inner),))
    if tlv.tag == FILTER_EQUALITY:
        attr, val = ber.read_children(tlv.content)
        return Filter(
            kind="equality",
            attribute=ber.decode_octet_string(attr.content),
            value=ber.decode_octet_string(val.content),
        )
    if tlv.tag == FILTER_SUBSTRINGS:
        return _parse_substrings(tlv)
    raise UnsupportedOperation(f"filter choice tag 0x{tlv.tag:02x} is not supported")


def _parse_substrings(tlv: ber.TLV) -> Filter:
    attr_tlv, seq_tlv = ber.read_children(tlv.content)
    attribute = ber.decode_octet_string(attr_tlv.content)
    initial: str | None = None
    final: str | None = None
    anys: list[str] = []
    for part in ber.read_children(seq_tlv.content):
        text = ber.decode_octet_string(part.content)
        if part.tag == SUB_INITIAL:
            initial = text
        elif part.tag == SUB_FINAL:
            final = text
        elif part.tag == SUB_ANY:
            anys.append(text)
    return Filter(kind="substrings", attribute=attribute, initial=initial, any=tuple(anys), final=final)


# ---------------------------------------------------------------------------
# Outbound serialization
# ---------------------------------------------------------------------------
def _envelope(message_id: int, protocol_op: bytes) -> bytes:
    return ber.encode_sequence([ber.encode_integer(message_id), protocol_op])


def _ldap_result(code: ResultCode, matched_dn: str = "", message: str = "") -> list[bytes]:
    return [
        ber.encode_enumerated(int(code)),
        ber.encode_octet_string(matched_dn),
        ber.encode_octet_string(message),
    ]


def encode_bind_response(message_id: int, code: ResultCode, message: str = "") -> bytes:
    op = ber.encode_sequence(_ldap_result(code, message=message), tag=APP_BIND_RESPONSE)
    return _envelope(message_id, op)


def encode_search_result_done(message_id: int, code: ResultCode, message: str = "", matched_dn: str = "") -> bytes:
    op = ber.encode_sequence(_ldap_result(code, matched_dn=matched_dn, message=message), tag=APP_SEARCH_RESULT_DONE)
    return _envelope(message_id, op)


def encode_search_result_entry(message_id: int, entry: Entry) -> bytes:
    attr_items: list[bytes] = []
    for name, values in entry.attributes.items():
        vals_set = ber.encode_set([ber.encode_octet_string(v) for v in values])
        attr_items.append(ber.encode_sequence([ber.encode_octet_string(name), vals_set]))
    op = ber.encode_sequence(
        [ber.encode_octet_string(entry.dn), ber.encode_sequence(attr_items)],
        tag=APP_SEARCH_RESULT_ENTRY,
    )
    return _envelope(message_id, op)


# Maps a request op tag to the response op tag that correlates with it, so an
# unsupported-but-well-formed op can be refused with the right response type.
# Every listed response body is a bare LDAPResult (a valid prefix for
# BindResponse / ExtendedResponse too), which is all an unwilling refusal needs.
_RESPONSE_FOR_REQUEST = {
    APP_BIND_REQUEST: APP_BIND_RESPONSE,
    APP_SEARCH_REQUEST: APP_SEARCH_RESULT_DONE,
    APP_MODIFY_REQUEST: APP_MODIFY_RESPONSE,
    APP_ADD_REQUEST: APP_ADD_RESPONSE,
    APP_DEL_REQUEST: APP_DEL_RESPONSE,
    APP_MODIFY_DN_REQUEST: APP_MODIFY_DN_RESPONSE,
    APP_COMPARE_REQUEST: APP_COMPARE_RESPONSE,
    APP_EXTENDED_REQUEST: APP_EXTENDED_RESPONSE,
}


def encode_unwilling_response(message_id: int, op_tag: int, message: str = "") -> bytes | None:
    """Refuse an unsupported op with ``unwillingToPerform`` (RFC 4511 §4.2).

    Returns the encoded response keyed to ``op_tag``'s correlating response
    type, or ``None`` when the request type has no response to correlate
    against (the server then logs and ignores rather than fabricating a
    reply the client could not match to its request).
    """
    response_tag = _RESPONSE_FOR_REQUEST.get(op_tag)
    if response_tag is None:
        return None
    op = ber.encode_sequence(_ldap_result(ResultCode.UNWILLING_TO_PERFORM, message=message), tag=response_tag)
    return _envelope(message_id, op)


def encode_extended_response(
    message_id: int,
    code: ResultCode,
    *,
    response_name: str | None = None,
    message: str = "",
) -> bytes:
    """Encode an ExtendedResponse ([APPLICATION 24], RFC 4511 §4.12).

    ``response_name`` (the [10] OID) is echoed on a successful StartTLS so
    the client can correlate the upgrade; it is omitted on refusal.
    """
    fields = _ldap_result(code, message=message)
    if response_name is not None:
        fields.append(ber.encode_octet_string(response_name, tag=EXT_RESPONSE_NAME))
    op = ber.encode_sequence(fields, tag=APP_EXTENDED_RESPONSE)
    return _envelope(message_id, op)
