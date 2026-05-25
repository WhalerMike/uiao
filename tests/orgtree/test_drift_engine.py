"""Tests for the Model C drift engine orchestrator (ADR-084 §C5)."""

from __future__ import annotations


from uiao.adapters.entra_admin_units import EntraAdminUnitAdapter
from uiao.adapters.entra_dynamic_groups import EntraDynamicGroupAdapter
from uiao.adapters.entra_policy_targeting import EntraPolicyTargetAdapter
from uiao.governance.drift_engine import DriftEngine
from uiao.modernization.orgtree.admin_units import AdminUnitRegistry
from uiao.modernization.orgtree.drift_engine_config import (
    DriftEngineConfig,
    FacetRemediationPolicy,
    default_drift_engine_config,
)
from uiao.modernization.orgtree.dynamic_groups import DynamicGroupLibrary
from uiao.modernization.orgtree.policy_targeting import PolicyTargetLibrary
from uiao.modernization.orgtree.types import (
    CompositionSpec,
    FacetPredicate,
    PrincipalSnapshot,
    Snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _principal(pid: str = "u-1", **attrs: str) -> PrincipalSnapshot:
    base = {
        "extensionAttribute1": "EASTUS",
        "extensionAttribute2": "IT",
        "extensionAttribute3": "InfraOps",
        "extensionAttribute4": "Engineer",
        "extensionAttribute5": "CC-BAL",
        "extensionAttribute6": "Employee",
        "extensionAttribute7": "2024-01-15",
        "extensionAttribute8": "",
        "extensionAttribute9": "Secret",
        "extensionAttribute10": "Standard",
    }
    base.update(attrs)
    return PrincipalSnapshot(principal_id=pid, principal_type="user", attributes=base)


def _empty_snapshot(*principals: PrincipalSnapshot) -> Snapshot:
    return Snapshot.now(principals=tuple(principals))


def _empty_adapters(codebook):
    return {
        "dynamic_groups": EntraDynamicGroupAdapter(DynamicGroupLibrary.from_specs(codebook, [])),
        "admin_units": EntraAdminUnitAdapter(AdminUnitRegistry.from_specs(codebook, [])),
        "policy_targeting": EntraPolicyTargetAdapter(PolicyTargetLibrary.from_specs(codebook, [])),
    }


# ---------------------------------------------------------------------------
# Config — per-facet remediation policies + halt_on_critical
# ---------------------------------------------------------------------------


def test_default_config_is_dry_run_halts_on_p1():
    config = default_drift_engine_config()
    assert config.dry_run is True
    assert config.halt_on_critical == "P1"


def test_facet_policy_defaults_no_auto():
    config = DriftEngineConfig()
    policy = config.policy_for("department")
    assert policy.auto_remediate_value_drift is False
    assert policy.auto_remediate_phantom_drift is False


def test_critical_fires_detects_p1_above_p2_threshold():
    config = DriftEngineConfig(halt_on_critical="P2")
    assert config.critical_fires(["P1"]) is True
    assert config.critical_fires(["P3", "P4"]) is False


# ---------------------------------------------------------------------------
# Per-facet drift classification (UIAO_163 v2.0 categories)
# ---------------------------------------------------------------------------


def test_clean_principal_emits_no_findings(codebook_model_c):
    """A principal with every facet valid produces zero per-principal findings."""
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(_principal()))
    # Only Orphan findings (every enum value with no principal) — but our
    # one principal hits a representative value in each enum, so there
    # WILL be Orphan findings for the unused values.
    per_principal_findings = [f for f in report.findings if f.drift_category != "Orphan"]
    assert per_principal_findings == []


def test_value_drift_unknown_enum(codebook_model_c):
    p = _principal(extensionAttribute2="BogusDept")
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    value_findings = [f for f in report.findings if f.drift_category == "Value"]
    assert any(f.facet == "department" and "BogusDept" in (f.observed_value or "") for f in value_findings)
    bad = next(f for f in value_findings if f.facet == "department")
    assert bad.severity == "P2"
    assert bad.drift_class == "DRIFT-SEMANTIC"


def test_phantom_drift_deprecated_with_replacement(codebook_model_c):
    p = _principal(extensionAttribute3="OldCyber")  # deprecated → CyberOps
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    phantoms = report.findings_by_category("Phantom")
    assert len(phantoms) == 1
    assert phantoms[0].metadata["replaced_by"] == "CyberOps"
    assert phantoms[0].severity == "P3"


def test_format_drift_typed_pattern_violation(codebook_model_c):
    p = _principal(extensionAttribute7="01/15/2024")  # US format, fails ISO regex
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    format_findings = [f for f in report.findings if f.drift_category == "Format"]
    assert len(format_findings) == 1
    assert format_findings[0].facet == "hire_date"
    assert format_findings[0].severity == "P1"
    assert format_findings[0].drift_class == "DRIFT-SCHEMA"


def test_typed_facet_empty_when_allow_empty_is_clean(codebook_model_c):
    """term_date allow_empty=True — empty string is NOT Format Drift."""
    p = _principal(extensionAttribute8="")
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    assert not any(f.facet == "term_date" and f.drift_category == "Format" for f in report.findings)


def test_reserved_facet_with_value_is_value_drift(codebook_model_c):
    p = _principal()
    # Override the reserved slot to a non-empty value.
    new_attrs = dict(p.attributes)
    new_attrs["extensionAttribute11"] = "rogue"
    p = PrincipalSnapshot(principal_id=p.principal_id, principal_type=p.principal_type, attributes=new_attrs)
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    reserved_findings = [f for f in report.findings if f.facet == "reserved_11"]
    assert len(reserved_findings) == 1
    assert reserved_findings[0].drift_category == "Value"


def test_orphan_drift_emitted_for_unused_enumeration_values(codebook_model_c):
    """An enum value with zero matching principals surfaces as Orphan."""
    p = _principal(extensionAttribute2="IT")
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    orphans = report.findings_by_category("Orphan")
    # department.enumeration has IT, HR, Finance, Legal — only IT is used
    # → 3 orphans for department alone.
    orphaned_dept = [o for o in orphans if o.facet == "department"]
    assert len(orphaned_dept) == 3
    assert {o.observed_value for o in orphaned_dept} == {"HR", "Finance", "Legal"}


def test_severity_counts(codebook_model_c):
    p = _principal(
        extensionAttribute2="BogusDept",  # Value (P2)
        extensionAttribute7="bad-date",  # Format (P1)
    )
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    counts = report.severity_counts
    assert counts.get("P1", 0) >= 1
    assert counts.get("P2", 0) >= 1


# ---------------------------------------------------------------------------
# Halt-on-critical
# ---------------------------------------------------------------------------


def test_halt_on_critical_skips_remediation(codebook_model_c):
    """A P1 finding halts Remediate even when dry_run=False."""
    p = _principal(extensionAttribute7="bad-date")  # Format → P1
    # Library with one missing group → adapter would normally CREATE.
    lib = DynamicGroupLibrary.from_specs(
        codebook_model_c,
        [
            (
                "OrgTree-Test",
                "Region",
                CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),)),
                "test",
            )
        ],
    )
    recorded = []
    adapter = EntraDynamicGroupAdapter(lib, transport=lambda *a: recorded.append(a) or {})
    config = DriftEngineConfig(dry_run=False, halt_on_critical="P1")
    engine = DriftEngine(codebook_model_c, {"dynamic_groups": adapter}, config)
    report = engine.run(_empty_snapshot(p))
    assert report.halted is True
    # Nothing was dispatched to Graph despite dry_run=False
    assert recorded == []
    # apply_results recorded what WOULD have been planned, as dry
    assert report.apply_results["dynamic_groups"].dry_run is True


def test_no_halt_when_only_p2_p3_findings(codebook_model_c):
    """Value (P2) + Phantom (P3) findings do NOT halt at default P1 threshold."""
    p = _principal(extensionAttribute2="BogusDept")  # Value → P2
    config = DriftEngineConfig(dry_run=True, halt_on_critical="P1")
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c), config)
    report = engine.run(_empty_snapshot(p))
    # Per-principal Value finding doesn't halt
    assert report.halted is False


# ---------------------------------------------------------------------------
# Per-facet auto-remediate config
# ---------------------------------------------------------------------------


def test_value_drift_marked_auto_when_facet_policy_opts_in(codebook_model_c):
    p = _principal(extensionAttribute2="BogusDept")
    config = DriftEngineConfig(facet_policies={"department": FacetRemediationPolicy(auto_remediate_value_drift=True)})
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c), config)
    report = engine.run(_empty_snapshot(p))
    dept_value_finding = next(f for f in report.findings if f.facet == "department" and f.drift_category == "Value")
    assert dept_value_finding.auto_remediate is True


def test_value_drift_not_auto_for_facet_without_policy(codebook_model_c):
    p = _principal(extensionAttribute2="BogusDept")
    # No facet_policies → all default to False
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    finding = next(f for f in report.findings if f.facet == "department" and f.drift_category == "Value")
    assert finding.auto_remediate is False


# ---------------------------------------------------------------------------
# Orchestration over adapters (per-adapter plan + apply)
# ---------------------------------------------------------------------------


def test_engine_plans_dynamic_groups_from_snapshot(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(
        codebook_model_c,
        [
            (
                "OrgTree-NCR-Users",
                "Region",
                CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),)),
                "NCR",
            )
        ],
    )
    adapter = EntraDynamicGroupAdapter(lib)
    engine = DriftEngine(codebook_model_c, {"dynamic_groups": adapter})
    # No groups in snapshot → adapter plans 1 create
    report = engine.run(_empty_snapshot())
    assert report.apply_results["dynamic_groups"].planned_count == 1


def test_engine_plans_admin_units_from_snapshot(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(
        codebook_model_c,
        [
            (
                "AU-Test",
                CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),)),
                "test AU",
                (),
            )
        ],
    )
    adapter = EntraAdminUnitAdapter(reg)
    engine = DriftEngine(codebook_model_c, {"admin_units": adapter})
    snap = Snapshot.now(admin_units=())
    report = engine.run(snap)
    assert report.apply_results["admin_units"].planned_count == 1


def test_engine_dispatches_when_dry_run_false_and_not_halted(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(
        codebook_model_c,
        [
            (
                "OrgTree-Test",
                "Region",
                CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),)),
                "test",
            )
        ],
    )
    recorded = []
    adapter = EntraDynamicGroupAdapter(lib, transport=lambda *a: recorded.append(a) or {})
    config = DriftEngineConfig(dry_run=False)
    engine = DriftEngine(codebook_model_c, {"dynamic_groups": adapter}, config)
    # No P1 findings → engine doesn't halt
    p = _principal(extensionAttribute2="HR")  # Value Drift? No — HR is valid
    report = engine.run(_empty_snapshot(p))
    assert report.halted is False
    # Adapter dispatched the create
    assert len(recorded) == 1
    assert report.apply_results["dynamic_groups"].sent_count == 1


def test_engine_dry_run_overrides_config(codebook_model_c):
    config = DriftEngineConfig(dry_run=False)
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c), config)
    report = engine.run(_empty_snapshot(_principal()), dry_run=True)
    assert report.dry_run is True


# ---------------------------------------------------------------------------
# DriftScanReport shape
# ---------------------------------------------------------------------------


def test_scan_report_to_dict_roundtrip(codebook_model_c):
    p = _principal(extensionAttribute2="BogusDept")
    engine = DriftEngine(codebook_model_c, _empty_adapters(codebook_model_c))
    report = engine.run(_empty_snapshot(p))
    finding = next(iter(report.findings))
    d = finding.to_dict()
    assert d["facet"] == finding.facet
    assert d["drift_category"] == finding.drift_category
    assert d["severity"] == finding.severity
