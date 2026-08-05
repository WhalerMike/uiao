"""Unit tests for the markdown-only doc zip added to
scripts/build_day2_kit_download.py — the "docs only, no source, no Word"
kit built from the Markdown render_md_orgcomp merges into ``_site``.

Scoped to the new ``collect_markdown`` / ``build_markdown_one`` functions;
the pre-existing DOCX kit build has no test coverage of its own to extend.
"""

import importlib.util
import zipfile
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "build_day2_kit_download",
    Path(__file__).resolve().parents[1] / "scripts" / "build_day2_kit_download.py",
)
bdkd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bdkd)


def _make_series(tmp_path: Path) -> Path:
    site_root = tmp_path / "_site"
    series = site_root / bdkd.SITE_SERIES_REL
    series.mkdir(parents=True)
    return site_root


def test_collect_markdown_resolves_md_siblings_for_target(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    series = site_root / bdkd.SITE_SERIES_REL
    for stem in bdkd.TARGET_DOCX_SET:
        (series / f"{stem}.md").write_text(f"# {stem}\n")

    members, notes = bdkd.collect_markdown(site_root, "target")

    assert len(members) == len(bdkd.TARGET_DOCX_SET)
    assert "0_START_HERE.md" in members
    assert "8_Kit_Expansion_Roadmap.md" in members
    assert any(f"{len(bdkd.TARGET_DOCX_SET)}/{len(bdkd.TARGET_DOCX_SET)}" in n for n in notes)


def test_collect_markdown_skips_missing_files(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    series = site_root / bdkd.SITE_SERIES_REL
    # Only render one of the current-edition stems.
    first_stem = next(iter(bdkd.CURRENT_DOCX_SET))
    (series / f"{first_stem}.md").write_text("# only one\n")

    members, _ = bdkd.collect_markdown(site_root, "current")

    assert len(members) == 1


def test_build_markdown_one_writes_zip_with_root_prefix(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    series = site_root / bdkd.SITE_SERIES_REL
    for stem in bdkd.TARGET_DOCX_SET:
        (series / f"{stem}.md").write_text(f"# {stem}\n")

    out_dir = tmp_path / "out"
    rc = bdkd.build_markdown_one(site_root, out_dir, "2026-08-04", "target")
    assert rc == 0

    zip_path = out_dir / bdkd.ZIP_NAMES_MD["target"]
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        root = bdkd.ROOTS["target"]
        assert f"{root}/README.txt" in names
        assert f"{root}/0_START_HERE.md" in names
        # No servicenow-day2 kit source and no .docx in the markdown-only zip.
        assert not any(n.startswith(f"{root}/servicenow-day2/") for n in names)
        assert not any(n.endswith(".docx") for n in names)


def test_build_markdown_one_is_never_fatal_when_nothing_rendered(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    rc = bdkd.build_markdown_one(site_root, tmp_path / "out", "2026-08-04", "current")
    assert rc == 0
    assert not (tmp_path / "out" / bdkd.ZIP_NAMES_MD["current"]).exists()
