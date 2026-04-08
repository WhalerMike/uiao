from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao_core.ir.adapters.scuba.transformer import (
    SCuBATransformResult,
    transform_scuba_to_ir,
)
from uiao_core.ir.models.core import Evidence


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scuba_normalized_sample.json"


def run_transform() -> SCuBATransformResult:
    return transform_scuba_to_ir(FIXTURE_PATH)


def test_transform_returns_result():
    result = run_transform()
    assert isinstance(result, SCuBATransformResult)


def test_evidence_count_matches_ksi_results():
    """One Evidence object must be produced per ksi_results entry."""
    result = run_transform()
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(result.evidence) == len(fixture["ksi_results"])


def test_pass_warn_fail_counts_are_correct():
    result = run_transform()
    assert result.pass_count == 2
    assert result.warn_count == 1
    assert result.fail_count == 2


def test_unmapped_ksi_flagged():
    result = run_transform()
    assert "KSI-UNKNOWN-99" in result.unmapped_ksi_ids


def test_known_ksi_is_mapped():
    result = run_transform()
    assert "KSI-IA-01" not in result.unmapped_ksi_ids


def test_evidence_ids_are_unique():
    result = run_transform()
    ids = [e.id for e in result.evidence]
    assert len(ids) == len(set(ids)), "Duplicate evidence IDs detected"


def test_evidence_provenance_timestamp():
    result = run_transform()
    for e in result.evidence:
        assert e.provenance.timestamp == "2026-04-08T00:00:00Z"


def test_evidence_control_linkage():
    result = run_transform()
    ia01 = next(e for e in result.evidence if e.data["ksi_id"] == "KSI-IA-01")
    assert ia01.control_id == "KSI-IA-01"


def test_evidence_policy_linkage():
    result = run_transform()
    ia01 = next(e for e in result.evidence if e.data["ksi_id"] == "KSI-IA-01")
    assert ia01.policy_id == "policy:ksi:KSI-IA-01:default"


def test_unmapped_evidence_has_no_control_id():
    result = run_transform()
    unknown = next(e for e in result.evidence if e.data["ksi_id"] == "KSI-UNKNOWN-99")
    assert unknown.control_id is None
    assert unknown.policy_id is None


def test_transform_is_deterministic():
    result_a = run_transform()
    result_b = run_transform()
    hashes_a = sorted(e.hash() for e in result_a.evidence)
    hashes_b = sorted(e.hash() for e in result_b.evidence)
    assert hashes_a == hashes_b, "Transform is not deterministic"


def test_evidence_hash_is_stable():
    result = run_transform()
    ia01_a = next(e for e in result.evidence if e.data["ksi_id"] == "KSI-IA-01")
    result2 = run_transform()
    ia01_b = next(e for e in result2.evidence if e.data["ksi_id"] == "KSI-IA-01")
    assert ia01_a.hash() == ia01_b.hash()


def test_canonical_json_is_stable():
    result_a = run_transform()
    result_b = run_transform()
    canon_a = sorted(e.to_canonical() for e in result_a.evidence)
    canon_b = sorted(e.to_canonical() for e in result_b.evidence)
    assert canon_a == canon_b


def test_summary_contains_run_id():
    result = run_transform()
    assert "scuba-run-20260408-000000" in result.summary()


def test_summary_contains_counts():
    result = run_transform()
    summary = result.summary()
    assert "PASS" in summary
    assert "FAIL" in summary
    assert "WARN" in summary


def test_to_dict_is_serializable():
    result = run_transform()
    d = result.to_dict()
    serialized = json.dumps(d)
    assert len(serialized) > 0
