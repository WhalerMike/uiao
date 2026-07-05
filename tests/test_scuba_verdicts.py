"""Tests for the ScubaDrift verdicts artifact (scuba_verdicts.py).

Covers:
- KSI_SCUBA_POLICIES map covers exactly the ScuBA-sourced rules (KSI-001..010)
- build_scuba_verdicts merge (flat + full ScubaGear shapes, dispositions)
- evaluate_scuba_rule verdict paths (satisfied / governed / actionable /
  missing policy / missing artifact / unmapped rule)
- load_scuba_verdicts robustness (absent file, malformed JSON, wrong shape)
- ksi_ar integration: ScuBA-sourced rules are evidence-backed, never
  unconditionally satisfied
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from uiao.ksi.scuba_verdicts import (
    KSI_SCUBA_POLICIES,
    build_scuba_verdicts,
    evaluate_scuba_rule,
    export_scuba_verdicts,
    load_scuba_verdicts,
)
from uiao.oscal.ksi_ar import build_ksi_ar

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RESULTS_FLAT: dict = {
    "metadata": {"ProductName": "AAD", "TenantId": "<T>"},
    "results": [
        {"PolicyId": "MS.AAD.1.1v1", "Result": "Pass", "Criticality": "Shall"},
        {"PolicyId": "MS.AAD.3.1v1", "Result": "Fail", "Criticality": "Shall"},
        {"PolicyId": "MS.AAD.3.2v1", "Result": "Pass", "Criticality": "Shall"},
        {"PolicyId": "MS.AAD.7.1v1", "Result": "Fail", "Criticality": "Shall"},
    ],
}

_TRIAGE: dict = {
    "as_of": "2026-07-05",
    "triaged": [
        {
            "policy_id": "MS.AAD.3.1v1",
            "result": "Fail",
            "disposition": "governed_exception",
            "reason": "accepted until 2026-12-31 (POAM-1042)",
            "acceptance": {"ticket": "POAM-1042", "expiry_date": "2026-12-31"},
        },
        {
            "policy_id": "MS.AAD.7.1v1",
            "result": "Fail",
            "disposition": "lapsed_acceptance",
            "reason": "risk-acceptance expired 2026-01-15 (POAM-0911)",
            "acceptance": {"ticket": "POAM-0911", "expiry_date": "2026-01-15"},
        },
    ],
}


def _verdicts(**overrides: object) -> dict:
    doc = build_scuba_verdicts(_RESULTS_FLAT, _TRIAGE, provenance_source="sample-fixture")
    doc.update(overrides)
    return doc


# ---------------------------------------------------------------------------
# Policy map coverage
# ---------------------------------------------------------------------------


def test_policy_map_covers_exactly_the_scuba_sourced_rules() -> None:
    expected = {f"KSI-{n:03d}" for n in range(1, 11)}
    assert set(KSI_SCUBA_POLICIES) == expected
    for rule_id, policies in KSI_SCUBA_POLICIES.items():
        assert policies, f"{rule_id} has an empty policy list"
        for pid in policies:
            assert pid.startswith("MS."), f"{rule_id} maps non-SCuBA policy id {pid}"


# ---------------------------------------------------------------------------
# build_scuba_verdicts
# ---------------------------------------------------------------------------


def test_build_merges_pass_and_dispositions() -> None:
    doc = _verdicts()
    policies = doc["policies"]
    assert policies["MS.AAD.1.1v1"] == {"result": "pass"}
    governed = policies["MS.AAD.3.1v1"]
    assert governed["result"] == "fail"
    assert governed["disposition"] == "governed_exception"
    assert governed["ticket"] == "POAM-1042"
    lapsed = policies["MS.AAD.7.1v1"]
    assert lapsed["disposition"] == "lapsed_acceptance"
    assert doc["as_of"] == "2026-07-05"
    assert doc["provenance"]["source"] == "sample-fixture"


def test_build_accepts_full_scubaresults_shape() -> None:
    full = {
        "MetaData": {"TenantId": "<T>"},
        "Results": {
            "AAD": [{"Control ID": "MS.AAD.1.1v1", "Result": "Pass"}],
            "EXO": [{"Control ID": "MS.EXO.1.1v2", "Result": "Fail"}],
        },
    }
    doc = build_scuba_verdicts(full, {"as_of": "2026-07-05", "triaged": []})
    assert doc["policies"]["MS.AAD.1.1v1"]["result"] == "pass"
    # Failing but absent from triage -> conservatively ungoverned.
    assert doc["policies"]["MS.EXO.1.1v2"]["disposition"] == "actionable_new_drift"


# ---------------------------------------------------------------------------
# evaluate_scuba_rule
# ---------------------------------------------------------------------------


def test_evaluate_satisfied_all_pass() -> None:
    state, detail = evaluate_scuba_rule("KSI-002", _verdicts())  # MS.AAD.1.1v1 passes
    assert state == "satisfied"
    assert "sample-fixture" in detail


def test_evaluate_satisfied_via_governed_exception() -> None:
    state, detail = evaluate_scuba_rule("KSI-001", _verdicts())  # 3.1 governed, 3.2 pass
    assert state == "satisfied"
    assert "governed" in detail
    assert "POAM-1042" in detail


def test_evaluate_not_satisfied_on_lapsed_acceptance() -> None:
    state, detail = evaluate_scuba_rule("KSI-003", _verdicts())  # MS.AAD.7.1v1 lapsed
    assert state == "not-satisfied"
    assert "lapsed_acceptance" in detail


def test_evaluate_other_when_policy_not_assessed() -> None:
    state, detail = evaluate_scuba_rule("KSI-010", _verdicts())  # DEFENDER not in run
    assert state == "other"
    assert "not assessed" in detail


def test_evaluate_other_when_artifact_missing() -> None:
    state, detail = evaluate_scuba_rule("KSI-001", None)
    assert state == "other"
    assert "No ScubaDrift verdicts artifact" in detail


def test_evaluate_other_when_rule_unmapped() -> None:
    state, _ = evaluate_scuba_rule("KSI-999", _verdicts())
    assert state == "other"


# ---------------------------------------------------------------------------
# load / export round-trip
# ---------------------------------------------------------------------------


def test_load_returns_none_for_missing_file() -> None:
    assert load_scuba_verdicts(Path("does/not/exist.json")) is None


def test_load_returns_none_for_malformed_content() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bad = Path(tmpdir) / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        assert load_scuba_verdicts(bad) is None
        wrong_shape = Path(tmpdir) / "wrong.json"
        wrong_shape.write_text(json.dumps({"schema": "x"}), encoding="utf-8")
        assert load_scuba_verdicts(wrong_shape) is None


def test_export_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        results_p = tmp / "results.json"
        triage_p = tmp / "triage.json"
        results_p.write_text(json.dumps(_RESULTS_FLAT), encoding="utf-8")
        triage_p.write_text(json.dumps(_TRIAGE), encoding="utf-8")
        out = export_scuba_verdicts(tmp / "verdicts.json", results_p, triage_p)
        doc = load_scuba_verdicts(Path(out))
        assert doc is not None
        assert len(doc["policies"]) == 4
        # Default provenance names the input files.
        assert "results.json" in doc["provenance"]["note"]


# ---------------------------------------------------------------------------
# ksi_ar integration
# ---------------------------------------------------------------------------

_SCUBA_MAPPING_ROW: dict = {
    "local_rule": "KSI-002",
    "local_title": "Legacy Authentication Disabled",
    "local_nist": ["AC-17", "IA-5"],
    "cr26_controls": ["KSI-IAM-APM"],
    "confidence": "high",
}

_SCUBA_RULE_DOC: dict = {
    "KSI_ID": "KSI-002",
    "Title": "Legacy Authentication Disabled",
    "Source": {"SCuBA_Field": "LegacyAuthEnabled"},
    "Mappings": {"CISA_SCUBA": "M365-AUTH-002"},
}


def _build_scuba_ar(verdicts_doc: dict | None) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        rules_dir = tmp / "rules"
        rules_dir.mkdir()
        import yaml

        (rules_dir / "KSI-002.yaml").write_text(yaml.dump(_SCUBA_RULE_DOC), encoding="utf-8")
        verdicts_path = tmp / "scubadrift-verdicts.json"
        if verdicts_doc is not None:
            verdicts_path.write_text(json.dumps(verdicts_doc), encoding="utf-8")
        return build_ksi_ar(
            mapping={"version": "0.1.0", "snapshot_sha": "abc", "mappings": [_SCUBA_MAPPING_ROW]},
            slots_dir=tmp / "no_slots",
            rules_dir=rules_dir,
            scuba_verdicts_path=verdicts_path,
        )


def test_ksi_ar_scuba_rule_satisfied_with_artifact() -> None:
    ar = _build_scuba_ar(_verdicts())
    result = ar["assessment-results"]["results"][0]
    finding = result["findings"][0]
    assert finding["target"]["status"]["state"] == "satisfied"
    obs = result["observations"][0]
    assert "sample-fixture" in obs["description"]
    prop_names = {p["name"] for p in obs["subjects"][0]["props"]}
    assert "evidence-artifact" in prop_names


def test_ksi_ar_scuba_rule_not_evaluated_without_artifact() -> None:
    """The pre-ScubaDrift behavior (unconditional satisfied) must be gone."""
    ar = _build_scuba_ar(None)
    finding = ar["assessment-results"]["results"][0]["findings"][0]
    assert finding["target"]["status"]["state"] == "other"


def test_ksi_ar_scuba_rule_not_satisfied_opens_risk() -> None:
    doc = _verdicts()
    doc["policies"]["MS.AAD.1.1v1"] = {
        "result": "fail",
        "disposition": "actionable_new_drift",
        "reason": "no risk-acceptance on file",
    }
    ar = _build_scuba_ar(doc)
    result = ar["assessment-results"]["results"][0]
    assert result["findings"][0]["target"]["status"]["state"] == "not-satisfied"
    assert len(result["risks"]) == 1
    assert result["risks"][0]["status"] == "open"


def test_ksi_ar_real_bundle_scuba_rules_are_evidence_backed() -> None:
    """With the committed sample artifact, KSI-001..010 verdicts carry the
    artifact reference and its provenance instead of a bare assertion."""
    committed = Path("output/artifacts/ksi-bundle/scubadrift-verdicts.json")
    if not committed.is_file():  # repo-root-relative; skip elsewhere
        return
    ar = build_ksi_ar(scuba_verdicts_path=committed)
    result = ar["assessment-results"]["results"][0]
    scuba_ids = set(KSI_SCUBA_POLICIES)
    seen = 0
    for obs in result["observations"]:
        props = {p["name"]: p["value"] for p in obs["subjects"][0]["props"]}
        if props.get("ksi-id") in scuba_ids:
            seen += 1
            assert "ScubaDrift" in obs["description"]
            assert "provenance" in obs["description"]
    assert seen == 10
