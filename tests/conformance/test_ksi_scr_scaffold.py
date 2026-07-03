"""Conformance tests for the KSI-SCR scaffold rules (ADR-111 / UIAO_137 §5).

KSI-015 and KSI-016 are scaffold rules that seed the CR26 KSI-SCR (Supply
Chain Risk) theme — the first non-CMT new theme scaffolded in Phase 2.
They are intentionally *not yet evaluable* (``Status: scaffold``); these
tests assert the scaffolds are well-formed, map to real snapshot controls,
and stay in lockstep with the UIAO_137 mapping companion.

The KSI-SCR rules carry ``confidence: low`` because the evidence-engine
wiring for SCRM telemetry is pending — unlike KSI-CMT which was upgraded
to ``high`` after the Part 12 VER contract landed.

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

_SCAFFOLD_TO_CR26 = {
    "KSI-015": "KSI-SCR-MIT",
    "KSI-016": "KSI-SCR-MON",
}

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
    assert rule["Theme"] == "KSI-SCR"
    assert rule["Mappings"]["CR26"] == _SCAFFOLD_TO_CR26[rule_id]
    assert rule["Mappings"]["NIST_800-53"]
    assert rule["Title"].strip()


def test_scaffolds_cover_exactly_the_two_ksi_scr_controls() -> None:
    covered = {_load_rule(r)["Mappings"]["CR26"] for r in _SCAFFOLD_TO_CR26}
    assert covered == {"KSI-SCR-MIT", "KSI-SCR-MON"}


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_cr26_id_resolves_in_pinned_snapshot(rule_id: str) -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert _SCAFFOLD_TO_CR26[rule_id] in snapshot_ids


# ---------------------------------------------------------------------------
# Lockstep — scaffolds, mapping companion, and gap list agree
# ---------------------------------------------------------------------------


def test_mapping_companion_includes_every_scr_scaffold() -> None:
    mapping = load_mapping()
    rows = {row["local_rule"]: row for row in mapping["mappings"]}
    for rule_id, cr26 in _SCAFFOLD_TO_CR26.items():
        assert rule_id in rows, f"{rule_id} missing from ksi-mapping.yaml"
        assert rows[rule_id]["cr26_controls"] == [cr26]
        # KSI-SCR scaffolds carry confidence: low — evidence-engine wiring pending.
        assert rows[rule_id]["confidence"] == "low"


def test_ksi_scr_is_no_longer_listed_as_a_zero_coverage_gap() -> None:
    mapping = load_mapping()
    gaps = mapping.get("gaps", {})
    assert "KSI-SCR" not in gaps.get("themes_with_zero_local_rules", [])
    zero_controls = set(gaps.get("controls_with_zero_local_rules", []))
    assert not (zero_controls & set(_SCAFFOLD_TO_CR26.values()))


# ---------------------------------------------------------------------------
# Adapter still reconciles cleanly with the expanded corpus
# ---------------------------------------------------------------------------


def test_validate_mapping_stays_clean_with_scr_scaffold_rows() -> None:
    findings = validate_mapping()
    assert findings == [], "Scaffold CR26 IDs must resolve in the snapshot; got: " + ", ".join(
        f.summary for f in findings
    )


def test_reconcile_stays_clean_with_scr_rules() -> None:
    findings = reconcile()
    assert findings == [], "Expanded KSI corpus should reconcile cleanly; got: " + ", ".join(
        f.summary for f in findings
    )


# ---------------------------------------------------------------------------
# Failure mode — resolution check is meaningful; scaffolds are non-evaluable
# ---------------------------------------------------------------------------


def test_fabricated_ksi_scr_id_does_not_resolve_in_snapshot() -> None:
    catalog = load_catalog(default_snapshot_dir())
    snapshot_ids = {c["id"] for ctls in enumerate_ksi_controls(catalog).values() for c in ctls}
    assert "KSI-SCR-ZZZ" not in snapshot_ids


@pytest.mark.parametrize("rule_id", sorted(_SCAFFOLD_TO_CR26))
def test_scaffold_logic_is_marked_pending_not_evaluable(rule_id: str) -> None:
    rule = _load_rule(rule_id)
    assert "PENDING" in rule["Evaluation"]["Logic"]
