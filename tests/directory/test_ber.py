"""BER/ASN.1 codec tests for the Active Governance Directory (ADR-099)."""

from __future__ import annotations

import pytest

from uiao.directory import ber


@pytest.mark.parametrize("value", [0, 1, 127, 128, 255, 256, 65535, 1234567, -1, -128, -129, -32768])
def test_integer_round_trip(value: int) -> None:
    tlv, offset = ber.read_tlv(ber.encode_integer(value))
    assert tlv.tag == ber.TAG_INTEGER
    assert ber.decode_integer(tlv.content) == value
    assert offset == len(ber.encode_integer(value))


def test_integer_minimal_encoding() -> None:
    # 128 needs a leading 0x00 to stay positive in two's complement.
    tlv, _ = ber.read_tlv(ber.encode_integer(128))
    assert tlv.content == b"\x00\x80"
    # 127 must not carry a redundant sign octet.
    tlv2, _ = ber.read_tlv(ber.encode_integer(127))
    assert tlv2.content == b"\x7f"


def test_boolean_round_trip() -> None:
    assert ber.decode_boolean(ber.read_tlv(ber.encode_boolean(True))[0].content) is True
    assert ber.decode_boolean(ber.read_tlv(ber.encode_boolean(False))[0].content) is False


def test_octet_string_round_trip() -> None:
    tlv, _ = ber.read_tlv(ber.encode_octet_string("uiaoOrgPathRegion"))
    assert ber.decode_octet_string(tlv.content) == "uiaoOrgPathRegion"


def test_long_form_length() -> None:
    payload = b"x" * 1000
    encoded = ber.encode_octet_string(payload)
    tlv, offset = ber.read_tlv(encoded)
    assert tlv.content == payload
    assert offset == len(encoded)


def test_sequence_and_children() -> None:
    seq = ber.encode_sequence([ber.encode_integer(5), ber.encode_octet_string("x")])
    tlv, _ = ber.read_tlv(seq)
    assert tlv.tag == ber.TAG_SEQUENCE
    children = ber.read_children(tlv.content)
    assert len(children) == 2
    assert ber.decode_integer(children[0].content) == 5
    assert ber.decode_octet_string(children[1].content) == "x"


def test_truncated_content_raises() -> None:
    good = ber.encode_octet_string("hello")
    with pytest.raises(ber.BERError):
        ber.read_tlv(good[:-2])


def test_indefinite_length_rejected() -> None:
    with pytest.raises(ber.BERError):
        ber.read_length(bytes((0x80,)), 0)


def test_high_tag_number_rejected() -> None:
    with pytest.raises(ber.BERError):
        ber.read_tlv(bytes((0x1F, 0x01, 0x00)))
