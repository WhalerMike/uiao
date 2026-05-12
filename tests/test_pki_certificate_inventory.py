"""Tests for the PKI certificate-inventory interface stub.

Covers the same contract shape as ``tests/test_active_directory_survey_spn_inventory.py``:

  1. Required-field enforcement
  2. Phase tagging round-trip (pre / post / unspecified)
  3. Discovery-method enum validation
  4. OrgPath resolution via principal (DN preferred over SAM)
  5. Fallback OrgPath resolution via hosting computer
  6. DRIFT-IDENTITY finding emission when both attribution hooks fail
  7. PIV / CAC flag round-trip
  8. Idempotence — repeated extraction yields identical output
  9. Empty record list — empty inventory, no findings
 10. Adapter manifest constants (registration metadata)

All tests use synthetic in-memory records. No live ADCS / DigiCert /
Entrust / Entra-CBA connection. Mirrors the PR #395 SPN inventory test
pattern exactly.
"""

from __future__ import annotations

from typing import Any

import pytest

from uiao.adapters.modernization.pki import (
    ADAPTER_CLASS,
    ADAPTER_ID,
    MISSION_CLASS,
    PKI_DISCOVERY_AD_OBJECTS,
    PKI_DISCOVERY_OCSP,
    PKI_DISCOVERY_TEMPLATES,
    PKI_PHASE_POST_MIGRATION,
    PKI_PHASE_PRE_MIGRATION,
    PKI_PHASE_UNSPECIFIED,
    CertificateInventory,
    CertificateRecord,
    extract_certificate_inventory,
)

_TS = "2026-05-11T12:00:00Z"


def _record(
    serial: str,
    *,
    subject_dn: str = "CN=service-finance,OU=ServiceAccounts,DC=corp,DC=example,DC=com",
    bound_principal_name: str | None = "service-finance",
    bound_principal_sam: str | None = "svc-fin",
    bound_principal_dn: str | None = None,
    bound_hosting_computer: str | None = None,
    template_name: str = "User",
    not_after: str = "2027-01-01T00:00:00Z",
    is_piv_or_cac: bool = False,
) -> dict[str, Any]:
    return {
        "serial_number": serial,
        "subject_dn": subject_dn,
        "issuer_dn": "CN=Contoso-Issuing-CA,DC=corp,DC=example,DC=com",
        "not_before": "2025-01-01T00:00:00Z",
        "not_after": not_after,
        "status": "issued",
        "template_name": template_name,
        "template_oid": "1.3.6.1.4.1.311.21.8.1.2.3.4.5",
        "bound_principal_name": bound_principal_name,
        "bound_principal_sam": bound_principal_sam,
        "bound_principal_dn": bound_principal_dn,
        "bound_hosting_computer": bound_hosting_computer,
        "is_piv_or_cac": is_piv_or_cac,
    }


# ---------------------------------------------------------------------------
# 1. Required-field enforcement
# ---------------------------------------------------------------------------


def test_missing_required_field_raises() -> None:
    bad = {"serial_number": "01"}  # missing subject_dn, etc.
    with pytest.raises(KeyError):
        extract_certificate_inventory(
            records=[bad],
            phase=PKI_PHASE_PRE_MIGRATION,
            discovery_timestamp=_TS,
        )


# ---------------------------------------------------------------------------
# 2. Phase tagging
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phase",
    [PKI_PHASE_PRE_MIGRATION, PKI_PHASE_POST_MIGRATION, PKI_PHASE_UNSPECIFIED],
)
def test_phase_round_trip(phase: str) -> None:
    inv, _ = extract_certificate_inventory(
        records=[_record("01")],
        phase=phase,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-fin": "/Root/Finance"},
    )
    assert inv.phase == phase
    assert inv.to_dict()["phase"] == phase


def test_invalid_phase_raises() -> None:
    with pytest.raises(ValueError):
        extract_certificate_inventory(
            records=[],
            phase="not-a-phase",
            discovery_timestamp=_TS,
        )


# ---------------------------------------------------------------------------
# 3. Discovery-method enum validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method",
    [PKI_DISCOVERY_AD_OBJECTS, PKI_DISCOVERY_OCSP, PKI_DISCOVERY_TEMPLATES],
)
def test_discovery_method_round_trip(method: str) -> None:
    inv, _ = extract_certificate_inventory(
        records=[_record("01")],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        discovery_method=method,
        principal_orgpath_index={"svc-fin": "/Root/Finance"},
    )
    assert inv.discovery_method == method


def test_invalid_discovery_method_raises() -> None:
    with pytest.raises(ValueError):
        extract_certificate_inventory(
            records=[],
            phase=PKI_PHASE_PRE_MIGRATION,
            discovery_timestamp=_TS,
            discovery_method="not-a-method",
        )


# ---------------------------------------------------------------------------
# 4. OrgPath resolution via principal (DN preferred over SAM)
# ---------------------------------------------------------------------------


def test_principal_orgpath_resolution_via_sam() -> None:
    inv, findings = extract_certificate_inventory(
        records=[_record("01")],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-fin": "/Root/Finance/DB"},
    )
    assert inv.records[0].principal_orgpath == "/Root/Finance/DB"
    assert inv.records[0].hosting_computer_orgpath is None
    assert inv.records[0].drift_finding_ref is None
    assert findings == []


def test_principal_orgpath_dn_wins_over_sam() -> None:
    inv, _ = extract_certificate_inventory(
        records=[
            _record(
                "01",
                bound_principal_dn="CN=svc,OU=ServiceAccounts,DC=corp",
                bound_principal_sam="svc",
            )
        ],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={
            "CN=svc,OU=ServiceAccounts,DC=corp": "/Root/Engineering",
            "svc": "/Root/Finance",
        },
    )
    assert inv.records[0].principal_orgpath == "/Root/Engineering"


# ---------------------------------------------------------------------------
# 5. Fallback OrgPath resolution via hosting computer
# ---------------------------------------------------------------------------


def test_hosting_computer_fallback_resolves_when_principal_unknown() -> None:
    inv, findings = extract_certificate_inventory(
        records=[
            _record(
                "01",
                bound_principal_name="ghost-account",
                bound_principal_sam="ghost",
                bound_hosting_computer="sql01.corp.example.com",
            )
        ],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={},  # principal does not resolve
        computer_orgpath_index={"sql01.corp.example.com": "/Root/IT/DB"},
    )
    assert inv.records[0].principal_orgpath is None
    assert inv.records[0].hosting_computer_orgpath == "/Root/IT/DB"
    assert inv.records[0].drift_finding_ref is None
    assert findings == []


def test_hosting_computer_short_hostname_match() -> None:
    inv, _ = extract_certificate_inventory(
        records=[
            _record(
                "01",
                bound_principal_name="ghost",
                bound_principal_sam="ghost",
                bound_hosting_computer="sql01.corp.example.com",
            )
        ],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        computer_orgpath_index={"sql01": "/Root/IT/DB"},
    )
    assert inv.records[0].hosting_computer_orgpath == "/Root/IT/DB"


# ---------------------------------------------------------------------------
# 6. DRIFT-IDENTITY finding emission
# ---------------------------------------------------------------------------


def test_unattributed_certificate_emits_drift_identity() -> None:
    inv, findings = extract_certificate_inventory(
        records=[
            _record(
                "01",
                bound_principal_name="orphan",
                bound_principal_sam="orphan",
            )
        ],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.drift_class == "DRIFT-IDENTITY"
    assert f.severity == "P2"
    assert f.object_type == "Certificate"
    assert "Certificate" in f.detail
    # Record carries back-reference
    assert inv.records[0].drift_finding_ref == f.error_code


def test_drift_finding_error_codes_unique_per_inventory() -> None:
    inv, findings = extract_certificate_inventory(
        records=[
            _record("01", bound_principal_name="a", bound_principal_sam="a-sam"),
            _record("02", bound_principal_name="b", bound_principal_sam="b-sam"),
        ],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
    )
    assert len(findings) == 2
    assert len({f.error_code for f in findings}) == 2
    # Both records carry their own back-reference
    refs = {r.drift_finding_ref for r in inv.records}
    assert len(refs) == 2 and None not in refs


# ---------------------------------------------------------------------------
# 7. PIV / CAC flag round-trip
# ---------------------------------------------------------------------------


def test_piv_or_cac_flag_round_trip() -> None:
    inv, _ = extract_certificate_inventory(
        records=[_record("01", is_piv_or_cac=True)],
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-fin": "/Root/Finance"},
    )
    assert inv.records[0].is_piv_or_cac is True
    assert inv.to_dict()["records"][0]["is_piv_or_cac"] is True


# ---------------------------------------------------------------------------
# 8. Idempotence — repeated extraction yields identical output
# ---------------------------------------------------------------------------


def test_repeated_extraction_yields_identical_output() -> None:
    records = [_record("01"), _record("02")]
    inv1, findings1 = extract_certificate_inventory(
        records=records,
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-fin": "/Root/Finance"},
    )
    inv2, findings2 = extract_certificate_inventory(
        records=records,
        phase=PKI_PHASE_PRE_MIGRATION,
        discovery_timestamp=_TS,
        principal_orgpath_index={"svc-fin": "/Root/Finance"},
    )
    assert inv1.to_dict() == inv2.to_dict()
    assert [f.__dict__ for f in findings1] == [f.__dict__ for f in findings2]


# ---------------------------------------------------------------------------
# 9. Empty record list — empty inventory, no findings
# ---------------------------------------------------------------------------


def test_empty_record_list_produces_empty_inventory() -> None:
    inv, findings = extract_certificate_inventory(
        records=[],
        phase=PKI_PHASE_UNSPECIFIED,
        discovery_timestamp=_TS,
    )
    assert inv.records == []
    assert findings == []
    assert inv.phase == PKI_PHASE_UNSPECIFIED


# ---------------------------------------------------------------------------
# 10. Adapter manifest constants (registration metadata)
# ---------------------------------------------------------------------------


def test_adapter_manifest_constants() -> None:
    assert ADAPTER_ID == "pki-certificate-inventory-v1"
    assert ADAPTER_CLASS == "modernization"
    assert MISSION_CLASS == "identity"


# ---------------------------------------------------------------------------
# Bonus: smoke-test the public package surface
# ---------------------------------------------------------------------------


def test_public_surface_exported() -> None:
    """Both the dataclasses and the extractor are importable from the package root."""
    assert CertificateInventory is not None
    assert CertificateRecord is not None
    assert callable(extract_certificate_inventory)
