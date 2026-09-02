"""Unit tests for scripts/check_kit_agency_leak.py.

The gate exists because a text sweep cannot see inside a .docx: two committed
Office files under OrgComp-Training-Program/ carried the agency edition and
shipped in every orgcomp-federal-series-latest.zip while the kit README said
"no agency is named". These tests pin the two properties that failure needs —
Office packages are opened and read, and the legitimate look-alike phrases are
not swept — plus the refuse-to-write behaviour in the build scripts.
"""

import importlib.util
import io
import zipfile
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_kit_agency_leak",
    Path(__file__).resolve().parents[1] / "scripts" / "check_kit_agency_leak.py",
)
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


def _docx(paragraphs: list[str]) -> bytes:
    """Minimal OOXML package with a readable word/document.xml."""
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body>{body}</w:body></w:document>")
    return buf.getvalue()


def _pptx(notes: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("ppt/slides/slide1.xml", "<p:sld><a:t>Title</a:t></p:sld>")
        z.writestr("ppt/notesSlides/notesSlide1.xml", f"<p:notes><a:t>{notes}</a:t></p:notes>")
    return buf.getvalue()


# --- the failure this gate was built for --------------------------------------


def test_finds_agency_inside_a_docx() -> None:
    data = _docx(["SSA Federal Application-Aware Networking (FedAAN)"])
    hits = gate.scan_one("kits/OrgComp_Executive_At_A_Glance.docx", data)
    assert [k for _, k, _ in hits] == ["agency.short"]


def test_finds_agency_in_a_pptx_speaker_note() -> None:
    hits = gate.scan_one("decks/Book_00.pptx", _pptx("Why it binds SSA"))
    assert hits, "a leak in a speaker note must be caught, not just on the slide"


def test_finds_the_spelled_out_agency_name() -> None:
    data = _docx(["systems operated by or on behalf of the Social Security Administration."])
    assert [k for _, k, _ in gate.scan_one("Vol_IV-Bundle.docx", data)] == ["agency.full"]


def test_finds_agency_in_the_archive_path_itself() -> None:
    hits = gate.scan_one("Runbooks/Some_SSA_Runbook.md", b"clean body")
    assert hits, "a filename naming the agency reaches the reader through INDEX.md"


def test_finds_domain_and_tenant() -> None:
    assert gate.scan_one("a.md", b"see https://ssa.gov/x")
    assert gate.scan_one("b.md", b"tenant ssagov.onmicrosoft.com")


# --- what must NOT trip it ----------------------------------------------------


def test_pii_vocabulary_is_not_a_leak() -> None:
    """Vol III Book 05's Purview DLP rules are full of this, correctly."""
    body = b"| U.S. Social Security Number | XXX-XX-XXXX | MP-4 |\nSSN detection at 85 confidence\n"
    assert gate.scan_one("Vol_III_Book_05.md", body) == []


def test_statute_citation_is_not_a_leak() -> None:
    assert gate.scan_one("book.md", b"to the standard required by the Social Security Act") == []


def test_lowercase_technical_identifiers_are_not_a_leak() -> None:
    """``ssa-attribute-service`` is an adapter slug, not agency identity."""
    assert gate.scan_one("adapters/ssa-attribute-service/spec.md", b"the ssa-attribute-service adapter") == []


def test_a_false_positive_does_not_mask_a_real_hit_on_the_same_line() -> None:
    body = b"The Social Security Number rules SSA published are strict.\n"
    assert [k for _, k, _ in gate.scan_one("x.md", body)] == ["agency.short"]


def test_allowlisted_path_is_skipped() -> None:
    """Book 01's filename is a tracked, named exception — not a silent hole."""
    assert gate.scan_one("Vol_I/Vol_I_Book_01_OrgComp_SSA_Landing_Zone_IPAM_FedRAMP.md", b"SSA") == []


def test_clean_members_pass() -> None:
    assert gate.scan_one("Vol_I_Book_01.md", _docx(["Agency operates four cloud environments."])) == []


# --- wiring -------------------------------------------------------------------


def test_scan_members_covers_generated_in_memory_members(tmp_path: Path) -> None:
    """Concatenated bundles never touch disk; they must still be scanned."""
    clean = tmp_path / "clean.md"
    clean.write_text("Agency operates the estate.\n", encoding="utf-8")
    findings = gate.scan_members({"Vol_I/clean.md": clean}, extra={"Vol_I-Bundle.md": "SSA operating this loop"})
    assert [a for a, _, _ in findings] == ["Vol_I-Bundle.md"]


def test_markdown_kit_build_refuses_to_write_a_leaking_zip(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "build_orgcomp_markdown_download",
        Path(__file__).resolve().parents[1] / "scripts" / "build_orgcomp_markdown_download.py",
    )
    bomd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bomd)

    series = tmp_path / "site" / "customer-documents" / "orgcomp-series"
    series.mkdir(parents=True)
    (series / "Vol_I_Book_01_Landing_Zone.md").write_text("SSA operating this loop\n", encoding="utf-8")
    out = tmp_path / "out"

    assert bomd.build(tmp_path / "site", out, "2026-09-02") == 1
    assert not (out / bomd.ZIP_NAME).exists(), "a leaking kit must never be written"


def test_markdown_kit_build_ships_when_clean(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "build_orgcomp_markdown_download",
        Path(__file__).resolve().parents[1] / "scripts" / "build_orgcomp_markdown_download.py",
    )
    bomd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bomd)

    series = tmp_path / "site" / "customer-documents" / "orgcomp-series"
    series.mkdir(parents=True)
    (series / "Vol_I_Book_01_Landing_Zone.md").write_text("Agency operating this loop\n", encoding="utf-8")
    out = tmp_path / "out"

    assert bomd.build(tmp_path / "site", out, "2026-09-02") == 0
    assert (out / bomd.ZIP_NAME).exists()
