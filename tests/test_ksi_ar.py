"""Tests for the KSI OSCAL Assessment Results generator (ksi_ar.py).

Covers:
- Slot file loading and CR26 binding index construction
- Verdict logic for satisfied / not-satisfied / not-evaluated paths
- OSCAL document structure (required keys, types, counts)
- Scaffold rule handling (evaluability ≠ mapping confidence)
- Round-trip export (file written, parses back to dict)
- CLI smoke test via build_ksi_ar() with real bundled data
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from uiao.oscal.ksi_ar import (
    build_cr26_binding_index,
    build_ksi_ar,
    build_ksi_ar_summary,
    export_ksi_ar,
    load_ksi_rules,
    load_slot_files,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_HIGH_SLOT: dict = {
    "slot_id": 6,
    "slot": "security",
    "ksi_category": "KSI-CMT",
    "nist_anchor": "CM-2 / AC-4",
    "artifacts": [{"id": "aan-part-12", "aan_part": 12}],
    "bindings": [
        {
            "cr26_theme_binding": True,
            "cr26_ksi_theme": "KSI-CMT",
            "cr26_controls": ["KSI-CMT-LMC"],
            "artifact_refs": ["aan-part-12", "aan-part-10"],
            "confidence": "high",
            "rationale": "Part 12 SBOM pipeline.",
        }
    ],
}

_MEDIUM_SLOT: dict = {
    "slot_id": 99,
    "slot": "test-slot",
    "ksi_category": "KSI-TEST",
    "nist_anchor": "SC-7",
    "artifacts": [],
    "bindings": [
        {
            "cr26_controls": ["KSI-TEST-SNT"],
            "artifact_refs": ["aan-part-99"],
            "confidence": "medium",
            "rationale": "Partial coverage.",
        }
    ],
}

_MAPPING_HIGH: dict = {
    "local_rule": "KSI-011",
    "local_title": "Change Logging and Monitoring",
    "local_nist": ["CM-3", "AU-6"],
    "cr26_controls": ["KSI-CMT-LMC"],
    "confidence": "high",
}

_MAPPING_MEDIUM: dict = {
    "local_rule": "KSI-004",
    "local_title": "External Forwarding Restrictions",
    "local_nist": ["SC-7"],
    "cr26_controls": ["KSI-TEST-SNT"],
    "confidence": "medium",
}

_MAPPING_NO_BINDING: dict = {
    "local_rule": "KSI-007",
    "local_title": "Safe Links Protection",
    "local_nist": ["SI-3"],
    "cr26_controls": ["KSI-SVC-VCM"],
    "confidence": "medium",
}

_SCAFFOLD_RULE: dict = {
    "KSI_ID": "KSI-011",
    "Status": "scaffold",
    "Title": "Change Logging and Monitoring",
    "Theme": "KSI-CMT",
    "Evaluation": {"Logic": "PENDING — scaffold"},
    "Mappings": {"CR26": "KSI-CMT-LMC", "NIST_800-53": "CM-3, AU-6"},
}

_ACTIVE_RULE: dict = {
    "KSI_ID": "KSI-004",
    "Status": "active",
    "Title": "External Forwarding Restrictions",
    "Theme": "KSI-SVC",
    "Evaluation": {"Logic": "some_check()"},
    "Mappings": {"CR26": "KSI-TEST-SNT", "NIST_800-53": "SC-7"},
}


# ---------------------------------------------------------------------------
# build_cr26_binding_index
# ---------------------------------------------------------------------------


def test_binding_index_high_confidence_entry() -> None:
    index = build_cr26_binding_index([_HIGH_SLOT])
    assert "KSI-CMT-LMC" in index
    entries = index["KSI-CMT-LMC"]
    assert len(entries) == 1
    assert entries[0]["confidence"] == "high"
    assert "aan-part-12" in entries[0]["artifact_refs"]
    assert entries[0]["slot_id"] == 6


def test_binding_index_multiple_slots_merged() -> None:
    slot_a = {
        "slot_id": 1,
        "slot": "identity",
        "artifacts": [],
        "bindings": [{"cr26_controls": ["KSI-IAM-APM"], "artifact_refs": ["aan-part-03"], "confidence": "high"}],
    }
    slot_b = {
        "slot_id": 2,
        "slot": "addressing",
        "artifacts": [],
        "bindings": [{"cr26_controls": ["KSI-IAM-APM"], "artifact_refs": ["aan-part-01"], "confidence": "medium"}],
    }
    index = build_cr26_binding_index([slot_a, slot_b])
    entries = index.get("KSI-IAM-APM", [])
    assert len(entries) == 2
    confidences = {e["confidence"] for e in entries}
    assert confidences == {"high", "medium"}


def test_binding_index_empty_slots_returns_empty() -> None:
    assert build_cr26_binding_index([]) == {}


# ---------------------------------------------------------------------------
# Verdict logic (via build_ksi_ar with minimal inputs)
# ---------------------------------------------------------------------------


def _mini_mapping(*rows: dict) -> dict:
    return {
        "version": "0.1.0",
        "snapshot_sha": "abc123",
        "mappings": list(rows),
    }


def _build_mini_ar(
    mapping_row: dict,
    slots: list[dict],
    rule_doc: dict | None = None,
    *,
    rules_dir: Path | None = None,
    slots_dir: Path | None = None,
) -> dict:
    """Helper: write slots to tmp dir, call build_ksi_ar, return the findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        # Write slot files.
        if slots_dir is None and slots:
            import yaml

            for i, slot in enumerate(slots, start=1):
                (tmp / f"slot-{i:02d}-test.yaml").write_text(yaml.dump(slot), encoding="utf-8")
            slots_dir = tmp

        # Write rule file if provided.
        if rules_dir is None and rule_doc is not None:
            import yaml

            rules_tmp = tmp / "rules"
            rules_tmp.mkdir(exist_ok=True)
            ksi_id = rule_doc.get("KSI_ID", "KSI-999")
            (rules_tmp / f"{ksi_id}.yaml").write_text(yaml.dump(rule_doc), encoding="utf-8")
            rules_dir = rules_tmp

        return build_ksi_ar(
            mapping=_mini_mapping(mapping_row),
            slots_dir=slots_dir,
            rules_dir=rules_dir or tmp / "empty_rules",
        )


def test_verdict_satisfied_high_confidence_high_binding() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    result = ar["assessment-results"]["results"][0]
    findings = result["findings"]
    assert len(findings) == 1
    assert findings[0]["target"]["status"]["state"] == "satisfied"


def test_verdict_scaffold_rule_still_satisfied_when_binding_is_high() -> None:
    """Scaffold status does not override high-confidence binding verdict."""
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT], rule_doc=_SCAFFOLD_RULE)
    result = ar["assessment-results"]["results"][0]
    finding = result["findings"][0]
    assert finding["target"]["status"]["state"] == "satisfied"
    # But the remark/description must mention scaffold.
    obs = result["observations"][0]
    assert "scaffold" in obs["description"].lower() or "scaffold" in finding.get("remarks", "").lower()


def test_verdict_not_satisfied_medium_mapping_confidence() -> None:
    ar = _build_mini_ar(_MAPPING_MEDIUM, [_MEDIUM_SLOT])
    result = ar["assessment-results"]["results"][0]
    finding = result["findings"][0]
    assert finding["target"]["status"]["state"] == "not-satisfied"


def test_verdict_other_when_no_slot_binding() -> None:
    ar = _build_mini_ar(_MAPPING_NO_BINDING, [_HIGH_SLOT])  # HIGH_SLOT has no KSI-SVC-VCM
    result = ar["assessment-results"]["results"][0]
    finding = result["findings"][0]
    assert finding["target"]["status"]["state"] == "other"


def test_no_risk_for_satisfied_verdict() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    risks = ar["assessment-results"]["results"][0]["risks"]
    assert risks == []


def test_risk_present_for_not_satisfied_verdict() -> None:
    ar = _build_mini_ar(_MAPPING_MEDIUM, [_MEDIUM_SLOT])
    risks = ar["assessment-results"]["results"][0]["risks"]
    assert len(risks) == 1
    assert risks[0]["status"] == "open"


# ---------------------------------------------------------------------------
# OSCAL document structure
# ---------------------------------------------------------------------------


def test_ar_top_level_keys() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    ar_root = ar["assessment-results"]
    for key in ("uuid", "metadata", "import-ap", "results", "back-matter"):
        assert key in ar_root, f"missing key: {key}"


def test_ar_metadata_required_fields() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    meta = ar["assessment-results"]["metadata"]
    for key in ("title", "published", "last-modified", "version", "oscal-version", "roles", "parties"):
        assert key in meta, f"missing metadata key: {key}"
    assert meta["oscal-version"] == "1.0.4"


def test_ar_reviewed_controls_contains_cr26_ids() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    ctrl_sel = ar["assessment-results"]["results"][0]["reviewed-controls"]["control-selections"]
    included = {c["control-id"] for sel in ctrl_sel for c in sel.get("include-controls", [])}
    assert "KSI-CMT-LMC" in included


def test_ar_observation_has_ksi_props() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    obs = ar["assessment-results"]["results"][0]["observations"][0]
    subject_props = obs["subjects"][0]["props"]
    prop_names = {p["name"] for p in subject_props}
    assert "ksi-id" in prop_names
    assert "verdict" in prop_names
    assert "cr26-control" in prop_names


def test_ar_finding_has_target_status() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    finding = ar["assessment-results"]["results"][0]["findings"][0]
    assert "target" in finding
    assert "status" in finding["target"]
    assert "state" in finding["target"]["status"]


def test_ar_back_matter_has_slot_resources() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    resources = ar["assessment-results"]["back-matter"]["resources"]
    assert len(resources) == 1
    prop_names = {p["name"] for p in resources[0]["props"]}
    assert "slot-id" in prop_names


def test_ar_result_counts_match_findings() -> None:
    """result props counts must agree with the actual lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import yaml

        tmp = Path(tmpdir)
        (tmp / "slot-06-test.yaml").write_text(yaml.dump(_HIGH_SLOT), encoding="utf-8")
        ar = build_ksi_ar(
            mapping=_mini_mapping(_MAPPING_HIGH, _MAPPING_MEDIUM, _MAPPING_NO_BINDING),
            slots_dir=tmp,
            rules_dir=tmp / "empty_rules",
        )

    result = ar["assessment-results"]["results"][0]
    props = {p["name"]: int(p["value"]) for p in result["props"] if p["value"].isdigit()}
    findings = result["findings"]
    total = props["satisfied-count"] + props["not-satisfied-count"] + props["not-evaluated-count"]
    assert total == len(findings)
    assert props["total-ksi-rules"] == len(findings)


# ---------------------------------------------------------------------------
# build_ksi_ar_summary
# ---------------------------------------------------------------------------


def test_summary_contains_key_lines() -> None:
    ar = _build_mini_ar(_MAPPING_HIGH, [_HIGH_SLOT])
    summary = build_ksi_ar_summary(ar)
    assert "Satisfied" in summary
    assert "Not-satisfied" in summary
    assert "Not-evaluated" in summary
    assert "Slots bound" in summary


# ---------------------------------------------------------------------------
# export_ksi_ar — round-trip to disk
# ---------------------------------------------------------------------------


def test_export_ksi_ar_writes_valid_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        import yaml

        tmp = Path(tmpdir)
        (tmp / "slot-06-test.yaml").write_text(yaml.dump(_HIGH_SLOT), encoding="utf-8")
        out_path = tmp / "out" / "ksi-ar.json"

        written = export_ksi_ar(
            output_path=out_path,
            slots_dir=tmp,
        )
        assert Path(written).is_file()
        doc = json.loads(Path(written).read_text(encoding="utf-8"))
        assert "assessment-results" in doc


# ---------------------------------------------------------------------------
# Integration — bundled real data
# ---------------------------------------------------------------------------


def test_build_ksi_ar_with_real_bundled_data() -> None:
    """Smoke test: real ksi-mapping.yaml + real slot evidence files."""
    ar = build_ksi_ar()
    ar_root = ar["assessment-results"]

    result = ar_root["results"][0]
    findings = result["findings"]
    observations = result["observations"]

    # Must have one finding + observation per mapping row.
    assert len(findings) == len(observations)
    assert len(findings) > 0

    # All KSI-CMT scaffold rules (KSI-011..014) should be satisfied
    # (high mapping confidence + slot-06 high-confidence binding).
    scaffold_ids = {"KSI-011", "KSI-012", "KSI-013", "KSI-014"}
    id_to_state = {}
    for finding in findings:
        ksi_id = next(
            (p["value"] for p in finding["target"]["props"] if p["name"] == "ksi-id"),
            None,
        )
        if ksi_id in scaffold_ids:
            id_to_state[ksi_id] = finding["target"]["status"]["state"]

    for ksi_id in scaffold_ids:
        assert id_to_state.get(ksi_id) == "satisfied", f"{ksi_id} expected satisfied, got {id_to_state.get(ksi_id)}"

    # Summary must not raise.
    summary = build_ksi_ar_summary(ar)
    assert "Satisfied" in summary


def test_build_ksi_ar_real_data_back_matter_has_six_slots() -> None:
    ar = build_ksi_ar()
    resources = ar["assessment-results"]["back-matter"]["resources"]
    # One resource per slot file (slots 1–6).
    assert len(resources) == 6


def test_load_slot_files_returns_six_slots() -> None:
    slots = load_slot_files()
    assert len(slots) == 6
    slot_ids = sorted(s.get("slot_id") for s in slots)
    assert slot_ids == [1, 2, 3, 4, 5, 6]


def test_load_ksi_rules_includes_scaffold_rules() -> None:
    rules = load_ksi_rules()
    for ksi_id in ("KSI-011", "KSI-012", "KSI-013", "KSI-014"):
        assert ksi_id in rules, f"{ksi_id} missing from loaded rules"
        assert rules[ksi_id]["Status"] == "scaffold"
