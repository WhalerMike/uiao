"""The renderer owns the ignore list for the artifacts it writes.

`refresh_gitignore` exists because "is this PNG derived?" is a *relational*
property -- a PNG is a build artifact iff a sibling `.svg` exists -- which
`.gitignore` cannot express. The pattern approximation (`*.png`) would also
swallow the 500+ legitimately tracked PNGs that have no SVG source, so a
genuinely new figure could vanish from `git status` unnoticed. These tests pin
the three properties that make the explicit-path approach safe.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import render_svg_images as rsi  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A miniature repo: two SVG-sourced figures and one PNG with no source."""
    (tmp_path / "docs" / "figs").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    for name in ("alpha", "beta"):
        (tmp_path / "docs" / "figs" / f"{name}.svg").write_text("<svg/>", encoding="utf-8")
    # legacy AI art: a tracked PNG with no SVG source, which must never be ignored
    (tmp_path / "docs" / "figs" / "legacy.png").write_bytes(b"\x89PNG")
    (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    (tmp_path / "scripts" / "svg-derived-png-allowlist.txt").write_text("# none\n", encoding="utf-8")
    monkeypatch.setattr(rsi, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(rsi, "ALLOWLIST", tmp_path / "scripts" / "svg-derived-png-allowlist.txt")
    return tmp_path


def _svgs(repo: Path) -> list[Path]:
    return sorted((repo / "docs" / "figs").glob("*.svg"))


def test_lists_the_png_and_its_sidecar_for_every_svg(repo):
    n = rsi.refresh_gitignore(_svgs(repo))
    body = (repo / ".gitignore").read_text(encoding="utf-8")
    assert n == 4  # two figures x (png + sidecar)
    for entry in (
        "/docs/figs/alpha.png",
        "/docs/figs/alpha.png.json",
        "/docs/figs/beta.png",
        "/docs/figs/beta.png.json",
    ):
        assert entry in body


def test_never_ignores_a_png_that_has_no_svg_source(repo):
    """The failure mode this design exists to prevent."""
    rsi.refresh_gitignore(_svgs(repo))
    body = (repo / ".gitignore").read_text(encoding="utf-8")
    assert "legacy.png" not in body


def test_skips_allowlisted_paths_so_nothing_is_both_tracked_and_ignored(repo):
    (repo / "scripts" / "svg-derived-png-allowlist.txt").write_text("^docs/figs/alpha$\n", encoding="utf-8")
    n = rsi.refresh_gitignore(_svgs(repo))
    body = (repo / ".gitignore").read_text(encoding="utf-8")
    assert n == 2
    assert "/docs/figs/alpha.png" not in body
    assert "/docs/figs/beta.png" in body


def test_rewrites_in_place_and_preserves_hand_written_rules(repo):
    rsi.refresh_gitignore(_svgs(repo))
    (repo / "docs" / "figs" / "gamma.svg").write_text("<svg/>", encoding="utf-8")
    rsi.refresh_gitignore(_svgs(repo))
    body = (repo / ".gitignore").read_text(encoding="utf-8")
    assert body.count(rsi.GITIGNORE_BEGIN) == 1, "block must be replaced, not appended"
    assert body.count(rsi.GITIGNORE_END) == 1
    assert "node_modules/" in body, "hand-written rules survive"
    assert "/docs/figs/gamma.png" in body


def test_is_deterministic(repo):
    rsi.refresh_gitignore(_svgs(repo))
    once = (repo / ".gitignore").read_text(encoding="utf-8")
    rsi.refresh_gitignore(_svgs(repo))
    assert (repo / ".gitignore").read_text(encoding="utf-8") == once


def test_entries_are_sorted(repo):
    rsi.refresh_gitignore(_svgs(repo))
    body = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    block = body[body.index(rsi.GITIGNORE_BEGIN) + 1 : body.index(rsi.GITIGNORE_END)]
    assert block == sorted(block)


def test_allowlist_comments_and_blanks_are_ignored(repo):
    (repo / "scripts" / "svg-derived-png-allowlist.txt").write_text(
        "# a comment\n\n   \n^docs/figs/beta$\n", encoding="utf-8"
    )
    pats = rsi._allowlist_patterns()
    assert [p.pattern for p in pats] == ["^docs/figs/beta$"]
    assert all(isinstance(p, re.Pattern) for p in pats)
