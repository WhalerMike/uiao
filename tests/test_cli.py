"""Tests for uiao_core.cli.app module."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from uiao_core.cli.app import app

runner = CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_version_flag(self) -> None:
        """--version prints version string and exits 0."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "uiao-core" in result.stdout

    def test_help_flag(self) -> None:
        """--help prints help text and exits 0."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "UIAO-Core" in result.stdout or "uiao" in result.stdout.lower()

    def test_generate_ssp_help(self) -> None:
        """generate-ssp --help shows subcommand help."""
        result = runner.invoke(app, ["generate-ssp", "--help"])
        assert result.exit_code == 0
        assert "canon" in result.stdout.lower()

    def test_validate_help(self) -> None:
        """validate --help shows subcommand help."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0

    def test_canon_check_help(self) -> None:
        """canon-check --help shows subcommand help."""
        result = runner.invoke(app, ["canon-check", "--help"])
        assert result.exit_code == 0

    def test_generate_docs_in_help(self) -> None:
        """generate-docs appears in top-level --help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "generate-docs" in result.stdout

    def test_generate_docs_help(self) -> None:
        """generate-docs --help shows subcommand help with expected options."""
        result = runner.invoke(app, ["generate-docs", "--help"])
        assert result.exit_code == 0
        # Strip ANSI escape codes before checking for option names
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).lower()
        assert "canon" in plain
        assert "data-dir" in plain
        assert "templates-dir" in plain
        assert "output-dir" in plain

    def test_generate_docs_runs(self, tmp_path) -> None:
        """generate-docs runs without crashing on a minimal project structure."""
        with patch(
            "uiao_core.generators.docs.build_docs",
            return_value=["docs/test.md"],
        ) as mock_build:
            result = runner.invoke(
                app,
                [
                    "generate-docs",
                    "--canon",
                    "canon/test.yaml",
                    "--data-dir",
                    str(tmp_path / "data"),
                    "--templates-dir",
                    str(tmp_path / "templates"),
                    "--output-dir",
                    str(tmp_path / "docs"),
                ],
            )
            assert result.exit_code == 0
            assert "Generated" in result.stdout
            assert "1" in result.stdout
            mock_build.assert_called_once_with(
                canon_path=Path("canon/test.yaml"),
                data_dir=Path(str(tmp_path / "data")),
                templates_dir=Path(str(tmp_path / "templates")),
                docs_dir=Path(str(tmp_path / "docs")),
                generate_diagrams=True,
                force_visuals=False,
            )


class TestGenerateAll:
    """Tests for the generate-all orchestration command."""

    def test_generate_all_in_help(self) -> None:
        """generate-all appears in top-level --help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "generate-all" in result.stdout

    def test_generate_all_help(self) -> None:
        """generate-all --help shows expected options."""
        result = runner.invoke(app, ["generate-all", "--help"])
        assert result.exit_code == 0
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).lower()
        assert "canon" in plain
        assert "data-dir" in plain
        assert "exports-dir" in plain

    def test_generate_all_runs_all_steps(self, tmp_path) -> None:
        """generate-all invokes every generator and reports success."""
        patches = [
            patch("uiao_core.generators.mermaid.render_all_mermaid", return_value=["img1.png", "img2.png"]),
            patch("uiao_core.generators.docs.build_docs", return_value=["docs/a.md", "docs/b.md"]),
            patch("uiao_core.generators.oscal.build_oscal", return_value=tmp_path / "oscal.json"),
            patch("uiao_core.generators.ssp.build_ssp", return_value=tmp_path / "ssp.json"),
            patch("uiao_core.generators.poam.build_poam_export", return_value=tmp_path / "poam.json"),
            patch("uiao_core.generators.rich_docx.build_rich_docx", return_value=tmp_path / "brief.docx"),
            patch("uiao_core.generators.pptx.build_pptx", return_value=tmp_path / "deck.pptx"),
            patch("uiao_core.generators.sbom.build_sbom", return_value=tmp_path / "sbom.json"),
        ]

        with contextlib.ExitStack() as stack:
            for cm in patches:
                stack.enter_context(cm)

            result = runner.invoke(
                app,
                [
                    "generate-all",
                    "--canon", "canon/test.yaml",
                    "--data-dir", str(tmp_path / "data"),
                    "--exports-dir", str(tmp_path / "exports"),
                ],
            )

        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert result.exit_code == 0, plain
        assert "All artifacts generated" in plain

    def test_generate_all_skip_sbom(self, tmp_path) -> None:
        """--skip-sbom skips SBOM generation and still exits 0."""
        patches = [
            patch("uiao_core.generators.mermaid.render_all_mermaid", return_value=[]),
            patch("uiao_core.generators.docs.build_docs", return_value=[]),
            patch("uiao_core.generators.oscal.build_oscal", return_value=tmp_path / "o.json"),
            patch("uiao_core.generators.ssp.build_ssp", return_value=tmp_path / "s.json"),
            patch("uiao_core.generators.poam.build_poam_export", return_value=tmp_path / "p.json"),
            patch("uiao_core.generators.rich_docx.build_rich_docx", return_value=tmp_path / "d.docx"),
            patch("uiao_core.generators.pptx.build_pptx", return_value=tmp_path / "p.pptx"),
        ]

        with contextlib.ExitStack() as stack:
            for cm in patches:
                stack.enter_context(cm)
            result = runner.invoke(app, ["generate-all", "--skip-sbom"])

        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert result.exit_code == 0, plain
        assert "SBOM skipped" in plain

    def test_generate_all_partial_failure_exits_nonzero(self, tmp_path) -> None:
        """generate-all exits with code 1 and reports errors when a generator raises."""
        patches = [
            patch("uiao_core.generators.mermaid.render_all_mermaid", return_value=[]),
            patch("uiao_core.generators.docs.build_docs", side_effect=RuntimeError("template missing")),
            patch("uiao_core.generators.oscal.build_oscal", return_value=tmp_path / "o.json"),
            patch("uiao_core.generators.ssp.build_ssp", return_value=tmp_path / "s.json"),
            patch("uiao_core.generators.poam.build_poam_export", return_value=tmp_path / "p.json"),
            patch("uiao_core.generators.rich_docx.build_rich_docx", return_value=tmp_path / "d.docx"),
            patch("uiao_core.generators.pptx.build_pptx", return_value=tmp_path / "p.pptx"),
            patch("uiao_core.generators.sbom.build_sbom", return_value=tmp_path / "sbom.json"),
        ]

        with contextlib.ExitStack() as stack:
            for cm in patches:
                stack.enter_context(cm)
            result = runner.invoke(app, ["generate-all"])

        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert result.exit_code == 1, plain
        assert "template missing" in plain
