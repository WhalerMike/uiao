"""Tests for the FedRAMP CR26 Catalog conformance adapter (ADR-061 D3).

Covers happy-path enumeration against the real vendored snapshot and
failure modes around missing/malformed snapshots and synthetic drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.fedramp_cr26_catalog import (
    ADAPTER_ID,
    DEFAULT_SNAPSHOT_SHA,
    EXPECTED_KSI_THEMES,
    STATUS,
    Cr26CatalogAdapter,
    Cr26CatalogMalformed,
    Cr26MappingMalformed,
    Cr26SnapshotNotFound,
    default_snapshot_dir,
    enumerate_ksi_controls,
    enumerate_ksi_themes,
    load_catalog,
    load_mapping,
    reconcile,
    validate_mapping,
)


# ---------------------------------------------------------------------------
# Identity / constants
# ---------------------------------------------------------------------------


def test_adapter_id_is_kebab_case_and_matches_registry() -> None:
    assert ADAPTER_ID == "fedramp-cr26-catalog"


def test_status_is_proposed_while_adr_061_is_proposed() -> None:
    assert STATUS == "proposed"


def test_expected_ksi_themes_are_the_ten_phase_two_themes() -> None:
    assert set(EXPECTED_KSI_THEMES) == {
        "KSI-CMT",
        "KSI-CNA",
        "KSI-CED",
        "KSI-IAM",
        "KSI-INR",
        "KSI-MLA",
        "KSI-PIY",
        "KSI-RPL",
        "KSI-SVC",
        "KSI-SCR",
    }


# ---------------------------------------------------------------------------
# Default snapshot resolution
# ---------------------------------------------------------------------------


def test_default_snapshot_dir_resolves_to_vendored_pin() -> None:
    snap = default_snapshot_dir()
    assert snap.name == DEFAULT_SNAPSHOT_SHA
    assert (snap / "catalog" / "json" / "FedRAMP_CR26_catalog.json").is_file()


# ---------------------------------------------------------------------------
# Catalog enumeration against the real snapshot
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_catalog() -> dict:
    return load_catalog(default_snapshot_dir())


def test_load_catalog_returns_oscal_catalog_shape(real_catalog: dict) -> None:
    assert "catalog" in real_catalog
    assert real_catalog["catalog"].get("uuid")
    assert real_catalog["catalog"].get("metadata", {}).get("title")


def test_enumerate_ksi_themes_returns_all_ten_in_catalog_order(
    real_catalog: dict,
) -> None:
    themes = enumerate_ksi_themes(real_catalog)
    assert len(themes) == 10
    assert set(themes) == set(EXPECTED_KSI_THEMES)


def test_enumerate_ksi_controls_returns_46_controls_across_ten_themes(
    real_catalog: dict,
) -> None:
    controls = enumerate_ksi_controls(real_catalog)
    assert set(controls.keys()) == set(EXPECTED_KSI_THEMES)
    total = sum(len(v) for v in controls.values())
    # 4 + 8 + 1 + 6 + 3 + 5 + 5 + 4 + 8 + 2 = 46 — see snapshot PROVENANCE.md
    assert total == 46
    # Spot-check a known control ID.
    iam_ids = {c["id"] for c in controls["KSI-IAM"]}
    assert "KSI-IAM-ELP" in iam_ids


# ---------------------------------------------------------------------------
# Reconciliation — happy path against the real snapshot
# ---------------------------------------------------------------------------


def test_reconcile_against_real_snapshot_emits_no_findings() -> None:
    findings = reconcile()
    assert findings == [], "Real vendored snapshot should reconcile cleanly; got: " + ", ".join(
        f.summary for f in findings
    )


def test_adapter_class_reconcile_matches_function_reconcile() -> None:
    adapter = Cr26CatalogAdapter()
    assert adapter.ADAPTER_ID == ADAPTER_ID
    assert adapter.reconcile() == reconcile()


# ---------------------------------------------------------------------------
# Failure modes — missing / malformed snapshots
# ---------------------------------------------------------------------------


def test_load_catalog_raises_when_snapshot_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(Cr26SnapshotNotFound):
        load_catalog(tmp_path / "nonexistent-sha")


def test_load_catalog_raises_when_json_is_invalid(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog" / "json"
    catalog_path.mkdir(parents=True)
    (catalog_path / "FedRAMP_CR26_catalog.json").write_text("not-json")
    with pytest.raises(Cr26CatalogMalformed):
        load_catalog(tmp_path)


def test_load_catalog_raises_when_catalog_key_missing(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog" / "json"
    catalog_path.mkdir(parents=True)
    (catalog_path / "FedRAMP_CR26_catalog.json").write_text(json.dumps({"not-a-catalog": {}}))
    with pytest.raises(Cr26CatalogMalformed):
        load_catalog(tmp_path)


# ---------------------------------------------------------------------------
# Synthetic drift — DRIFT-SCHEMA and DRIFT-PROVENANCE paths
# ---------------------------------------------------------------------------


def _write_synthetic_snapshot(tmp_path: Path, catalog_payload: dict) -> Path:
    """Write a minimal snapshot directory containing only the catalog JSON."""
    cat_dir = tmp_path / "catalog" / "json"
    cat_dir.mkdir(parents=True)
    (cat_dir / "FedRAMP_CR26_catalog.json").write_text(json.dumps(catalog_payload))
    return tmp_path


def test_reconcile_emits_schema_drift_when_ksi_group_absent(
    tmp_path: Path,
) -> None:
    snapshot = _write_synthetic_snapshot(
        tmp_path,
        {"catalog": {"groups": [{"id": "FRR", "title": "Only FRR"}]}},
    )
    findings = reconcile(snapshot_dir=snapshot, ksi_rules_dir=tmp_path)
    classes = {f.drift_class for f in findings}
    assert "DRIFT-SCHEMA" in classes
    # The summary should name the missing group so reviewers can act.
    assert any("KSI" in f.summary for f in findings)


def test_reconcile_emits_provenance_drift_for_missing_theme(
    tmp_path: Path,
) -> None:
    # KSI group is present but lacks KSI-IAM — should fire DRIFT-PROVENANCE
    # for the missing theme.
    snapshot = _write_synthetic_snapshot(
        tmp_path,
        {
            "catalog": {
                "groups": [
                    {
                        "id": "KSI",
                        "groups": [
                            {
                                "id": "KSI-CMT",
                                "title": "Change Management",
                                "controls": [{"id": "KSI-CMT-LMC", "title": "Logging Changes"}],
                            }
                        ],
                    }
                ]
            }
        },
    )
    findings = reconcile(snapshot_dir=snapshot, ksi_rules_dir=tmp_path)
    prov = [f for f in findings if f.drift_class == "DRIFT-PROVENANCE"]
    missing_themes = {f.details.get("expected_theme") for f in prov if "expected_theme" in f.details}
    assert "KSI-IAM" in missing_themes


def test_reconcile_emits_schema_drift_when_theme_has_zero_controls(
    tmp_path: Path,
) -> None:
    # All ten themes present but one has no controls — should fire
    # DRIFT-SCHEMA for that theme.
    themes_with_one_control = [
        {
            "id": theme,
            "controls": [{"id": f"{theme}-XYZ", "title": "stub"}],
        }
        for theme in EXPECTED_KSI_THEMES
    ]
    themes_with_one_control[3]["controls"] = []  # KSI-IAM empty
    snapshot = _write_synthetic_snapshot(
        tmp_path,
        {"catalog": {"groups": [{"id": "KSI", "groups": themes_with_one_control}]}},
    )
    findings = reconcile(snapshot_dir=snapshot, ksi_rules_dir=tmp_path)
    schema_findings = [f for f in findings if f.drift_class == "DRIFT-SCHEMA"]
    assert any("zero controls" in f.summary for f in schema_findings)


def test_reconcile_finding_serializes_to_dict(tmp_path: Path) -> None:
    snapshot = _write_synthetic_snapshot(
        tmp_path,
        {"catalog": {"groups": [{"id": "FRR"}]}},
    )
    findings = reconcile(snapshot_dir=snapshot, ksi_rules_dir=tmp_path)
    assert findings, "Synthetic catalog should produce at least one finding."
    payload = findings[0].to_dict()
    assert set(payload.keys()) == {"drift_class", "severity", "summary", "details"}
    assert payload["drift_class"].startswith("DRIFT-")


# ---------------------------------------------------------------------------
# UIAO_137 mapping — loader and consistency against the real snapshot
# ---------------------------------------------------------------------------


def test_load_mapping_returns_uiao_137_payload() -> None:
    mapping = load_mapping()
    assert mapping["snapshot_sha"] == DEFAULT_SNAPSHOT_SHA
    assert mapping["governing_doc"] == "UIAO_137"
    assert isinstance(mapping["mappings"], list)
    assert len(mapping["mappings"]) >= 10  # at least KSI-001..010
    # Every row must declare local_rule + cr26_controls + confidence.
    for row in mapping["mappings"]:
        assert "local_rule" in row
        assert "cr26_controls" in row
        assert row["confidence"] in {"high", "medium", "low"}


def test_load_mapping_covers_all_ten_local_ksi_rules() -> None:
    mapping = load_mapping()
    covered = {row["local_rule"] for row in mapping["mappings"]}
    expected = {f"KSI-{n:03d}" for n in range(1, 11)}
    assert expected <= covered, f"Local rules missing from mapping: {expected - covered}"


def test_validate_mapping_against_real_snapshot_is_consistent() -> None:
    findings = validate_mapping()
    assert findings == [], "Every CR26 ID in UIAO_137 must resolve in the pinned snapshot; got: " + ", ".join(
        f.summary for f in findings
    )


def test_validate_mapping_flags_mismatched_snapshot_sha() -> None:
    mapping = load_mapping()
    bogus = dict(mapping)
    bogus["snapshot_sha"] = "0" * 40
    findings = validate_mapping(mapping=bogus)
    assert any("does not match" in f.summary for f in findings)


def test_validate_mapping_flags_unresolvable_cr26_id() -> None:
    mapping = load_mapping()
    bogus = dict(mapping)
    bogus["mappings"] = list(mapping["mappings"]) + [
        {
            "local_rule": "KSI-099",
            "cr26_controls": ["KSI-XYZ-ZZZ"],
            "confidence": "high",
        }
    ]
    findings = validate_mapping(mapping=bogus)
    assert any("KSI-XYZ-ZZZ" in f.summary for f in findings)


def test_load_mapping_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(Cr26MappingMalformed):
        load_mapping(tmp_path / "no-such.yaml")


def test_load_mapping_raises_when_required_keys_missing(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("mappings: []\n")  # no snapshot_sha
    with pytest.raises(Cr26MappingMalformed):
        load_mapping(p)
