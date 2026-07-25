"""Tests for the ConMon dashboard external-interconnections panel
(UIAO_145 §7 / ADR-132 Phase 2).

Covers:
- The exported dashboard artifact carries the panel, sourced from the
  canon link registry
- Counterparty-class rollup and live gap counts are present
- Per-link rows expose agreement state (type, anchored, next review)
  and never payload data
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from uiao.dashboard.export import DashboardExporter


@pytest.fixture()
def ksi_mappings_yml(tmp_path: Path) -> Path:
    data = {
        "ksi_mappings": [
            {
                "ksi_id": "KSI-TEST-1",
                "title": "Test KSI Implemented",
                "control_ids": ["IA-2"],
                "evidence_source": "Entra ID Logs",
                "status": "Implemented",
            }
        ]
    }
    path = tmp_path / "ksi-mappings.yml"
    path.write_text(yaml.safe_dump(data))
    return path


def test_dashboard_carries_links_panel(ksi_mappings_yml: Path, tmp_path: Path) -> None:
    exporter = DashboardExporter(ksi_mappings_yml)
    out = exporter.export_json(tmp_path / "dash.json")
    data = json.loads(out.read_text())

    panel = data["external_interconnections"]
    assert panel["available"] is True
    assert panel["source"].startswith("src/uiao/canon/link-registry.yaml")
    assert panel["total_links"] >= 5
    assert panel["active_links"] >= 5
    assert panel["by_counterparty_class"].get("federal-agency", 0) >= 4

    # Live gap counts from the shared link-gap core.
    assert panel["gap_counts"].get("GAP-AGREEMENT-UNRECORDED") == 3
    assert "GAP-REVIEW-MISSING" not in panel["gap_counts"]

    # Per-link rows carry agreement state, never payload attributes.
    row = next(r for r in panel["links"] if r["id"] == "federal-hrit-integration")
    assert row["provenance_anchored"] == "true"
    assert row["next_review"] == "2027-07-25"
    assert set(row) == {
        "id",
        "counterparty_class",
        "direction",
        "ssot_stance",
        "status",
        "agreement_type",
        "provenance_anchored",
        "next_review",
    }
