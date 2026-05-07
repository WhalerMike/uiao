"""tests/test_kyc_evidence_oscal.py — KYC OSCAL evidence emitter tests.

Covers the three public emitters in ``uiao.oscal.kyc_evidence``:

* ``emit_customer_identity_record``       — UIAO_141 / UIAO_142 / ADR-055
* ``emit_reciprocity_attribute_record``   — UIAO_141 §6 / UIAO_142 §5
* ``emit_reciprocity_record``             — UIAO_140 / ADR-054

Test layers
-----------
1. Public-API happy paths (each emitter writes a valid OSCAL JSON file).
2. Determinism (identical input → identical output bytes).
3. Field surfacing (key UIAO bindings appear as OSCAL props).
4. Graceful degradation on missing optional fields.
5. Filename-safety (slash / colon / etc. in the input identifier).
"""

from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import pytest

# trestle warns on Pydantic V1 incompatibility under Python 3.14+; not relevant here.
warnings.filterwarnings("ignore", category=UserWarning, module="trestle")

from uiao.oscal.kyc_evidence import (
    emit_customer_identity_record,
    emit_reciprocity_attribute_record,
    emit_reciprocity_record,
)

# ---------------------------------------------------------------------------
# Fixed datetime anchor for deterministic golden-style assertions.
# ---------------------------------------------------------------------------

_FIXED_NOW: datetime = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Sample inputs
# ---------------------------------------------------------------------------


def _sample_cir() -> dict:
    return {
        "canonical_identifier": "ssa.ssn-123-45-6789",
        "identity_assurance_level": "IAL-2",
        "authentication_assurance_level": "AAL-2",
        "federation_assurance_level": "FAL-2",
        "authority_of_record": "ssa-attribute-service",
        "lifecycle_state": "active",
    }


def _sample_entitlement() -> dict:
    return {
        "id": "irs-ssa-ssn-001",
        "attribute_id": "ssa.ssn",
        "authority_of_record": "ssa-attribute-service",
        "consumer_principal": "irs.gov",
        "legal_basis": {
            "type": "privacy-act-sorn-routine-use",
            "citation": "OPM/GOVT-1 routine use 12",
        },
        "scope": ["full-ssn"],
        "freshness_window_hours": 24,
        "effective_date": "2026-05-05",
        "signed_by": "ssa-cio",
    }


def _sample_reciprocity() -> dict:
    return {
        "agency_id": "doj.gov",
        "ssp_version": "1.0",
        "ato_decision_id": "OPM-HRIT-ATO-2026-001",
        "acknowledged_by": "doj.cio@doj.gov",
        "acknowledged_at": "2026-05-05T14:00:00Z",
        "configuration_latitude": {"tenant-region": "us-east", "mfa-policy": "piv-required"},
    }


# ---------------------------------------------------------------------------
# emit_customer_identity_record
# ---------------------------------------------------------------------------


class TestCustomerIdentityRecordEmitter:
    def test_writes_valid_oscal_assessment_results(self, tmp_path: Path) -> None:
        out = emit_customer_identity_record(_sample_cir(), tmp_path, now_dt=_FIXED_NOW)
        assert out.exists()
        payload = json.loads(out.read_text())
        ar = payload["assessment-results"]
        assert "uuid" in ar
        assert ar["metadata"]["title"].startswith("Customer Identity Record")
        assert ar["metadata"]["oscal-version"] == "1.0.4"

    def test_filename_anchored_on_canonical_identifier(self, tmp_path: Path) -> None:
        out = emit_customer_identity_record(_sample_cir(), tmp_path, now_dt=_FIXED_NOW)
        assert "ssa.ssn-123-45-6789" in out.name
        assert out.suffix == ".json"

    def test_deterministic_output(self, tmp_path: Path) -> None:
        a = emit_customer_identity_record(_sample_cir(), tmp_path, now_dt=_FIXED_NOW)
        b = emit_customer_identity_record(_sample_cir(), tmp_path, now_dt=_FIXED_NOW)
        assert a.read_text() == b.read_text()

    def test_six_required_bindings_surfaced_as_props(self, tmp_path: Path) -> None:
        out = emit_customer_identity_record(_sample_cir(), tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        inv = ar["results"][0]["local-definitions"]["inventory-items"][0]
        prop_names = {p["name"] for p in inv["props"]}
        # UIAO_141 §2 — six required bindings
        assert {
            "canonical-identifier",
            "identity-assurance-level",
            "authentication-assurance-level",
            "federation-assurance-level",
            "authority-of-record",
            "lifecycle-state",
        } <= prop_names

    def test_graceful_on_missing_optional_fields(self, tmp_path: Path) -> None:
        partial = {"canonical_identifier": "irs.tin-12-3456789"}
        out = emit_customer_identity_record(partial, tmp_path, now_dt=_FIXED_NOW)
        assert out.exists()
        ar = json.loads(out.read_text())["assessment-results"]
        # Should still produce one inventory item with "(unknown)" prop values.
        assert ar["results"][0]["local-definitions"]["inventory-items"]


# ---------------------------------------------------------------------------
# emit_reciprocity_attribute_record
# ---------------------------------------------------------------------------


class TestReciprocityAttributeRecordEmitter:
    def test_writes_valid_oscal_assessment_results(self, tmp_path: Path) -> None:
        out = emit_reciprocity_attribute_record(_sample_entitlement(), tmp_path, now_dt=_FIXED_NOW)
        assert out.exists()
        ar = json.loads(out.read_text())["assessment-results"]
        assert ar["metadata"]["title"].startswith("Reciprocity Attribute Record")

    def test_filename_anchored_on_entitlement_id(self, tmp_path: Path) -> None:
        out = emit_reciprocity_attribute_record(_sample_entitlement(), tmp_path, now_dt=_FIXED_NOW)
        assert "irs-ssa-ssn-001" in out.name

    def test_deterministic_output(self, tmp_path: Path) -> None:
        a = emit_reciprocity_attribute_record(_sample_entitlement(), tmp_path, now_dt=_FIXED_NOW)
        b = emit_reciprocity_attribute_record(_sample_entitlement(), tmp_path, now_dt=_FIXED_NOW)
        assert a.read_text() == b.read_text()

    def test_legal_basis_surfaced_as_props(self, tmp_path: Path) -> None:
        out = emit_reciprocity_attribute_record(_sample_entitlement(), tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        inv = ar["results"][0]["local-definitions"]["inventory-items"][0]
        props = {p["name"]: p["value"] for p in inv["props"]}
        assert props["legal-basis-type"] == "privacy-act-sorn-routine-use"
        assert props["legal-basis-citation"] == "OPM/GOVT-1 routine use 12"
        assert props["attribute-id"] == "ssa.ssn"
        assert props["consumer-principal"] == "irs.gov"
        assert props["authority-of-record"] == "ssa-attribute-service"

    def test_string_legal_basis_flattened(self, tmp_path: Path) -> None:
        ent = _sample_entitlement()
        ent["legal_basis"] = "5 U.S.C. §552a routine use"
        out = emit_reciprocity_attribute_record(ent, tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        props = {p["name"]: p["value"] for p in ar["results"][0]["local-definitions"]["inventory-items"][0]["props"]}
        assert props["legal-basis-type"] == "(unknown)"
        assert "5 U.S.C." in props["legal-basis-citation"]

    def test_optional_expiry_date_passes_through(self, tmp_path: Path) -> None:
        ent = _sample_entitlement()
        ent["expiry_date"] = "2027-05-05"
        out = emit_reciprocity_attribute_record(ent, tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        prop_names = {p["name"] for p in ar["results"][0]["local-definitions"]["inventory-items"][0]["props"]}
        assert "expiry-date" in prop_names


# ---------------------------------------------------------------------------
# emit_reciprocity_record (UIAO_140 single-ATO)
# ---------------------------------------------------------------------------


class TestReciprocityRecordEmitter:
    def test_writes_valid_oscal_assessment_results(self, tmp_path: Path) -> None:
        out = emit_reciprocity_record(_sample_reciprocity(), tmp_path, now_dt=_FIXED_NOW)
        assert out.exists()
        ar = json.loads(out.read_text())["assessment-results"]
        assert ar["metadata"]["title"].startswith("Single-ATO Reciprocity Record")

    def test_filename_anchored_on_agency_id(self, tmp_path: Path) -> None:
        out = emit_reciprocity_record(_sample_reciprocity(), tmp_path, now_dt=_FIXED_NOW)
        assert "doj.gov" in out.name

    def test_deterministic_output(self, tmp_path: Path) -> None:
        a = emit_reciprocity_record(_sample_reciprocity(), tmp_path, now_dt=_FIXED_NOW)
        b = emit_reciprocity_record(_sample_reciprocity(), tmp_path, now_dt=_FIXED_NOW)
        assert a.read_text() == b.read_text()

    def test_canon_ref_marks_uiao_140(self, tmp_path: Path) -> None:
        out = emit_reciprocity_record(_sample_reciprocity(), tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        result_props = {p["name"]: p["value"] for p in ar["results"][0]["props"]}
        assert result_props["uiao-canon-ref"] == "UIAO_140"
        assert result_props["uiao-event-type"] == "reciprocity-record"

    def test_configuration_latitude_dict_summary(self, tmp_path: Path) -> None:
        out = emit_reciprocity_record(_sample_reciprocity(), tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        props = {p["name"]: p["value"] for p in ar["results"][0]["local-definitions"]["inventory-items"][0]["props"]}
        # Sorted keys: mfa-policy=piv-required, tenant-region=us-east
        assert "mfa-policy=piv-required" in props["configuration-latitude"]
        assert "tenant-region=us-east" in props["configuration-latitude"]

    def test_configuration_latitude_list_summary(self, tmp_path: Path) -> None:
        recip = _sample_reciprocity()
        recip["configuration_latitude"] = ["us-east", "piv-required"]
        out = emit_reciprocity_record(recip, tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        props = {p["name"]: p["value"] for p in ar["results"][0]["local-definitions"]["inventory-items"][0]["props"]}
        assert props["configuration-latitude"] == "us-east,piv-required"

    def test_missing_configuration_latitude_default(self, tmp_path: Path) -> None:
        recip = _sample_reciprocity()
        del recip["configuration_latitude"]
        out = emit_reciprocity_record(recip, tmp_path, now_dt=_FIXED_NOW)
        ar = json.loads(out.read_text())["assessment-results"]
        props = {p["name"]: p["value"] for p in ar["results"][0]["local-definitions"]["inventory-items"][0]["props"]}
        assert props["configuration-latitude"] == "(default)"


# ---------------------------------------------------------------------------
# Cross-cutting — filename safety and out-of-tree characters
# ---------------------------------------------------------------------------


class TestFilenameSafety:
    @pytest.mark.parametrize(
        "raw,expected_substr",
        [
            ("ssa.ssn-123-45-6789", "ssa.ssn-123-45-6789"),
            ("path/with/slashes", "path-with-slashes"),
            ("colon:in:value", "colon-in-value"),
            ("space and stuff", "space-and-stuff"),
        ],
    )
    def test_filename_is_safe(self, tmp_path: Path, raw: str, expected_substr: str) -> None:
        cir = _sample_cir()
        cir["canonical_identifier"] = raw
        out = emit_customer_identity_record(cir, tmp_path, now_dt=_FIXED_NOW)
        assert out.exists()
        assert expected_substr in out.name


# ---------------------------------------------------------------------------
# Public API exports
# ---------------------------------------------------------------------------


class TestPublicAPI:
    def test_emitters_exported_from_uiao_oscal(self) -> None:
        from uiao import oscal as oscal_pkg

        assert hasattr(oscal_pkg, "emit_customer_identity_record")
        assert hasattr(oscal_pkg, "emit_reciprocity_attribute_record")
        assert hasattr(oscal_pkg, "emit_reciprocity_record")
