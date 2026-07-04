"""Unit tests for the KSI slot-evidence evaluator (ADR-111)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uiao.ksi.slot_evaluator import evaluate_rule, evaluate_slot

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_HIGH_BINDING: dict = {
    "slot_id": "slot-06",
    "confidence": "high",
    "artifact_refs": ["aan-part-12"],
}

_LOW_BINDING: dict = {
    "slot_id": "slot-06",
    "confidence": "low",
    "artifact_refs": ["aan-part-12"],
}

_BINDING_INDEX_HIGH: dict = {"KSI-CMT-LMC": [_HIGH_BINDING]}
_BINDING_INDEX_LOW: dict = {"KSI-CMT-LMC": [_LOW_BINDING]}
_BINDING_INDEX_EMPTY: dict = {}

_ACTIVE_RULE: dict = {
    "KSI_ID": "KSI-011",
    "Status": "active",
    "Evaluation": {"Logic": "IF slot_binding(KSI-CMT-LMC, confidence=high) THEN PASS ELSE FAIL"},
}

_SCAFFOLD_RULE: dict = {
    "KSI_ID": "KSI-020",
    "Status": "scaffold",
    "Evaluation": {"Logic": "PENDING — scaffold"},
}

_MAPPING_ROW_SINGLE: dict = {"local_rule": "KSI-011", "cr26_controls": ["KSI-CMT-LMC"]}
_MAPPING_ROW_EMPTY: dict = {"local_rule": "KSI-011", "cr26_controls": []}
_MAPPING_ROW_MULTI: dict = {
    "local_rule": "KSI-XXX",
    "cr26_controls": ["KSI-CMT-LMC", "KSI-CMT-RMV"],
}


# ---------------------------------------------------------------------------
# evaluate_slot
# ---------------------------------------------------------------------------


def test_evaluate_slot_returns_pass_for_high_confidence() -> None:
    assert evaluate_slot("KSI-CMT-LMC", _BINDING_INDEX_HIGH) == "pass"


def test_evaluate_slot_returns_fail_for_low_confidence_only() -> None:
    assert evaluate_slot("KSI-CMT-LMC", _BINDING_INDEX_LOW) == "fail"


def test_evaluate_slot_returns_inconclusive_when_no_binding() -> None:
    assert evaluate_slot("KSI-CMT-LMC", _BINDING_INDEX_EMPTY) == "inconclusive"


def test_evaluate_slot_returns_inconclusive_for_unknown_control() -> None:
    assert evaluate_slot("KSI-ZZZ-ZZZ", _BINDING_INDEX_HIGH) == "inconclusive"


def test_evaluate_slot_pass_when_mixed_confidence_includes_high() -> None:
    index = {"KSI-CMT-LMC": [_LOW_BINDING, _HIGH_BINDING]}
    assert evaluate_slot("KSI-CMT-LMC", index) == "pass"


def test_evaluate_slot_custom_require_confidence() -> None:
    assert evaluate_slot("KSI-CMT-LMC", _BINDING_INDEX_LOW, require_confidence="low") == "pass"


# ---------------------------------------------------------------------------
# evaluate_rule — scaffold raises ValueError
# ---------------------------------------------------------------------------


def test_evaluate_rule_raises_for_scaffold() -> None:
    with pytest.raises(ValueError, match="scaffold"):
        evaluate_rule(_SCAFFOLD_RULE, _MAPPING_ROW_SINGLE, _BINDING_INDEX_HIGH)


# ---------------------------------------------------------------------------
# evaluate_rule — active rule verdicts
# ---------------------------------------------------------------------------


def test_evaluate_rule_pass_with_high_binding() -> None:
    assert evaluate_rule(_ACTIVE_RULE, _MAPPING_ROW_SINGLE, _BINDING_INDEX_HIGH) == "pass"


def test_evaluate_rule_fail_with_low_binding_only() -> None:
    assert evaluate_rule(_ACTIVE_RULE, _MAPPING_ROW_SINGLE, _BINDING_INDEX_LOW) == "fail"


def test_evaluate_rule_inconclusive_with_no_binding() -> None:
    assert evaluate_rule(_ACTIVE_RULE, _MAPPING_ROW_SINGLE, _BINDING_INDEX_EMPTY) == "inconclusive"


def test_evaluate_rule_inconclusive_when_cr26_list_empty() -> None:
    assert evaluate_rule(_ACTIVE_RULE, _MAPPING_ROW_EMPTY, _BINDING_INDEX_HIGH) == "inconclusive"


# ---------------------------------------------------------------------------
# evaluate_rule — multiple CR26 controls
# ---------------------------------------------------------------------------


def test_evaluate_rule_fail_when_one_control_lacks_high_binding() -> None:
    index = {
        "KSI-CMT-LMC": [_HIGH_BINDING],
        "KSI-CMT-RMV": [_LOW_BINDING],
    }
    rule = {**_ACTIVE_RULE, "Evaluation": {"Logic": "IF slot_binding(...) THEN PASS ELSE FAIL"}}
    assert evaluate_rule(rule, _MAPPING_ROW_MULTI, index) == "fail"


def test_evaluate_rule_pass_when_all_controls_have_high_binding() -> None:
    index = {
        "KSI-CMT-LMC": [_HIGH_BINDING],
        "KSI-CMT-RMV": [_HIGH_BINDING],
    }
    rule = {**_ACTIVE_RULE}
    assert evaluate_rule(rule, _MAPPING_ROW_MULTI, index) == "pass"


def test_evaluate_rule_inconclusive_when_all_controls_lack_binding() -> None:
    index: dict = {}
    rule = {**_ACTIVE_RULE}
    assert evaluate_rule(rule, _MAPPING_ROW_MULTI, index) == "inconclusive"


def test_evaluate_rule_fail_when_one_control_missing_entirely() -> None:
    index = {"KSI-CMT-LMC": [_HIGH_BINDING]}
    rule = {**_ACTIVE_RULE}
    assert evaluate_rule(rule, _MAPPING_ROW_MULTI, index) == "fail"


# ---------------------------------------------------------------------------
# Integration — evaluate_rule against real bundled slot data (KSI-011..014)
# ---------------------------------------------------------------------------

_SLOTS_DIR = Path(__file__).resolve().parents[1] / "src" / "uiao" / "adapters" / "fedramp_aan_catalog" / "mappings"

_RULES_DIR = Path(__file__).resolve().parents[1] / "src" / "uiao" / "ksi" / "rules"


def _build_binding_index() -> dict:
    index: dict = {}
    for slot_file in sorted(_SLOTS_DIR.glob("slot-*.yaml")):
        slot = yaml.safe_load(slot_file.read_text(encoding="utf-8"))
        slot_id = f"slot-{slot['slot_id']:02d}"
        for binding in slot.get("bindings", []):
            entry = {
                "slot_id": slot_id,
                "confidence": binding.get("confidence", "low"),
                "artifact_refs": [a.get("id", "") for a in slot.get("artifacts", [])],
            }
            for cr26 in binding.get("cr26_controls", []):
                index.setdefault(cr26, []).append(entry)
    return index


@pytest.mark.parametrize(
    "rule_id,cr26,slot",
    [
        ("KSI-011", "KSI-CMT-LMC", "slot-06"),
        ("KSI-012", "KSI-CMT-RMV", "slot-06"),
        ("KSI-013", "KSI-CMT-RVP", "slot-06"),
        ("KSI-014", "KSI-CMT-VTD", "slot-06"),
        ("KSI-015", "KSI-SCR-MIT", "slot-06"),
        ("KSI-016", "KSI-SCR-MON", "slot-06"),
        ("KSI-020", "KSI-PIY-RSD", "slot-05"),
    ],
)
def test_active_rules_pass_with_real_slot_data(rule_id: str, cr26: str, slot: str) -> None:
    rule = yaml.safe_load((_RULES_DIR / f"{rule_id}.yaml").read_text(encoding="utf-8"))
    row = {"local_rule": rule_id, "cr26_controls": [cr26]}
    index = _build_binding_index()
    result = evaluate_rule(rule, row, index)
    assert result == "pass", (
        f"{rule_id} expected pass with real slot data; got {result!r}. "
        f"Check {slot}-*-evidence.yaml bindings for {cr26}."
    )


def test_scaffold_rule_raises_with_real_slot_data() -> None:
    # KSI-022 (KSI-CED-RAT) remains scaffold — AT-family LMS evidence not yet machine-readable.
    rule = yaml.safe_load((_RULES_DIR / "KSI-022.yaml").read_text(encoding="utf-8"))
    row = {"local_rule": "KSI-022", "cr26_controls": ["KSI-CED-RAT"]}
    index = _build_binding_index()
    with pytest.raises(ValueError, match="scaffold"):
        evaluate_rule(rule, row, index)
