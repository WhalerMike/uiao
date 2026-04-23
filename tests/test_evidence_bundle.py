from __future__ import annotations

import json
from pathlib import Path

from uiao.evidence.bundle import EvidenceBundle, build_bundle_from_transform_result
from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scuba_normalized_sample.json"


def _bundle() -> EvidenceBundle:
    result = transform_scuba_to_ir(FIXTURE_PATH)
    return build_bundle_from_transform_result(result)


def test_bundle_returns_instance():
    b = _bundle()
    assert isinstance(b, EvidenceBundle)


def test_bundle_run_id():
    b = _bundle()
    assert b.run_id == "scuba-run-20260408-000000"


def test_bundle_evidence_count():
    b = _bundle()
    assert len(b.evidence) == 5


def test_bundle_summary_counts():
    b = _bundle()
    assert b.pass_count == 2
    assert b.warn_count == 1
    assert b.fail_count == 2


def test_bundle_unmapped_ksi():
    b = _bundle()
    assert "KSI-UNKNOWN-99" in b.unmapped_ksi_ids


def test_bundle_evidence_sorted():
    b = _bundle()
    ids = [e.id for e in b.evidence]
    assert ids == sorted(ids), "Evidence must be sorted by ID"


def test_bundle_to_dict_serializable():
    b = _bundle()
    d = b.to_dict()
    serialized = json.dumps(d)
    assert len(serialized) > 0


def test_bundle_canonical_is_stable():
    b1 = _bundle()
    b2 = _bundle()
    assert b1.to_canonical() == b2.to_canonical()


def test_bundle_hash_is_stable():
    b1 = _bundle()
    b2 = _bundle()
    assert b1.hash() == b2.hash()


def test_bundle_hash_is_not_empty():
    b = _bundle()
    assert len(b.hash()) == 64


def test_bundle_summary_contains_run_id():
    b = _bundle()
    assert "scuba-run-20260408-000000" in b.summary()


def test_bundle_summary_contains_hash():
    b = _bundle()
    assert "Bundle hash" in b.summary()
