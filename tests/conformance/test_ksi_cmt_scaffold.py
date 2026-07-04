"""Conformance tests for the KSI-CMT rules (ADR-111 / FINDING-004 §4).

KSI-011..014 seed the CR26 KSI-CMT (Change Management) theme and are now
``Status: active`` — the evaluation engine was wired in ADR-111 phase 5
once the VER evidence contract was fulfilled by the Part 12
(SBOM/VDR/VEX pipeline) bound to slot-06-security-evidence.yaml and
confidence upgraded from low to high.

These tests assert the rules are well-formed, map to real snapshot
controls, carry concrete slot-binding Logic expressions, and stay in
lockstep with the UIAO_137 mapping companion.

Companion:
- src/uiao/ksi/rules/KSI-011.yaml … KSI-014.yaml
- src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml
- src/uiao/canon/specs/fedramp-cr26-ksi-mapping.md (UIAO_137)
- src/uiao/adapters/fedramp_aan_catalog/mappings/slot-06-security-evidence.yaml
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

# The four CR26 KSI-CMT controls and the active rule that claims each.
_SCAFFOLD_TO_CR26 = {
    "KSI-011": "KSI-CMT-LMC",
    "KSI-012": "KSI-CMT-RMV",
    "KSI-013": "KSI-CMT-RVP",
    "KSI-014": "KSI-CMT-VTD",
}

_RULES_DIR = Path(__file__).resolve().parents[2] / "src" / "uiao" / "ksi" / "rules"


def _load_rule(rule_id: str) -> dict:
    path = _RULES_DIR / f"{rule_id}.yaml"
    assert path.is_file(), f"scaffold rule file missing: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Happy path — the scaffold rule files are well-formed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_file_parses_and_has_required_shape(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert rule["KSI_ID"] == rule_id
    assert rule["Status"] == "active"
    assert rule["Theme"] == "KSI-CMT"
    assert rule["Mappings"]["CR26"] == _SCAFFOLD_TO_CR26[rule_id]
    assert rule["Mappings"]["NIST_800-53"]
    assert rule["Title"].strip()


def test_scaffolds_cover_exactly_the_four_ksi_cmt_controls() -> None:
    covered = {_load_rule(r)["Mappings"]["CR26"] for r in _SCAFFOLD_TO_CR26}
    assert covered == {"KSI-CMT-LMC", "KSI-CMT-RMV", "KSI-CMT-RVP", "KSI-CMT-VTD"}


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_cr26_id_resolves_in_pinned_snapshot(rule_id: str) -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert _SCAFFOLD_TO_CR26[rule_id] in snapshot_ids


# ---------------------------------------------------------------------------
# Lockstep — scaffolds, mapping companion, and gap list agree
# ---------------------------------------------------------------------------


def test_mapping_companion_includes_every_scaffold() -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    for rule_id, cr26 in _SCAFFOLD_TO_CR26.items():
        assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
        assert rows[rule_id]["cr26_controls"] == [cr26]
        # Phase 1 (2026-07-03): confidence upgraded low → high after Part 12
        # VER evidence contract bound to slot-06-security-evidence.yaml.
        assert rows[rule_id]["confidence"] == "high"


def test_ksi_cmt_is_no_longer_listed_as_a_zero_coverage_gap() -> None:
    mapping = load_mapping()
    gaps = mapping.get("gaps", {})
    assert "KSI-CMT" not in gaps.get("themes_with_zero_local_rules", [])
    zero_controls = set(gaps.get("controls_with_zero_local_rules", []))
    assert not (zero_controls & set(_SCAFFOLD_TO_CR26.values()))


# ---------------------------------------------------------------------------
# Adapter still reconciles cleanly with the expanded corpus
# ---------------------------------------------------------------------------


def test_validate_mapping_stays_clean_with_scaffold_rows() -> None:
    findings = validate_mapping()
    assert findings == [], "Scaffold CR26 IDs must resolve in the snapshot; got: " + ", ".join(
        f.summary for f in findings
    )


def test_reconcile_stays_clean_with_expanded_rule_corpus() -> None:
    findings = reconcile()
    assert findings == [], "Expanded KSI corpus should reconcile cleanly; got: " + ", ".join(
        f.summary for f in findings
    )


# ---------------------------------------------------------------------------
# Failure mode — the resolution check is meaningful, and scaffolds are
# explicitly marked non-evaluable
# ---------------------------------------------------------------------------


def test_fabricated_cr26_id_does_not_resolve_in_snapshot() -> None:
    # Guards that the resolution assertions above are not vacuous: a
    # made-up KSI-CMT control must NOT be present in the pinned snapshot.
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert "KSI-CMT-ZZZ" not in snapshot_ids


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_active_rule_logic_uses_slot_binding_expression(rule_id: str) -> None:
    # Active rules must carry a concrete slot-binding Logic expression,
    # not the PENDING placeholder.
    rule = _load_rule(rule_id)
    logic = rule["Evaluation"]["Logic"]
    assert "PENDING" not in logic
    assert "slot_binding" in logic
