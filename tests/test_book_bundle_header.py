"""Unit tests for the per-book running-header rewrite in
scripts/bundle_section_docx.py — see _stamp_book_header / _rewrite_header_xml.
"""

import importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET

_SPEC = importlib.util.spec_from_file_location(
    "bundle_section_docx",
    Path(__file__).resolve().parents[1] / "scripts" / "bundle_section_docx.py",
)
bsd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bsd)

RPR = bsd._HDR_RPR


def _field(instr: str, cached: str) -> str:
    return (
        f'<w:r>{RPR}<w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r>{RPR}<w:instrText xml:space="preserve">{instr} </w:instrText></w:r>'
        f'<w:r>{RPR}<w:fldChar w:fldCharType="separate"/></w:r>'
        f"<w:r>{RPR}<w:t>{cached}</w:t></w:r>"
        f'<w:r>{RPR}<w:fldChar w:fldCharType="end"/></w:r>'
    )


def _header() -> str:
    return (
        '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="9360"/></w:tabs></w:pPr>'
        + _field('STYLEREF "Heading 1" \\* MERGEFORMAT', "Book Title")
        + f"<w:r>{RPR}<w:tab/></w:r>"
        + _field('STYLEREF "Heading 2" \\* MERGEFORMAT', "Chapter Title")
        + "</w:p></w:hdr>"
    )


def test_left_field_becomes_static_book_title():
    out, n_left = bsd._rewrite_header_xml(_header(), "Book_05 — OrgPath and Microsoft Intune")
    assert n_left == 1
    # The static title text is present as a literal run.
    assert "Book_05 — OrgPath and Microsoft Intune" in out
    # Exactly one STYLEREF field remains — the right one, now repointed to
    # Heading 1 (chapter). The left Heading-1 field is gone (static).
    assert out.count("STYLEREF") == 1
    assert 'STYLEREF "Heading 1"' in out
    assert 'STYLEREF "Heading 2"' not in out
    # Only one field begin/end pair remains (the right field).
    assert out.count('w:fldCharType="begin"') == 1
    assert out.count('w:fldCharType="end"') == 1
    # Still well-formed XML.
    ET.fromstring(out)


def test_title_is_xml_escaped():
    out, n_left = bsd._rewrite_header_xml(_header(), "Risk & AI <draft>")
    assert n_left == 1
    assert "Risk &amp; AI &lt;draft&gt;" in out
    ET.fromstring(out)


def test_no_op_when_no_styleref_heading1():
    plain = '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p/></w:hdr>'
    out, n_left = bsd._rewrite_header_xml(plain, "Book_99 — Nothing")
    assert n_left == 0
    assert out == plain
