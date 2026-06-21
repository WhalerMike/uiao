"""Tests for the Phase-3 GPO → OrgPath migration planner.

Pure/offline: drives the planner from Phase-1 fixtures and asserts the
scope-target (OU intent → recommended group) and the per-bucket Intune
remediation rollup.

Canon reference: GPO settings analyzer (Phase 3).
"""

from __future__ import annotations

from pathlib import Path

from uiao.adapters.intune_gpo_analytics import SettingMapping, apply_mdm_verdicts
from uiao.adapters.modernization.active_directory.gpo_analytics import (
    analyze_backup,
    parse_gpo_report_file,
)
from uiao.adapters.modernization.active_directory.gpo_orgpath_plan import (
    build_migration_plan,
    build_plans,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "gpo" / "backup"
_ADMIN = _FIXTURES / "{A1111111-1111-1111-1111-111111111111}" / "gpreport.xml"
_SECURITY = _FIXTURES / "{B2222222-2222-2222-2222-222222222222}" / "gpreport.xml"
_PREFS = _FIXTURES / "{C3333333-3333-3333-3333-333333333333}" / "gpreport.xml"


def test_functional_ou_recommends_facet_scoped_group() -> None:
    plan = build_migration_plan(parse_gpo_report_file(_ADMIN))
    assert plan.gpo_name == "Finance Workstations Policy"
    assert len(plan.scope_targets) == 1
    target = plan.scope_targets[0]
    assert target.scope_level == "ou"
    assert target.ou_name == "Finance"
    assert target.intent == "functional"
    assert target.recommended_group == "OrgTree-Finance-Devices"


def test_admin_template_remediation_is_settings_catalog() -> None:
    plan = build_migration_plan(parse_gpo_report_file(_ADMIN))
    assert plan.total_settings == 3
    assert plan.headline_difficulty == "csp-mappable"
    assert len(plan.remediations) == 1
    rem = plan.remediations[0]
    assert rem.portability_class == "csp-mappable"
    assert rem.count == 3
    assert rem.intune_mechanism == "Intune Settings Catalog profile"
    assert rem.action == "port"


def test_domain_linked_gpo_is_not_ou_scoped() -> None:
    plan = build_migration_plan(parse_gpo_report_file(_SECURITY))
    target = plan.scope_targets[0]
    assert target.scope_level == "domain"
    assert target.ou_name == ""
    assert target.recommended_group == ""
    # Security baseline → partial bucket → per-setting review mechanism.
    rem = plan.remediations[0]
    assert rem.portability_class == "partial"
    assert rem.action == "port-with-review"


def test_disabled_link_excluded_enabled_link_kept() -> None:
    # The prefs/scripts GPO links Engineering (enabled) + Sales (disabled).
    plan = build_migration_plan(parse_gpo_report_file(_PREFS))
    names = {t.som_name for t in plan.scope_targets}
    assert names == {"Engineering"}
    # Scripts + drive maps → needs-platform-script bucket.
    assert plan.remediations[0].portability_class == "needs-platform-script"
    assert plan.remediations[0].intune_mechanism == "Intune platform script / Proactive Remediation"


def test_remediations_are_hardest_first() -> None:
    analysis = analyze_backup(_FIXTURES)
    mixed = next(r for r in analysis.reports if r.name == "Mixed Estate Policy")
    plan = build_migration_plan(mixed)
    # Mixed GPO has csp-mappable + review-required + needs-different-mechanism;
    # the hardest (review-required) must lead.
    assert plan.remediations[0].portability_class == "review-required"
    assert plan.headline_difficulty == "review-required"


def test_plan_consumes_phase2_enriched_report() -> None:
    # After the Phase-2 join flips a setting to no-csp, the plan's remediation
    # rollup reflects the authoritative bucket.
    report = parse_gpo_report_file(_ADMIN)
    enriched = apply_mdm_verdicts(report, [SettingMapping("Turn off Autoplay", False)])
    plan = build_migration_plan(enriched)
    buckets = {r.portability_class: r.count for r in plan.remediations}
    assert buckets.get("no-csp") == 1
    assert buckets.get("csp-mappable") == 2
    assert plan.headline_difficulty == "no-csp"


def test_build_plans_over_tree() -> None:
    analysis = analyze_backup(_FIXTURES)
    plans = build_plans(analysis.reports)
    assert len(plans) == analysis.gpo_count
    assert all(p.gpo_guid for p in plans)
    # to_dict is JSON-shaped.
    payload = plans[0].to_dict()
    assert "scope_targets" in payload and "remediations" in payload
