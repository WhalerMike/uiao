"""Tests for uiao_core.cli.app module."""

from __future__ import annotations

import json
import contextlib
import re
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
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
                    "generation-inputs/test.yaml",
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
                canon_path=Path("generation-inputs/test.yaml"),
                data_dir=Path(str(tmp_path / "data")),
                templates_dir=Path(str(tmp_path / "templates")),
                docs_dir=Path(str(tmp_path / "docs")),
                generate_diagrams=True,
                force_visuals=False,
            )


# ---------------------------------------------------------------------------
# Fixtures shared by conmon tests
# ---------------------------------------------------------------------------


@pytest.fixture
def sentinel_alert_json(tmp_path: Path) -> Path:
    """Write a minimal Sentinel alert JSON to a temp file."""
    payload = {
        "properties": {
            "systemAlertId": "cli-alert-001",
            "alertDisplayName": "CLI Test Alert",
            "severity": "High",
            "productName": "Microsoft Sentinel",
            "description": "CLI integration test alert",
            "timeGenerated": "2026-03-25T00:00:00Z",
        }
    }
    p = tmp_path / "alert.json"
    p.write_text(json.dumps(payload))
    return p


@pytest.fixture
def monitoring_sources_yml(tmp_path: Path) -> Path:
    data = {
        "monitoring_sources": [
            {
                "name": "CLI SIEM",
                "type": "siem",
                "telemetry": [
                    {
                        "signal": "identity_anomaly",
                        "maps_to_control": "AC-2",
                        "description": "Anomalous identity behavior",
                    }
                ],
            }
        ]
    }
    p = tmp_path / "monitoring-sources.yml"
    p.write_text(yaml.dump(data))
    return p


@pytest.fixture
def ksi_mappings_yml(tmp_path: Path) -> Path:
    data = {
        "ksi_mappings": [
            {
                "ksi_id": "KSI-CLI-1",
                "title": "CLI KSI Implemented",
                "control_ids": ["IA-2"],
                "evidence_source": "Entra ID",
                "status": "Implemented",
            },
            {
                "ksi_id": "KSI-CLI-2",
                "title": "CLI KSI Partial",
                "control_ids": ["CM-2"],
                "evidence_source": "Intune",
                "status": "Partial",
            },
        ]
    }
    p = tmp_path / "ksi-mappings.yml"
    p.write_text(yaml.dump(data))
    return p


# ===========================================================================
# conmon-process tests
# ===========================================================================


class TestConmonProcess:
    def test_help_shows_command(self) -> None:
        result = runner.invoke(app, ["conmon-process", "--help"])
        assert result.exit_code == 0
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).lower()
        assert "alert" in plain

    def test_missing_alert_json_exits_nonzero(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "conmon-process",
                "--alert-json",
                str(tmp_path / "nonexistent.json"),
            ],
        )
        assert result.exit_code != 0

    def test_no_upsert_dry_run(
        self,
        sentinel_alert_json: Path,
        monitoring_sources_yml: Path,
        tmp_path: Path,
    ) -> None:
        poam_out = tmp_path / "poam.yml"
        result = runner.invoke(
            app,
            [
                "conmon-process",
                "--alert-json",
                str(sentinel_alert_json),
                "--monitoring-sources",
                str(monitoring_sources_yml),
                "--poam-path",
                str(poam_out),
                "--no-upsert",
            ],
        )
        assert result.exit_code == 0
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        assert "Dry-run" in plain
        # File must NOT have been created in dry-run mode
        assert not poam_out.exists()

    def test_upsert_writes_poam_file(
        self,
        sentinel_alert_json: Path,
        monitoring_sources_yml: Path,
        tmp_path: Path,
    ) -> None:
        poam_out = tmp_path / "poam.yml"
        result = runner.invoke(
            app,
            [
                "conmon-process",
                "--alert-json",
                str(sentinel_alert_json),
                "--monitoring-sources",
                str(monitoring_sources_yml),
                "--poam-path",
                str(poam_out),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert poam_out.exists()
        findings = yaml.safe_load(poam_out.read_text())
        assert isinstance(findings, list)
        assert len(findings) >= 1
        assert findings[0]["id"].startswith("POAM-UIAO-")


# ===========================================================================
# conmon-export-oa tests
# ===========================================================================


class TestConmonExportOa:
    def test_help_shows_command(self) -> None:
        result = runner.invoke(app, ["conmon-export-oa", "--help"])
        assert result.exit_code == 0
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).lower()
        assert "ongoing" in plain or "authorization" in plain or "oscal" in plain

    def test_exports_valid_json(
        self,
        monitoring_sources_yml: Path,
        ksi_mappings_yml: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "oa.json"
        result = runner.invoke(
            app,
            [
                "conmon-export-oa",
                "--monitoring-sources",
                str(monitoring_sources_yml),
                "--ksi-mappings",
                str(ksi_mappings_yml),
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()
        doc = json.loads(out.read_text())
        assert "ongoing-authorization" in doc
        assert len(doc["ongoing-authorization"]["observations"]) > 0

    def test_output_path_in_stdout(
        self,
        monitoring_sources_yml: Path,
        ksi_mappings_yml: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "oa-output.json"
        result = runner.invoke(
            app,
            [
                "conmon-export-oa",
                "--monitoring-sources",
                str(monitoring_sources_yml),
                "--ksi-mappings",
                str(ksi_mappings_yml),
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0
        assert str(out) in result.stdout


# ===========================================================================
# conmon-dashboard tests
# ===========================================================================


class TestConmonDashboard:
    def test_help_shows_command(self) -> None:
        result = runner.invoke(app, ["conmon-dashboard", "--help"])
        assert result.exit_code == 0
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).lower()
        assert "ksi" in plain or "dashboard" in plain

    def test_exports_json_by_default(self, ksi_mappings_yml: Path, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.json"
        result = runner.invoke(
            app,
            [
                "conmon-dashboard",
                "--ksi-mappings",
                str(ksi_mappings_yml),
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()
        data = json.loads(out.read_text())
        assert "ksi_summary" in data
        assert data["oscal_version"] == "1.0.4"

    def test_exports_yaml_format(self, ksi_mappings_yml: Path, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.yml"
        result = runner.invoke(
            app,
            [
                "conmon-dashboard",
                "--ksi-mappings",
                str(ksi_mappings_yml),
                "--output",
                str(out),
                "--format",
                "yaml",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()
        data = yaml.safe_load(out.read_text())
        assert "ksi_summary" in data

    def test_invalid_format_exits_nonzero(self, ksi_mappings_yml: Path, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.xml"
        result = runner.invoke(
            app,
            [
                "conmon-dashboard",
                "--ksi-mappings",
                str(ksi_mappings_yml),
                "--output",
                str(out),
                "--format",
                "xml",
            ],
        )
        assert result.exit_code != 0


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
            patch("uiao_core.generators.plantuml.render_plantuml_dir", return_value=["img1.png", "img2.png"]),
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
                    "--canon",
                    "generation-inputs/test.yaml",
                    "--data-dir",
                    str(tmp_path / "data"),
                    "--exports-dir",
                    str(tmp_path / "exports"),
                ],
            )

        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert result.exit_code == 0, plain
        assert "All artifacts generated" in plain

    def test_generate_all_skip_sbom(self, tmp_path) -> None:
        """--skip-sbom skips SBOM generation and still exits 0."""
        patches = [
            patch("uiao_core.generators.plantuml.render_plantuml_dir", return_value=[]),
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
            patch("uiao_core.generators.plantuml.render_plantuml_dir", return_value=[]),
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
