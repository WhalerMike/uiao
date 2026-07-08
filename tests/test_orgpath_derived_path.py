"""Tests for ADR-127 derived-path enforcement on the Python side.

Three surfaces, one contract:

* ``Codebook.derive_org_path`` — the single source of truth for the
  derivation (Python counterpart of UIAO.OrgPath's ``New-OrgPath``);
* ``DriftEngine`` — a stored ``extensionAttribute15`` that does not
  equal the recomputation is DRIFT-SEMANTIC::derived-path, catching the
  stale-but-well-formed paths the per-facet pattern check cannot see;
* ``DeviceOrgPathPlanner`` — writer parity: the derived path is stamped
  alongside the governance facets, recomputed, never taken from input.
"""

from __future__ import annotations

from uiao.governance.drift_engine import DriftEngine
from uiao.modernization.orgtree.codebook import load_codebook
from uiao.modernization.orgtree.device_orgpath import (
    DeviceFacetAssignment,
    DeviceOrgPathPlanner,
)
from uiao.modernization.orgtree.types import PrincipalSnapshot, Snapshot

_HIERARCHY = {"region": "NCR", "department": "IT", "division": "CyberOps"}
_FULL_PATH = "Region=NCR|Department=IT|Division=CyberOps|"


def _principal(attributes: dict[str, str], principal_id: str = "u-1") -> PrincipalSnapshot:
    return PrincipalSnapshot(
        principal_id=principal_id,
        principal_type="user",
        attributes=attributes,
    )


def _engine() -> DriftEngine:
    return DriftEngine(load_codebook(), adapters={})


def _derived_findings(report):
    return [f for f in report.findings if f.drift_category == "Derived"]


def _scan(attributes: dict[str, str]):
    snapshot = Snapshot(generated_at="2026-07-08T00:00:00Z", principals=(_principal(attributes),))
    return _engine().run(snapshot, dry_run=True)


# ---------------------------------------------------------------------------
# Codebook.derive_org_path
# ---------------------------------------------------------------------------


def test_derive_full_path_with_trailing_delimiter() -> None:
    codebook = load_codebook()
    assert codebook.derive_org_path(_HIERARCHY) == _FULL_PATH


def test_derive_truncates_at_first_unpopulated_facet() -> None:
    codebook = load_codebook()
    assert codebook.derive_org_path({"region": "NCR"}) == "Region=NCR|"
    # Division without department is not a path — contiguous-prefix rule.
    assert codebook.derive_org_path({"region": "NCR", "division": "CyberOps"}) == "Region=NCR|"
    assert codebook.derive_org_path({}) == ""


def test_derive_truncates_at_codebook_invalid_value() -> None:
    # An invalid department is the department facet's own Value-drift
    # finding; the derived path never embeds it.
    codebook = load_codebook()
    values = {"region": "NCR", "department": "NotADept", "division": "CyberOps"}
    assert codebook.derive_org_path(values) == "Region=NCR|"


def test_derive_every_segment_is_terminated() -> None:
    codebook = load_codebook()
    path = codebook.derive_org_path(_HIERARCHY)
    assert path.endswith("|")
    assert path.count("|") == 3


def test_derive_matches_org_path_facet_pattern() -> None:
    codebook = load_codebook()
    org_path = codebook.facet("org_path")
    assert org_path.is_active(codebook.derive_org_path(_HIERARCHY))
    assert org_path.is_active(codebook.derive_org_path({"region": "NCR"}))


# ---------------------------------------------------------------------------
# DriftEngine — DRIFT-SEMANTIC::derived-path
# ---------------------------------------------------------------------------


def test_in_sync_derived_path_emits_no_derived_finding() -> None:
    report = _scan(
        {
            "extensionAttribute1": "NCR",
            "extensionAttribute2": "IT",
            "extensionAttribute3": "CyberOps",
            "extensionAttribute15": _FULL_PATH,
        }
    )
    assert _derived_findings(report) == []


def test_stale_path_after_facet_move_is_derived_drift() -> None:
    # Well-formed path, passes the pattern check — but the user moved
    # from IT to HR and the path was never restamped. Only the
    # reconciliation catches this.
    report = _scan(
        {
            "extensionAttribute1": "NCR",
            "extensionAttribute2": "HR",
            "extensionAttribute15": "Region=NCR|Department=IT|",
        }
    )
    findings = _derived_findings(report)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.drift_class == "DRIFT-SEMANTIC::derived-path"
    assert finding.severity == "P2"
    assert finding.auto_remediate is False
    assert finding.attribute == "extensionAttribute15"
    assert finding.metadata["expected"] == "Region=NCR|Department=HR|"
    assert "stale" in finding.reason


def test_unstamped_path_with_populated_facets_is_derived_drift() -> None:
    report = _scan({"extensionAttribute1": "NCR", "extensionAttribute2": "IT"})
    findings = _derived_findings(report)
    assert len(findings) == 1
    assert findings[0].metadata["expected"] == "Region=NCR|Department=IT|"
    assert "not stamped" in findings[0].reason


def test_missing_trailing_delimiter_named_in_reason() -> None:
    report = _scan(
        {
            "extensionAttribute1": "NCR",
            "extensionAttribute2": "IT",
            "extensionAttribute15": "Region=NCR|Department=IT",
        }
    )
    findings = _derived_findings(report)
    assert len(findings) == 1
    assert "trailing" in findings[0].reason
    # The malformed value also fires the typed-facet Format check.
    format_findings = [f for f in report.findings if f.drift_category == "Format" and f.facet == "org_path"]
    assert len(format_findings) == 1


def test_empty_facets_and_empty_slot_are_clean() -> None:
    report = _scan({})
    assert _derived_findings(report) == []


def test_invalid_hierarchy_value_truncates_expectation() -> None:
    # Department invalid → expected path is Region=NCR| only; the stored
    # full path is divergent, and the department raises its own Value drift.
    report = _scan(
        {
            "extensionAttribute1": "NCR",
            "extensionAttribute2": "BogusDept",
            "extensionAttribute15": "Region=NCR|Department=BogusDept|",
        }
    )
    findings = _derived_findings(report)
    assert len(findings) == 1
    assert findings[0].metadata["expected"] == "Region=NCR|"
    value_findings = [f for f in report.findings if f.drift_category == "Value" and f.facet == "department"]
    assert len(value_findings) == 1


# ---------------------------------------------------------------------------
# DeviceOrgPathPlanner — writer parity
# ---------------------------------------------------------------------------


def _plan(facet_values: dict[str, str], disposition: str = "ENTRA-DEVICE"):
    planner = DeviceOrgPathPlanner(load_codebook())
    return planner.plan_device(
        DeviceFacetAssignment(device_id="dev-1", disposition=disposition, facet_values=facet_values)
    )


def _derived_ops(plan):
    return [op for op in plan.writes if op.metadata.get("derived")]


def test_planner_stamps_derived_path_on_entra_plane() -> None:
    plan = _plan(_HIERARCHY)
    ops = _derived_ops(plan)
    assert len(ops) == 1
    assert ops[0].facet == "org_path"
    assert ops[0].attribute == "extensionAttribute15"
    assert ops[0].value == _FULL_PATH


def test_planner_stamps_orgpath_tag_on_arm_plane() -> None:
    plan = _plan(_HIERARCHY, disposition="ARC-SERVER")
    ops = _derived_ops(plan)
    assert len(ops) == 1
    assert ops[0].attribute == "tags.OrgPath"
    assert ops[0].value == _FULL_PATH


def test_planner_ignores_caller_supplied_org_path() -> None:
    # The derived path is never hand-authored: caller input is discarded
    # and the recomputation wins.
    plan = _plan({**_HIERARCHY, "org_path": "Region=FAKE|"})
    ops = [op for op in plan.writes if op.facet == "org_path"]
    assert len(ops) == 1
    assert ops[0].value == _FULL_PATH


def test_planner_skips_derived_path_when_no_hierarchy_facet_supplied() -> None:
    # A partial assignment that never mentions the hierarchy must not
    # clear a previously stamped path.
    plan = _plan({"clearance_level": "Secret"})
    assert _derived_ops(plan) == []


def test_planner_partial_hierarchy_stamps_contiguous_prefix() -> None:
    plan = _plan({"region": "NCR", "department": "IT"})
    ops = _derived_ops(plan)
    assert len(ops) == 1
    assert ops[0].value == "Region=NCR|Department=IT|"


def test_skip_disposition_emits_no_derived_write() -> None:
    plan = _plan(_HIERARCHY, disposition="STAY-AD-DC")
    assert plan.plane == "skip"
    assert plan.writes == ()
