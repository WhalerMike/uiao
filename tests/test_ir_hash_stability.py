"""IR hash stability regression tests.

Verifies Evidence and ProvenanceRecord hashes are stable
across multiple instantiations of identical objects.
"""

from __future__ import annotations

from datetime import datetime, timezone

from uiao.ir.models.core import Evidence, ProvenanceRecord


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test-suite",
        timestamp=datetime(2026, 4, 8, tzinfo=timezone.utc).isoformat(),
        version="0.0.1-test",
        content_hash=None,
        actor="pytest",
    )


def _make_evidence() -> Evidence:
    return Evidence(
        id="e1",
        source="scuba:run",
        control_id="KSI-IA-01",
        policy_id="policy:ksi:KSI-IA-01:default",
        timestamp="2026-04-08T00:00:00Z",
        data={"ksi_id": "KSI-IA-01", "status": "PASS"},
        evaluation={"passed": True, "failed": False, "warning": False},
        provenance=_prov(),
    )


def test_evidence_hash_stable_for_same_content() -> None:
    e1 = _make_evidence()
    e2 = _make_evidence()
    assert e1.hash() == e2.hash()


def test_evidence_hash_changes_with_different_content() -> None:
    e1 = _make_evidence()
    e2 = Evidence(
        id="e1",
        source="scuba:run",
        control_id="KSI-IA-01",
        policy_id="policy:ksi:KSI-IA-01:default",
        timestamp="2026-04-08T00:00:00Z",
        data={"ksi_id": "KSI-IA-01", "status": "FAIL"},
        evaluation={"passed": False, "failed": True, "warning": False},
        provenance=_prov(),
    )
    assert e1.hash() != e2.hash()


def test_provenance_hash_stable() -> None:
    p1 = _prov()
    p2 = _prov()
    assert p1.hash() == p2.hash()


def test_evidence_canonical_json_stable() -> None:
    e1 = _make_evidence()
    e2 = _make_evidence()
    assert e1.to_canonical() == e2.to_canonical()


def test_evidence_hash_is_64_hex_chars() -> None:
    e = _make_evidence()
    h = e.hash()
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
