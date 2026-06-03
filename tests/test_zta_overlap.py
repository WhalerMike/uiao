"""Tests for uiao.adapters.zta.overlap — ZT ↔ SCuBA classification."""

from __future__ import annotations

from pathlib import Path

from uiao.adapters.zta.ingest import load_report
from uiao.adapters.zta.overlap import build_overlap, classify
from uiao.adapters.zta.render.overlap import render_overlap_md

FIXTURES = Path(__file__).parent / "fixtures" / "zta"
MINI_JSON = FIXTURES / "sample-mini.json"


def test_classify_shared_and_ztonly():
    assert classify("Identity", "Access control").klass == "shared"
    assert classify("Identity", "Access control").scuba_product == "aad"
    assert classify("Network", "Global Secure Access").klass == "zt-only"
    assert classify("Devices", "Tenant").klass == "zt-only"
    assert classify("Infrastructure", "Manage access and permissions").klass == "zt-only"


def test_classify_data_pillar_overrides():
    assert classify("Data", "Information Protection").klass == "zt-only"  # Purview default
    sp = classify("Data", "SharePoint Online")
    assert sp.klass == "shared" and sp.scuba_product == "sharepoint"


def test_classify_application_management_is_aad_any_pillar():
    # The unscoped override: app-management is Entra regardless of pillar (incl. none).
    for pillar in ("Identity", "Data", None):
        c = classify(pillar, "Application management")
        assert c.klass == "shared" and c.scuba_product == "aad"


def test_classify_hybrid_is_ztonly():
    assert classify("Identity", "Hybrid infrastructure").klass == "zt-only"


def test_build_overlap_counts_on_mini():
    overlap = build_overlap(load_report(MINI_JSON))
    assert overlap.total == 7
    # shared: 21001 (Identity/Authentication), 23004 (Identity/Monitoring)
    assert overlap.shared == 2
    assert overlap.zt_only == 5
    assert overlap.shared_pct + overlap.zt_only_pct == 100
    assert overlap.by_pillar["Network"]["zt-only"] == 2


def test_scuba_only_inverse_gap_present():
    overlap = build_overlap(load_report(MINI_JSON))
    products = {item["product"] for item in overlap.scuba_only}
    assert {"exo", "defender", "teams", "powerplatform"} <= products


def test_render_overlap_md():
    report = load_report(MINI_JSON)
    md = render_overlap_md(report, build_overlap(report))
    assert "Overlap Map" in md
    assert "Shared surface" in md
    assert "SCuBA-only" in md
    assert "Exchange Online" in md
