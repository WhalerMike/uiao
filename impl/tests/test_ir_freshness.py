from __future__ import annotations

from datetime import datetime, timezone


from uiao_impl.freshness.engine import (
    build_freshness_records,
    classify_age,
    generate_refresh_actions,
    parseiso,
)
from uiao_impl.governance.actions import GovernanceAction
from uiao_impl.ir.models.core import Evidence, ProvenanceRecord


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


class TestClassifyAge:
    def test_fresh(self):
        assert classify_age(10.0, 30) == "fresh"

    def test_stale_soon(self):
        assert classify_age(40.0, 30) == "stale-soon"

    def test_stale(self):
        assert classify_age(100.0, 30) == "stale"


class TestParseIso:
    def test_parses_utc_z(self):
        dt = parseiso("2025-01-01T00:00:00Z")
        assert dt.tzinfo is not None
        assert dt.year == 2025

    def test_parses_iso_offset(self):
        dt = parseiso("2025-06-01T12:00:00+00:00")
        assert dt.tzinfo is not None


class TestBuildFreshnessRecords:
    def test_fresh_evidence(self):
        now = datetime(2025, 1, 31, tzinfo=timezone.utc)
        ts = "2025-01-30T00:00:00Z"
        ev = _make_evidence("e1", "AC-2", ts)
        records = build_freshness_records([ev], now=now)
        assert len(records) == 1
        assert records[0].status == "fresh"
        assert records[0].evidence_id == "e1"

    def test_stale_evidence(self):
        now = datetime(2025, 3, 1, tzinfo=timezone.utc)
        ts = "2025-01-01T00:00:00Z"
        ev = _make_evidence("e2", "AC-2", ts)
        records = build_freshness_records([ev], now=now)
        assert records[0].status == "stale"

    def test_missing_timestamp_is_stale(self):
        ev = Evidence(
            id="e3",
            source="test",
            timestamp="",
            control_id="AC-2",
            policy_id=None,
            data={},
            evaluation={},
            provenance=_prov(),
        )
        records = build_freshness_records([ev])
        assert records[0].status == "stale"

    def test_threshold_lookup_by_family(self):
        now = datetime(2025, 1, 10, tzinfo=timezone.utc)
        ts = "2025-01-08T00:00:00Z"
        ev = _make_evidence("e4", "AU-3", ts)
        records = build_freshness_records([ev], now=now)
        assert records[0].threshold_days == 7


class TestGenerateRefreshActions:
    def test_generates_action_for_stale(self):
        now = datetime(2025, 3, 1, tzinfo=timezone.utc)
        ts = "2025-01-01T00:00:00Z"
        ev = _make_evidence("e5", "AC-2", ts)
        records = build_freshness_records([ev], now=now)
        actions = generate_refresh_actions(records, existing_actions=[])
        assert len(actions) == 1
        assert actions[0].action_type == "refresh"
        assert actions[0].evidence_id == "e5"

    def test_deduplication(self):
        now = datetime(2025, 3, 1, tzinfo=timezone.utc)
        ts = "2025-01-01T00:00:00Z"
        ev = _make_evidence("e6", "AC-2", ts)
        records = build_freshness_records([ev], now=now)
        existing = [
            GovernanceAction(
                ksi_id="AC-2",
                control_id="AC-2",
                policy_id=None,
                severity="Medium",
                drift_classification=None,
                owner="ops",
                sla_days=7,
                action_type="refresh",
                description="existing",
                evidence_id="e6",
            )
        ]
        actions = generate_refresh_actions(records, existing_actions=existing)
        assert len(actions) == 0

