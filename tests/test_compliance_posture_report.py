"""Smoke tests for scripts/compliance_posture_report.py.

Structural assertions only — they validate the report's shape and internal
consistency, not specific counts (which legitimately change as the corpus
grows).
"""

from __future__ import annotations

import importlib.util
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "compliance_posture_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("compliance_posture_report", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_report_has_three_panels():
    mod = _load_module()
    r = mod.build_report()
    assert set(r) == {"control_library", "ksi", "poam"}


def test_control_panel_internally_consistent():
    mod = _load_module()
    c = mod.build_report()["control_library"]
    # base + enhancements == total controls
    assert c["base"] + c["enhancements"] == c["total_controls"]
    nc = c["narrative_coverage"]
    # with + without narrative partitions the curated set exactly
    assert nc["with_narrative"] + nc["without_narrative"] == c["total_controls"]
    assert len(nc["missing"]) == nc["without_narrative"]
    assert 0.0 <= nc["pct"] <= 100.0


def test_ksi_panel_counts_match_ids():
    mod = _load_module()
    k = mod.build_report()["ksi"]
    assert k["count"] == len(k["ids"])
    assert sum(k["by_severity"].values()) == k["count"]


def test_poam_panel_template_flag():
    mod = _load_module()
    p = mod.build_report()["poam"]
    assert p["is_template"] == (p["tracked_items"] == 0)


def test_text_render_runs():
    mod = _load_module()
    text = mod._render_text(mod.build_report())
    assert "Compliance Posture Report" in text
    assert "Control library" in text
