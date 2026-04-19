"""TST-002: tests for briefing data-collector functions and build_briefing."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
import yaml
from uiao.impl.config import Settings
from uiao.impl.generators.briefing import (
    STATUS_EMOJI, build_briefing, collect_adapter_status, collect_changelog,
    collect_ci_status, collect_control_coverage,
    collect_memory_entries, collect_oscal_status, collect_priorities,
)

WARN = STATUS_EMOJI["unknown"]
PASS = STATUS_EMOJI["pass"]
FAIL = STATUS_EMOJI["fail"]


def mk(tmp_path, rel, text):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p


def cfg(tmp_path):
        return Settings(project_root=tmp_path)

# -- collect_ci_status -------------------------------------------------------

def test_ci_returns_six_rows(tmp_path):
        assert len(collect_ci_status(tmp_path)) == 6


def test_ci_rows_have_required_keys(tmp_path):
        for row in collect_ci_status(tmp_path):
                    assert {"component", "status", "last_changed", "notes"} <= row.keys()


def test_ci_drift_unknown_without_report(tmp_path):
        rows = collect_ci_status(tmp_path)
        drift = next(r for r in rows if "Drift" in r["component"])
        assert drift["status"] == WARN


def test_ci_drift_pass_on_empty_issues(tmp_path):
        mk(tmp_path, "reports/drift-report.json", json.dumps({"issues": []}))
        rows = collect_ci_status(tmp_path)
        drift = next(r for r in rows if "Drift" in r["component"])
        assert drift["status"] == PASS


def test_ci_drift_fail_on_issues(tmp_path):
        mk(tmp_path, "reports/drift-report.json", json.dumps({"issues": ["x", "y"]}))
        rows = collect_ci_status(tmp_path)
        drift = next(r for r in rows if "Drift" in r["component"])
        assert drift["status"] == FAIL
        assert "2 drift issues" in drift["notes"]


# -- collect_memory_entries --------------------------------------------------

def test_memory_fallback_when_missing(tmp_path):
        e = collect_memory_entries(tmp_path)
        assert "not found" in e[0]["task"].lower()


def test_memory_parses_pipe_rows(tmp_path):
        mk(tmp_path, "UIAO-MEMORY.md", "| 2025-01-10 | Fix cert | Success | -- | Rotated |\n")
        e = collect_memory_entries(tmp_path)
                                assert e[0]["date"] == "2025-01-10"
    assert e[0]["task"] == "Fix cert"
    assert e[0]["outcome"] == "Success"


def test_memory_n_limit(tmp_path):
        rows = "".join("| 2025-01-{:02d} | T{} | Done | -- | F{} |\n".format(i, i, i) for i in range(1, 8))
    mk(tmp_path, "UIAO-MEMORY.md", rows)
    assert len(collect_memory_entries(tmp_path, n=3)) == 3


def test_memory_empty_file_returns_fallback(tmp_path):
        mk(tmp_path, "UIAO-MEMORY.md", "# no rows\n")
    e = collect_memory_entries(tmp_path)
    assert len(e) == 1


# -- collect_adapter_status --------------------------------------------------

def test_adapter_fallback_when_dir_missing(tmp_path):
        assert "not found" in collect_adapter_status(tmp_path)[0]["vendor"].lower()


def test_adapter_parses_cisco(tmp_path):
        data = yaml.dump({"name": "Cisco SD-WAN", "status": "active", "controls": ["SC-7"], "role": "net"})
    mk(tmp_path, "data/vendor-overlays/cisco.yaml", data)
    rows = collect_adapter_status(tmp_path)
    assert rows[0]["vendor"] == "Cisco SD-WAN"
    assert rows[0]["plane"] == "Network"
    assert "SC-7" in rows[0]["controls"]


def test_adapter_skips_example_yaml(tmp_path):
        mk(tmp_path, "data/vendor-overlays/example.yaml", yaml.dump({"name": "Ex"}))
    assert collect_adapter_status(tmp_path)[0]["vendor"] == "No overlays found"


def test_adapter_empty_dir_returns_fallback(tmp_path):
        (tmp_path / "data" / "vendor-overlays").mkdir(parents=True)
    assert collect_adapter_status(tmp_path)[0]["vendor"] == "No overlays found"


# -- collect_control_coverage ------------------------------------------------

def test_coverage_fallback_when_dir_missing(tmp_path):
        _, gold, covered, total = collect_control_coverage(tmp_path)
        assert total == 0 and gold == 0 and covered == 0


def test_coverage_parses_full_control(tmp_path):
        data = yaml.dump({"title": "AC-2", "narrative": "ok", "evidence_links": ["x"]})
        mk(tmp_path, "data/control-library/AC-2.yml", data)
        rows, gold, covered, total = collect_control_coverage(tmp_path)
        assert total == 1 and covered == 1


def test_coverage_gold_standard(tmp_path):
        data = yaml.dump({"title": "SC-8", "narrative": "tls", "gold_standard": True, "evidence_links": ["x"]})
        mk(tmp_path, "data/control-library/SC-8.yml", data)
        _, gold, covered, total = collect_control_coverage(tmp_path)
        assert gold == 1


def test_coverage_narrative_gap(tmp_path):
        mk(tmp_path, "data/control-library/IA-2.yml", yaml.dump({"title": "IA-2"}))
        rows, _, _, _ = collect_control_coverage(tmp_path)
        assert rows[0]["gap"] == "narrative gap"


def test_coverage_skips_matrix_file(tmp_path):
        mk(tmp_path, "data/control-library/uiao-control-matrix.yml", yaml.dump({"title": "m"}))
        _, _, _, total = collect_control_coverage(tmp_path)
        assert total == 0


# -- collect_oscal_status ----------------------------------------------------

def test_oscal_returns_three_keys(tmp_path):
        assert set(collect_oscal_status(tmp_path).keys()) == {"SSP", "Component Definition", "POA&M"}


def test_oscal_absent_not_present(tmp_path):
        for info in collect_oscal_status(tmp_path).values():
                    assert info["present"] is False and info["valid_structure"] is False


def test_oscal_valid_ssp_detected(tmp_path):
        mk(tmp_path, "exports/oscal/uiao-ssp-skeleton.json", json.dumps({"system-security-plan": {"uuid": "x"}}))
        s = collect_oscal_status(tmp_path)
        assert s["SSP"]["present"] is True and s["SSP"]["valid_structure"] is True


def test_oscal_malformed_json_invalid(tmp_path):
        mk(tmp_path, "exports/oscal/uiao-ssp-skeleton.json", "{ bad json }")
        assert collect_oscal_status(tmp_path)["SSP"]["valid_structure"] is False


def test_oscal_missing_key_invalid(tmp_path):
        mk(tmp_path, "exports/oscal/uiao-ssp-skeleton.json", json.dumps({"metadata": {}}))
        assert collect_oscal_status(tmp_path)["SSP"]["valid_structure"] is False


# -- collect_priorities -------------------------------------------------------

def test_priorities_fallback_when_missing(tmp_path):
        p, d = collect_priorities(tmp_path)
        assert "not found" in p[0].lower() and d == []


def test_priorities_parses_section(tmp_path):
        mk(tmp_path, "PROJECT-CONTEXT.md", "## Current Priorities\n\n* Do OSCAL\n* Wire mypy\n\n## Done\n")
        p, _ = collect_priorities(tmp_path)
        assert "Do OSCAL" in p and "Wire mypy" in p


def test_priorities_parses_decisions(tmp_path):
        mk(tmp_path, "PROJECT-CONTEXT.md", "* 2025-03-01: Adopted OSCAL\n* 2025-04-15: Split repos\n")
        _, d = collect_priorities(tmp_path)
        assert len(d) == 2 and d[0].startswith("2025-03-01:")


def test_priorities_decisions_capped_at_five(tmp_path):
        text = "".join("* 2025-01-{:02d}: Decision {}\n".format(i, i) for i in range(1, 10))
        mk(tmp_path, "PROJECT-CONTEXT.md", text)
        _, d = collect_priorities(tmp_path)
        assert len(d) == 5


# -- collect_changelog --------------------------------------------------------

def test_changelog_fallback_when_missing(tmp_path):
        assert "not found" in collect_changelog(tmp_path)[0].lower()


def test_changelog_parses_entries(tmp_path):
        mk(tmp_path, "CHANGELOG.md", "* Add adapter ([#1](x))\n* Fix test ([#2](x))\n")
        e = collect_changelog(tmp_path)
        assert e[0] == "Add adapter" and len(e) == 2


def test_changelog_n_limit(tmp_path):
        text = "".join("* Entry {} ([#{} ](x))\n".format(i, i) for i in range(1, 20))
        mk(tmp_path, "CHANGELOG.md", text)
        assert len(collect_changelog(tmp_path, n=5)) == 5


def test_changelog_empty_returns_fallback(tmp_path):
        mk(tmp_path, "CHANGELOG.md", "# No entries\n")
        assert collect_changelog(tmp_path) == ["No changelog entries found"]


# -- build_briefing (end-to-end smoke tests) ----------------------------------

def test_build_creates_docx(tmp_path):
        result = build_briefing(cfg(tmp_path))
        assert result.exists() and result.suffix == ".docx"


def test_build_output_in_exports(tmp_path):
        result = build_briefing(cfg(tmp_path))
        assert result.parent == tmp_path / "exports"


def test_build_file_non_empty(tmp_path):
        assert build_briefing(cfg(tmp_path)).stat().st_size > 0


def test_build_filename_has_date(tmp_path):
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", build_briefing(cfg(tmp_path)).name)


def test_build_no_history_smaller(tmp_path):
        s = cfg(tmp_path)
        size_with = build_briefing(s, include_history=True).stat().st_size
        size_without = build_briefing(s, include_history=False).stat().st_size
        assert size_without < size_with
    
