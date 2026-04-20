"""Tests for uiao.impl.generators.briefing — data collectors and build_briefing().

Coverage targets (TST-002):
  collect_ci_status        — always returns 6 rows; drift-report awareness
  collect_memory_entries   — missing file fallback; pipe-table parsing; n limit
  collect_adapter_status   — missing dir fallback; YAML parsing; example skip
  collect_control_coverage — missing dir fallback; narrative/evidence/gold flags
  collect_oscal_status     — missing files; present + valid-structure detection
  collect_priorities       — missing file fallback; section + decision parsing
  collect_changelog        — missing file fallback; entry regex; n limit
  build_briefing           — end-to-end: DOCX created, path exists, non-empty
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from uiao.impl.config import Settings
from uiao.impl.generators.briefing import (
    build_briefing,
    collect_adapter_status,
    collect_changelog,
    collect_ci_status,
    collect_control_coverage,
    collect_memory_entries,
    collect_oscal_status,
    collect_priorities,
)


def _settings(tmp_path: Path) -> Settings:
    """Return a Settings instance pointing at a temp directory."""
    return Settings(project_root=tmp_path)


class TestCollectCiStatus:
    def test_returns_six_rows(self, tmp_path):
        rows = collect_ci_status(tmp_path)
        assert len(rows) == 6

    def test_each_row_has_required_keys(self, tmp_path):
        rows = collect_ci_status(tmp_path)
        for row in rows:
            assert {"component", "status", "last_changed", "notes"} <= row.keys()

    def test_drift_row_unknown_when_no_report(self, tmp_path):
        rows = collect_ci_status(tmp_path)
        drift_row = next(r for r in rows if "Drift" in r["component"])
        assert drift_row["status"] == "⚠️"

    def test_drift_row_pass_when_no_issues(self, tmp_path):
        report_dir = tmp_path / "reports"
        report_dir.mkdir()
        (report_dir / "drift-report.json").write_text(
            json.dumps({"issues": []}), encoding="utf-8"
        )
        rows = collect_ci_status(tmp_path)
        drift_row = next(r for r in rows if "Drift" in r["component"])
        assert drift_row["status"] == "🟢"

    def test_drift_row_fail_when_issues_present(self, tmp_path):
        report_dir = tmp_path / "reports"
        report_dir.mkdir()
        (report_dir / "drift-report.json").write_text(
            json.dumps({"issues": ["drift-001", "drift-002"]}), encoding="utf-8"
        )
        rows = collect_ci_status(tmp_path)
        drift_row = next(r for r in rows if "Drift" in r["component"])
        assert drift_row["status"] == "🔴"
        assert "2 drift issues" in drift_row["notes"]


class TestCollectMemoryEntries:
    def test_fallback_when_missing(self, tmp_path):
        entries = collect_memory_entries(tmp_path)
        assert len(entries) == 1
        assert "not found" in entries[0]["task"].lower()

    def test_parses_pipe_table_rows(self, tmp_path):
        content = (
            "# UIAO-MEMORY
"
            "| Date | Task | Outcome | Notes | Correction |
"
            "|------|------|---------|-------|------------|
"
            "| 2025-01-10 | Fix cert | Success | — | Rotated cert |
"
            "| 2025-02-20 | Debug drift | Partial | — | Re-ran scanner |
"
        )
        (tmp_path / "UIAO-MEMORY.md").write_text(content, encoding="utf-8")
        entries = collect_memory_entries(tmp_path)
        assert len(entries) == 2
        assert entries[0]["date"] == "2025-01-10"
        assert entries[0]["task"] == "Fix cert"
        assert entries[0]["outcome"] == "Success"

    def test_respects_n_limit(self, tmp_path):
        lines = "
".join(
            f"| 2025-01-{i:02d} | Task {i} | Done | — | Fix {i} |"
            for i in range(1, 8)
        )
        (tmp_path / "UIAO-MEMORY.md").write_text(lines, encoding="utf-8")
        entries = collect_memory_entries(tmp_path, n=3)
        assert len(entries) == 3

    def test_empty_file_returns_fallback(self, tmp_path):
        (tmp_path / "UIAO-MEMORY.md").write_text("# no rows
", encoding="utf-8")
        entries = collect_memory_entries(tmp_path)
        assert len(entries) == 1
        assert entries[0]["date"] == "—"


class TestCollectAdapterStatus:
    def test_fallback_when_dir_missing(self, tmp_path):
        rows = collect_adapter_status(tmp_path)
        assert len(rows) == 1
        assert "not found" in rows[0]["vendor"].lower()

    def test_parses_vendor_yaml(self, tmp_path):
        overlays_dir = tmp_path / "data" / "vendor-overlays"
        overlays_dir.mkdir(parents=True)
        (overlays_dir / "cisco.yaml").write_text(
            yaml.dump(
                {
                    "name": "Cisco SD-WAN",
                    "status": "active",
                    "controls": ["SC-7", "SC-8"],
                    "role": "Network segmentation",
                }
            ),
            encoding="utf-8",
        )
        rows = collect_adapter_status(tmp_path)
        assert len(rows) == 1
        assert rows[0]["vendor"] == "Cisco SD-WAN"
        assert rows[0]["plane"] == "Network"
        assert "SC-7" in rows[0]["controls"]

    def test_skips_example_yaml(self, tmp_path):
        overlays_dir = tmp_path / "data" / "vendor-overlays"
        overlays_dir.mkdir(parents=True)
        (overlays_dir / "example.yaml").write_text(
            yaml.dump({"name": "Example", "status": "inactive"}), encoding="utf-8"
        )
        rows = collect_adapter_status(tmp_path)
        assert rows[0]["vendor"] == "No overlays found"

    def test_returns_fallback_for_empty_dir(self, tmp_path):
        overlays_dir = tmp_path / "data" / "vendor-overlays"
        overlays_dir.mkdir(parents=True)
        rows = collect_adapter_status(tmp_path)
        assert rows[0]["vendor"] == "No overlays found"


class TestCollectControlCoverage:
    def test_fallback_when_dir_missing(self, tmp_path):
        rows, gold, covered, total = collect_control_coverage(tmp_path)
        assert total == 0
        assert gold == 0
        assert covered == 0

    def test_parses_control_with_narrative_and_evidence(self, tmp_path):
        ctl_dir = tmp_path / "data" / "control-library"
        ctl_dir.mkdir(parents=True)
        (ctl_dir / "AC-2.yml").write_text(
            yaml.dump(
                {
                    "title": "Account Management",
                    "narrative": "Accounts are managed via Entra ID.",
                    "evidence_links": ["https://example.com/evidence"],
                }
            ),
            encoding="utf-8",
        )
        rows, gold, covered, total = collect_control_coverage(tmp_path)
        assert total == 1
        assert covered == 1
        assert rows[0]["gap"] == "—"
        assert rows[0]["evidence"] == "✅"

    def test_identifies_gold_standard(self, tmp_path):
        ctl_dir = tmp_path / "data" / "control-library"
        ctl_dir.mkdir(parents=True)
        (ctl_dir / "SC-8.yml").write_text(
            yaml.dump(
                {
                    "title": "Transmission Integrity",
                    "narrative": "TLS 1.2+ enforced on all links.",
                    "gold_standard": True,
                    "evidence_links": ["https://example.com/sc8"],
                }
            ),
            encoding="utf-8",
        )
        rows, gold, covered, total = collect_control_coverage(tmp_path)
        assert gold == 1
        assert rows[0]["narrative"] == "✅ Gold"

    def test_narrative_gap_when_no_narrative(self, tmp_path):
        ctl_dir = tmp_path / "data" / "control-library"
        ctl_dir.mkdir(parents=True)
        (ctl_dir / "IA-2.yml").write_text(
            yaml.dump({"title": "Identification and Authentication"}),
            encoding="utf-8",
        )
        rows, gold, covered, total = collect_control_coverage(tmp_path)
        assert rows[0]["gap"] == "narrative gap"

    def test_skips_matrix_file(self, tmp_path):
        ctl_dir = tmp_path / "data" / "control-library"
        ctl_dir.mkdir(parents=True)
        (ctl_dir / "uiao-control-matrix.yml").write_text(
            yaml.dump({"title": "Matrix", "narrative": "skip me"}), encoding="utf-8"
        )
        rows, gold, covered, total = collect_control_coverage(tmp_path)
        assert total == 0


class TestCollectOscalStatus:
    def test_all_three_keys_present(self, tmp_path):
        status = collect_oscal_status(tmp_path)
        assert set(status.keys()) == {"SSP", "Component Definition", "POA&M"}

    def test_absent_artifacts_marked_not_present(self, tmp_path):
        status = collect_oscal_status(tmp_path)
        for info in status.values():
            assert info["present"] is False
            assert info["valid_structure"] is False

    def test_present_ssp_with_valid_structure(self, tmp_path):
        oscal_dir = tmp_path / "exports" / "oscal"
        oscal_dir.mkdir(parents=True)
        ssp = {"system-security-plan": {"uuid": "abc-123"}}
        (oscal_dir / "uiao-ssp-skeleton.json").write_text(
            json.dumps(ssp), encoding="utf-8"
        )
        status = collect_oscal_status(tmp_path)
        assert status["SSP"]["present"] is True
        assert status["SSP"]["valid_structure"] is True

    def test_present_but_malformed_json_marks_invalid(self, tmp_path):
        oscal_dir = tmp_path / "exports" / "oscal"
        oscal_dir.mkdir(parents=True)
        (oscal_dir / "uiao-ssp-skeleton.json").write_text(
            "{ not valid json }", encoding="utf-8"
        )
        status = collect_oscal_status(tmp_path)
        assert status["SSP"]["present"] is True
        assert status["SSP"]["valid_structure"] is False

    def test_present_json_missing_oscal_key_marks_invalid(self, tmp_path):
        oscal_dir = tmp_path / "exports" / "oscal"
        oscal_dir.mkdir(parents=True)
        (oscal_dir / "uiao-ssp-skeleton.json").write_text(
            json.dumps({"metadata": {"title": "oops"}}), encoding="utf-8"
        )
        status = collect_oscal_status(tmp_path)
        assert status["SSP"]["valid_structure"] is False


class TestCollectPriorities:
    def test_fallback_when_missing(self, tmp_path):
        priorities, decisions = collect_priorities(tmp_path)
        assert "not found" in priorities[0].lower()
        assert decisions == []

    def test_parses_priorities_section(self, tmp_path):
        content = (
            "# PROJECT-CONTEXT

"
            "## Current Priorities

"
            "* Finish OSCAL SSP skeleton
"
            "* Wire mypy into CI

"
            "## Another Section
"
        )
        (tmp_path / "PROJECT-CONTEXT.md").write_text(content, encoding="utf-8")
        priorities, _ = collect_priorities(tmp_path)
        assert "Finish OSCAL SSP skeleton" in priorities
        assert "Wire mypy into CI" in priorities

    def test_parses_date_prefixed_decisions(self, tmp_path):
        content = (
            "## Architecture Decisions

"
            "* 2025-03-01: Adopted OSCAL 1.1 as canonical format
"
            "* 2025-04-15: Split core and impl into separate modules
"
        )
        (tmp_path / "PROJECT-CONTEXT.md").write_text(content, encoding="utf-8")
        _, decisions = collect_priorities(tmp_path)
        assert len(decisions) == 2
        assert decisions[0].startswith("2025-03-01:")

    def test_decisions_capped_at_five(self, tmp_path):
        lines = "
".join(
            f"* 2025-01-{i:02d}: Decision {i}" for i in range(1, 10)
        )
        (tmp_path / "PROJECT-CONTEXT.md").write_text(lines, encoding="utf-8")
        _, decisions = collect_priorities(tmp_path)
        assert len(decisions) == 5


class TestCollectChangelog:
    def test_fallback_when_missing(self, tmp_path):
        entries = collect_changelog(tmp_path)
        assert len(entries) == 1
        assert "not found" in entries[0].lower()

    def test_parses_changelog_entries(self, tmp_path):
        content = (
            "# Changelog

"
            "* Add Infoblox Tier 4 adapter ([#108](https://example.com))
"
            "* Fix coveragerc namespace ([#107](https://example.com))
"
            "* Retire stale ci.yml workflow ([#107](https://example.com))
"
        )
        (tmp_path / "CHANGELOG.md").write_text(content, encoding="utf-8")
        entries = collect_changelog(tmp_path)
        assert len(entries) == 3
        assert entries[0] == "Add Infoblox Tier 4 adapter"

    def test_respects_n_limit(self, tmp_path):
        lines = "
".join(
            f"* Entry {i} ([#{i}](https://example.com))" for i in range(1, 20)
        )
        (tmp_path / "CHANGELOG.md").write_text(lines, encoding="utf-8")
        entries = collect_changelog(tmp_path, n=5)
        assert len(entries) == 5

    def test_empty_changelog_returns_fallback(self, tmp_path):
        (tmp_path / "CHANGELOG.md").write_text("# No entries
", encoding="utf-8")
        entries = collect_changelog(tmp_path)
        assert entries == ["No changelog entries found"]


class TestBuildBriefing:
    def test_returns_path_object(self, tmp_path):
        settings = _settings(tmp_path)
        result = build_briefing(settings)
        assert isinstance(result, Path)

    def test_output_file_exists(self, tmp_path):
        settings = _settings(tmp_path)
        result = build_briefing(settings)
        assert result.exists()

    def test_output_is_docx(self, tmp_path):
        settings = _settings(tmp_path)
        result = build_briefing(settings)
        assert result.suffix == ".docx"

    def test_output_is_non_empty(self, tmp_path):
        settings = _settings(tmp_path)
        result = build_briefing(settings)
        assert result.stat().st_size > 0

    def test_output_path_contains_date(self, tmp_path):
        """Output filename must embed a YYYY-MM-DD datestamp."""
        import re
        settings = _settings(tmp_path)
        result = build_briefing(settings)
        assert re.search(r"\d{4}-\d{2}-\d{2}", result.name)

    def test_output_in_exports_dir(self, tmp_path):
        settings = _settings(tmp_path)
        result = build_briefing(settings)
        assert result.parent == tmp_path / "exports"

    def test_no_history_skips_page6(self, tmp_path):
        """With include_history=False the file should be smaller."""
        settings = _settings(tmp_path)
        with_history = build_briefing(settings, include_history=True)
        size_with = with_history.stat().st_size
        without_history = build_briefing(settings, include_history=False)
        size_without = without_history.stat().st_size
        assert size_without < size_with

    def test_build_with_real_overlays(self, tmp_path):
        """End-to-end with a real vendor-overlays/ dir populates Page 2."""
        overlays_dir = tmp_path / "data" / "vendor-overlays"
        overlays_dir.mkdir(parents=True)
        (overlays_dir / "splunk.yaml").write_text(
            yaml.dump(
                {
                    "name": "Splunk SIEM",
                    "status": "active",
                    "controls": ["AU-2", "AU-3", "SI-4"],
                    "role": "Log aggregation and alerting",
                }
            ),
            encoding="utf-8",
        )
        settings = _settings(tmp_path)
        result = build_briefing(settings)
        assert result.exists()
        assert result.stat().st_size > 0
