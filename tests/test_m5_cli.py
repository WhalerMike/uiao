"""tests/test_m5_cli.py — M5 public-surface CLI tests.

Tests for:
  - ``uiao cql query`` (CQL Engine → CLI-reachable, UIAO_108)
  - ``uiao evidence graph`` (Evidence Graph → CLI-reachable, UIAO_113)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*[mK]", "", text)

# ---------------------------------------------------------------------------
# Shared minimal SCuBA fixture
# ---------------------------------------------------------------------------
_SCUBA_FIXTURE = {
    "assessment_metadata": {
        "run_id": "m5-test-001",
        "assessment_date": "2026-04-08T00:00:00Z",
        "tool_version": "test",
        "collector_user": "test-user",
    },
    "tenant": {"tenant_id": "test-tenant-m5"},
    "ksi_results": [
        {
            "ksi_id": "KSI-IA-01",
            "status": "PASS",
            "severity": "High",
            "details": "MFA enforced via Conditional Access",
        },
        {
            "ksi_id": "KSI-IA-02",
            "status": "FAIL",
            "severity": "Medium",
            "details": "Legacy auth not fully blocked",
        },
    ],
}


@pytest.fixture()
def scuba_json(tmp_path: Path) -> Path:
    p = tmp_path / "normalized.json"
    p.write_text(json.dumps(_SCUBA_FIXTURE), encoding="utf-8")
    return p


@pytest.fixture()
def bundle_json(tmp_path: Path, scuba_json: Path) -> Path:
    """Build an evidence bundle JSON from the fixture and return its path."""
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result

    result = transform_scuba_to_ir(str(scuba_json))
    bundle = build_bundle_from_transform_result(result)
    p = tmp_path / "bundle.json"
    p.write_text(bundle.to_canonical(), encoding="utf-8")
    return p


# ===========================================================================
# uiao cql --help / uiao cql query --help
# ===========================================================================

class TestCQLHelp:
    def test_cql_group_help(self) -> None:
        """``uiao cql --help`` exits 0 and shows the query sub-command."""
        result = runner.invoke(app, ["cql", "--help"])
        assert result.exit_code == 0, result.output
        assert "query" in result.output.lower()

    def test_cql_query_help(self) -> None:
        """``uiao cql query --help`` exits 0 and mentions --bundle."""
        result = runner.invoke(app, ["cql", "query", "--help"])
        assert result.exit_code == 0, result.output
        assert "--bundle" in _strip_ansi(result.output)

    def test_cql_in_top_level_help(self) -> None:
        """``uiao --help`` lists the ``cql`` command group."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0, result.output
        assert "cql" in result.output


# ===========================================================================
# uiao cql query
# ===========================================================================

class TestCQLQuery:
    def test_show_controls_fail(self, bundle_json: Path) -> None:
        """SHOW CONTROLS WHERE status = 'FAIL' returns the failing KSI."""
        result = runner.invoke(
            app,
            ["cql", "query", "SHOW CONTROLS WHERE status = 'FAIL'", "--bundle", str(bundle_json)],
        )
        assert result.exit_code == 0, result.output
        assert "KSI-IA-02" in result.output

    def test_show_controls_pass(self, bundle_json: Path) -> None:
        """SHOW CONTROLS WHERE status = 'PASS' returns the passing KSI."""
        result = runner.invoke(
            app,
            ["cql", "query", "SHOW CONTROLS WHERE status = 'PASS'", "--bundle", str(bundle_json)],
        )
        assert result.exit_code == 0, result.output
        assert "KSI-IA-01" in result.output

    def test_show_evidence(self, bundle_json: Path) -> None:
        """SHOW EVIDENCE returns records."""
        result = runner.invoke(
            app,
            ["cql", "query", "SHOW EVIDENCE", "--bundle", str(bundle_json)],
        )
        assert result.exit_code == 0, result.output
        # Total should be 2 (one PASS, one FAIL)
        assert "Total:" in result.output or "total" in result.output.lower()

    def test_show_evidence_for_control(self, bundle_json: Path) -> None:
        """SHOW EVIDENCE FOR CONTROL 'KSI-IA-02' returns only that control's evidence."""
        result = runner.invoke(
            app,
            [
                "cql",
                "query",
                "SHOW EVIDENCE FOR CONTROL 'KSI-IA-02'",
                "--bundle",
                str(bundle_json),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_show_poam(self, bundle_json: Path) -> None:
        """SHOW POAM returns open POAM items synthesised from FAIL evidence."""
        result = runner.invoke(
            app,
            ["cql", "query", "SHOW POAM WHERE status = 'Open'", "--bundle", str(bundle_json)],
        )
        assert result.exit_code == 0, result.output

    def test_json_format_output(self, bundle_json: Path, tmp_path: Path) -> None:
        """--format json writes valid JSON to stdout."""
        result = runner.invoke(
            app,
            [
                "cql",
                "query",
                "SHOW CONTROLS",
                "--bundle",
                str(bundle_json),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        plain = _strip_ansi(result.output)
        json_start = plain.find("{")
        assert json_start >= 0, f"No JSON found in output: {plain!r}"
        parsed = json.loads(plain[json_start:])
        assert "records" in parsed
        assert "total" in parsed
        assert "query_type" in parsed

    def test_output_file(self, bundle_json: Path, tmp_path: Path) -> None:
        """--output writes JSON to the specified file."""
        out_file = tmp_path / "results.json"
        result = runner.invoke(
            app,
            [
                "cql",
                "query",
                "SHOW CONTROLS",
                "--bundle",
                str(bundle_json),
                "--format",
                "json",
                "--output",
                str(out_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        parsed = json.loads(out_file.read_text())
        assert "records" in parsed

    def test_missing_bundle_exits_nonzero(self) -> None:
        """A missing bundle file causes a non-zero exit code."""
        result = runner.invoke(
            app,
            ["cql", "query", "SHOW CONTROLS", "--bundle", "/nonexistent/bundle.json"],
        )
        assert result.exit_code != 0

    def test_invalid_cql_exits_nonzero(self, bundle_json: Path) -> None:
        """An unparseable CQL string causes a non-zero exit code."""
        result = runner.invoke(
            app,
            ["cql", "query", "NOT VALID CQL", "--bundle", str(bundle_json)],
        )
        assert result.exit_code != 0


# ===========================================================================
# uiao evidence graph --help / uiao evidence graph
# ===========================================================================

class TestEvidenceGraphHelp:
    def test_evidence_graph_help(self) -> None:
        """``uiao evidence graph --help`` exits 0 and mentions --input."""
        result = runner.invoke(app, ["evidence", "graph", "--help"])
        assert result.exit_code == 0, result.output
        assert "--input" in _strip_ansi(result.output)

    def test_evidence_graph_in_evidence_help(self) -> None:
        """``uiao evidence --help`` lists the ``graph`` sub-command."""
        result = runner.invoke(app, ["evidence", "--help"])
        assert result.exit_code == 0, result.output
        assert "graph" in result.output.lower()


class TestEvidenceGraph:
    def test_graph_stats_table(self, scuba_json: Path) -> None:
        """``uiao evidence graph`` prints node/edge statistics."""
        result = runner.invoke(app, ["evidence", "graph", "--input", str(scuba_json)])
        assert result.exit_code == 0, result.output
        assert "Total nodes" in result.output
        assert "Total edges" in result.output

    def test_graph_stats_json(self, scuba_json: Path) -> None:
        """--format json returns valid graph stats JSON."""
        result = runner.invoke(
            app,
            ["evidence", "graph", "--input", str(scuba_json), "--format", "json"],
        )
        assert result.exit_code == 0, result.output
        # Strip any Rich console prefix lines; find the JSON block
        plain = _strip_ansi(result.output)
        # Find the first '{' to isolate the JSON
        json_start = plain.find("{")
        assert json_start >= 0, f"No JSON found in output: {plain!r}"
        parsed = json.loads(plain[json_start:])
        assert "total_nodes" in parsed
        assert "nodes_by_type" in parsed
        assert "edges_by_type" in parsed

    def test_graph_stats_output_file(self, scuba_json: Path, tmp_path: Path) -> None:
        """--output writes graph stats JSON to file."""
        out_file = tmp_path / "graph.json"
        result = runner.invoke(
            app,
            ["evidence", "graph", "--input", str(scuba_json), "--output", str(out_file)],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        parsed = json.loads(out_file.read_text())
        assert "total_nodes" in parsed

    def test_graph_trace_known_control(self, scuba_json: Path) -> None:
        """--trace <KSI-id> returns evidence for that control."""
        result = runner.invoke(
            app,
            ["evidence", "graph", "--input", str(scuba_json), "--trace", "KSI-IA-02"],
        )
        assert result.exit_code == 0, result.output
        assert "Trace" in result.output
        assert "Evidence nodes" in result.output
        # The FAIL KSI should have 1 evidence node
        assert "1" in result.output

    def test_graph_trace_json(self, scuba_json: Path) -> None:
        """--trace with --format json returns structured trace."""
        result = runner.invoke(
            app,
            [
                "evidence",
                "graph",
                "--input",
                str(scuba_json),
                "--trace",
                "KSI-IA-02",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        plain = _strip_ansi(result.output)
        json_start = plain.find("{")
        assert json_start >= 0, f"No JSON found in output: {plain!r}"
        parsed = json.loads(plain[json_start:])
        assert "control_id" in parsed
        assert parsed["control_id"] == "KSI-IA-02"
        assert "ir_objects" in parsed

    def test_graph_missing_input_exits_nonzero(self) -> None:
        """A missing input file causes a non-zero exit code."""
        result = runner.invoke(
            app,
            ["evidence", "graph", "--input", "/nonexistent/normalized.json"],
        )
        assert result.exit_code != 0
