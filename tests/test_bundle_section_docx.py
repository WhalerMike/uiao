"""Unit tests for section/bundle naming in scripts/bundle_section_docx.py.

Covers the nested sub-section support added so a focused
``orgpath-implementation-bundle.docx`` can be produced under
``operational-guides/`` in addition to the whole-section bundle. The
naming logic (``_bundle_filename``) is pure, so these tests need none of
the docx rendering dependencies.
"""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "bundle_section_docx",
    Path(__file__).resolve().parents[1] / "scripts" / "bundle_section_docx.py",
)
bsd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bsd)


def test_top_level_section_filename_unchanged() -> None:
    """Back-compat: a plain section name maps to ``<section>-bundle.docx``."""
    assert bsd._bundle_filename("operational-guides") == "operational-guides-bundle.docx"
    assert bsd._bundle_filename("compliance") == "compliance-bundle.docx"


def test_nested_section_uses_final_component() -> None:
    """A nested path yields a flat, slash-free bundle filename."""
    name = bsd._bundle_filename("operational-guides/orgpath-implementation")
    assert name == "orgpath-implementation-bundle.docx"
    assert "/" not in name


def test_every_default_section_yields_slashfree_filename() -> None:
    """No bundle filename may contain a path separator (would break the write path)."""
    for section in bsd.DEFAULT_SECTIONS:
        name = bsd._bundle_filename(section)
        assert "/" not in name
        assert name.endswith("-bundle.docx")


def test_orgpath_implementation_is_registered() -> None:
    """The focused OrgPath bundle is wired into the --all run."""
    assert "operational-guides/orgpath-implementation" in bsd.DEFAULT_SECTIONS


def test_sql_server_implementation_is_registered() -> None:
    """The SQL Server Implementation Companion is bundled by the --all run,
    so ``sql-server-implementation-bundle.docx`` is produced on every deploy."""
    assert "sql-server-implementation" in bsd.DEFAULT_SECTIONS
    # Single-file books — bundled as a whole-companion pack, not per-book.
    assert "sql-server-implementation" not in bsd.BOOK_BUNDLE_SECTIONS
    assert bsd._bundle_filename("sql-server-implementation") == "sql-server-implementation-bundle.docx"


def test_bundle_filename_matches_skip_filter() -> None:
    """Generated bundle names must be recognised by the bundle-skip filter
    (endswith '-bundle.docx') so a re-run never folds a bundle into itself."""
    for section in ("operational-guides", "operational-guides/orgpath-implementation"):
        assert bsd._bundle_filename(section).endswith("-bundle.docx")


def test_orgcomp_series_registered_for_volume_bundles() -> None:
    assert "orgcomp-series" in bsd.VOLUME_BUNDLE_SECTIONS


def test_vol_id_regex_extracts_roman_token() -> None:
    assert bsd.VOL_ID_RE.match("Vol_IX_Book_03_OrgComp_X").group(1) == "IX"
    assert bsd.VOL_ID_RE.match("Vol_0_Book_00a_OrgComp_Y").group(1) == "0"
    assert bsd.VOL_ID_RE.match("OrgComp_Evidence_Contract_Spec") is None


def test_roman_rank_orders_volumes_in_reading_order() -> None:
    vols = ["X", "IX", "V", "0", "VIII", "I"]
    assert sorted(vols, key=bsd._ROMAN_RANK.get) == ["0", "I", "V", "VIII", "IX", "X"]


def test_orgcomp_series_key_puts_books_first_training_last(tmp_path: Path) -> None:
    sec = tmp_path / "orgcomp-series"
    paths = [
        sec / "OrgComp-Training-Program" / "assessment-rubrics.docx",
        sec / "OrgComp_Evidence_Contract_Spec.docx",
        sec / "Vol_IX_Book_00_OrgComp_Overview.docx",
        sec / "Vol_V_Book_01_OrgComp_Track.docx",
        sec / "boundary" / "B1-model.docx",
        sec / "Vol_0_Book_00_OrgComp_Summary.docx",
    ]
    ordered = sorted(paths, key=lambda d: bsd._orgcomp_series_key(sec, d))
    names = [p.name for p in ordered]
    assert names == [
        "Vol_0_Book_00_OrgComp_Summary.docx",
        "Vol_V_Book_01_OrgComp_Track.docx",
        "Vol_IX_Book_00_OrgComp_Overview.docx",
        "B1-model.docx",
        "OrgComp_Evidence_Contract_Spec.docx",
        "assessment-rubrics.docx",
    ]
