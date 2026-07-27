"""Unit tests for scripts/scan_publication_gaps.py.

Focuses on Pass 2 (disk -> sidebar "unregistered page" detection) added to
close the structural blind spot ADR-072's source-driven Pass 1 had for
orgpath-narrative chapters authored directly as .qmd. Those pages reached
main unregistered three separate times (PRs #746/#747/#748). The check here
is the regression guard that fails the gate the next time.
"""

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "scan_publication_gaps",
    _REPO_ROOT / "scripts" / "scan_publication_gaps.py",
)
spg = importlib.util.module_from_spec(_SPEC)
# Register before exec so @dataclass can resolve the module (Python 3.12+).
sys.modules[_SPEC.name] = spg
_SPEC.loader.exec_module(spg)


def _make_book(root: Path, name: str) -> Path:
    """Create a stub orgpath-narrative Book .qmd on disk."""
    d = root / "docs" / "customer-documents" / "orgpath-narrative"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text("---\ntitle: stub\n---\n\nbody\n", encoding="utf-8")
    return p


def _rel(name: str) -> str:
    return f"docs/customer-documents/orgpath-narrative/{name}"


# ---------------------------------------------------------------------------
# Pass 2 — find_unregistered_docs() unit behavior against a fixture tree
# ---------------------------------------------------------------------------


def test_unregistered_book_chapter_is_flagged(tmp_path: Path) -> None:
    """A Book chapter on disk but absent from the sidebar is reported."""
    _make_book(tmp_path, "Book_07b.qmd")
    _make_book(tmp_path, "Book_07b_CPT_01.qmd")
    # Sidebar registers only the landing page, not the chapter.
    sidebar = {_rel("Book_07b.qmd")}

    orphans = spg.find_unregistered_docs(tmp_path, sidebar)

    assert [o.rel_path for o in orphans] == [_rel("Book_07b_CPT_01.qmd")]
    assert "orgpath-narrative" in orphans[0].rule


def test_fully_registered_books_produce_no_orphans(tmp_path: Path) -> None:
    """When every matched page is in the sidebar, there are no orphans."""
    _make_book(tmp_path, "Book_07b.qmd")
    _make_book(tmp_path, "Book_07b_CPT_01.qmd")
    sidebar = {_rel("Book_07b.qmd"), _rel("Book_07b_CPT_01.qmd")}

    assert spg.find_unregistered_docs(tmp_path, sidebar) == []


def test_landing_page_registered_as_section_counts(tmp_path: Path) -> None:
    """collect_sidebar_qmds() normalizes section: landings to docs/-prefixed
    paths; a landing registered that way must not be reported as an orphan.

    This mirrors the real _quarto.yml shape, where book landing pages appear
    as ``- section: customer-documents/orgpath-narrative/Book_NN.qmd``.
    """
    quarto = tmp_path / "docs" / "_quarto.yml"
    quarto.parent.mkdir(parents=True, exist_ok=True)
    quarto.write_text(
        "website:\n"
        "  sidebar:\n"
        "    contents:\n"
        "      - section: customer-documents/orgpath-narrative/Book_07b.qmd\n"
        "        contents:\n"
        "          - customer-documents/orgpath-narrative/Book_07b_CPT_01.qmd\n",
        encoding="utf-8",
    )
    _make_book(tmp_path, "Book_07b.qmd")
    _make_book(tmp_path, "Book_07b_CPT_01.qmd")

    sidebar = spg.collect_sidebar_qmds(quarto)
    assert spg.find_unregistered_docs(tmp_path, sidebar) == []


def test_non_book_qmd_is_not_in_scope(tmp_path: Path) -> None:
    """index.qmd (and other non-Book pages) are not registration-required."""
    d = tmp_path / "docs" / "customer-documents" / "orgpath-narrative"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.qmd").write_text("---\ntitle: idx\n---\n", encoding="utf-8")

    assert spg.find_unregistered_docs(tmp_path, set()) == []


def test_custom_globs_extend_coverage(tmp_path: Path) -> None:
    """The glob list is the extension point — a custom section is enforced."""
    d = tmp_path / "docs" / "customer-documents" / "whitepapers"
    d.mkdir(parents=True, exist_ok=True)
    (d / "new-paper.qmd").write_text("---\ntitle: wp\n---\n", encoding="utf-8")

    globs = [("docs/customer-documents/whitepapers/*.qmd", "whitepaper")]
    orphans = spg.find_unregistered_docs(tmp_path, set(), globs=globs)

    assert [o.rel_path for o in orphans] == ["docs/customer-documents/whitepapers/new-paper.qmd"]


def _make_adr_wrapper(root: Path, name: str) -> Path:
    """Create a stub ADR wrapper .qmd on disk."""
    d = root / "docs" / "adr"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text("---\ntitle: stub\n---\n\nbody\n", encoding="utf-8")
    return p


def test_unregistered_adr_wrapper_is_flagged(tmp_path: Path) -> None:
    """An ADR wrapper on disk but absent from the sidebar is reported.

    This is the PR #1372 failure mode: eight wrappers rendered to the site
    but were unreachable from navigation, and Pass 1's link-back-id
    detection kept every gate green because the sidebar-listed ADR index
    mentions every ADR ID.
    """
    _make_adr_wrapper(tmp_path, "adr-084-phase5-consumer-architecture.qmd")
    _make_adr_wrapper(tmp_path, "adr-index.qmd")
    sidebar = {"docs/adr/adr-index.qmd"}

    orphans = spg.find_unregistered_docs(tmp_path, sidebar)

    assert [o.rel_path for o in orphans] == ["docs/adr/adr-084-phase5-consumer-architecture.qmd"]
    assert "ADR wrapper" in orphans[0].rule


def test_registered_adr_wrappers_produce_no_orphans(tmp_path: Path) -> None:
    """When every ADR wrapper is in the sidebar, there are no orphans."""
    _make_adr_wrapper(tmp_path, "adr-084-phase5-consumer-architecture.qmd")
    _make_adr_wrapper(tmp_path, "adr-index.qmd")
    sidebar = {
        "docs/adr/adr-084-phase5-consumer-architecture.qmd",
        "docs/adr/adr-index.qmd",
    }

    assert spg.find_unregistered_docs(tmp_path, sidebar) == []


# ---------------------------------------------------------------------------
# Regression — the live repo must stay clean, and the default globs must
# actually point at on-disk orgpath-narrative content.
# ---------------------------------------------------------------------------


def test_default_globs_target_existing_orgpath_books() -> None:
    """REGISTRATION_REQUIRED_GLOBS must match real Book_*.qmd files (guards
    against a typo'd glob silently matching nothing).
    """
    matched = 0
    for pattern, _rule in spg.REGISTRATION_REQUIRED_GLOBS:
        matched += sum(1 for p in spg.REPO_ROOT.glob(pattern) if p.is_file())
    assert matched > 0, "default registration-required globs matched zero files"


def test_repo_has_no_unregistered_orgpath_pages() -> None:
    """The checked-in repo must have every orgpath-narrative Book page wired
    into docs/_quarto.yml. This is the gate that #746/#747/#748 had to fix by
    hand; once green it stays green.
    """
    sidebar = spg.collect_sidebar_qmds(spg.QUARTO_CONFIG)
    orphans = spg.find_unregistered_docs(spg.REPO_ROOT, sidebar)
    assert orphans == [], "unregistered orgpath-narrative pages: " + ", ".join(o.rel_path for o in orphans)
