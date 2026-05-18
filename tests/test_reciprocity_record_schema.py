"""Tests for WS-A1: Reciprocity-Record JSON Schema.

Covers:
- Schema meta-validates as Draft 2020-12
- A minimal valid example object (all required fields) passes validation
- An empty object fails validation (missing all required fields)
- An object missing ``legal_basis`` fails validation
- An object with a ``legal_basis`` value not in the enum fails
- An object with ``consuming_agency_code: "treas"`` (lowercase) fails the pattern
- ``signature`` sub-object required fields are enforced
- ``provenance`` sub-object required fields are enforced
- ``additionalProperties: false`` is enforced on the root object
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent / "src" / "uiao" / "schemas" / "reciprocity-record" / "reciprocity-record.schema.json"
)


def _load_schema() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(_SCHEMA_PATH.read_text())
    return result


# ---------------------------------------------------------------------------
# Minimal valid example — all required fields populated with synthetic data
# ---------------------------------------------------------------------------

_MINIMAL_VALID: dict[str, Any] = {
    "schema-version": "1.0.0",
    "controlling_ato_id": "OPM-HRIT-2026-001",
    "consuming_agency_code": "TREAS",
    "reciprocity_basis": (
        "Treasury consumes the OPM HRIT platform under the single controlling ATO "
        "issued by OPM CIO pursuant to PWS §5.1.1 #5."
    ),
    "legal_basis": "interagency-mou",
    "effective_at": "2026-06-01T00:00:00Z",
    "expires_at": "2027-06-01T00:00:00Z",
    "configuration_latitude_ref": "OPM-HRIT-2026-001#latitude/treas-tier-1",
    "signature": {
        "algorithm": "HMAC-SHA256",
        "value": "a" * 64,
        "signed_at": "2026-05-11T12:00:00Z",
        "signer": "CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
    },
    "provenance": {
        "source": "src/uiao/canon/specs/single-ato-reciprocity-model.md",
        "version": "1.0",
        "derived_at": "2026-05-11T12:00:00Z",
        "derived_by": "uiao.oscal.reciprocity_record v0.6.0",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validator() -> Any:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    return jsonschema.Draft202012Validator(schema)


def _validation_errors(instance: dict[str, Any]) -> list[Any]:
    return list(_validator().iter_errors(instance))


def _is_valid(instance: dict[str, Any]) -> bool:
    return not _validation_errors(instance)


def _error_paths_and_messages(instance: dict[str, Any]) -> list[str]:
    errors = _validation_errors(instance)
    return [f"{e.json_path}: {e.message}" for e in errors]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSchemaMeta:
    """The schema itself must be a valid JSON Schema Draft 2020-12 document."""

    def test_schema_file_exists(self) -> None:
        assert _SCHEMA_PATH.exists(), f"Schema not found at {_SCHEMA_PATH}"

    def test_schema_meta_validates(self) -> None:
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema()
        # check_schema raises SchemaError if the schema is malformed
        jsonschema.Draft202012Validator.check_schema(schema)

    def test_schema_id(self) -> None:
        schema = _load_schema()
        assert schema["$id"] == ("https://uiao.gov/schemas/reciprocity-record/reciprocity-record.schema.json")

    def test_schema_draft(self) -> None:
        schema = _load_schema()
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


class TestMinimalValid:
    """A fully-populated minimal example must pass validation."""

    def test_minimal_valid_passes(self) -> None:
        assert _is_valid(_MINIMAL_VALID), _error_paths_and_messages(_MINIMAL_VALID)

    def test_all_legal_basis_enum_values_pass(self) -> None:
        enum_values = [
            "privacy-act-sorn-routine-use",
            "cmppa-matching-agreement",
            "statute",
            "customer-consent",
            "interagency-mou",
        ]
        for value in enum_values:
            instance = {**_MINIMAL_VALID, "legal_basis": value}
            assert _is_valid(instance), (
                f"legal_basis={value!r} should be valid but got errors: {_error_paths_and_messages(instance)}"
            )


class TestEmptyObjectFails:
    """An empty object must fail with errors for all required fields."""

    def test_empty_object_fails(self) -> None:
        jsonschema = pytest.importorskip("jsonschema")
        validator = _validator()
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({})

    def test_empty_object_reports_all_required_fields(self) -> None:
        errors = _validation_errors({})
        # There should be at least one error per required top-level field
        required_fields = {
            "schema-version",
            "controlling_ato_id",
            "consuming_agency_code",
            "reciprocity_basis",
            "legal_basis",
            "effective_at",
            "expires_at",
            "configuration_latitude_ref",
            "signature",
            "provenance",
        }
        # All errors for an empty object come from the 'required' keyword at root
        assert errors, "Expected validation errors on empty object"
        # Collect field names mentioned in errors
        error_messages = " ".join(e.message for e in errors)
        for field in required_fields:
            assert field in error_messages, f"Expected missing-field error for {field!r} but got: {error_messages}"


class TestMissingRequiredFields:
    """Individual required field omissions must each produce a validation error."""

    @pytest.mark.parametrize(
        "field",
        [
            "schema-version",
            "controlling_ato_id",
            "consuming_agency_code",
            "reciprocity_basis",
            "legal_basis",
            "effective_at",
            "expires_at",
            "configuration_latitude_ref",
            "signature",
            "provenance",
        ],
    )
    def test_missing_required_field_fails(self, field: str) -> None:
        instance = {k: v for k, v in _MINIMAL_VALID.items() if k != field}
        assert not _is_valid(instance), f"Expected validation failure when {field!r} is absent"


class TestLegalBasis:
    """legal_basis must be present and must be an allowed enum value."""

    def test_missing_legal_basis_fails(self) -> None:
        instance = {k: v for k, v in _MINIMAL_VALID.items() if k != "legal_basis"}
        assert not _is_valid(instance)

    def test_invalid_legal_basis_fails(self) -> None:
        instance = {**_MINIMAL_VALID, "legal_basis": "not-a-real-basis"}
        assert not _is_valid(instance)

    def test_empty_string_legal_basis_fails(self) -> None:
        instance = {**_MINIMAL_VALID, "legal_basis": ""}
        assert not _is_valid(instance)


class TestConsumingAgencyCode:
    """consuming_agency_code must match ^[A-Z]{3,6}$."""

    def test_lowercase_fails(self) -> None:
        instance = {**_MINIMAL_VALID, "consuming_agency_code": "treas"}
        assert not _is_valid(instance), "consuming_agency_code='treas' (lowercase) should fail pattern ^[A-Z]{3,6}$"

    def test_mixed_case_fails(self) -> None:
        instance = {**_MINIMAL_VALID, "consuming_agency_code": "Treas"}
        assert not _is_valid(instance)

    def test_too_short_fails(self) -> None:
        # Less than 3 uppercase letters
        instance = {**_MINIMAL_VALID, "consuming_agency_code": "AB"}
        assert not _is_valid(instance)

    def test_too_long_fails(self) -> None:
        # More than 6 uppercase letters
        instance = {**_MINIMAL_VALID, "consuming_agency_code": "TOOLONG"}
        assert not _is_valid(instance)

    @pytest.mark.parametrize("code", ["OPM", "TREAS", "SSA", "IRS", "USCIS", "NARA"])
    def test_valid_agency_codes_pass(self, code: str) -> None:
        instance = {**_MINIMAL_VALID, "consuming_agency_code": code}
        assert _is_valid(instance), f"consuming_agency_code={code!r} should be valid"


class TestSignatureObject:
    """signature sub-object required fields and constraints."""

    def test_missing_algorithm_fails(self) -> None:
        sig = {k: v for k, v in _MINIMAL_VALID["signature"].items() if k != "algorithm"}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)

    def test_invalid_algorithm_fails(self) -> None:
        sig = {**_MINIMAL_VALID["signature"], "algorithm": "SHA-256"}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)

    def test_missing_value_fails(self) -> None:
        sig = {k: v for k, v in _MINIMAL_VALID["signature"].items() if k != "value"}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)

    def test_non_hex_value_fails(self) -> None:
        # 64 chars but not hex
        sig = {**_MINIMAL_VALID["signature"], "value": "z" * 64}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)

    def test_short_value_fails(self) -> None:
        # Only 32 hex chars (half a SHA-256)
        sig = {**_MINIMAL_VALID["signature"], "value": "a" * 32}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)

    def test_missing_signed_at_fails(self) -> None:
        sig = {k: v for k, v in _MINIMAL_VALID["signature"].items() if k != "signed_at"}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)

    def test_missing_signer_fails(self) -> None:
        sig = {k: v for k, v in _MINIMAL_VALID["signature"].items() if k != "signer"}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)

    def test_additional_properties_in_signature_fails(self) -> None:
        sig = {**_MINIMAL_VALID["signature"], "extra_field": "unexpected"}
        instance = {**_MINIMAL_VALID, "signature": sig}
        assert not _is_valid(instance)


class TestProvenanceObject:
    """provenance sub-object required fields."""

    @pytest.mark.parametrize("field", ["source", "version", "derived_at", "derived_by"])
    def test_missing_provenance_field_fails(self, field: str) -> None:
        prov = {k: v for k, v in _MINIMAL_VALID["provenance"].items() if k != field}
        instance = {**_MINIMAL_VALID, "provenance": prov}
        assert not _is_valid(instance), f"Expected failure when provenance.{field!r} is absent"

    def test_provenance_extra_properties_allowed(self) -> None:
        # provenance uses additionalProperties: true
        prov = {**_MINIMAL_VALID["provenance"], "canon_refs": ["UIAO_140", "ADR-054"]}
        instance = {**_MINIMAL_VALID, "provenance": prov}
        assert _is_valid(instance)


class TestAdditionalProperties:
    """Root object must reject additional properties (additionalProperties: false)."""

    def test_extra_root_property_fails(self) -> None:
        instance = {**_MINIMAL_VALID, "unexpected_field": "should-be-rejected"}
        assert not _is_valid(instance), "Root object with an extra field should fail due to additionalProperties: false"
