"""Conformance tests for the KSI-SCR rules (ADR-111 / UIAO_137 §5).

KSI-015 and KSI-016 seed the CR26 KSI-SCR (Supply Chain Risk) theme.
Both were activated in ADR-111 phase 5 (2026-07-04) after evidence review
confirmed the existing SBOM pipeline + SCRM charter satisfy CR26 requirements
without requiring additional telemetry pipeline wiring:

  KSI-015 → KSI-SCR-MIT   active    confidence: high  (slot-06, Parts 12+13)
  KSI-016 → KSI-SCR-MON   active    confidence: high  (slot-06, Parts 12+10)

Key insight: CR26 KSI-SCR-MON explicitly names "contractual notification
requirements" as a qualifying mechanism — PSIRT/MSRC subscriptions directly
satisfy SR-8 without requiring a full Sentinel telemetry pipeline.

Companion:
- src/uiao/ksi/rules/KSI-015.yaml … KSI-016.yaml
- src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml
- src/uiao/adapters/fedramp_aan_catalog/mappings/slot-06-security-evidence.yaml
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

_ACTIVE_TO_CR26 = {
    "KSI-015": "KSI-SCR-MIT",
    "KSI-016": "KSI-SCR-MON",
}

_RULES_DIR = Path(__file__).resolve().parents[2] / "src" / "uiao" / "ksi" / "rules"


def _load_rule(rule_id: str) -> dict:
    path = _RULES_DIR / f"{rule_id}.yaml"
    assert path.is_file(), f"rule file missing: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Happy path — rule files are well-formed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(_ACTIVE_TO_CR26))
def test_active_rule_file_parses_and_has_required_shape(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert rule["KSI_ID"] == rule_id
    assert rule["Status"] == "active"
    assert rule["Theme"] == "KSI-SCR"
    assert rule["Mappings"]["CR26"] == _ACTIVE_TO_CR26[rule_id]
    assert rule["Mappings"]["NIST_800-53"]
    assert rule["Title"].strip()


def test_rules_cover_exactly_the_two_ksi_scr_controls() -> None:
    covered = {_load_rule(r)["Mappings"]["CR26"] for r in _ACTIVE_TO_CR26}
    assert covered == {"KSI-SCR-MIT", "KSI-SCR-MON"}


@pytest.mark.parametrize("rule_id", sorted(_ACTIVE_TO_CR26))
def test_cr26_id_resolves_in_pinned_snapshot(rule_id: str) -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert _ACTIVE_TO_CR26[rule_id] in snapshot_ids


# ---------------------------------------------------------------------------
# Confidence assertions — both rules high-confidence after phase 5
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(_ACTIVE_TO_CR26))
def test_high_confidence_scr_rules_in_mapping(rule_id: str) -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
    assert rows[rule_id]["confidence"] == "high", (
        f"{rule_id} should be confidence:high (slot-06 binding active); got {rows[rule_id]['confidence']}"
    )


# ---------------------------------------------------------------------------
# Lockstep — rules, mapping companion, and gap list agree
# ---------------------------------------------------------------------------


def test_mapping_companion_includes_every_scr_rule() -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    for rule_id, cr26 in _ACTIVE_TO_CR26.items():
        assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
        assert rows[rule_id]["cr26_controls"] == [cr26]


def test_ksi_scr_is_no_longer_listed_as_a_zero_coverage_gap() -> None:
    mapping = load_mapping()
    gaps = mapping.get("gaps", {})
    assert "KSI-SCR" not in gaps.get("themes_with_zero_local_rules", [])
    zero_controls = set(gaps.get("controls_with_zero_local_rules", []))
    assert not (zero_controls & set(_ACTIVE_TO_CR26.values()))


# ---------------------------------------------------------------------------
# Adapter still reconciles cleanly with the expanded corpus
# ---------------------------------------------------------------------------


def test_validate_mapping_stays_clean_with_scr_rows() -> None:
    findings = validate_mapping()
    assert findings == [], "KSI-SCR CR26 IDs must resolve in the snapshot; got: " + ", ".join(
        f.summary for f in findings
    )


def test_reconcile_stays_clean_with_scr_rules() -> None:
    findings = reconcile()
    assert findings == [], "Expanded KSI corpus should reconcile cleanly; got: " + ", ".join(
        f.summary for f in findings
    )


# ---------------------------------------------------------------------------
# Failure mode — resolution check is meaningful; active rules use slot_binding
# ---------------------------------------------------------------------------


def test_fabricated_ksi_scr_id_does_not_resolve_in_snapshot() -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert "KSI-SCR-ZZZ" not in snapshot_ids


@pytest.mark.parametrize("rule_id", sorted(_ACTIVE_TO_CR26))
def test_active_rule_logic_uses_slot_binding_expression(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    logic = rule["Evaluation"]["Logic"]
    assert "PENDING" not in logic
    assert "slot_binding" in logic
