"""
tests/test_active_directory_survey_spn_inventory.py
----------------------------------------------------
Unit tests for the SPN inventory artifact emitted by the AD survey adapter.

Coverage:
  1. SPN string parsing (host:port, host:instance-name, host alone)
  2. Service-class filtering (default MSSQLSvc only; custom filters)
  3. OrgPath join via principal (preferred) and hosting computer (fallback)
  4. DRIFT-IDENTITY finding emission when neither attribution hook resolves
  5. Phase tagging (pre_migration, post_migration, unspecified)
  6. objectClass enum normalization (known values pass-through, unknown -> 'other')
  7. ADSurveyReport carries spn_inventory through as_dict() correctly
  8. Idempotence: repeated extraction yields identical output
  9. Schema validation: emitted artifact validates against orgtree-readiness schema
 10. Empty / no-SPN principals are skipped without error

All tests use synthetic in-memory principal records — no live LDAP required.

Canon refs:
  - src/uiao/canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md (UIAO_139)
  - docs/customer-documents/whitepapers/federal-ssot-alignment.qmd
  - docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd
  - docs/docs/16_DriftDetectionStandard.qmd §7
"""

from __future__ import annotations

import json
from importlib.resources import files as _res_files
from typing import Any

import pytest

from uiao.adapters.modernization.active_directory.survey import (
    DEFAULT_SPN_SERVICE_CLASS_FILTER,
    SPN_METHOD_LDAP,
    SPN_PHASE_POST_MIGRATION,
    SPN_PHASE_PRE_MIGRATION,
    SPN_PHASE_UNSPECIFIED,
    ADSurveyReport,
    _parse_spn,
    extract_spn_inventory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = "2026-05-11T12:00:00Z"


def _principal(
    name: str,
    spns: list[str],
    *,
    object_class: str = "user",
    sam: str | None = None,
    dn: str | None = None,
) -> dict[str, Any]:
    return {
        "principal_name": name,
        "object_class": object_class,
        "spns": spns,
        "sam_account_name": sam or f"{name.lower()}-svc",
        "distinguished_name": dn or f"CN={name},OU=Service Accounts,DC=corp,DC=example,DC=com",
    }


# ---------------------------------------------------------------------------
# 1. SPN string parsing
# ---------------------------------------------------------------------------


def test_parse_spn_host_only():
    service_class, host, port_or_instance, full = _parse_spn("MSSQLSvc/sql01.corp.example.com")
    assert service_class == "MSSQLSvc"
    assert host == "sql01.corp.example.com"
    assert port_or_instance is None
    assert full == "MSSQLSvc/sql01.corp.example.com"


def test_parse_spn_host_and_port():
    service_class, host, port_or_instance, _ = _parse_spn("MSSQLSvc/sql01.corp.example.com:1433")
    assert service_class == "MSSQLSvc"
    assert host == "sql01.corp.example.com"
    assert port_or_instance == "1433"


def test_parse_spn_host_and_named_instance():
    service_class, host, port_or_instance, _ = _parse_spn("MSSQLSvc/sql01.corp.example.com:SQL2K22")
    assert service_class == "MSSQLSvc"
    assert host == "sql01.corp.example.com"
    assert port_or_instance == "SQL2K22"


def test_parse_spn_malformed_no_slash():
    service_class, host, port_or_instance, full = _parse_spn("not-an-spn")
    assert service_class == ""
    assert host == ""
    assert port_or_instance is None
    assert full == "not-an-spn"


# ---------------------------------------------------------------------------
# 2. Service-class filtering
# ---------------------------------------------------------------------------


def test_filter_keeps_only_mssqlsvc_by_default():
    principals = [
        _principal("svc-sql", ["MSSQLSvc/sql01:1433", "HTTP/intranet"]),
        _principal("svc-web", ["HTTP/web01"], object_class="user"),
    ]
    inv, findings = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-sql": "/Root/Finance/DB"},
    )
    assert {r.spn for r in inv.records} == {"MSSQLSvc/sql01:1433"}
    assert findings == []


def test_filter_accepts_custom_service_class_list():
    principals = [_principal("svc-web", ["HTTP/web01", "MSSQLSvc/sql01"])]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        service_class_filter=["HTTP"],
        principal_orgpath_index={"svc-web": "/Root/Web"},
    )
    assert {r.service_class for r in inv.records} == {"HTTP"}
    assert {r.spn for r in inv.records} == {"HTTP/web01"}
    assert inv.service_class_filter == ["HTTP"]


def test_default_filter_constant_is_mssqlsvc():
    assert DEFAULT_SPN_SERVICE_CLASS_FILTER == ("MSSQLSvc",)


# ---------------------------------------------------------------------------
# 3. OrgPath join (principal preferred, hosting computer fallback)
# ---------------------------------------------------------------------------


def test_principal_orgpath_resolution_via_sam_account_name():
    principals = [
        _principal(
            "svc-sql-finance",
            ["MSSQLSvc/sql01.corp.example.com:1433"],
            sam="svc-sql-fin",
        )
    ]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-sql-fin": "/Root/Finance/DB"},
    )
    assert inv.records[0].principal_orgpath == "/Root/Finance/DB"
    assert inv.records[0].hosting_computer_orgpath is None
    assert inv.records[0].drift_finding_ref is None


def test_principal_orgpath_resolution_prefers_dn_over_sam():
    principals = [
        _principal(
            "svc",
            ["MSSQLSvc/sql01"],
            sam="svc",
            dn="CN=svc,OU=ServiceAccounts,DC=corp",
        )
    ]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={
            "CN=svc,OU=ServiceAccounts,DC=corp": "/Root/Engineering",
            "svc": "/Root/Finance",
        },
    )
    # DN wins over sAMAccountName
    assert inv.records[0].principal_orgpath == "/Root/Engineering"


def test_hosting_computer_orgpath_fallback_when_principal_unresolved():
    principals = [_principal("orphaned-svc", ["MSSQLSvc/sql01.corp.example.com:1433"])]
    inv, findings = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={},  # principal does not resolve
        computer_orgpath_index={"sql01.corp.example.com": "/Root/IT/DB"},
    )
    assert inv.records[0].principal_orgpath is None
    assert inv.records[0].hosting_computer_orgpath == "/Root/IT/DB"
    assert inv.records[0].drift_finding_ref is None
    assert findings == []  # at least one hook resolved -> no drift


def test_hosting_computer_orgpath_short_hostname_match():
    principals = [_principal("orphaned-svc", ["MSSQLSvc/sql01.corp.example.com"])]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        computer_orgpath_index={"sql01": "/Root/IT/DB"},
    )
    assert inv.records[0].hosting_computer_orgpath == "/Root/IT/DB"


# ---------------------------------------------------------------------------
# 4. DRIFT-IDENTITY finding emission
# ---------------------------------------------------------------------------


def test_unattributed_spn_emits_drift_identity_finding():
    principals = [_principal("shadow-svc", ["MSSQLSvc/legacy01"])]
    inv, findings = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.drift_class == "DRIFT-IDENTITY"
    assert f.severity == "P2"
    assert f.object_type == "SPN"
    assert "MSSQLSvc/legacy01" in f.detail
    # Record carries the back-reference
    assert inv.records[0].drift_finding_ref == f.error_code


def test_drift_finding_error_codes_are_unique_per_inventory():
    principals = [
        _principal("svc-a", ["MSSQLSvc/host-a"]),
        _principal("svc-b", ["MSSQLSvc/host-b"]),
    ]
    _, findings = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
    )
    assert len(findings) == 2
    codes = {f.error_code for f in findings}
    assert len(codes) == 2


# ---------------------------------------------------------------------------
# 5. Phase tagging
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phase", [SPN_PHASE_PRE_MIGRATION, SPN_PHASE_POST_MIGRATION, SPN_PHASE_UNSPECIFIED])
def test_phase_round_trip(phase):
    principals = [_principal("svc", ["MSSQLSvc/sql01"])]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=phase,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc": "/Root/Finance"},
    )
    assert inv.phase == phase
    assert inv.to_dict()["phase"] == phase


def test_invalid_phase_raises():
    with pytest.raises(ValueError):
        extract_spn_inventory(
            principals=[],
            phase="invalid-phase",
            discovery_timestamp=_TS,
        )


# ---------------------------------------------------------------------------
# 6. objectClass enum normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("user", "user"),
        ("computer", "computer"),
        ("msDS-GroupManagedServiceAccount", "msDS-GroupManagedServiceAccount"),
        ("msDS-ManagedServiceAccount", "msDS-ManagedServiceAccount"),
        ("organizationalUnit", "other"),
        ("group", "other"),
        ("", "other"),
    ],
)
def test_object_class_normalization(raw, expected):
    principals = [_principal("svc", ["MSSQLSvc/sql01"], object_class=raw)]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc": "/Root/X"},
    )
    assert inv.records[0].object_class == expected


# ---------------------------------------------------------------------------
# 7. ADSurveyReport carries spn_inventory
# ---------------------------------------------------------------------------


def test_report_as_dict_includes_spn_inventory_when_populated():
    report = ADSurveyReport(forest_root="DC=corp,DC=example,DC=com")
    principals = [_principal("svc", ["MSSQLSvc/sql01:1433"])]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc": "/Root/Finance"},
    )
    report.spn_inventory = inv
    d = report.as_dict()
    assert d["spn_inventory"] is not None
    assert d["spn_inventory"]["phase"] == SPN_PHASE_PRE_MIGRATION
    assert d["spn_inventory"]["records"][0]["spn"] == "MSSQLSvc/sql01:1433"


def test_report_as_dict_when_no_spn_inventory():
    report = ADSurveyReport(forest_root="DC=corp,DC=example,DC=com")
    d = report.as_dict()
    assert d["spn_inventory"] is None


# ---------------------------------------------------------------------------
# 8. Idempotence
# ---------------------------------------------------------------------------


def test_repeated_extraction_yields_identical_output():
    principals = [
        _principal("svc-a", ["MSSQLSvc/host-a:1433"]),
        _principal("svc-b", ["MSSQLSvc/host-b:SQL2K22"]),
    ]
    inv1, findings1 = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-a": "/Root/A", "svc-b": "/Root/B"},
    )
    inv2, findings2 = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-a": "/Root/A", "svc-b": "/Root/B"},
    )
    assert inv1.to_dict() == inv2.to_dict()
    assert [f.__dict__ for f in findings1] == [f.__dict__ for f in findings2]


# ---------------------------------------------------------------------------
# 9. Schema validation
# ---------------------------------------------------------------------------


def _load_schema() -> dict:
    raw = _res_files("uiao.schemas").joinpath("orgtree-readiness").joinpath("orgtree-readiness.schema.json").read_text()
    return json.loads(raw)


def test_emitted_spn_inventory_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    principals = [
        _principal(
            "svc-sql-fin",
            ["MSSQLSvc/sql01.corp.example.com:1433", "MSSQLSvc/sql01.corp.example.com:SQL2K22"],
            object_class="msDS-GroupManagedServiceAccount",
        ),
        _principal("svc-orphan", ["MSSQLSvc/legacy01"]),
    ]
    inv, findings = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_POST_MIGRATION,
        discovery_timestamp=_TS,
        discovery_method=SPN_METHOD_LDAP,
        discovery_scope="GC://corp.example.com",
        principal_orgpath_index={"svc-sql-fin": "/Root/Finance/DB"},
    )

    # Schema validates a minimal but complete orgtree-readiness bundle with spn_inventory included.
    bundle = {
        "version": "0.6.0",
        "generated_at": "2026-05-11T12:00:00Z",
        "users": [],
        "groups": [],
        "computers": [],
        "servers": [],
        "orgpath_plan": {"assignments": []},
        "intune_plan": {"enrollments": []},
        "arc_plan": {"onboardings": []},
        "findings": [],
        "provenance": {
            "schema_id": "https://uiao.gov/schemas/orgtree-readiness/orgtree-readiness.schema.json",
            "schema_version": "0.6.0",
            "source_hash": "a" * 64,
            "signature": "b" * 64,
            "hmac_alg": "hmac-sha256",
        },
        "spn_inventory": inv.to_dict(),
    }
    errors = sorted(validator.iter_errors(bundle), key=lambda e: e.path)
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_schema_rejects_invalid_phase():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    bundle = {
        "version": "0.6.0",
        "generated_at": "2026-05-11T12:00:00Z",
        "users": [],
        "groups": [],
        "computers": [],
        "servers": [],
        "orgpath_plan": {"assignments": []},
        "intune_plan": {"enrollments": []},
        "arc_plan": {"onboardings": []},
        "findings": [],
        "provenance": {
            "schema_id": "https://uiao.gov/schemas/orgtree-readiness/orgtree-readiness.schema.json",
            "schema_version": "0.6.0",
            "source_hash": "a" * 64,
            "signature": "b" * 64,
            "hmac_alg": "hmac-sha256",
        },
        "spn_inventory": {
            "phase": "not-a-phase",
            "discovery_timestamp": "2026-05-11T12:00:00Z",
            "discovery_method": "AD-SPN-LDAP",
            "records": [],
        },
    }
    errors = list(validator.iter_errors(bundle))
    assert any("phase" in str(e.path) or "not-a-phase" in str(e.message) for e in errors)


# ---------------------------------------------------------------------------
# 10. Empty / no-SPN principals
# ---------------------------------------------------------------------------


def test_principal_with_no_spns_is_skipped():
    principals = [
        {"principal_name": "no-spn-user", "object_class": "user", "spns": []},
        _principal("svc-sql", ["MSSQLSvc/sql01"]),
    ]
    inv, _ = extract_spn_inventory(
        principals=principals,
        phase=SPN_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-sql": "/Root/DB"},
    )
    assert len(inv.records) == 1
    assert inv.records[0].principal_name == "svc-sql"


def test_empty_principal_list_produces_empty_inventory():
    inv, findings = extract_spn_inventory(
        principals=[],
        phase=SPN_PHASE_UNSPECIFIED,
        discovery_timestamp=_TS,
    )
    assert inv.records == []
    assert findings == []
    assert inv.phase == SPN_PHASE_UNSPECIFIED
