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


def test_bundle_filename_matches_skip_filter() -> None:
    """Generated bundle names must be recognised by the bundle-skip filter
    (endswith '-bundle.docx') so a re-run never folds a bundle into itself."""
    for section in ("operational-guides", "operational-guides/orgpath-implementation"):
        assert bsd._bundle_filename(section).endswith("-bundle.docx")
