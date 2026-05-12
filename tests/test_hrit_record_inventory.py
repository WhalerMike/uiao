"""Tests for the HRIT record-inventory interface stub.

Same shape as ``tests/test_active_directory_survey_spn_inventory.py`` (PR
#395) and ``tests/test_pki_certificate_inventory.py`` (PR #429):

  1. Required-field enforcement (KeyError on miss)
  2. Phase tagging round-trip (pre / post / unspecified)
  3. Discovery-method enum validation (5 federal sources)
  4. OrgPath resolution priority (organization_code > division > department > cost_center)
  5. DRIFT-IDENTITY finding emission when no key resolves
  6. Empty record list
  7. Adapter manifest constants
  8. Public surface exports
  9. Idempotence — repeated extraction yields identical output
 10. adapter_metadata round-trip (per-source provenance bag)

All tests use synthetic in-memory records. No live HR-system connection.
"""

from __future__ import annotations

from typing import Any

import pytest

from uiao.adapters.modernization.hrit import (
    ADAPTER_CLASS,
    ADAPTER_ID,
    HRIT_DISCOVERY_DCPDS,
    HRIT_DISCOVERY_DOI_IBC,
    HRIT_DISCOVERY_NFC_EMPOWHR,
    HRIT_DISCOVERY_TREASURY_HR_CONNECT,
    HRIT_DISCOVERY_USA_STAFFING,
    HRIT_PHASE_POST_MIGRATION,
    HRIT_PHASE_PRE_MIGRATION,
    HRIT_PHASE_UNSPECIFIED,
    MISSION_CLASS,
    HRRecord,
    HRRecordInventory,
    extract_hrit_record_inventory,
)

_TS = "2026-05-11T12:00:00Z"


def _record(
    employee_id: str,
    *,
    department: str = "Office of the CFO",
    division: str | None = "Finance",
    organization_code: str | None = "ORG-FIN-001",
    cost_center: str | None = "CC-1001",
    worker_type: str = "FullTimeEmployee",
    employment_status: str = "Active",
    adapter_metadata: dict | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "employee_id": employee_id,
        "first_name": "Alice",
        "last_name": "Example",
        "department": department,
        "hire_date": "2026-01-15",
        "worker_type": worker_type,
        "location_code": "DC-HQ-001",
        "country": "US",
        "employment_status": employment_status,
        "extracted_at": _TS,
        "division": division,
        "organization_code": organization_code,
        "cost_center": cost_center,
        "job_title": "Senior Analyst",
        "manager_employee_id": "E000000",
    }
    if adapter_metadata is not None:
        rec["adapter_metadata"] = adapter_metadata
    return rec


# ---------------------------------------------------------------------------
# 1. Required-field enforcement
# ---------------------------------------------------------------------------


def test_missing_required_field_raises() -> None:
    bad = {"employee_id": "E1"}  # missing first_name, last_name, etc.
    with pytest.raises(KeyError):
        extract_hrit_record_inventory(
            records=[bad],
            phase=HRIT_PHASE_PRE_MIGRATION,
            discovery_timestamp=_TS,
        )


# ---------------------------------------------------------------------------
# 2. Phase tagging
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phase",
    [HRIT_PHASE_PRE_MIGRATION, HRIT_PHASE_POST_MIGRATION, HRIT_PHASE_UNSPECIFIED],
)
def test_phase_round_trip(phase: str) -> None:
    inv, _ = extract_hrit_record_inventory(
        records=[_record("E1")],
        phase=phase,
        discovery_timestamp=_TS,
        orgpath_index={"ORG-FIN-001": "/Root/Finance"},
    )
    assert inv.phase == phase
    assert inv.to_dict()["phase"] == phase


def test_invalid_phase_raises() -> None:
    with pytest.raises(ValueError):
        extract_hrit_record_inventory(
            records=[],
            phase="not-a-phase",
            discovery_timestamp=_TS,
        )


# ---------------------------------------------------------------------------
# 3. Discovery-method enum validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method",
    [
        HRIT_DISCOVERY_NFC_EMPOWHR,
        HRIT_DISCOVERY_TREASURY_HR_CONNECT,
        HRIT_DISCOVERY_DCPDS,
        HRIT_DISCOVERY_DOI_IBC,
        HRIT_DISCOVERY_USA_STAFFING,
    ],
)
def test_discovery_method_round_trip(method: str) -> None:
    inv, _ = extract_hrit_record_inventory(
        records=[_record("E1")],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        discovery_method=method,
        orgpath_index={"ORG-FIN-001": "/Root/Finance"},
    )
    assert inv.discovery_method == method


def test_invalid_discovery_method_raises() -> None:
    with pytest.raises(ValueError):
        extract_hrit_record_inventory(
            records=[],
            phase=HRIT_PHASE_PRE_MIGRATION,
            discovery_timestamp=_TS,
            discovery_method="not-a-method",
        )


# ---------------------------------------------------------------------------
# 4. OrgPath resolution priority — organization_code > division > department > cost_center
# ---------------------------------------------------------------------------


def test_organization_code_wins_over_others() -> None:
    inv, findings = extract_hrit_record_inventory(
        records=[_record("E1")],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={
            "ORG-FIN-001": "/Root/Finance",
            "Finance": "/Root/Engineering",  # division — should NOT win
            "Office of the CFO": "/Root/Operations",  # department — should NOT win
            "CC-1001": "/Root/Other",  # cost_center — should NOT win
        },
    )
    assert inv.records[0].resolved_orgpath == "/Root/Finance"
    assert findings == []


def test_division_wins_when_organization_code_missing() -> None:
    inv, _ = extract_hrit_record_inventory(
        records=[_record("E1", organization_code=None)],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={
            "Finance": "/Root/Finance",
            "Office of the CFO": "/Root/Engineering",  # should NOT win
        },
    )
    assert inv.records[0].resolved_orgpath == "/Root/Finance"


def test_department_wins_when_organization_code_and_division_missing() -> None:
    inv, _ = extract_hrit_record_inventory(
        records=[_record("E1", organization_code=None, division=None)],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={"Office of the CFO": "/Root/Finance"},
    )
    assert inv.records[0].resolved_orgpath == "/Root/Finance"


def test_cost_center_last_resort_resolves() -> None:
    inv, _ = extract_hrit_record_inventory(
        records=[
            _record(
                "E1",
                organization_code=None,
                division=None,
                department="No-Match-Dept",  # department exists but isn't in index
                cost_center="CC-1001",
            )
        ],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={"CC-1001": "/Root/FinanceByCC"},
    )
    assert inv.records[0].resolved_orgpath == "/Root/FinanceByCC"


# ---------------------------------------------------------------------------
# 5. DRIFT-IDENTITY finding emission
# ---------------------------------------------------------------------------


def test_unresolvable_record_emits_drift_identity() -> None:
    inv, findings = extract_hrit_record_inventory(
        records=[
            _record(
                "E1",
                organization_code="UNKNOWN-ORG",
                division="UNKNOWN-DIV",
                department="UNKNOWN-DEPT",
                cost_center="UNKNOWN-CC",
            )
        ],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={"ORG-FIN-001": "/Root/Finance"},
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.drift_class == "DRIFT-IDENTITY"
    assert f.severity == "P2"
    assert f.object_type == "HRRecord"
    assert "E1" in f.detail
    assert inv.records[0].drift_finding_ref == f.error_code


def test_unattributed_error_codes_unique_per_inventory() -> None:
    inv, findings = extract_hrit_record_inventory(
        records=[
            _record("E1", organization_code="UNK-A", division=None, department="DEPT-A", cost_center=None),
            _record("E2", organization_code="UNK-B", division=None, department="DEPT-B", cost_center=None),
            _record("E3", organization_code="UNK-C", division=None, department="DEPT-C", cost_center=None),
        ],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={},
    )
    assert len(findings) == 3
    assert len({f.error_code for f in findings}) == 3
    # Each record carries its own back-reference
    refs = {r.drift_finding_ref for r in inv.records}
    assert len(refs) == 3 and None not in refs


def test_no_orgpath_index_emits_drift_for_all_records() -> None:
    inv, findings = extract_hrit_record_inventory(
        records=[_record("E1"), _record("E2"), _record("E3")],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index=None,
    )
    assert len(findings) == 3
    assert all(f.drift_class == "DRIFT-IDENTITY" for f in findings)


# ---------------------------------------------------------------------------
# 6. Empty record list — empty inventory, no findings
# ---------------------------------------------------------------------------


def test_empty_record_list_produces_empty_inventory() -> None:
    inv, findings = extract_hrit_record_inventory(
        records=[],
        phase=HRIT_PHASE_UNSPECIFIED,
        discovery_timestamp=_TS,
    )
    assert inv.records == []
    assert findings == []
    assert inv.phase == HRIT_PHASE_UNSPECIFIED


# ---------------------------------------------------------------------------
# 7. Adapter manifest constants
# ---------------------------------------------------------------------------


def test_adapter_manifest_constants() -> None:
    assert ADAPTER_ID == "hrit-record-inventory-v1"
    assert ADAPTER_CLASS == "modernization"
    assert MISSION_CLASS == "identity"


# ---------------------------------------------------------------------------
# 8. Public surface exports
# ---------------------------------------------------------------------------


def test_public_surface_exported() -> None:
    """Dataclasses, extractor, phase constants, and discovery constants
    are importable from the package root."""
    assert HRRecordInventory is not None
    assert HRRecord is not None
    assert callable(extract_hrit_record_inventory)
    # All five federal-source discovery methods are exported
    assert HRIT_DISCOVERY_NFC_EMPOWHR == "NFC-EMPOWHR"
    assert HRIT_DISCOVERY_TREASURY_HR_CONNECT == "TREASURY-HR-CONNECT"
    assert HRIT_DISCOVERY_DCPDS == "DCPDS"
    assert HRIT_DISCOVERY_DOI_IBC == "DOI-IBC"
    assert HRIT_DISCOVERY_USA_STAFFING == "USA-STAFFING"


# ---------------------------------------------------------------------------
# 9. Idempotence
# ---------------------------------------------------------------------------


def test_repeated_extraction_yields_identical_output() -> None:
    records = [_record("E1"), _record("E2")]
    inv1, findings1 = extract_hrit_record_inventory(
        records=records,
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={"ORG-FIN-001": "/Root/Finance"},
    )
    inv2, findings2 = extract_hrit_record_inventory(
        records=records,
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={"ORG-FIN-001": "/Root/Finance"},
    )
    assert inv1.to_dict() == inv2.to_dict()
    assert [f.__dict__ for f in findings1] == [f.__dict__ for f in findings2]


# ---------------------------------------------------------------------------
# 10. adapter_metadata round-trip (per-source provenance bag)
# ---------------------------------------------------------------------------


def test_adapter_metadata_round_trip() -> None:
    metadata = {
        "source_system": "NFC EmpowHR",
        "source_version": "9.2.0.42",
        "extraction_run_id": "run-20260511-0001",
    }
    inv, _ = extract_hrit_record_inventory(
        records=[_record("E1", adapter_metadata=metadata)],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={"ORG-FIN-001": "/Root/Finance"},
    )
    assert inv.records[0].adapter_metadata == metadata
    assert inv.to_dict()["records"][0]["adapter_metadata"] == metadata


def test_adapter_metadata_is_isolated_across_records() -> None:
    """Mutating one record's adapter_metadata must not affect another's."""
    shared = {"source_system": "DCPDS"}
    inv, _ = extract_hrit_record_inventory(
        records=[
            _record("E1", adapter_metadata=shared),
            _record("E2", adapter_metadata=shared),
        ],
        phase=HRIT_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        orgpath_index={"ORG-FIN-001": "/Root/Finance"},
    )
    inv.records[0].adapter_metadata["mutation"] = "leaked?"
    assert "mutation" not in inv.records[1].adapter_metadata
