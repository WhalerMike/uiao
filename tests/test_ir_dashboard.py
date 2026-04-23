from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from uiao.dashboard.ir_dashboard import build_ir_dashboard, export_ir_dashboard
from uiao.governance.actions import GovernanceAction
from uiao.ir.models.core import Evidence, ProvenanceRecord


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(source="test", timestamp="2025-01-01T00:00:00Z", version="1")


def _make_evidence(eid: str, control_id: str, ts: str) -> Evidence:
    return Evidence(
        id=eid,
        source="test",
        timestamp=ts,
        control_id=control_id,
        policy_id=None,
        data={"ksi_id": control_id},
        evaluation={},
        provenance=_prov(),
    )


def _make_action(eid: str, severity: str = "Medium") -> GovernanceAction:
    return GovernanceAction(
        ksi_id="AC-2",
        control_id="AC-2",
        policy_id=None,
        severity=severity,
        drift_classification=None,
        owner="ops",
        sla_days=7,
        action_type="monitor",
        description="test action",
        evidence_id=eid,
    )


class TestBuildIrDashboard:
    def test_structure(self):
        now = datetime(2025, 1, 31, tzinfo=timezone.utc)
        ev = _make_evidence("e1", "AC-2", "2025-01-30T00:00:00Z")
        action = _make_action("e1")
        result = build_ir_dashboard([ev], [action], now=now)
        assert "generated_at" in result
        assert "freshness_summary" in result
        assert "governance_summary" in result
        assert result["evidence_total"] == 1

    def test_freshness_counts(self):
        now = datetime(2025, 3, 1, tzinfo=timezone.utc)
        fresh_ev = _make_evidence("e1", "AC-2", "2025-02-28T00:00:00Z")
        stale_ev = _make_evidence("e2", "AC-2", "2025-01-01T00:00:00Z")
        result = build_ir_dashboard([fresh_ev, stale_ev], [], now=now)
        fs = result["freshness_summary"]
        assert fs["fresh"] == 1
        assert fs["stale"] == 1

    def test_governance_summary_by_severity(self):
        now = datetime(2025, 1, 31, tzinfo=timezone.utc)
        ev = _make_evidence("e1", "AC-2", "2025-01-30T00:00:00Z")
        actions = [_make_action("e1", "High"), _make_action("e1", "Medium")]
        result = build_ir_dashboard([ev], actions, now=now)
        gs = result["governance_summary"]
        assert gs["total_actions"] == 2
        assert gs["by_severity"]["High"] == 1
        assert gs["by_severity"]["Medium"] == 1

    def test_freshness_records_serializable(self):
        now = datetime(2025, 1, 31, tzinfo=timezone.utc)
        ev = _make_evidence("e1", "AC-2", "2025-01-30T00:00:00Z")
        result = build_ir_dashboard([ev], [], now=now)
        records = result["freshness_records"]
        assert isinstance(records, list)
        assert records[0]["evidence_id"] == "e1"

    def test_export_writes_file(self, tmp_path):
        ev = _make_evidence("e1", "AC-2", "2025-01-30T00:00:00Z")
        out_file = str(tmp_path / "dashboard.json")
        path = export_ir_dashboard([ev], [], out_file)
        assert Path(path).exists()
        data = json.loads(Path(path).read_text())
        assert data["evidence_total"] == 1
