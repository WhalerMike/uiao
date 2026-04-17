from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao.impl.cli.app import app
from uiao.impl.freshness.engine import (
    FreshnessRecord,
)
from uiao.impl.freshness.scheduler import (
    _urgency,
    build_refresh_schedule,
    group_jobs_by_owner,
    schedule_summary,
)
from uiao.impl.governance.actions import GovernanceAction
from uiao.impl.ir.models.core import Evidence, ProvenanceRecord

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCUBA_FIXTURE = {
    "assessment_metadata": {
        "run_id": "sched-test-001",
        "assessment_date": "2026-01-01T00:00:00Z",
        "tool_version": "test",
        "collector_user": "test-user",
    },
    "tenant": {"tenant_id": "test-tenant-001"},
    "ksi_results": [
        {
            "ksi_id": "KSI-IA-01",
            "status": "PASS",
            "severity": "High",
            "details": "MFA enforced",
        },
        {
            "ksi_id": "KSI-IA-02",
            "status": "FAIL",
            "severity": "Medium",
            "details": "Legacy auth not blocked",
        },
    ],
}


@pytest.fixture()
def scuba_json(tmp_path: Path) -> Path:
    p = tmp_path / "normalized.json"
    p.write_text(json.dumps(SCUBA_FIXTURE), encoding="utf-8")
    return p


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(source="test", timestamp="2025-01-01T00:00:00Z", version="1")


def _make_evidence(eid: str, control_id: str, ts: str) -> Evidence:
    return Evidence(
        id=eid,
        source="test",
        timestamp=ts,
        control_id=control_id,
        policy_id=None,
        data={"ksi_id": control_id, "severity": "Medium", "status": "FAIL"},
        evaluation={},
        provenance=_prov(),
    )


def _stale_record(eid: str, control_id: str = "AC-2") -> FreshnessRecord:
    return FreshnessRecord(
        evidence_id=eid,
        control_id=control_id,
        age_days=100.0,
        threshold_days=30,
        status="stale",
        generated_at="2025-01-01T00:00:00+00:00",
    )


def _refresh_action(eid: str, owner: str = "ops@example.gov") -> GovernanceAction:
    return GovernanceAction(
        ksi_id="AC-2",
        control_id="AC-2",
        policy_id=None,
        severity="Medium",
        drift_classification=None,
        owner=owner,
        sla_days=7,
        action_type="refresh",
        description="Refresh evidence",
        evidence_id=eid,
    )


# ---------------------------------------------------------------------------
# Unit tests for _urgency
# ---------------------------------------------------------------------------


class TestUrgency:
    def test_normal(self) -> None:
        assert _urgency(5.0, 30) == "normal"

    def test_high(self) -> None:
        # age > sla but <= 2x sla
        assert _urgency(45.0, 30) == "high"

    def test_critical(self) -> None:
        # age > 2x sla
        assert _urgency(100.0, 30) == "critical"

    def test_exact_sla_boundary(self) -> None:
        assert _urgency(30.0, 30) == "normal"

    def test_exact_2x_sla_boundary(self) -> None:
        # 60 <= 2*30 -> "high"
        assert _urgency(60.0, 30) == "high"


# ---------------------------------------------------------------------------
# Unit tests for build_refresh_schedule
# ---------------------------------------------------------------------------


class TestBuildRefreshSchedule:
    def test_no_stale_returns_empty(self) -> None:
        fresh_record = FreshnessRecord(
            evidence_id="e1",
            control_id="AC-2",
            age_days=5.0,
            threshold_days=30,
            status="fresh",
            generated_at="2025-01-01T00:00:00+00:00",
        )
        jobs = build_refresh_schedule([fresh_record], [])
        assert jobs == []

    def test_stale_without_matching_action_returns_empty(self) -> None:
        record = _stale_record("e1")
        # No matching action for e1
        jobs = build_refresh_schedule([record], [])
        assert jobs == []

    def test_stale_with_matching_action_produces_job(self) -> None:
        record = _stale_record("e1")
        action = _refresh_action("e1")
        jobs = build_refresh_schedule([record], [action])
        assert len(jobs) == 1
        job = jobs[0]
        assert job.evidence_id == "e1"
        assert job.control_id == "AC-2"
        assert job.urgency == "critical"  # age=100, sla=30, 100 > 2*30
        assert job.owner == "ops@example.gov"
        assert job.sla_days == 7

    def test_dispatch_ref_contains_evidence_id(self) -> None:
        record = _stale_record("e42")
        action = _refresh_action("e42")
        jobs = build_refresh_schedule([record], [action])
        assert "e42" in jobs[0].dispatch_ref

    def test_sorted_by_urgency_then_owner(self) -> None:
        now = datetime(2025, 3, 1, tzinfo=timezone.utc)
        # critical: age > 2*sla
        r_crit = FreshnessRecord(
            evidence_id="ecrit",
            control_id="AC-2",
            age_days=100.0,
            threshold_days=30,
            status="stale",
            generated_at=now.isoformat(),
        )
        # high: age between sla and 2*sla
        r_high = FreshnessRecord(
            evidence_id="ehigh",
            control_id="AC-3",
            age_days=45.0,
            threshold_days=30,
            status="stale",
            generated_at=now.isoformat(),
        )
        a_crit = _refresh_action("ecrit", "z-owner")
        a_high = _refresh_action("ehigh", "a-owner")
        jobs = build_refresh_schedule([r_high, r_crit], [a_crit, a_high])
        assert len(jobs) == 2
        assert jobs[0].urgency == "critical"
        assert jobs[1].urgency == "high"

    def test_only_refresh_actions_matched(self) -> None:
        record = _stale_record("e1")
        # action_type is "monitor", not "refresh" - should not produce a job
        monitor_action = GovernanceAction(
            ksi_id="AC-2",
            control_id="AC-2",
            policy_id=None,
            severity="Medium",
            drift_classification=None,
            owner="ops",
            sla_days=7,
            action_type="monitor",
            description="Monitor",
            evidence_id="e1",
        )
        jobs = build_refresh_schedule([record], [monitor_action])
        assert jobs == []

    def test_scheduled_at_is_now(self) -> None:
        now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        record = _stale_record("e1")
        action = _refresh_action("e1")
        jobs = build_refresh_schedule([record], [action], now=now)
        assert jobs[0].scheduled_at == now.isoformat()

    def test_refresh_job_is_frozen_dataclass(self) -> None:
        record = _stale_record("e1")
        action = _refresh_action("e1")
        jobs = build_refresh_schedule([record], [action])
        job = jobs[0]
        with pytest.raises((AttributeError, TypeError)):
            job.urgency = "normal"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Unit tests for group_jobs_by_owner
# ---------------------------------------------------------------------------


class TestGroupJobsByOwner:
    def test_groups_correctly(self) -> None:
        r1 = _stale_record("e1")
        r2 = _stale_record("e2")
        a1 = _refresh_action("e1", "team-a@gov")
        a2 = _refresh_action("e2", "team-b@gov")
        jobs = build_refresh_schedule([r1, r2], [a1, a2])
        groups = group_jobs_by_owner(jobs)
        assert "team-a@gov" in groups
        assert "team-b@gov" in groups
        assert len(groups["team-a@gov"]) == 1
        assert len(groups["team-b@gov"]) == 1

    def test_empty_jobs_empty_groups(self) -> None:
        groups = group_jobs_by_owner([])
        assert groups == {}

    def test_same_owner_grouped_together(self) -> None:
        r1 = _stale_record("e1")
        r2 = _stale_record("e2")
        a1 = _refresh_action("e1", "shared@gov")
        a2 = _refresh_action("e2", "shared@gov")
        jobs = build_refresh_schedule([r1, r2], [a1, a2])
        groups = group_jobs_by_owner(jobs)
        assert len(groups["shared@gov"]) == 2


# ---------------------------------------------------------------------------
# Unit tests for schedule_summary
# ---------------------------------------------------------------------------


class TestScheduleSummary:
    def test_empty_returns_no_jobs_message(self) -> None:
        msg = schedule_summary([])
        assert "No refresh jobs" in msg

    def test_summary_contains_count(self) -> None:
        record = _stale_record("e1")
        action = _refresh_action("e1")
        jobs = build_refresh_schedule([record], [action])
        msg = schedule_summary(jobs)
        assert "1 job" in msg

    def test_summary_contains_urgency_counts(self) -> None:
        record = _stale_record("e1")
        action = _refresh_action("e1")
        jobs = build_refresh_schedule([record], [action])
        msg = schedule_summary(jobs)
        assert "Critical" in msg or "critical" in msg.lower()

    def test_summary_contains_owner(self) -> None:
        record = _stale_record("e1")
        action = _refresh_action("e1", "special-owner@gov")
        jobs = build_refresh_schedule([record], [action])
        msg = schedule_summary(jobs)
        assert "special-owner@gov" in msg


# ---------------------------------------------------------------------------
# CLI smoke tests for ir-freshness-schedule
# ---------------------------------------------------------------------------


class TestIRFreshnessScheduleCLI:
    def test_runs_without_error(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-freshness-schedule", str(scuba_json)])
        assert result.exit_code == 0, result.output

    def test_output_contains_schedule_text(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-freshness-schedule", str(scuba_json)])
        assert result.exit_code == 0
        # Should print either "No refresh jobs" or "Refresh schedule"
        assert "refresh" in result.output.lower() or "No refresh" in result.output

    def test_out_writes_json(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "schedule.json"
        result = runner.invoke(
            app,
            ["ir-freshness-schedule", str(scuba_json), "--out", str(out)],
        )
        assert result.exit_code == 0, result.output
        if out.exists():
            data = json.loads(out.read_text())
            assert isinstance(data, list)

    def test_threshold_days_option(self, scuba_json: Path) -> None:
        result = runner.invoke(
            app,
            ["ir-freshness-schedule", str(scuba_json), "--threshold-days", "1"],
        )
        assert result.exit_code == 0, result.output

    def test_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["ir-freshness-schedule", str(tmp_path / "nonexistent.json")],
        )
        assert result.exit_code != 0

