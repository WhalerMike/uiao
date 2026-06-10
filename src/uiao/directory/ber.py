"""Minimal BER/ASN.1 codec for the LDAP subset (RFC 4511 §5.1).

LDAP rides on the Basic Encoding Rules of ASN.1. This module implements
just enough of BER to encode and decode ``LDAPMessage`` and its
``protocolOp`` children — the *Active Governance Directory* (AGD) speaks
the wire protocol directly rather than depending on a third-party LDAP
stack, keeping the in-path directory data plane (ADR-099) pure-stdlib.

Scope is deliberately narrow:

* definite-length TLV only (LDAP never uses the indefinite form);
* the universal types LDAP uses (INTEGER, OCTET STRING, ENUMERATED,
  BOOLEAN, SEQUENCE, SET, NULL) plus arbitrary application/context tags;
* two's-complement INTEGER/ENUMERATED encoding.

It is a codec, not a validator: structural validation lives in
:mod:`uiao.directory.protocol`.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Tag classes (high two bits of the identifier octet) -------------------
UNIVERSAL = 0x00
APPLICATION = 0x40
CONTEXT = 0x80
CONSTRUCTED = 0x20

# --- Universal tags LDAP uses ----------------------------------------------
TAG_BOOLEAN = 0x01
TAG_INTEGER = 0x02
TAG_OCTET_STRING = 0x04
TAG_NULL = 0x05
TAG_ENUMERATED = 0x0A
TAG_SEQUENCE = 0x20 | 0x10  # 0x30, constructed
TAG_SET = 0x20 | 0x11  # 0x31, constructed


class BERError(ValueError):
    """Raised when a BER stream is malformed or truncated."""


# ---------------------------------------------------------------------------
# Length
# ---------------------------------------------------------------------------
def encode_length(length: int) -> bytes:
    """Encode a definite length in BER short or long form."""
    if length < 0:
        raise BERError(f"length must be non-negative, got {length}")
    if length < 0x80:
        return bytes((length,))
    body = b""
    n = length
    while n:
        body = bytes((n & 0xFF,)) + body
        n >>= 8
    if len(body) > 0x7E:
        raise BERError("length too large for BER long form")
    return bytes((0x80 | len(body),)) + body


def read_length(buf: bytes, offset: int) -> tuple[int, int]:
    """Read a definite length starting at ``offset``; return (length, next)."""
    if offset >= len(buf):
        raise BERError("truncated length octet")
    first = buf[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    num = first & 0x7F
    if num == 0:
        raise BERError("indefinite length is not permitted in LDAP BER")
    if offset + num > len(buf):
        raise BERError("truncated long-form length")
    length = int.from_bytes(buf[offset : offset + num], "big")
    return length, offset + num


# ---------------------------------------------------------------------------
# TLV
# ---------------------------------------------------------------------------
def encode_tlv(tag: int, content: bytes) -> bytes:
    """Wrap ``content`` in a tag + length envelope."""
    return bytes((tag,)) + encode_length(len(content)) + content


@dataclass(frozen=True)
class TLV:
    """A decoded tag-length-value triple."""

    tag: int
    content: bytes

    @property
    def is_constructed(self) -> bool:
        return bool(self.tag & CONSTRUCTED)

    @property
    def tag_number(self) -> int:
        """The low-5-bit tag number (class/constructed bits stripped)."""
        return self.tag & 0x1F


def read_tlv(buf: bytes, offset: int = 0) -> tuple[TLV, int]:
    """Read one TLV starting at ``offset``; return (TLV, next_offset).

    Only low-tag-number form (tag number < 31) is supported — sufficient
    for every LDAP protocol op and filter choice.
    """
    if offset >= len(buf):
        raise BERError("truncated tag octet")
    tag = buf[offset]
    if (tag & 0x1F) == 0x1F:
        raise BERError("high-tag-number form is not supported")
    offset += 1
    length, offset = read_length(buf, offset)
    end = offset + length
    if end > len(buf):
        raise BERError(f"content runs past buffer (need {end}, have {len(buf)})")
    return TLV(tag=tag, content=buf[offset:end]), end


def read_children(content: bytes) -> list[TLV]:
    """Decode every TLV in a constructed value's content."""
    out: list[TLV] = []
    offset = 0
    while offset < len(content):
        tlv, offset = read_tlv(content, offset)
        out.append(tlv)
    return out


# ---------------------------------------------------------------------------
# Primitive encoders
# ---------------------------------------------------------------------------
def encode_integer(value: int, tag: int = TAG_INTEGER) -> bytes:
    """Encode a (possibly negative) integer in two's-complement BER."""
    if value == 0:
        body = b"\x00"
    else:
        length = (value.bit_length() + 8) // 8
        body = value.to_bytes(length, "big", signed=True)
        # Strip redundant leading sign-extension octets.
        while len(body) > 1 and ((body[0] == 0x00 and not (body[1] & 0x80)) or (body[0] == 0xFF and (body[1] & 0x80))):
            body = body[1:]
    return encode_tlv(tag, body)


def encode_enumerated(value: int) -> bytes:
    return encode_integer(value, tag=TAG_ENUMERATED)


def encode_boolean(value: bool) -> bytes:
    return encode_tlv(TAG_BOOLEAN, b"\xff" if value else b"\x00")


def encode_octet_string(value: str | bytes, tag: int = TAG_OCTET_STRING) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return encode_tlv(tag, raw)


def encode_null(tag: int = TAG_NULL) -> bytes:
    return encode_tlv(tag, b"")


def encode_sequence(items: list[bytes], tag: int = TAG_SEQUENCE) -> bytes:
    return encode_tlv(tag, b"".join(items))


def encode_set(items: list[bytes], tag: int = TAG_SET) -> bytes:
    return encode_tlv(tag, b"".join(items))


# ---------------------------------------------------------------------------
# Primitive decoders
# ---------------------------------------------------------------------------
def decode_integer(content: bytes) -> int:
    if not content:
        raise BERError("empty INTEGER content")
    return int.from_bytes(content, "big", signed=True)


def decode_boolean(content: bytes) -> bool:
    if len(content) != 1:
        raise BERError("BOOLEAN content must be exactly one octet")
    return content[0] != 0x00


def decode_octet_string(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")
