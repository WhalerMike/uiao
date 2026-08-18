"""Unit tests for the markdown-only doc zip added to
scripts/build_day2_kit_download.py — the "docs only, no source, no Word"
kit built from the Markdown render_md_orgcomp merges into ``_site``.

Scoped to the new ``collect_markdown`` / ``build_markdown_one`` functions;
the pre-existing DOCX kit build has no test coverage of its own to extend.
"""

import importlib.util
import re
import zipfile
from pathlib import Path

import pytest

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


TEST_SITE_BASE = "https://example.test/uiao/"


def _make_src(tmp_path: Path, site_url: str | None = TEST_SITE_BASE) -> Path:
    """A src_root with a docs/_quarto.yml shaped like the real one."""
    src_root = tmp_path / "src"
    cfg = src_root / bdkd.QUARTO_CONFIG_REL
    cfg.parent.mkdir(parents=True, exist_ok=True)
    body = 'website:\n  title: "UIAO"\n'
    if site_url:
        body += f"  site-url: {site_url}\n"
    cfg.write_text(body, encoding="utf8")
    return src_root


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
    rc = bdkd.build_markdown_one(site_root, out_dir, "2026-08-04", "target", _make_src(tmp_path))
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
    rc = bdkd.build_markdown_one(site_root, tmp_path / "out", "2026-08-04", "current", _make_src(tmp_path))
    assert rc == 0
    assert not (tmp_path / "out" / bdkd.ZIP_NAMES_MD["current"]).exists()


def test_bundle_doc_names_composes_repo_stem_to_numbered_name() -> None:
    current = bdkd.bundle_doc_names("current")
    assert current["KIT-VARIABLES-REFERENCE"] == "1_Variables_Reference"
    assert current["CURRENT-STATE-BUILD-DELTA"] == "2_Build_Delta"
    # Same shared doc, different slot in the other edition's reading order.
    assert bdkd.bundle_doc_names("target")["KIT-VARIABLES-REFERENCE"] == "2_Variables_Reference"
    # Docs the edition does not ship are absent, not mapped to a wrong name.
    assert "KIT-SCRIPTS" not in current
    assert "CURRENT-STATE-BUILD-DELTA" not in bdkd.bundle_doc_names("target")


def test_rewrite_retargets_links_and_bare_names() -> None:
    body = (
        "See the [Variables Reference](./KIT-VARIABLES-REFERENCE.md) and\n"
        "`CURRENT-STATE-BUILD-DELTA.md` §5, plus KIT-BUILD-SPEC.\n"
    )
    out, n, absent = bdkd.rewrite_doc_references(body, "current")

    assert "(./1_Variables_Reference.md)" in out
    assert "`2_Build_Delta.md` §5" in out
    assert "plus 7_Build_Specification." in out
    assert "KIT-VARIABLES-REFERENCE" not in out
    assert n == 3
    assert absent == {}


def test_rewrite_annotates_references_to_docs_this_edition_omits() -> None:
    body = "Every script is described in the [Scripts Manifest](./KIT-SCRIPTS.md).\n"
    out, _, absent = bdkd.rewrite_doc_references(body, "current")

    # Flattened to plain text rather than left pointing at a file that is not here.
    assert "](./" not in out
    assert f"Scripts Manifest ({bdkd._ABSENT_NOTE})" in out
    assert absent == {"KIT-SCRIPTS": 1}


def test_rewrite_leaves_kit_source_paths_alone() -> None:
    body = "- `atf/README.md` — the test suites Phase 6 runs.\n"
    out, n, _ = bdkd.rewrite_doc_references(body, "current")

    assert out == body
    assert n == 0


def test_rewrite_prefers_the_longest_matching_stem() -> None:
    body = "CURRENT-STATE-START-HERE and START-HERE are different documents.\n"
    out, _, _ = bdkd.rewrite_doc_references(body, "target")

    # target ships START-HERE as 0_START_HERE; CURRENT-STATE-START-HERE it does not.
    assert f"CURRENT-STATE-START-HERE ({bdkd._ABSENT_NOTE})" in out
    assert "and 0_START_HERE are different" in out


def test_built_markdown_zip_contains_no_unresolvable_doc_links(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    series = site_root / bdkd.SITE_SERIES_REL
    for stem in bdkd.CURRENT_DOCX_SET:
        (series / f"{stem}.md").write_text(
            "See [Variables Reference](./KIT-VARIABLES-REFERENCE.md).\n", encoding="utf8"
        )

    out_dir = tmp_path / "out"
    assert bdkd.build_markdown_one(site_root, out_dir, "2026-08-18", "current", _make_src(tmp_path)) == 0

    with zipfile.ZipFile(out_dir / bdkd.ZIP_NAMES_MD["current"]) as z:
        names = set(z.namelist())
        root = bdkd.ROOTS["current"]
        assert "DOC NAMES" in z.read(f"{root}/README.txt").decode("utf8")
        for arc in names:
            if not arc.endswith(".md"):
                continue
            body = z.read(arc).decode("utf8")
            for target in re.findall(r"\]\((?:\./)?([\w.-]+\.md)\)", body):
                assert f"{root}/{target}" in names, f"{arc} links to missing {target}"


def test_rewrite_figure_srcs_points_at_the_published_site() -> None:
    body = (
        '<img src="servicenow-day2/figs/day2kit-task-01-password-reset.png"\n'
        'style="width:100.0%"\n'
        'data-fig-alt="Password reset task card: split actuation."\n'
        'alt="Password reset current-state write path." />\n'
    )
    out, n = bdkd.rewrite_figure_srcs(body, TEST_SITE_BASE)

    assert n == 1
    assert out.startswith(f'<img src="{TEST_SITE_BASE}{bdkd.FIGS_REL}/day2kit-task-01')
    # No relative src survives -- that is the thing that was broken in the bundle.
    assert 'src="servicenow-day2/' not in out
    # The description an AI actually reads must survive untouched.
    assert 'data-fig-alt="Password reset task card: split actuation."' in out
    assert 'alt="Password reset current-state write path."' in out


def test_markdown_zip_leaves_no_relative_figure_src(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    series = site_root / bdkd.SITE_SERIES_REL
    for stem in bdkd.CURRENT_DOCX_SET:
        (series / f"{stem}.md").write_text('<img src="servicenow-day2/figs/x.png" alt="x" />\n', encoding="utf8")

    out_dir = tmp_path / "out"
    assert bdkd.build_markdown_one(site_root, out_dir, "2026-08-18", "current", _make_src(tmp_path)) == 0

    with zipfile.ZipFile(out_dir / bdkd.ZIP_NAMES_MD["current"]) as z:
        for arc in z.namelist():
            if arc.endswith(".md"):
                body = z.read(arc).decode("utf8")
                assert 'src="servicenow-day2/' not in body
                assert TEST_SITE_BASE in body


def test_collect_takes_figure_pngs_from_the_rendered_site(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    figs = site_root / bdkd.FIGS_REL
    figs.mkdir(parents=True)
    # One shared, one current-only, one target-only.
    for name in (
        "day2kit-current-fig-01-hybrid-path.png",
        "day2kit-task-01-password-reset.png",
        "day2kit-target-task-01-password-reset.png",
    ):
        (figs / name).write_bytes(b"png")

    src_root = tmp_path / "src"
    (src_root / bdkd.KIT_SRC_REL).mkdir(parents=True)

    members, notes = bdkd.collect(site_root, src_root, "current")

    pngs = {k for k in members if k.endswith(".png")}
    assert "servicenow-day2/figs/day2kit-task-01-password-reset.png" in pngs
    # The other edition's task figures must not leak in.
    assert "servicenow-day2/figs/day2kit-target-task-01-password-reset.png" not in pngs
    assert any("figure PNGs from _site: 2" in n for n in notes)


def test_collect_warns_when_only_svg_sources_are_present(tmp_path: Path) -> None:
    site_root = _make_series(tmp_path)
    src_root = tmp_path / "src"
    src_figs = src_root / bdkd.KIT_SRC_REL / "figs"
    src_figs.mkdir(parents=True)
    (src_figs / "day2kit-task-01-password-reset.svg").write_text("<svg/>", encoding="utf8")

    _, notes = bdkd.collect(site_root, src_root, "current")

    # Shipping SVG with no rendered PNG breaks every <img> -- say so, loudly.
    assert any("WARNING" in n and ".png" in n for n in notes)


def test_read_site_base_reads_site_url_from_quarto_config(tmp_path: Path) -> None:
    assert bdkd.read_site_base(_make_src(tmp_path)) == TEST_SITE_BASE


def test_read_site_base_normalises_a_missing_trailing_slash(tmp_path: Path) -> None:
    src = _make_src(tmp_path, "https://example.test/uiao")
    assert bdkd.read_site_base(src) == "https://example.test/uiao/"


def test_read_site_base_warns_and_falls_back_rather_than_raising(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # No site-url key at all.
    assert bdkd.read_site_base(_make_src(tmp_path, None)) == bdkd.SITE_BASE_FALLBACK
    assert "WARNING" in capsys.readouterr().out

    # No config file at all -- must not raise; the kit build depends on it.
    assert bdkd.read_site_base(tmp_path / "nope") == bdkd.SITE_BASE_FALLBACK
    assert "WARNING" in capsys.readouterr().out


def test_fallback_site_base_matches_the_real_quarto_config() -> None:
    """The fallback is a duplicate of docs/_quarto.yml -- fail if it drifts."""
    repo_root = Path(__file__).resolve().parents[1]
    assert bdkd.read_site_base(repo_root) == bdkd.SITE_BASE_FALLBACK
