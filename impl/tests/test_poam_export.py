from __future__ import annotations

import json
from pathlib import Path

from uiao.impl.evidence.bundle import build_bundle_from_transform_result
from uiao.impl.evidence.poam import build_poam, poam_summary, poam_to_json
from uiao.impl.ir.adapters.scuba.transformer import transform_scuba_to_ir


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scuba_normalized_sample.json"


def _poam():
    result = transform_scuba_to_ir(FIXTURE_PATH)
    bundle = build_bundle_from_transform_result(result)
    return build_poam(bundle)


def test_poam_only_contains_fail_and_warn():
    rows = _poam()
    for r in rows:
        assert r["status"] in ("FAIL", "WARN"), f"Unexpected status: {r['status']}"


def test_poam_row_count():
    rows = _poam()
    assert len(rows) == 3


def test_poam_sorted_by_severity():
    rows = _poam()
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    severities = [order[r["severity"]] for r in rows]
    assert severities == sorted(severities), "POA&M not sorted by severity"


def test_poam_has_required_fields():
    rows = _poam()
    required = {
        "ksi_id",
        "control_id",
        "policy_id",
        "status",
        "severity",
        "evidence_id",
        "evidence_hash",
        "remediation_sla_days",
        "recommended_action",
    }
    for r in rows:
        assert required.issubset(r.keys()), f"Missing fields in row: {r}"


def test_poam_sla_critical_is_15():
    result = transform_scuba_to_ir(FIXTURE_PATH)
    bundle = build_bundle_from_transform_result(result)
    rows = build_poam(bundle)
    critical = [r for r in rows if r["severity"] == "Critical"]
    for r in critical:
        assert r["remediation_sla_days"] == 15


def test_poam_evidence_hash_is_64_chars():
    rows = _poam()
    for r in rows:
        assert len(r["evidence_hash"]) == 64


def test_poam_to_json_is_valid():
    rows = _poam()
    output = poam_to_json(rows)
    parsed = json.loads(output)
    assert len(parsed) == len(rows)


def test_poam_is_deterministic():
    rows_a = _poam()
    rows_b = _poam()
    assert poam_to_json(rows_a) == poam_to_json(rows_b)


def test_poam_summary_output():
    rows = _poam()
    summary = poam_summary(rows)
    assert "POA&M Summary" in summary
    assert "3 items" in summary

