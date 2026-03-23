"""Tests for uiao_core.cli.app module."""
from __future__ import annotations

from pathlib import Path

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
        import re

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
        from unittest.mock import patch

        with patch("uiao_core.generators.docs.build_docs", return_value=["docs/test.md"]) as mock_build:
            result = runner.invoke(
                app,
                [
                    "generate-docs",
                    "--canon", "canon/test.yaml",
                    "--data-dir", str(tmp_path / "data"),
                    "--templates-dir", str(tmp_path / "templates"),
                    "--output-dir", str(tmp_path / "docs"),
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
        )
