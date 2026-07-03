"""Conformance tests for the KSI-PIY scaffold rules (ADR-111 / UIAO_137 §6).

KSI-017 through KSI-021 seed the CR26 KSI-PIY (Inventory) theme — the last
remaining theme with zero local-rule coverage after KSI-SCR was closed in
Phase 2B.

KSI-PIY coverage:
  KSI-017 → KSI-PIY-GIV   confidence: high  (slot-05, Part 8)
  KSI-018 → KSI-PIY-RES   confidence: high  (slot-05, Part 8)
  KSI-019 → KSI-PIY-RIS   confidence: high  (slot-05, Part 8)
  KSI-020 → KSI-PIY-RSD   confidence: low   (no slot binding yet; Part 14 pending)
  KSI-021 → KSI-PIY-RVD   confidence: high  (slot-05, Part 7)

All five rules carry ``Status: scaffold`` — evaluability and mapping
confidence are orthogonal per ADR-111 / FINDING-004 §4.

Companion:
- src/uiao/ksi/rules/KSI-017.yaml … KSI-021.yaml
- src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml
- src/uiao/adapters/fedramp_aan_catalog/mappings/slot-05-endpoint-evidence.yaml
- src/uiao/canon/specs/fedramp-cr26-ksi-mapping.md (UIAO_137)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uiao.adapters.fedramp_cr26_catalog import (
    default_snapshot_dir,
    enumerate_ksi_controls,
    load_catalog,
    load_mapping,
    reconcile,
    validate_mapping,
)

_SCAFFOLD_TO_CR26 = {
    "KSI-017": "KSI-PIY-GIV",
    "KSI-018": "KSI-PIY-RES",
    "KSI-019": "KSI-PIY-RIS",
    "KSI-020": "KSI-PIY-RSD",
    "KSI-021": "KSI-PIY-RVD",
}

_HIGH_CONFIDENCE_RULES = {"KSI-017", "KSI-018", "KSI-019", "KSI-021"}
_LOW_CONFIDENCE_RULES = {"KSI-020"}

_RULES_DIR = Path(__file__).resolve().parents[2] / "src" / "uiao" / "ksi" / "rules"


def _load_rule(rule_id: str) -> dict:
    path = _RULES_DIR / f"{rule_id}.yaml"
    assert path.is_file(), f"scaffold rule file missing: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Happy path — rule files are well-formed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_file_parses_and_has_required_shape(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert rule["KSI_ID"] == rule_id
    assert rule["Status"] == "scaffold"
    assert rule["Theme"] == "KSI-PIY"
    assert rule["Mappings"]["CR26"] == _SCAFFOLD_TO_CR26[rule_id]
    assert rule["Mappings"]["NIST_800-53"]
    assert rule["Title"].strip()


def test_scaffolds_cover_exactly_the_five_ksi_piy_controls() -> None:
    covered = {_load_rule(r)["Mappings"]["CR26"] for r in _SCAFFOLD_TO_CR26}
    assert covered == {"KSI-PIY-GIV", "KSI-PIY-RES", "KSI-PIY-RIS", "KSI-PIY-RSD", "KSI-PIY-RVD"}


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_cr26_id_resolves_in_pinned_snapshot(rule_id: str) -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert _SCAFFOLD_TO_CR26[rule_id] in snapshot_ids


# ---------------------------------------------------------------------------
# Confidence assertions — high for slot-05-backed rules, low for RSD
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(_HIGH_CONFIDENCE_RULES))
def test_high_confidence_piy_rules_in_mapping(rule_id: str) -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
    assert rows[rule_id]["confidence"] == "high", (
        f"{rule_id} should be confidence:high (slot-05 binding exists); got {rows[rule_id]['confidence']}"
    )


@pytest.mark.parametrize("rule_id", sorted(_LOW_CONFIDENCE_RULES))
def test_low_confidence_piy_rules_in_mapping(rule_id: str) -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
    assert rows[rule_id]["confidence"] == "low", (
        f"{rule_id} should be confidence:low (no slot binding yet); got {rows[rule_id]['confidence']}"
    )


# ---------------------------------------------------------------------------
# Lockstep — scaffolds, mapping companion, and gap list agree
# ---------------------------------------------------------------------------


def test_mapping_companion_includes_every_piy_scaffold() -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    for rule_id, cr26 in _SCAFFOLD_TO_CR26.items():
        assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
        assert rows[rule_id]["cr26_controls"] == [cr26]


def test_ksi_piy_is_no_longer_listed_as_a_zero_coverage_gap() -> None:
    mapping = load_mapping()
    gaps = mapping.get("gaps", {})
    assert "KSI-PIY" not in gaps.get("themes_with_zero_local_rules", [])
    zero_controls = set(gaps.get("controls_with_zero_local_rules", []))
    assert not (zero_controls & set(_SCAFFOLD_TO_CR26.values()))


# ---------------------------------------------------------------------------
# Adapter still reconciles cleanly with the expanded corpus
# ---------------------------------------------------------------------------


def test_validate_mapping_stays_clean_with_piy_scaffold_rows() -> None:
    findings = validate_mapping()
    assert findings == [], "Scaffold CR26 IDs must resolve in the snapshot; got: " + ", ".join(
        f.summary for f in findings
    )


def test_reconcile_stays_clean_with_piy_rules() -> None:
    findings = reconcile()
    assert findings == [], "Expanded KSI corpus should reconcile cleanly; got: " + ", ".join(
        f.summary for f in findings
    )


# ---------------------------------------------------------------------------
# Failure mode — resolution check is meaningful; scaffolds are non-evaluable
# ---------------------------------------------------------------------------


def test_fabricated_ksi_piy_id_does_not_resolve_in_snapshot() -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert "KSI-PIY-ZZZ" not in snapshot_ids


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_logic_is_marked_pending_not_evaluable(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert "PENDING" in rule["Evaluation"]["Logic"]
