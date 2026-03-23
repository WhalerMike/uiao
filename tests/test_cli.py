"""Tests for uiao_core.cli.app module."""
from __future__ import annotations

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
