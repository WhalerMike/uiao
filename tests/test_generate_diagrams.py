"""Tests for scripts/generate_diagrams.py routing logic.

Covers:
- is_gemini_owned(): folder-based and frontmatter tag-based routing
- collect_gemini_files(): multi-directory Gemini file collection
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts/ to sys.path so we can import generate_diagrams directly
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_md(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _with_frontmatter(owner: str) -> str:
    return f"---\ndiagram-owner: {owner}\n---\n# Test\n"


def _no_frontmatter() -> str:
    return "# Just a doc\n\nNo frontmatter here.\n"


# ---------------------------------------------------------------------------
# is_gemini_owned()
# ---------------------------------------------------------------------------
class TestIsGeminiOwned:
    """Verify the folder- and tag-based routing gate."""

    def _load(self):
        import importlib
        import unittest.mock as mock

        # generate_diagrams exits with code 1 when GEMINI_API_KEY is unset;
        # patch os.getenv so the module-level guard doesn't fire.
        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            spec = importlib.util.spec_from_file_location(
                "generate_diagrams",
                _SCRIPTS_DIR / "generate_diagrams.py",
            )
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    @pytest.fixture(autouse=True)
    def _mod(self):
        self.mod = self._load()

    # -- folder-based routing ------------------------------------------------

    def test_src_templates_always_gemini(self, tmp_path: Path) -> None:
        _write_md(tmp_path / "src/templates/arch.md", _no_frontmatter())
        # Patch the path check by passing a relative-looking string
        # is_gemini_owned uses str(filepath).startswith("src/templates/")
        assert self.mod.is_gemini_owned(Path("src/templates/arch.md"))

    def test_docs_untagged_not_gemini(self, tmp_path: Path) -> None:
        md = _write_md(tmp_path / "doc.md", _no_frontmatter())
        assert not self.mod.is_gemini_owned(md)

    def test_canon_untagged_not_gemini(self, tmp_path: Path) -> None:
        md = _write_md(tmp_path / "canon" / "spec.md", _no_frontmatter())
        assert not self.mod.is_gemini_owned(md)

    # -- tag-based routing ---------------------------------------------------

    def test_gemini_tag_returns_true(self, tmp_path: Path) -> None:
        md = _write_md(tmp_path / "docs" / "arch.md", _with_frontmatter("gemini"))
        assert self.mod.is_gemini_owned(md)

    def test_unknown_tag_returns_false(self, tmp_path: Path) -> None:
        md = _write_md(tmp_path / "docs" / "flow.md", _with_frontmatter("unknown-owner"))
        assert not self.mod.is_gemini_owned(md)

    def test_no_tag_returns_false(self, tmp_path: Path) -> None:
        md = _write_md(tmp_path / "docs" / "readme.md", _no_frontmatter())
        assert not self.mod.is_gemini_owned(md)

    def test_gemini_tag_in_src_templates(self, tmp_path: Path) -> None:
        """Files in src/templates/ are Gemini-owned regardless of tag."""
        assert self.mod.is_gemini_owned(Path("src/templates/tagged.md"))

    def test_malformed_frontmatter_treated_as_unowned(self, tmp_path: Path) -> None:
        bad = _write_md(tmp_path / "bad.md", "---\n: invalid: yaml:\n---\n")
        assert not self.mod.is_gemini_owned(bad)

    def test_missing_file_treated_as_unowned(self, tmp_path: Path) -> None:
        assert not self.mod.is_gemini_owned(tmp_path / "nonexistent.md")


# ---------------------------------------------------------------------------
# collect_gemini_files()
# ---------------------------------------------------------------------------
class TestCollectGeminiFiles:
    """Verify multi-directory Gemini file collection."""

    def _load(self):
        import importlib
        import unittest.mock as mock

        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            spec = importlib.util.spec_from_file_location(
                "generate_diagrams",
                _SCRIPTS_DIR / "generate_diagrams.py",
            )
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    @pytest.fixture(autouse=True)
    def _mod(self, tmp_path, monkeypatch):
        self.tmp = tmp_path
        monkeypatch.chdir(tmp_path)
        self.mod = self._load()

    def test_empty_repo_returns_empty(self) -> None:
        result = self.mod.collect_gemini_files()
        assert result == []

    def test_src_templates_picked_up(self) -> None:
        _write_md(self.tmp / "src/templates/a.md", _no_frontmatter())
        _write_md(self.tmp / "src/templates/sub/b.md", _no_frontmatter())
        result = self.mod.collect_gemini_files()
        stems = {Path(f).name for f in result}
        assert stems == {"a.md", "b.md"}

    def test_docs_tagged_gemini_picked_up(self) -> None:
        _write_md(self.tmp / "docs/overview.md", _with_frontmatter("gemini"))
        result = self.mod.collect_gemini_files()
        assert any(Path(f).name == "overview.md" for f in result)

    def test_docs_untagged_not_picked_up(self) -> None:
        _write_md(self.tmp / "docs/plain.md", _no_frontmatter())
        result = self.mod.collect_gemini_files()
        assert not any(Path(f).name == "plain.md" for f in result)

    def test_no_duplicates_when_src_templates_and_secondary_scan_overlap(self) -> None:
        """src/templates/ files must not appear twice even if secondary glob matches."""
        _write_md(self.tmp / "src/templates/arch.md", _with_frontmatter("gemini"))
        result = self.mod.collect_gemini_files()
        assert len(result) == len(set(result)), "collect_gemini_files() must deduplicate results"

    def test_canon_tagged_gemini_picked_up(self) -> None:
        _write_md(self.tmp / "generation-inputs/spec.md", _with_frontmatter("gemini"))
        result = self.mod.collect_gemini_files()
        assert any(Path(f).name == "spec.md" for f in result)

    def test_templates_tagged_gemini_picked_up(self) -> None:
        _write_md(self.tmp / "templates/layout.md", _with_frontmatter("gemini"))
        result = self.mod.collect_gemini_files()
        assert any(Path(f).name == "layout.md" for f in result)
