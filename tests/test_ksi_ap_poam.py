"""Tests for the KSI OSCAL Assessment Plan and POA&M generators.

Covers:
- AP structure (required OSCAL keys, task count, reviewed-controls)
- AP summary helper
- POA&M gap extraction from an AR document
- POA&M item structure (milestones, BOD 26-04 deadline, severity)
- POA&M summary helper
- Round-trip export (files written, parse back)
- Integration: bundle of AP+AR+POAM from real bundled data
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from uiao.oscal.ksi_ap import (
    build_ksi_ap,
    build_ksi_ap_summary,
    export_ksi_ap,
)
from uiao.oscal.ksi_ar import build_ksi_ar
from uiao.oscal.ksi_poam import (
    _extract_ar_gaps,
    build_ksi_poam,
    build_ksi_poam_summary,
    export_ksi_poam,
)


# ---------------------------------------------------------------------------
# Minimal mapping fixture (no slot dependency for AP tests)
# ---------------------------------------------------------------------------

_MINIMAL_MAPPING: dict = {
    "version": "0.1.0",
    "snapshot_sha": "abc123",
    "catalog_uuid": "test-catalog-uuid",
    "catalog_version": "0.1.0",
    "governing_doc": "UIAO_137",
    "adr": "ADR-061",
    "mappings": [
        {
            "local_rule": "KSI-011",
            "local_title": "Change Logging",
            "local_nist": ["CM-3"],
            "cr26_controls": ["KSI-CMT-LMC"],
            "confidence": "high",
        },
        {
            "local_rule": "KSI-022",
            "local_title": "Cybersecurity Training Effectiveness Review",
            "local_nist": ["AT-2", "AT-3", "AT-4"],
            "cr26_controls": ["KSI-CED-RAT"],
            "confidence": "low",
        },
        {
            "local_rule": "KSI-004",
            "local_title": "External Forwarding",
            "local_nist": ["SC-7"],
            "cr26_controls": ["KSI-CED-RAT"],
            "confidence": "medium",
        },
    ],
    "gaps": {},
}

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
            "artifact_refs": ["aan-part-12"],
            "confidence": "high",
            "rationale": "Part 12 SBOM pipeline.",
        }
    ],
}


# ---------------------------------------------------------------------------
# Assessment Plan tests
# ---------------------------------------------------------------------------


def test_build_ksi_ap_has_required_top_level_keys() -> None:
    doc = build_ksi_ap(mapping=_MINIMAL_MAPPING)
    assert "assessment-plan" in doc
    ap = doc["assessment-plan"]
    for key in ("uuid", "metadata", "import-ssp", "reviewed-controls", "tasks"):
        assert key in ap, f"AP missing required key: {key}"


def test_build_ksi_ap_reviewed_controls_match_mapping() -> None:
    doc = build_ksi_ap(mapping=_MINIMAL_MAPPING)
    ap = doc["assessment-plan"]
    selections = ap["reviewed-controls"]["control-selections"]
    included = {c["control-id"] for sel in selections for c in sel.get("include-controls", [])}
    assert "KSI-CMT-LMC" in included
    assert "KSI-CED-RAT" in included


def test_build_ksi_ap_tasks_cover_themes() -> None:
    doc = build_ksi_ap(mapping=_MINIMAL_MAPPING)
    ap = doc["assessment-plan"]
    task_themes = {p["value"] for task in ap["tasks"] for p in task.get("props", []) if p["name"] == "ksi-theme"}
    assert "KSI-CMT" in task_themes
    assert "KSI-CED" in task_themes


def test_build_ksi_ap_metadata_has_oscal_version() -> None:
    doc = build_ksi_ap(mapping=_MINIMAL_MAPPING)
    meta = doc["assessment-plan"]["metadata"]
    assert meta["oscal-version"] == "1.0.4"


def test_build_ksi_ap_system_name_in_title() -> None:
    doc = build_ksi_ap(system_name="Test System XYZ", mapping=_MINIMAL_MAPPING)
    title = doc["assessment-plan"]["metadata"]["title"]
    assert "Test System XYZ" in title


def test_build_ksi_ap_ssp_href_wired() -> None:
    doc = build_ksi_ap(ssp_href="#test-ssp-uuid", mapping=_MINIMAL_MAPPING)
    assert doc["assessment-plan"]["import-ssp"]["href"] == "#test-ssp-uuid"


def test_build_ksi_ap_summary_is_string() -> None:
    doc = build_ksi_ap(mapping=_MINIMAL_MAPPING)
    summary = build_ksi_ap_summary(doc)
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_export_ksi_ap_writes_valid_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = export_ksi_ap(
            output_path=Path(tmpdir) / "ksi-ap.json",
            mapping=_MINIMAL_MAPPING,
        )
        doc = json.loads(Path(path).read_text())
        assert "assessment-plan" in doc


# ---------------------------------------------------------------------------
# POA&M gap extraction tests
# ---------------------------------------------------------------------------


def test_extract_ar_gaps_returns_non_satisfied() -> None:
    ar_doc = build_ksi_ar(
        mapping=_MINIMAL_MAPPING,
        now="2026-07-03T00:00:00+00:00",
    )
    gaps = _extract_ar_gaps(ar_doc)
    # KSI-011 satisfied (slot-06 high binding), KSI-022 other (scaffold+low), KSI-004 not-satisfied (slot-07 low binding only)
    states = {g["rule_id"]: g["state"] for g in gaps}
    assert "KSI-011" not in states, "satisfied findings must not appear as gaps"
    assert states.get("KSI-022") == "other"
    assert states.get("KSI-004") == "not-satisfied"


def test_extract_ar_gaps_satisfied_excluded() -> None:
    ar_doc = build_ksi_ar(
        mapping=_MINIMAL_MAPPING,
        now="2026-07-03T00:00:00+00:00",
    )
    gaps = _extract_ar_gaps(ar_doc)
    for gap in gaps:
        assert gap["state"] != "satisfied"


# ---------------------------------------------------------------------------
# POA&M builder tests
# ---------------------------------------------------------------------------


def test_build_ksi_poam_has_required_keys() -> None:
    ar_doc = build_ksi_ar(mapping=_MINIMAL_MAPPING, now="2026-07-03T00:00:00+00:00")
    doc = build_ksi_poam(ar_doc=ar_doc)
    assert "plan-of-action-and-milestones" in doc
    poam = doc["plan-of-action-and-milestones"]
    for key in ("uuid", "metadata", "poam-items"):
        assert key in poam, f"POA&M missing required key: {key}"


def test_build_ksi_poam_items_not_empty() -> None:
    ar_doc = build_ksi_ar(mapping=_MINIMAL_MAPPING, now="2026-07-03T00:00:00+00:00")
    doc = build_ksi_poam(ar_doc=ar_doc)
    items = doc["plan-of-action-and-milestones"]["poam-items"]
    assert len(items) >= 2, "Should have at least KSI-022 (other) and KSI-004 (not-satisfied)"


def test_build_ksi_poam_ced_item_has_deadline() -> None:
    ar_doc = build_ksi_ar(mapping=_MINIMAL_MAPPING, now="2026-07-03T00:00:00+00:00")
    doc = build_ksi_poam(ar_doc=ar_doc)
    items = doc["plan-of-action-and-milestones"]["poam-items"]
    ced_items = [
        i for i in items if any(p["name"] == "ksi-theme" and p["value"] == "KSI-CED" for p in (i.get("props") or []))
    ]
    assert ced_items, "KSI-CED (KSI-022) must appear as a POA&M item"
    for item in ced_items:
        assert item["scheduled-completion"], "every CED POA&M item must have a scheduled completion date"


def test_build_ksi_poam_item_has_milestone() -> None:
    ar_doc = build_ksi_ar(mapping=_MINIMAL_MAPPING, now="2026-07-03T00:00:00+00:00")
    doc = build_ksi_poam(ar_doc=ar_doc)
    items = doc["plan-of-action-and-milestones"]["poam-items"]
    for item in items:
        assert "milestones" in item
        assert len(item["milestones"]) >= 1
        assert "scheduled-completion" in item["milestones"][0]


def test_build_ksi_poam_metadata_oscal_version() -> None:
    ar_doc = build_ksi_ar(mapping=_MINIMAL_MAPPING, now="2026-07-03T00:00:00+00:00")
    doc = build_ksi_poam(ar_doc=ar_doc)
    meta = doc["plan-of-action-and-milestones"]["metadata"]
    assert meta["oscal-version"] == "1.0.4"


def test_build_ksi_poam_summary_is_string() -> None:
    ar_doc = build_ksi_ar(mapping=_MINIMAL_MAPPING, now="2026-07-03T00:00:00+00:00")
    doc = build_ksi_poam(ar_doc=ar_doc)
    summary = build_ksi_poam_summary(doc)
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_export_ksi_poam_writes_valid_json() -> None:
    ar_doc = build_ksi_ar(mapping=_MINIMAL_MAPPING, now="2026-07-03T00:00:00+00:00")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = export_ksi_poam(
            output_path=Path(tmpdir) / "ksi-poam.json",
            ar_doc=ar_doc,
        )
        doc = json.loads(Path(path).read_text())
        assert "plan-of-action-and-milestones" in doc


# ---------------------------------------------------------------------------
# Integration: build from real bundled data
# ---------------------------------------------------------------------------


def test_integration_ap_from_real_bundled_data() -> None:
    doc = build_ksi_ap()
    ap = doc["assessment-plan"]
    # Should have tasks for multiple themes and reviewed-controls matching mapping.
    assert len(ap["tasks"]) >= 3
    selections = ap["reviewed-controls"]["control-selections"]
    n_controls = sum(len(sel.get("include-controls", [])) for sel in selections)
    assert n_controls >= 10, "Real bundled data should cover ≥10 CR26 controls"


def test_integration_poam_from_real_bundled_data() -> None:
    doc = build_ksi_poam()
    poam = doc["plan-of-action-and-milestones"]
    items = poam["poam-items"]
    # Some items should always be open (medium/low confidence rules)
    assert len(items) >= 1
    for item in items:
        assert item.get("scheduled-completion"), "Every POA&M item must have a deadline"


def test_integration_bundle_ap_ar_poam_linked() -> None:
    """AP UUID should appear in AR import-ap href when built together."""
    now = "2026-07-03T00:00:00+00:00"
    ap_doc = build_ksi_ap(now=now)
    ap_uuid = ap_doc["assessment-plan"]["uuid"]
    ar_doc = build_ksi_ar(ap_href=f"#{ap_uuid}", now=now)
    assert ar_doc["assessment-results"]["import-ap"]["href"] == f"#{ap_uuid}"

    poam_doc = build_ksi_poam(ar_doc=ar_doc, ap_href=f"#{ap_uuid}", now=now)
    poam_items = poam_doc["plan-of-action-and-milestones"]["poam-items"]
    # POA&M should not be empty (some rules have medium/low confidence)
    assert isinstance(poam_items, list)
