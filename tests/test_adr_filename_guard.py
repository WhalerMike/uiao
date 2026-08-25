"""Tests for the ADR-filename guard in check_adr_references.py.

The number-only guard asserts that ``ADR-047`` resolves to *some*
``adr-047-*.md``. That is a weak assertion: a number survives a renumbering and
a slug does not, so a citation left pointing at
``adr-047-fedramp-20x-integration.md`` passed the number guard for months even
though ADR-047 is the Continuous Monitoring Program and the FedRAMP 20x decision
had moved to ADR-106. This guard closes that gap by requiring the whole filename
to match.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_adr_references",
    Path(__file__).parent.parent / "scripts" / "check_adr_references.py",
)
guard = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(guard)


# ---------------------------------------------------------------------------
# Filename extraction
# ---------------------------------------------------------------------------


def _matches(line: str) -> list[str]:
    return [m.group(0) for m in guard.ADR_FILENAME_RE.finditer(line)]


def test_matches_every_citation_shape_the_corpus_uses() -> None:
    # Markdown link target, relative and absolute.
    assert _matches("see [ADR-092](adr-092-active-governance.md)") == ["adr-092-active-governance.md"]
    assert _matches("[x](../../adr/adr-092-active-governance.qmd)") == ["adr-092-active-governance.qmd"]
    assert _matches("[x](/docs/adr/adr-092-active-governance.html)") == ["adr-092-active-governance.html"]
    # Inline code — the shape that hid the CHANGELOG's ADR-058 defect, because
    # it is not a link and so no link checker ever looked at it.
    assert _matches("- **ADR-058** (`src/uiao/canon/adr/adr-058-x-y.md`) — text") == ["adr-058-x-y.md"]
    # Frontmatter scalar (adr-062's `prior_filename` provenance field).
    assert _matches('  prior_filename: "adr-045-orgpath-depth-extension.md"') == ["adr-045-orgpath-depth-extension.md"]


def test_ignores_non_adr_and_partial_shapes() -> None:
    assert _matches("ADR-047 without a filename") == []
    assert _matches("adr-47-short-number.md") == []  # not 3-digit
    assert _matches("(adr-092-active-governance.pdf)") == []  # not a doc extension
    assert _matches("xadr-092-active-governance.md") == []  # no word boundary


def test_two_filenames_on_one_line_are_both_reported() -> None:
    line = "[ADR-072](adr-072-canon-publication-policy.md) / [ADR-068](adr-068-canon-publication-policy.qmd)"
    assert _matches(line) == [
        "adr-072-canon-publication-policy.md",
        "adr-068-canon-publication-policy.qmd",
    ]


# ---------------------------------------------------------------------------
# Stem map
# ---------------------------------------------------------------------------


def test_stem_map_covers_both_adr_directories() -> None:
    """docs/adr is the rendered `.qmd` mirror; citing it must stay valid."""
    root = guard.repo_root()
    stems = guard.valid_adr_stems(root)
    assert stems, "no ADR stems found — wrong working directory?"
    # ADR-092 exists as .md in canon and .qmd in docs; one stem, both surfaces.
    assert "adr-092-active-governance" in stems["092"]
    assert set(guard.ADR_DIRS) == {guard.ADR_DIR, Path("docs/adr")}


def test_slot_collisions_are_representable() -> None:
    """A number maps to a set, so an unresolved collision is not silently lost."""
    root = guard.repo_root()
    stems = guard.valid_adr_stems(root)
    assert all(isinstance(v, set) and v for v in stems.values())


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _scan(tmp_path: Path, body: str) -> list[str]:
    src = tmp_path / "doc.md"
    src.write_text(body, encoding="utf-8")
    stems = {"047": {"adr-047-continuous-monitoring-program"}}
    _, misnamed = guard.scan_file(src, tmp_path, {"047"}, stems)
    return misnamed


def test_right_number_wrong_slug_is_caught(tmp_path: Path) -> None:
    found = _scan(tmp_path, "[ADR-047](adr-047-fedramp-20x-integration.md)\n")
    assert len(found) == 1
    # The message names the real filename so the fix needs no lookup.
    assert "adr-047-continuous-monitoring-program.md" in found[0]
    assert "doc.md:1" in found[0]


def test_correct_filename_passes(tmp_path: Path) -> None:
    assert _scan(tmp_path, "[ADR-047](adr-047-continuous-monitoring-program.md)\n") == []


def test_extension_does_not_affect_the_verdict(tmp_path: Path) -> None:
    """`.html` is the Quarto render target of a `.qmd`; the stem carries identity."""
    for ext in ("md", "qmd", "html"):
        assert _scan(tmp_path, f"[x](adr-047-continuous-monitoring-program.{ext})\n") == []
        assert len(_scan(tmp_path, f"[x](adr-047-wrong-slug.{ext})\n")) == 1


def test_unallocated_number_in_a_bare_filename_is_caught(tmp_path: Path) -> None:
    """A filename citation with no `ADR-NNN` on the line is still checked."""
    found = _scan(tmp_path, "see `src/uiao/canon/adr/adr-142-invented.md` for details\n")
    assert len(found) == 1
    assert "no ADR 142 exists" in found[0]


def test_allow_marker_exempts_deliberate_historical_mentions(tmp_path: Path) -> None:
    body = "- `adr-047-fedramp-20x-integration.md` <!-- adr-ref-allow --> (renumbered to ADR-106)\n"
    assert _scan(tmp_path, body) == []


# ---------------------------------------------------------------------------
# Live corpus
# ---------------------------------------------------------------------------


def test_changelog_is_in_scope() -> None:
    """The v0.6.0 ADR-058 defect sat outside the original path filter."""
    assert "CHANGELOG.md" in guard.SCAN_GLOBS
    assert guard.repo_root() / "CHANGELOG.md" in guard.iter_scan_files(guard.repo_root())


def test_live_corpus_filenames_all_resolve() -> None:
    root = guard.repo_root()
    valid = guard.valid_adr_ids(root)
    stems = guard.valid_adr_stems(root)
    misnamed: list[str] = []
    for path in guard.iter_scan_files(root):
        misnamed.extend(guard.scan_file(path, root, valid, stems)[1])
    assert misnamed == [], "ADR filename citations that do not resolve:\n" + "\n".join(misnamed)
