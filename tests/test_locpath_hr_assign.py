"""Tests for the HR duty-station → LocPath assignment pass (ADR-102 §D6 phase 2).

Covers: the shipped reference duty-station map loads and validates
against the reference location registry; every map integrity rule
(case-insensitive code uniqueness, target existence, Site-or-deeper);
and the assignment pass — resolution with provenance and governing
Site, plus every GOV-LOCPATH finding path. Findings reuse the HRIT
DriftFinding shape so they merge into the substrate report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.modernization.locpath import (
    DutyStationMapValidationError,
    assign_locpaths,
    load_duty_station_map,
    load_duty_station_map_from_path,
    load_location_registry,
)
from uiao.modernization.locpath.hr_assign import (
    ERROR_DUPLICATE_EMPLOYEE,
    ERROR_EMPTY_LOCATION_CODE,
    ERROR_INACTIVE_TARGET,
    ERROR_UNMAPPED_LOCATION_CODE,
)

MAP_YAML = Path(__file__).resolve().parents[1] / "src/uiao/canon/data/locpath/duty-station-map.yaml"


def _map_doc() -> dict[str, Any]:
    doc = yaml.safe_load(MAP_YAML.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def _write(tmp_path: Path, doc: dict[str, Any]) -> Path:
    out = tmp_path / "duty-station-map.yaml"
    out.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return out


def _record(employee_id: str = "E-1001", location_code: str = "HQ-B3") -> HRRecord:
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
        adapter_metadata={"source": "test-hr-feed"},
    )


# ---------------------------------------------------------------------------
# Reference duty-station map — loading + integrity
# ---------------------------------------------------------------------------


def test_reference_map_loads_from_packaged_canon() -> None:
    duty_map = load_duty_station_map()
    assert duty_map.map_id == "reference"
    assert duty_map.status == "reference"
    assert len(duty_map.entries) == 3


def test_resolve_is_case_insensitive() -> None:
    duty_map = load_duty_station_map()
    mapping = duty_map.resolve("hq-b3")
    assert mapping is not None
    assert mapping.loc_path == "/USA/MD/ANNAPOLIS-HQ/BLDG-3"
    assert duty_map.resolve("NOPE") is None


def test_duplicate_code_rejected(tmp_path: Path) -> None:
    doc = _map_doc()
    doc["entries"].append({"locationCode": "hq-b3", "locPath": "/USA/MD/ANNAPOLIS-HQ"})
    with pytest.raises(DutyStationMapValidationError, match="collides"):
        load_duty_station_map_from_path(_write(tmp_path, doc))


def test_unregistered_target_rejected(tmp_path: Path) -> None:
    doc = _map_doc()
    doc["entries"][0]["locPath"] = "/USA/MD/NOWHERE"
    with pytest.raises(DutyStationMapValidationError, match="not in location registry"):
        load_duty_station_map_from_path(_write(tmp_path, doc))


def test_above_site_target_rejected(tmp_path: Path) -> None:
    doc = _map_doc()
    doc["entries"][0]["locPath"] = "/USA/MD"  # Region level — above the governance floor
    with pytest.raises(DutyStationMapValidationError, match="Site level or deeper"):
        load_duty_station_map_from_path(_write(tmp_path, doc))


def test_map_schema_enforced(tmp_path: Path) -> None:
    doc = _map_doc()
    doc["status"] = "experimental"
    with pytest.raises(DutyStationMapValidationError, match="schema validation failed"):
        load_duty_station_map_from_path(_write(tmp_path, doc))


# ---------------------------------------------------------------------------
# Assignment pass — resolution
# ---------------------------------------------------------------------------


def test_assignment_resolves_with_site_and_provenance() -> None:
    plan = assign_locpaths([_record()])
    assert plan.findings == ()
    (assignment,) = plan.assignments
    assert assignment.employee_id == "E-1001"
    assert assignment.loc_path == "/USA/MD/ANNAPOLIS-HQ/BLDG-3"
    assert assignment.site_path == "/USA/MD/ANNAPOLIS-HQ"
    assert assignment.primary_duty_station is True
    assert assignment.provenance["hr_extracted_at"] == "2026-06-11T00:00:00Z"
    assert assignment.provenance["duty_station_map"] == "reference"
    assert assignment.provenance["location_registry"] == "reference"


def test_site_level_assignment_is_its_own_site() -> None:
    plan = assign_locpaths([_record(location_code="HQ")])
    (assignment,) = plan.assignments
    assert assignment.loc_path == "/USA/MD/ANNAPOLIS-HQ"
    assert assignment.site_path == "/USA/MD/ANNAPOLIS-HQ"


def test_space_level_assignment_resolves_governing_site() -> None:
    plan = assign_locpaths([_record(location_code="HQ-B3-210")])
    (assignment,) = plan.assignments
    assert assignment.loc_path == "/USA/MD/ANNAPOLIS-HQ/BLDG-3/FL-2/RM-210"
    assert assignment.site_path == "/USA/MD/ANNAPOLIS-HQ"


def test_location_code_matching_is_case_insensitive() -> None:
    plan = assign_locpaths([_record(location_code="hq-b3")])
    assert plan.findings == ()
    assert plan.assignments[0].loc_path == "/USA/MD/ANNAPOLIS-HQ/BLDG-3"


# ---------------------------------------------------------------------------
# Assignment pass — findings (never raises on record-level problems)
# ---------------------------------------------------------------------------


def test_unmapped_code_emits_finding_not_assignment() -> None:
    plan = assign_locpaths([_record(location_code="FIELD-99")])
    assert plan.assignments == ()
    (finding,) = plan.findings
    assert finding.drift_class == "DRIFT-IDENTITY"
    assert finding.error_code == ERROR_UNMAPPED_LOCATION_CODE
    assert finding.path == "E-1001"
    assert plan.unmapped_codes() == ("FIELD-99",)


def test_empty_location_code_emits_finding() -> None:
    plan = assign_locpaths([_record(location_code="  ")])
    assert plan.assignments == ()
    (finding,) = plan.findings
    assert finding.error_code == ERROR_EMPTY_LOCATION_CODE


def test_duplicate_employee_first_record_wins() -> None:
    plan = assign_locpaths([_record(), _record(location_code="HQ")])
    (assignment,) = plan.assignments
    assert assignment.loc_path == "/USA/MD/ANNAPOLIS-HQ/BLDG-3"
    (finding,) = plan.findings
    assert finding.error_code == ERROR_DUPLICATE_EMPLOYEE


def test_inactive_target_assigns_with_warning_finding(tmp_path: Path) -> None:
    registry_yaml = Path(__file__).resolve().parents[1] / "src/uiao/canon/data/locpath/location-registry.yaml"
    reg_doc = yaml.safe_load(registry_yaml.read_text(encoding="utf-8"))
    for node in reg_doc["nodes"]:
        if node["locPath"] == "/USA/MD/ANNAPOLIS-HQ/BLDG-3":
            node["status"] = "Deprecated"
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(reg_doc, sort_keys=False), encoding="utf-8")

    from uiao.modernization.locpath import load_location_registry_from_path

    registry = load_location_registry_from_path(reg_path)
    duty_map = load_duty_station_map_from_path(MAP_YAML, registry)
    plan = assign_locpaths([_record()], duty_station_map=duty_map, registry=registry)
    (assignment,) = plan.assignments  # still assigned
    assert assignment.loc_path == "/USA/MD/ANNAPOLIS-HQ/BLDG-3"
    (finding,) = plan.findings  # but flagged for remap
    assert finding.error_code == ERROR_INACTIVE_TARGET
    assert finding.severity == "P3"


def test_mixed_batch_partitions_cleanly() -> None:
    plan = assign_locpaths(
        [
            _record("E-1", "HQ"),
            _record("E-2", "FIELD-99"),
            _record("E-3", "HQ-B3-210"),
            _record("E-4", ""),
        ]
    )
    assert [a.employee_id for a in plan.assignments] == ["E-1", "E-3"]
    assert sorted(f.path for f in plan.findings) == ["E-2", "E-4"]
    assert plan.map_id == "reference"
    assert plan.registry_id == load_location_registry().registry_id
