"""Tests for the location Mover pass + location drift classes (ADR-102 §D6 phase 3).

Covers: the three location drift sub-classes; the Mover diff (join /
leave / move, within-site vs cross-site, boundary-transition impacts);
and the policy/boundary detector against the reference registry's
governed site classification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.modernization.locpath import (
    DRIFT_LOCATION_ASSIGNMENT,
    DRIFT_LOCATION_BOUNDARY,
    DRIFT_LOCATION_POLICY,
    LocPathAssignmentPlan,
    ObservedSiteState,
    assign_locpaths,
    detect_location_policy_drift,
    load_location_registry_from_path,
    plan_location_moves,
)
from uiao.modernization.locpath.drift import (
    ERROR_BREAKOUT_CLASS_MISMATCH,
    ERROR_DISALLOWED_TELEMETRY_DESTINATION,
    ERROR_INTERNAL_ONLY_EGRESS,
    ERROR_STALE_ASSIGNMENT,
    ERROR_UNAPPROVED_DIA_BREAKOUT,
    ERROR_UNREGISTERED_OBSERVED_SITE,
)
from uiao.modernization.locpath.mover import (
    IMPACT_ADMIN_UNITS,
    IMPACT_DIA_TRANSITION,
    IMPACT_DYNAMIC_GROUPS,
    IMPACT_E911,
    KIND_JOIN,
    KIND_LEAVE,
    KIND_MOVE,
)

REGISTRY_YAML = Path(__file__).resolve().parents[1] / "src/uiao/canon/data/locpath/location-registry.yaml"


def _record(employee_id: str, location_code: str) -> HRRecord:
    return HRRecord(
        employee_id=employee_id,
        first_name="Jordan",
        last_name="Example",
        department="Finance",
        hire_date="2024-01-08",
        worker_type="FullTimeEmployee",
        location_code=location_code,
        country="US",
        employment_status="Active",
        extracted_at="2026-06-11T00:00:00Z",
    )


def _plan(*pairs: tuple[str, str]) -> LocPathAssignmentPlan:
    return assign_locpaths([_record(emp, code) for emp, code in pairs])


# ---------------------------------------------------------------------------
# Drift class names — the UIAO_194 reserved names, as taxonomy sub-classes
# ---------------------------------------------------------------------------


def test_location_drift_classes_are_canonical_sub_classes() -> None:
    assert DRIFT_LOCATION_ASSIGNMENT == "DRIFT-IDENTITY::location-assignment"
    assert DRIFT_LOCATION_POLICY == "DRIFT-AUTHZ::location-policy"
    assert DRIFT_LOCATION_BOUNDARY == "DRIFT-BOUNDARY::location-boundary"


def test_hr_assign_findings_reclassed_to_location_assignment() -> None:
    plan = _plan(("E-1", "FIELD-99"))
    (finding,) = plan.findings
    assert finding.drift_class == DRIFT_LOCATION_ASSIGNMENT


# ---------------------------------------------------------------------------
# Mover pass — join / leave / move + impacts
# ---------------------------------------------------------------------------


def test_unchanged_assignments_produce_no_events() -> None:
    before = _plan(("E-1", "HQ-B3"))
    after = _plan(("E-1", "hq-b3"))  # same place, different code casing
    plan = plan_location_moves(before, after)
    assert plan.events == ()
    assert plan.findings == ()


def test_joiner_and_leaver_events() -> None:
    before = _plan(("E-1", "HQ-B3"))
    after = _plan(("E-2", "HQ"))
    plan = plan_location_moves(before, after)
    (joiner,) = plan.joiners()
    (leaver,) = plan.leavers()
    assert joiner.employee_id == "E-2" and joiner.kind == KIND_JOIN
    assert joiner.previous_loc_path is None and joiner.new_loc_path == "/USA/MD/ANNAPOLIS-HQ"
    assert leaver.employee_id == "E-1" and leaver.kind == KIND_LEAVE
    assert leaver.new_loc_path is None
    assert IMPACT_E911 in joiner.impacts and IMPACT_DYNAMIC_GROUPS in joiner.impacts
    assert IMPACT_ADMIN_UNITS in leaver.impacts


def test_within_site_move_is_p3_without_group_impacts() -> None:
    before = _plan(("E-1", "HQ-B3"))
    after = _plan(("E-1", "HQ-B3-210"))  # same Site, deeper node
    plan = plan_location_moves(before, after)
    (event,) = plan.movers()
    assert event.kind == KIND_MOVE
    assert event.site_changed is False
    assert event.impacts == (IMPACT_E911,)  # dispatchable location only
    (finding,) = plan.findings
    assert finding.drift_class == DRIFT_LOCATION_ASSIGNMENT
    assert finding.error_code == ERROR_STALE_ASSIGNMENT
    assert finding.severity == "P3"


def test_cross_site_move_requires_second_site(tmp_path: Path) -> None:
    # Extend the reference registry with a second site that flips the
    # boundary classification, then move an employee across.
    doc: dict[str, Any] = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    doc["nodes"].extend(
        [
            {
                "locPathId": "9b1c5a40-22e4-4a31-8b51-0000000000a1",
                "locPath": "/USA/MD/FIELD-12",
                "displayName": "Field Office 12",
                "level": "Site",
                "status": "Active",
                "lastUpdated": "2026-06-11T00:00:00Z",
                "sourceSystem": "reference-example",
                "network": {"diaApproved": False, "sdwanBreakoutType": "Centralized"},
                "boundaries": {"telemetryBoundary": "InternalOnly"},
            }
        ]
    )
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    registry = load_location_registry_from_path(reg_path)

    map_yaml = Path(__file__).resolve().parents[1] / "src/uiao/canon/data/locpath/duty-station-map.yaml"
    map_doc: dict[str, Any] = yaml.safe_load(map_yaml.read_text(encoding="utf-8"))
    map_doc["entries"].append({"locationCode": "FLD-12", "locPath": "/USA/MD/FIELD-12"})
    map_path = tmp_path / "map.yaml"
    map_path.write_text(yaml.safe_dump(map_doc, sort_keys=False), encoding="utf-8")

    from uiao.modernization.locpath import load_duty_station_map_from_path

    duty_map = load_duty_station_map_from_path(map_path, registry)
    before = assign_locpaths([_record("E-1", "HQ-B3")], duty_station_map=duty_map, registry=registry)
    after = assign_locpaths([_record("E-1", "FLD-12")], duty_station_map=duty_map, registry=registry)

    plan = plan_location_moves(before, after, registry=registry)
    (event,) = plan.movers()
    assert event.site_changed is True
    assert event.previous_site == "/USA/MD/ANNAPOLIS-HQ"
    assert event.new_site == "/USA/MD/FIELD-12"
    # Cross-site: groups/AUs stale + the classification deltas the move transits.
    assert IMPACT_DYNAMIC_GROUPS in event.impacts
    assert IMPACT_ADMIN_UNITS in event.impacts
    assert IMPACT_DIA_TRANSITION in event.impacts  # diaApproved True → False
    assert "telemetry-boundary-transition" in event.impacts  # GCCAllowed → InternalOnly
    (finding,) = plan.findings
    assert finding.severity == "P2"


# ---------------------------------------------------------------------------
# Policy / boundary drift detection
# ---------------------------------------------------------------------------


def test_compliant_observation_emits_nothing() -> None:
    observed = ObservedSiteState(
        loc_path="/USA/MD/ANNAPOLIS-HQ",
        breakout_observed="Local",  # site is diaApproved: true, sdwanBreakoutType: Local
        telemetry_destinations=("MicrosoftGCC",),  # no allow-list declared at the site
    )
    assert detect_location_policy_drift([observed]) == ()


def test_unregistered_observed_site_is_semantic_gap() -> None:
    (finding,) = detect_location_policy_drift([ObservedSiteState(loc_path="/USA/MD/NOWHERE")])
    assert finding.drift_class == "DRIFT-SEMANTIC"
    assert finding.error_code == ERROR_UNREGISTERED_OBSERVED_SITE


def _restricted_site_registry(tmp_path: Path) -> Any:
    doc: dict[str, Any] = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    for node in doc["nodes"]:
        if node["locPath"] == "/USA/MD/ANNAPOLIS-HQ":
            node["network"] = {"diaApproved": False, "sdwanBreakoutType": "Centralized"}
            node["boundaries"] = {
                "telemetryBoundary": "GCCAllowed",
                "allowedTelemetryDestinations": ["MicrosoftGCC", "InternalSIEM"],
            }
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return load_location_registry_from_path(reg_path)


def test_unapproved_dia_breakout_is_p1_policy_drift(tmp_path: Path) -> None:
    registry = _restricted_site_registry(tmp_path)
    observed = ObservedSiteState(loc_path="/USA/MD/ANNAPOLIS-HQ", internet_egress_observed=True)
    findings = detect_location_policy_drift([observed], registry)
    assert [f.error_code for f in findings] == [ERROR_UNAPPROVED_DIA_BREAKOUT]
    assert findings[0].drift_class == DRIFT_LOCATION_POLICY
    assert findings[0].severity == "P1"


def test_breakout_class_mismatch_is_p2_policy_drift(tmp_path: Path) -> None:
    registry = _restricted_site_registry(tmp_path)
    observed = ObservedSiteState(loc_path="/USA/MD/ANNAPOLIS-HQ", breakout_observed="Hybrid")
    findings = detect_location_policy_drift([observed], registry)
    assert [f.error_code for f in findings] == [ERROR_BREAKOUT_CLASS_MISMATCH]
    assert findings[0].severity == "P2"


def test_disallowed_telemetry_destination_is_boundary_drift(tmp_path: Path) -> None:
    registry = _restricted_site_registry(tmp_path)
    observed = ObservedSiteState(
        loc_path="/USA/MD/ANNAPOLIS-HQ",
        telemetry_destinations=("MicrosoftGCC", "commercial-analytics.example"),
    )
    findings = detect_location_policy_drift([observed], registry)
    assert [f.error_code for f in findings] == [ERROR_DISALLOWED_TELEMETRY_DESTINATION]
    assert findings[0].drift_class == DRIFT_LOCATION_BOUNDARY
    assert "commercial-analytics.example" in findings[0].detail


def test_internal_only_egress_is_boundary_drift(tmp_path: Path) -> None:
    doc: dict[str, Any] = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    for node in doc["nodes"]:
        if node["locPath"] == "/USA/MD/ANNAPOLIS-HQ":
            node["boundaries"]["telemetryBoundary"] = "InternalOnly"
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    registry = load_location_registry_from_path(reg_path)

    observed = ObservedSiteState(loc_path="/USA/MD/ANNAPOLIS-HQ", telemetry_destinations=("anywhere.example",))
    findings = detect_location_policy_drift([observed], registry)
    assert [f.error_code for f in findings] == [ERROR_INTERNAL_ONLY_EGRESS]
    assert findings[0].drift_class == DRIFT_LOCATION_BOUNDARY
    assert findings[0].severity == "P1"
