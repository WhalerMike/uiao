"""Tests for the diagram automation feature.

Covers:
- Loading generation-inputs/diagrams.yaml
- generate_diagrams_from_canon() creating .mermaid files
- replace_mermaid_blocks_with_images() post-processing
- Mermaid theme configuration consistency
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).parent.parent
_DIAGRAMS_CANON = _REPO_ROOT / "generation-inputs" / "diagrams.yaml"
_MERMAID_CONFIG = _REPO_ROOT / "data" / "mermaid-config.json"


# ---------------------------------------------------------------------------
# Canon YAML loading
# ---------------------------------------------------------------------------
class TestDiagramsCanon:
    """Verify that generation-inputs/diagrams.yaml loads and is well-formed."""

    def test_file_exists(self) -> None:
        assert _DIAGRAMS_CANON.exists(), f"generation-inputs/diagrams.yaml not found at {_DIAGRAMS_CANON}"

    def test_loads_as_yaml(self) -> None:
        data = yaml.safe_load(_DIAGRAMS_CANON.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "Top-level YAML must be a mapping"

    def test_diagrams_section_present(self) -> None:
        data = yaml.safe_load(_DIAGRAMS_CANON.read_text(encoding="utf-8"))
        assert "diagrams" in data, "'diagrams' key must exist in generation-inputs/diagrams.yaml"

    def test_expected_diagram_keys(self) -> None:
        data = yaml.safe_load(_DIAGRAMS_CANON.read_text(encoding="utf-8"))
        diagrams = data["diagrams"]
        expected = {
            "architecture_overview",
            "authorization_boundary",
            "data_flow",
            "uiao_planes",
            "generation_pipeline",
            "zero_trust_journey",
        }
        assert expected.issubset(set(diagrams.keys())), f"Missing diagram keys: {expected - set(diagrams.keys())}"

    def test_each_diagram_has_required_fields(self) -> None:
        data = yaml.safe_load(_DIAGRAMS_CANON.read_text(encoding="utf-8"))
        for key, meta in data["diagrams"].items():
            assert "type" in meta, f"Diagram '{key}' missing 'type'"
            assert "title" in meta, f"Diagram '{key}' missing 'title'"
            assert "description" in meta, f"Diagram '{key}' missing 'description'"
            assert "content" in meta, f"Diagram '{key}' missing 'content'"
            assert meta["content"].strip(), f"Diagram '{key}' has empty 'content'"

    def test_load_diagrams_canon_function(self) -> None:
        from uiao_core.generators.diagrams import load_diagrams_canon

        diagrams = load_diagrams_canon(_DIAGRAMS_CANON)
        assert isinstance(diagrams, dict)
        assert len(diagrams) >= 6

    def test_load_diagrams_canon_missing_file(self, tmp_path: Path) -> None:
        from uiao_core.generators.diagrams import load_diagrams_canon

        result = load_diagrams_canon(tmp_path / "nonexistent.yaml")
        assert result == {}


# ---------------------------------------------------------------------------
# generate_diagrams_from_canon()
# ---------------------------------------------------------------------------
class TestGenerateDiagramsFromCanon:
    """Verify that generate_diagrams_from_canon() writes .mermaid files."""

    def test_creates_mermaid_files(self, tmp_path: Path) -> None:
        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        visuals_dir = tmp_path / "visuals"
        output_dir = tmp_path / "images"

        # Skip PNG rendering (no mmdc/Playwright in CI) — only check .mermaid writes
        import unittest.mock as mock

        with mock.patch("uiao_core.generators.diagrams.render_mermaid_file", return_value=None):
            generate_diagrams_from_canon(
                canon_path=_DIAGRAMS_CANON,
                visuals_dir=visuals_dir,
                output_dir=output_dir,
            )

        mermaid_files = list(visuals_dir.glob("*.mermaid"))
        assert len(mermaid_files) >= 6, f"Expected ≥6 .mermaid files, got {len(mermaid_files)}"

    def test_mermaid_file_names_match_keys(self, tmp_path: Path) -> None:
        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        visuals_dir = tmp_path / "visuals"

        import unittest.mock as mock

        with mock.patch("uiao_core.generators.diagrams.render_mermaid_file", return_value=None):
            generate_diagrams_from_canon(
                canon_path=_DIAGRAMS_CANON,
                visuals_dir=visuals_dir,
                output_dir=tmp_path / "images",
            )

        stems = {p.stem for p in visuals_dir.glob("*.mermaid")}
        expected = {
            "architecture_overview",
            "authorization_boundary",
            "data_flow",
            "uiao_planes",
            "generation_pipeline",
            "zero_trust_journey",
        }
        assert expected.issubset(stems), f"Missing .mermaid files: {expected - stems}"

    def test_mermaid_file_content_is_nonempty(self, tmp_path: Path) -> None:
        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        visuals_dir = tmp_path / "visuals"

        import unittest.mock as mock

        with mock.patch("uiao_core.generators.diagrams.render_mermaid_file", return_value=None):
            generate_diagrams_from_canon(
                canon_path=_DIAGRAMS_CANON,
                visuals_dir=visuals_dir,
                output_dir=tmp_path / "images",
            )

        for mmd in visuals_dir.glob("*.mermaid"):
            assert mmd.read_text(encoding="utf-8").strip(), f"{mmd.name} is empty"

    def test_mermaid_file_content_is_valid_mermaid(self, tmp_path: Path) -> None:
        """Each generated .mermaid file must contain Mermaid flowchart keywords."""
        import unittest.mock as mock

        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        visuals_dir = tmp_path / "visuals"

        with mock.patch("uiao_core.generators.diagrams.render_mermaid_file", return_value=None):
            generate_diagrams_from_canon(
                canon_path=_DIAGRAMS_CANON,
                visuals_dir=visuals_dir,
                output_dir=tmp_path / "images",
            )

        for mmd in visuals_dir.glob("*.mermaid"):
            text = mmd.read_text(encoding="utf-8")
            # All canon diagrams are flowcharts with edges
            assert "flowchart" in text.lower(), f"{mmd.name} missing 'flowchart' keyword"
            assert "-->" in text, f"{mmd.name} missing '-->' edge syntax"

    def test_strict_mode_raises_on_render_failure(self, tmp_path: Path) -> None:
        import unittest.mock as mock

        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        with (
            mock.patch("uiao_core.generators.diagrams.render_mermaid_file", return_value=None),
            pytest.raises(RuntimeError, match="Failed to render"),
        ):
            generate_diagrams_from_canon(
                canon_path=_DIAGRAMS_CANON,
                visuals_dir=tmp_path / "visuals",
                output_dir=tmp_path / "images",
                strict=True,
            )

    def test_returns_empty_list_for_missing_canon(self, tmp_path: Path) -> None:
        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        result = generate_diagrams_from_canon(
            canon_path=tmp_path / "nonexistent.yaml",
            visuals_dir=tmp_path / "visuals",
            output_dir=tmp_path / "images",
        )
        assert result == []

    def test_build_diagrams_returns_output_dir(self, tmp_path: Path) -> None:
        import unittest.mock as mock

        from uiao_core.generators.diagrams import build_diagrams

        with mock.patch("uiao_core.generators.diagrams.render_mermaid_file", return_value=None):
            result = build_diagrams(
                canon_path=_DIAGRAMS_CANON,
                visuals_dir=tmp_path / "visuals",
                output_dir=tmp_path / "images",
            )

        assert result == tmp_path / "images"


# ---------------------------------------------------------------------------
# replace_mermaid_blocks_with_images()
# ---------------------------------------------------------------------------
class TestReplaceMermaidBlocks:
    """Verify the Mermaid fence → <img> post-processing helper."""

    def test_replaces_single_block(self) -> None:
        from uiao_core.generators.docs import replace_mermaid_blocks_with_images

        md = "# Title\n\n```mermaid\nflowchart TD\n    A --> B\n```\n\nEnd."
        result = replace_mermaid_blocks_with_images(md)
        assert "```mermaid" not in result
        assert "<img" in result
        assert ".png" in result

    def test_replaces_multiple_blocks(self) -> None:
        from uiao_core.generators.docs import replace_mermaid_blocks_with_images

        md = "```mermaid\nflowchart LR\n    A --> B\n```\n\n```mermaid\nflowchart TD\n    C --> D\n```\n"
        result = replace_mermaid_blocks_with_images(md)
        assert result.count("<img") == 2
        assert "```mermaid" not in result

    def test_leaves_non_mermaid_fences_intact(self) -> None:
        from uiao_core.generators.docs import replace_mermaid_blocks_with_images

        md = "```python\nprint('hello')\n```\n"
        result = replace_mermaid_blocks_with_images(md)
        assert result == md

    def test_no_mermaid_blocks_unchanged(self) -> None:
        from uiao_core.generators.docs import replace_mermaid_blocks_with_images

        md = "# No diagrams here\n\nJust text."
        assert replace_mermaid_blocks_with_images(md) == md

    def test_img_contains_images_dir(self) -> None:
        from uiao_core.generators.docs import replace_mermaid_blocks_with_images

        md = "```mermaid\nflowchart TD\n    A --> B\n```"
        result = replace_mermaid_blocks_with_images(md, images_dir="custom/dir")
        assert "custom/dir" in result

    def test_empty_string_unchanged(self) -> None:
        from uiao_core.generators.docs import replace_mermaid_blocks_with_images

        assert replace_mermaid_blocks_with_images("") == ""


# ---------------------------------------------------------------------------
# Module import checks
# ---------------------------------------------------------------------------
class TestDiagramsModuleImports:
    """Verify diagrams module exports the expected symbols."""

    def test_import_diagrams_module(self) -> None:
        from uiao_core.generators import diagrams

        assert hasattr(diagrams, "generate_diagrams_from_canon")
        assert hasattr(diagrams, "build_diagrams")
        assert hasattr(diagrams, "load_diagrams_canon")

    def test_build_diagrams_in_package(self) -> None:
        from uiao_core.generators import build_diagrams

        assert callable(build_diagrams)


# ---------------------------------------------------------------------------
# build_docs integration: canon_path + force_visuals passthrough
# ---------------------------------------------------------------------------
class TestBuildDocsDiagramIntegration:
    """Verify build_docs passes canon_path and force_visuals to generate_diagrams_from_canon."""

    def test_build_docs_calls_generate_diagrams_with_canon_path(self, tmp_path: Path) -> None:
        """build_docs(..., generate_diagrams=True) forwards canon_path to the compiler."""
        import unittest.mock as mock

        import yaml

        from uiao_core.generators.docs import build_docs

        # Minimal template and context so build_docs can complete
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        docs_dir = tmp_path / "docs"
        site_dir = tmp_path / "site"
        canon_file = tmp_path / "test_canon.yaml"
        canon_file.write_text(yaml.dump({"version": "1.0", "diagrams": {}}), encoding="utf-8")

        with mock.patch(
            "uiao_core.generators.diagrams.generate_diagrams_from_canon",
            return_value=[],
        ) as mock_gen:
            build_docs(
                canon_path=canon_file,
                templates_dir=templates_dir,
                docs_dir=docs_dir,
                site_dir=site_dir,
                template_mapping={},
                generate_diagrams=True,
                force_visuals=False,
            )

        mock_gen.assert_called_once_with(canon_path=canon_file, force=False)

    def test_build_docs_honors_force_visuals(self, tmp_path: Path) -> None:
        """build_docs(..., force_visuals=True) passes force=True to generate_diagrams_from_canon."""
        import unittest.mock as mock

        import yaml

        from uiao_core.generators.docs import build_docs

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        canon_file = tmp_path / "test_canon.yaml"
        canon_file.write_text(yaml.dump({"version": "1.0", "diagrams": {}}), encoding="utf-8")

        with mock.patch(
            "uiao_core.generators.diagrams.generate_diagrams_from_canon",
            return_value=[],
        ) as mock_gen:
            build_docs(
                canon_path=canon_file,
                templates_dir=templates_dir,
                docs_dir=tmp_path / "docs",
                site_dir=tmp_path / "site",
                template_mapping={},
                generate_diagrams=True,
                force_visuals=True,
            )

        mock_gen.assert_called_once_with(canon_path=canon_file, force=True)

    def test_build_docs_skips_diagrams_when_disabled(self, tmp_path: Path) -> None:
        """build_docs(..., generate_diagrams=False) does not call generate_diagrams_from_canon."""
        import unittest.mock as mock

        import yaml

        from uiao_core.generators.docs import build_docs

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        canon_file = tmp_path / "test_canon.yaml"
        canon_file.write_text(yaml.dump({"version": "1.0", "diagrams": {}}), encoding="utf-8")

        with mock.patch(
            "uiao_core.generators.diagrams.generate_diagrams_from_canon",
            return_value=[],
        ) as mock_gen:
            build_docs(
                canon_path=canon_file,
                templates_dir=templates_dir,
                docs_dir=tmp_path / "docs",
                site_dir=tmp_path / "site",
                template_mapping={},
                generate_diagrams=False,
            )

        mock_gen.assert_not_called()

    def test_load_diagrams_from_leadership_briefing_canon(self) -> None:
        """generate_diagrams_from_canon reads diagrams from the main leadership briefing canon."""
        import unittest.mock as mock

        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        leadership_canon = _REPO_ROOT / "generation-inputs" / "uiao_leadership_briefing_v1.0.yaml"
        assert leadership_canon.exists(), f"Canon not found: {leadership_canon}"

        with mock.patch("uiao_core.generators.diagrams.render_mermaid_file", return_value=None) as mock_render:
            import tempfile

            with tempfile.TemporaryDirectory() as td:
                visuals_dir = Path(td) / "visuals"
                output_dir = Path(td) / "images"
                generate_diagrams_from_canon(
                    canon_path=leadership_canon,
                    visuals_dir=visuals_dir,
                    output_dir=output_dir,
                )

        # At least one .mermaid file should have been targeted for rendering
        # (render_mermaid_file was called at least once)
        assert mock_render.call_count >= 1


# ---------------------------------------------------------------------------
# Mermaid theme configuration consistency
# ---------------------------------------------------------------------------
class TestMermaidThemeConfiguration:
    """Verify that all Mermaid rendering paths use the canonical 'neutral' theme."""

    def test_mermaid_config_file_exists(self) -> None:
        assert _MERMAID_CONFIG.exists(), f"data/mermaid-config.json not found at {_MERMAID_CONFIG}"

    def test_mermaid_config_is_valid_json(self) -> None:
        data = json.loads(_MERMAID_CONFIG.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "mermaid-config.json must be a JSON object"

    def test_mermaid_config_theme_is_neutral(self) -> None:
        data = json.loads(_MERMAID_CONFIG.read_text(encoding="utf-8"))
        assert data.get("theme") == "neutral", (
            f"data/mermaid-config.json 'theme' must be 'neutral', got {data.get('theme')!r}"
        )

    def test_quarto_yml_mermaid_theme_is_neutral(self) -> None:
        quarto_yml = _REPO_ROOT / "_quarto.yml"
        assert quarto_yml.exists(), "_quarto.yml not found"
        cfg = yaml.safe_load(quarto_yml.read_text(encoding="utf-8"))
        mermaid_section = cfg.get("mermaid", {})
        assert mermaid_section.get("theme") == "neutral", (
            f"_quarto.yml mermaid.theme must be 'neutral', got {mermaid_section.get('theme')!r}"
        )

    def test_mermaid_html_uses_canonical_theme(self) -> None:
        from uiao_core.generators.mermaid import MERMAID_THEME, _mermaid_html

        html = _mermaid_html("flowchart TD\n    A --> B")
        assert f"theme:'{MERMAID_THEME}'" in html, f"_mermaid_html() must use theme '{MERMAID_THEME}'"

    def test_mermaid_module_theme_constant_is_neutral(self) -> None:
        from uiao_core.generators.mermaid import MERMAID_THEME

        assert MERMAID_THEME == "neutral", f"MERMAID_THEME constant must be 'neutral', got {MERMAID_THEME!r}"

    def test_config_theme_matches_module_constant(self) -> None:
        from uiao_core.generators.mermaid import MERMAID_THEME

        data = json.loads(_MERMAID_CONFIG.read_text(encoding="utf-8"))
        assert data.get("theme") == MERMAID_THEME, (
            f"data/mermaid-config.json theme ({data.get('theme')!r}) must match "
            f"MERMAID_THEME constant ({MERMAID_THEME!r})"
        )

    def test_render_mmdc_passes_config_file(self, tmp_path: Path) -> None:
        """_render_mmdc must include either --configFile or --theme in its command."""
        import unittest.mock as mock

        from uiao_core.generators.mermaid import _render_mmdc

        mmd_path = tmp_path / "test.mermaid"
        mmd_path.write_text("flowchart TD\n    A --> B", encoding="utf-8")
        png_path = tmp_path / "test.png"

        captured_args: list[str] = []

        def fake_run(cmd, **_kwargs):
            captured_args.extend(cmd)
            # Simulate success by creating the PNG
            png_path.touch()
            result = mock.MagicMock()
            result.returncode = 0
            return result

        with (
            mock.patch("shutil.which", return_value="/usr/bin/mmdc"),
            mock.patch("subprocess.run", side_effect=fake_run),
        ):
            _render_mmdc(mmd_path, png_path)

        cmd_str = " ".join(captured_args)
        assert "--configFile" in cmd_str or "--theme" in cmd_str, (
            f"mmdc command must include --configFile or --theme; got: {cmd_str}"
        )
