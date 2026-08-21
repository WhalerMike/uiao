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


def test_volume_bundle_filename_carries_theme() -> None:
    """Per-volume bundles are named ``Vol_<N>-<Theme>-Bundle.docx`` so a
    downloaded file identifies its subject without opening it.

    The theme is URL-safed: these filenames become GitHub Release asset names,
    and GitHub rewrites spaces/commas/ampersands to '.' on upload — which is
    how 11 doc links came to 404 while pointing at the percent-encoded
    original.
    """
    assert bsd._volume_bundle_filename("I") == "Vol_I-Foundation-Transport-Bundle.docx"
    assert bsd._volume_bundle_filename("IX") == "Vol_IX-Day-2-Operations-Bundle.docx"
    assert bsd._volume_bundle_filename("0") == "Vol_0-Executive-Summary-Questionnaire-Control-Crosswalk-Bundle.docx"
    # Already-safe themes are untouched — no gratuitous renaming.
    assert bsd._volume_bundle_filename("VI") == "Vol_VI-Implementation-Bundle.docx"


def test_every_volume_bundle_filename_survives_being_a_url() -> None:
    """The property, not just the three strings above.

    A name that needs percent-encoding cannot round-trip through a release
    asset name, so assert it for EVERY registered volume rather than the
    handful someone thought to enumerate.
    """
    from urllib.parse import quote

    for vol_id in bsd.VOLUME_THEMES:
        name = bsd._volume_bundle_filename(vol_id)
        assert quote(name) == name, f"{name} would be percent-encoded in a URL"
        assert name.lower().endswith("-bundle.docx"), (
            f"{name} must keep the -Bundle.docx suffix the skip filter matches"
        )


def test_volume_bundle_filename_falls_back_without_theme() -> None:
    """An unmapped volume id still bundles, under the themeless legacy name."""
    assert bsd._volume_bundle_filename("XI") == "Vol_XI-bundle.docx"


def test_every_ranked_volume_has_a_theme() -> None:
    """Every volume the bundler can emit carries a theme, so no deployed
    bundle silently regresses to the themeless filename."""
    assert set(bsd.VOLUME_THEMES) == set(bsd._ROMAN_RANK)


def test_volume_bundle_filename_matches_skip_filter() -> None:
    """Volume bundle names (capital-B ``-Bundle.docx``) must be recognised by
    the case-insensitive bundle-skip filter so a re-run never folds a volume
    bundle into the section bundle or into itself."""
    for vol_id in bsd.VOLUME_THEMES:
        assert bsd._volume_bundle_filename(vol_id).lower().endswith("-bundle.docx")


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
