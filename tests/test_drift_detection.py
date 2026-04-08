from __future__ import annotations

from datetime import datetime, timezone

from uiao_core.governance.drift import build_drift_state
from uiao_core.ir.models.core import ProvenanceRecord


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test-suite",
        timestamp=datetime(2026, 4, 8, tzinfo=timezone.utc).isoformat(),
        version="0.0.1-test",
        hash=None,
        actor="pytest",
    )


def test_no_drift_is_benign():
    expected = {"a": 1, "b": 2}
    actual = {"a": 1, "b": 2}
    drift = build_drift_state(
        resource_id="res-1",
        policy_ref="policy:ksi:KSI-IA-01:default",
        expected_state=expected,
        actual_state=actual,
        provenance=_prov(),
    )
    assert drift.drift_detected is False
    assert drift.classification == "benign"
    assert drift.expected_hash == drift.actual_hash
    assert drift.delta["added"] == []
    assert drift.delta["removed"] == []
    assert drift.delta["changed"] == []


def test_small_drift_is_risky():
    expected = {"a": 1, "b": 2}
    actual = {"a": 1, "b": 3}
    drift = build_drift_state(
        resource_id="res-1",
        policy_ref="policy:ksi:KSI-IA-01:default",
        expected_state=expected,
        actual_state=actual,
        provenance=_prov(),
    )
    assert drift.drift_detected is True
    assert drift.classification == "risky"
    assert drift.delta["changed"] == ["b"]


def test_large_drift_is_unauthorized():
    expected = {"a": 1, "b": 2, "c": 3}
    actual = {"x": 10, "y": 20, "z": 30}
    drift = build_drift_state(
        resource_id="res-1",
        policy_ref="policy:ksi:KSI-IA-01:default",
        expected_state=expected,
        actual_state=actual,
        provenance=_prov(),
    )
    assert drift.drift_detected is True
    assert drift.classification == "unauthorized"
    assert set(drift.delta["removed"]) == {"a", "b", "c"}
    assert set(drift.delta["added"]) == {"x", "y", "z"}


def test_drift_state_is_deterministic():
    expected = {"a": 1, "b": 2}
    actual = {"a": 1, "b": 3}
    prov = _prov()
    drift_a = build_drift_state(
        resource_id="res-1",
        policy_ref="policy:ksi:KSI-IA-01:default",
        expected_state=expected,
        actual_state=actual,
        provenance=prov,
    )
    drift_b = build_drift_state(
        resource_id="res-1",
        policy_ref="policy:ksi:KSI-IA-01:default",
        expected_state=expected,
        actual_state=actual,
        provenance=prov,
    )
    assert drift_a.to_canonical() == drift_b.to_canonical()
    assert drift_a.hash() == drift_b.hash()
