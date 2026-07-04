"""Conformance tests for the KSI-CED, KSI-INR, and KSI-RPL rules
(ADR-111 / UIAO_137 §6). Phase 4 of the Federal AAN ConMon gap roadmap.

After ADR-111 phase 5 evaluation engine wiring, KSI-023..029 are
``Status: active``; KSI-022 remains ``Status: scaffold`` (AT family pending).

Coverage:
  KSI-022 → KSI-CED-RAT   scaffold  confidence: low   (CP-3/PM-14 partial)
  KSI-023 → KSI-INR-AAR   active    confidence: high  (slot-04 IR-4/8, slot-07 CP-4)
  KSI-024 → KSI-INR-RIR   active    confidence: high  (slot-04 IR-4/6/8)
  KSI-025 → KSI-INR-RPI   active    confidence: high  (slot-04 IR-4/5/8)
  KSI-026 → KSI-RPL-ABO   active    confidence: high  (slot-07 CP-9/CP-2.3)
  KSI-027 → KSI-RPL-ARP   active    confidence: high  (slot-07 CP-2 full plan)
  KSI-028 → KSI-RPL-RRO   active    confidence: high  (slot-07 BIA/CP-2.3)
  KSI-029 → KSI-RPL-TRC   active    confidence: high  (slot-07 CP-4 tabletop)

Companion:
- src/uiao/ksi/rules/KSI-022.yaml … KSI-029.yaml
- src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml
- src/uiao/adapters/fedramp_aan_catalog/mappings/slot-04-telemetry-evidence.yaml
- src/uiao/adapters/fedramp_aan_catalog/mappings/slot-07-continuity-evidence.yaml
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
    "KSI-023": "KSI-INR-AAR",
    "KSI-024": "KSI-INR-RIR",
    "KSI-025": "KSI-INR-RPI",
    "KSI-026": "KSI-RPL-ABO",
    "KSI-027": "KSI-RPL-ARP",
    "KSI-028": "KSI-RPL-RRO",
    "KSI-029": "KSI-RPL-TRC",
}

_SCAFFOLD_TO_CR26 = {
    "KSI-022": "KSI-CED-RAT",
}

_ALL_RULES_TO_CR26 = {**_SCAFFOLD_TO_CR26, **_ACTIVE_TO_CR26}

_THEME_FOR = {
    "KSI-022": "KSI-CED",
    "KSI-023": "KSI-INR",
    "KSI-024": "KSI-INR",
    "KSI-025": "KSI-INR",
    "KSI-026": "KSI-RPL",
    "KSI-027": "KSI-RPL",
    "KSI-028": "KSI-RPL",
    "KSI-029": "KSI-RPL",
}

_HIGH_CONFIDENCE_RULES = set(_ACTIVE_TO_CR26)
_LOW_CONFIDENCE_RULES = {"KSI-022"}

_RULES_DIR = Path(__file__).resolve().parents[2] / "src" / "uiao" / "ksi" / "rules"
_SLOT04 = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "uiao"
    / "adapters"
    / "fedramp_aan_catalog"
    / "mappings"
    / "slot-04-telemetry-evidence.yaml"
)
_SLOT07 = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "uiao"
    / "adapters"
    / "fedramp_aan_catalog"
    / "mappings"
    / "slot-07-continuity-evidence.yaml"
)


def _load_rule(rule_id: str) -> dict:
    path = _RULES_DIR / f"{rule_id}.yaml"
    assert path.is_file(), f"scaffold rule file missing: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Happy path — rule files are well-formed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(_ACTIVE_TO_CR26))
def test_active_rule_file_parses_and_has_required_shape(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert rule["KSI_ID"] == rule_id
    assert rule["Status"] == "active"
    assert rule["Theme"] == _THEME_FOR[rule_id]
    assert rule["Mappings"]["CR26"] == _ACTIVE_TO_CR26[rule_id]
    assert rule["Mappings"]["NIST_800-53"]
    assert rule["Title"].strip()


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_file_parses_and_has_required_shape(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert rule["KSI_ID"] == rule_id
    assert rule["Status"] == "scaffold"
    assert rule["Theme"] == _THEME_FOR[rule_id]
    assert rule["Mappings"]["CR26"] == _SCAFFOLD_TO_CR26[rule_id]
    assert rule["Mappings"]["NIST_800-53"]
    assert rule["Title"].strip()


def test_rules_cover_exactly_the_eight_ced_inr_rpl_controls() -> None:
    covered = {_load_rule(r)["Mappings"]["CR26"] for r in _ALL_RULES_TO_CR26}
    assert covered == {
        "KSI-CED-RAT",
        "KSI-INR-AAR",
        "KSI-INR-RIR",
        "KSI-INR-RPI",
        "KSI-RPL-ABO",
        "KSI-RPL-ARP",
        "KSI-RPL-RRO",
        "KSI-RPL-TRC",
    }


@pytest.mark.parametrize("rule_id", sorted(_ALL_RULES_TO_CR26))
def test_cr26_id_resolves_in_pinned_snapshot(rule_id: str) -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert _ALL_RULES_TO_CR26[rule_id] in snapshot_ids


# ---------------------------------------------------------------------------
# Confidence assertions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(_HIGH_CONFIDENCE_RULES))
def test_high_confidence_rules_in_mapping(rule_id: str) -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
    assert rows[rule_id]["confidence"] == "high", (
        f"{rule_id} should be confidence:high; got {rows[rule_id]['confidence']}"
    )


@pytest.mark.parametrize("rule_id", sorted(_LOW_CONFIDENCE_RULES))
def test_low_confidence_rules_in_mapping(rule_id: str) -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
    assert rows[rule_id]["confidence"] == "low", (
        f"{rule_id} should be confidence:low; got {rows[rule_id]['confidence']}"
    )


# ---------------------------------------------------------------------------
# Lockstep — scaffolds, mapping companion, and gap list agree
# ---------------------------------------------------------------------------


def test_mapping_companion_includes_every_ced_inr_rpl_rule() -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    for rule_id, cr26 in _ALL_RULES_TO_CR26.items():
        assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
        assert rows[rule_id]["cr26_controls"] == [cr26]


def test_ced_inr_rpl_no_longer_listed_as_zero_coverage_gaps() -> None:
    mapping = load_mapping()
    gaps = mapping.get("gaps", {})
    zero_themes = gaps.get("themes_with_zero_local_rules") or []
    assert "KSI-CED" not in zero_themes
    assert "KSI-INR" not in zero_themes
    assert "KSI-RPL" not in zero_themes


def test_ced_inr_rpl_controls_removed_from_zero_coverage_list() -> None:
    mapping = load_mapping()
    gaps = mapping.get("gaps", {})
    zero_controls = set(gaps.get("controls_with_zero_local_rules", []))
    for cr26 in _SCAFFOLD_TO_CR26.values():
        assert cr26 not in zero_controls, f"{cr26} still listed as zero-coverage"


# ---------------------------------------------------------------------------
# Adapter still reconciles cleanly
# ---------------------------------------------------------------------------


def test_validate_mapping_stays_clean_with_phase4_rows() -> None:
    findings = validate_mapping()
    assert findings == [], "Phase 4 CR26 IDs must resolve in the snapshot; got: " + ", ".join(
        f.summary for f in findings
    )


def test_reconcile_stays_clean_with_phase4_rules() -> None:
    findings = reconcile()
    assert findings == [], "Expanded KSI corpus should reconcile cleanly; got: " + ", ".join(
        f.summary for f in findings
    )


# ---------------------------------------------------------------------------
# Slot-07 continuity slot binds Part 11 and covers KSI-RPL
# ---------------------------------------------------------------------------


def test_slot07_exists_and_has_part11_artifact() -> None:
    assert _SLOT07.is_file(), "slot-07-continuity-evidence.yaml is missing"
    slot = yaml.safe_load(_SLOT07.read_text(encoding="utf-8"))
    assert slot["slot_id"] == 7
    artifact_ids = {a["id"] for a in slot.get("artifacts", [])}
    assert "aan-part-11" in artifact_ids, "slot-07 must bind aan-part-11"


def test_slot07_covers_all_four_rpl_controls() -> None:
    slot = yaml.safe_load(_SLOT07.read_text(encoding="utf-8"))
    rpl_controls: set[str] = set()
    for binding in slot.get("bindings", []):
        if binding.get("cr26_ksi_theme") == "KSI-RPL":
            rpl_controls.update(binding.get("cr26_controls", []))
    assert rpl_controls == {"KSI-RPL-ABO", "KSI-RPL-ARP", "KSI-RPL-RRO", "KSI-RPL-TRC"}


def test_slot07_has_inr_aar_binding() -> None:
    slot = yaml.safe_load(_SLOT07.read_text(encoding="utf-8"))
    inr_bindings = [b for b in slot.get("bindings", []) if b.get("cr26_ksi_theme") == "KSI-INR"]
    assert inr_bindings, "slot-07 must have at least one KSI-INR binding (CP-4 AAR)"
    controls = {c for b in inr_bindings for c in b.get("cr26_controls", [])}
    assert "KSI-INR-AAR" in controls


def test_slot07_rpl_bindings_are_high_confidence() -> None:
    slot = yaml.safe_load(_SLOT07.read_text(encoding="utf-8"))
    for binding in slot.get("bindings", []):
        if binding.get("cr26_ksi_theme") == "KSI-RPL":
            assert binding["confidence"] == "high", (
                f"KSI-RPL binding for {binding.get('cr26_controls')} must be confidence:high"
            )


def test_slot07_ced_binding_is_low_confidence() -> None:
    slot = yaml.safe_load(_SLOT07.read_text(encoding="utf-8"))
    ced_bindings = [b for b in slot.get("bindings", []) if b.get("cr26_ksi_theme") == "KSI-CED"]
    assert ced_bindings, "slot-07 must have a KSI-CED binding (CP-3 training)"
    for b in ced_bindings:
        assert b["confidence"] == "low", "KSI-CED-RAT via CP-3 only is confidence:low"


# ---------------------------------------------------------------------------
# Slot-04 extended with KSI-INR bindings
# ---------------------------------------------------------------------------


def test_slot04_has_inr_bindings_for_all_three_controls() -> None:
    slot = yaml.safe_load(_SLOT04.read_text(encoding="utf-8"))
    inr_controls: set[str] = set()
    for binding in slot.get("bindings", []):
        if binding.get("cr26_ksi_theme") == "KSI-INR":
            inr_controls.update(binding.get("cr26_controls", []))
    assert inr_controls == {"KSI-INR-AAR", "KSI-INR-RIR", "KSI-INR-RPI"}, (
        f"slot-04 must bind all three INR controls; got {inr_controls}"
    )


def test_slot04_inr_bindings_are_high_confidence() -> None:
    slot = yaml.safe_load(_SLOT04.read_text(encoding="utf-8"))
    for binding in slot.get("bindings", []):
        if binding.get("cr26_ksi_theme") == "KSI-INR":
            assert binding["confidence"] == "high", (
                f"INR binding for {binding.get('cr26_controls')} must be confidence:high"
            )


# ---------------------------------------------------------------------------
# Failure mode — snapshot resolution check is meaningful
# ---------------------------------------------------------------------------


def test_fabricated_ced_id_does_not_resolve_in_snapshot() -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert "KSI-CED-ZZZ" not in snapshot_ids


def test_fabricated_inr_id_does_not_resolve_in_snapshot() -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert "KSI-INR-ZZZ" not in snapshot_ids


def test_fabricated_rpl_id_does_not_resolve_in_snapshot() -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert "KSI-RPL-ZZZ" not in snapshot_ids


@pytest.mark.parametrize("rule_id", sorted(_ACTIVE_TO_CR26))
def test_active_rule_logic_uses_slot_binding_expression(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    logic = rule["Evaluation"]["Logic"]
    assert "PENDING" not in logic
    assert "slot_binding" in logic


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_logic_is_marked_pending(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert "PENDING" in rule["Evaluation"]["Logic"]
