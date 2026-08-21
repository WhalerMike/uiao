"""Tests for the OrgPath codebook-conformance guard.

The guard closes the hole its two siblings share: the prefix guard validates
``Facet=Value`` prefix *expressions* and excludes legacy path styles by
construction, and the slot guard only fires on a line naming exactly one
``extensionAttributeN``. Neither sees a bare composite-path literal in a
paragraph or a figure caption, and neither scans ``.svg`` at all.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_orgpath_codebook_conformance",
    Path(__file__).parent.parent / "scripts" / "check_orgpath_codebook_conformance.py",
)
lint = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(lint)

ROOT = lint.repo_root()


@pytest.fixture(scope="module")
def codebook() -> object:
    """The real codebook — a fixture copy would drift from the SSOT."""
    return lint.load_codebook(ROOT)


# ---------------------------------------------------------------------------
# Rule 1 — composite-path literals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "literal",
    [
        "ORG-FIN-AP-EAST",
        "ORG-FIN",
        "ORG-IT-INF-PLATFORM",
        "/Root/Finance",
        "/Root/Finance/AccountsPayable/Invoicing",
        "CORP/US/EAST/BALTIMORE/IT",
        "/COMM/MKT/MKTDIG",
    ],
)
def test_flags_retired_composite_paths(literal: str, codebook: object) -> None:
    findings = lint.scan_text(f"the server carries {literal} today", "doc.qmd", codebook)
    assert len(findings) == 1
    assert literal in findings[0]


@pytest.mark.parametrize(
    "group",
    ["ORG-NODE-FINANCE", "ORG-BRANCH-SALES", "ORG-BRANCH-UNPOSITIONED", "ORG-NODE-IT-CYBEROPS"],
)
def test_canon_group_names_are_not_path_literals(group: str, codebook: object) -> None:
    """ADR-036/ADR-039 group names are canon, not retired path values."""
    assert lint.scan_text(f"targets the {group} group", "doc.qmd", codebook) == []


def test_ordinary_paths_are_out_of_scope(codebook: object) -> None:
    lines = [
        "see src/uiao/canon/data/orgpath/codebook.yaml",
        "https://example.test/COMMUNITY/guide",
        "the ORGANISATION chart",
        "AU-ORG-Enterprise covers every principal",
    ]
    for line in lines:
        assert lint.scan_text(line, "doc.qmd", codebook) == [], line


# ---------------------------------------------------------------------------
# Rule 2 — facet values the codebook does not license
# ---------------------------------------------------------------------------


def test_flags_segment_value_outside_the_enumeration(codebook: object) -> None:
    findings = lint.scan_text('-startsWith "Region=NCR|Division=Payroll|"', "r.yaml", codebook)
    assert len(findings) == 1
    assert "Payroll" in findings[0] and "division" in findings[0]


def test_licensed_segments_are_clean(codebook: object) -> None:
    line = '(user.extensionAttribute15 -startsWith "Region=NCR|Department=IT|Division=InfraOps|")'
    assert lint.scan_text(line, "r.yaml", codebook) == []


def test_flags_slot_comparison_outside_the_enumeration(codebook: object) -> None:
    findings = lint.scan_text('(user.extensionAttribute3 -eq "Payroll")', "r.yaml", codebook)
    assert len(findings) == 1
    assert "extensionAttribute3" in findings[0]


def test_licensed_slot_comparison_is_clean(codebook: object) -> None:
    assert lint.scan_text('(user.extensionAttribute3 -eq "InfraOps")', "r.yaml", codebook) == []


def test_typed_facets_are_not_this_guards_business(codebook: object) -> None:
    """extensionAttribute7/8/15 are typed; their values have no enumeration."""
    lines = [
        '(user.extensionAttribute7 -eq "2019-03-04")',
        '(user.extensionAttribute15 -eq "Region=NCR|Department=IT|")',
    ]
    for line in lines:
        assert lint.scan_text(line, "r.yaml", codebook) == [], line


def test_empty_comparison_is_a_presence_test(codebook: object) -> None:
    """`-ne ""` asks whether the slot is populated; it asserts no value."""
    assert lint.scan_text('(user.extensionAttribute2 -ne "")', "r.yaml", codebook) == []


def test_escaped_pipe_in_a_pandoc_table_is_not_part_of_the_value(codebook: object) -> None:
    line = r"| rule | -startsWith \"Region=NCR\|Department=IT\|\" |"
    assert lint.scan_text(line, "doc.qmd", codebook) == []


def test_value_capture_stops_at_whitespace(codebook: object) -> None:
    """A run-on match would swallow prose up to the next delimiter."""
    line = "Division=InfraOps| (per the starter codebook) and pipe | in prose"
    assert lint.scan_text(line, "doc.qmd", codebook) == []


def test_allow_empty_facet_accepts_the_empty_value(codebook: object) -> None:
    assert codebook.licenses("device_type", "")
    assert not codebook.licenses("device_type", "Toaster")
    assert not codebook.licenses("region", "")


# ---------------------------------------------------------------------------
# Exemptions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("marker", lint.ALLOW_MARKERS)
def test_every_allow_marker_suppresses_the_line(marker: str, codebook: object) -> None:
    """A line already marked deliberate for a sibling guard is deliberate here."""
    line = f"the retired ORG-FIN-AP-EAST shape  # {marker}"
    assert lint.scan_text(line, "doc.qmd", codebook) == []


def test_file_marker_suppresses_the_whole_document(codebook: object) -> None:
    text = f"<!-- {lint.ALLOW_FILE_MARKER} -->\nORG-FIN-AP-EAST\n/Root/Finance\n"
    assert lint.scan_text(text, "history.md", codebook) == []


# ---------------------------------------------------------------------------
# Scope — the regression that let twenty-nine figures through
# ---------------------------------------------------------------------------


def test_svg_figures_are_in_scope() -> None:
    assert ".svg" in lint.SCANNABLE_SUFFIXES
    assert "images" not in lint.EXCLUDE_PARTS
    scanned = lint.iter_scan_files(ROOT, "docs")
    assert any(p.suffix == ".svg" and "/images/" in p.as_posix() for p in scanned)


# ---------------------------------------------------------------------------
# Repo invariants — a regression fails pytest, not only the workflow
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subtree", ["src/uiao/canon/data", "src/uiao/schemas"])
def test_executable_ssot_surfaces_stay_clean(subtree: str, codebook: object) -> None:
    findings: list[str] = []
    for path in lint.iter_scan_files(ROOT, subtree):
        findings.extend(
            lint.scan_text(
                path.read_text(encoding="utf-8", errors="replace"),
                path.relative_to(ROOT).as_posix(),
                codebook,
            )
        )
    assert findings == [], "\n".join(findings)
