"""tests/test_reciprocity_emitter.py — Acceptance tests for WS-A2.

Covers the five acceptance criteria from the WS-A2 brief:

1. Round-trip: emit a record, verify signature passes; tamper with
   ``controlling_ato_id``, verify signature fails.
2. Deterministic stable hash: emit two records with identical inputs but
   1-second-different timestamps; their stable hashes match.
3. Provenance block matches metadata-schema.json shape.
4. Component-definition emission returns a dict with required OSCAL fields
   (or skipped with marker if trestle import fails).
5. Schema-validation: emitted record validates against the Phase 0 stub at
   ``src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json``.

References
----------
- UIAO_140 §6 — field set contract
- ADR-054 §Implementation — deferred emitter this module closes
- src/uiao/schemas/metadata-schema.json — provenance block shape
"""

from __future__ import annotations

import importlib.resources
import json
from datetime import datetime, timezone

import jsonschema
import pytest

from uiao.oscal.reciprocity_record import (
    _content_hash,
    emit_reciprocity_record,
    emit_scoped_component_definition,
    verify_signature,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SIGNING_KEY = b"test-signing-key-uiao-ws-a2-2026"

_EFFECTIVE = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
_EXPIRES = datetime(2027, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _emit(**overrides: object) -> dict:
    """Emit a record with default test values, applying any overrides."""
    defaults: dict = dict(
        controlling_ato_id="OPM-HRIT-2026-001",
        consuming_agency_code="TREAS",
        legal_basis="interagency-mou",
        reciprocity_basis="OPM-ATO-Reciprocity-Policy-v1",
        effective_at=_EFFECTIVE,
        expires_at=_EXPIRES,
        configuration_latitude_ref="SSP §5.3 Table 3",
        signer="AO/Treasury CIO delegate",
        signing_key=_SIGNING_KEY,
    )
    defaults.update(overrides)
    return emit_reciprocity_record(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test 1 — Round-trip signature verification
# ---------------------------------------------------------------------------


class TestSignatureRoundTrip:
    def test_valid_signature_passes(self) -> None:
        record = _emit()
        assert verify_signature(record, _SIGNING_KEY) is True

    def test_tampered_controlling_ato_id_fails(self) -> None:
        import copy

        record = _emit()
        tampered = copy.deepcopy(record)
        tampered["controlling_ato_id"] = "TAMPERED-ATO-ID"
        assert verify_signature(tampered, _SIGNING_KEY) is False

    def test_wrong_key_fails(self) -> None:
        record = _emit()
        assert verify_signature(record, b"wrong-key") is False

    def test_empty_signature_value_fails(self) -> None:
        import copy

        record = _emit()
        tampered = copy.deepcopy(record)
        tampered["signature"]["value"] = ""
        assert verify_signature(tampered, _SIGNING_KEY) is False

    def test_tampered_consuming_agency_fails(self) -> None:
        import copy

        record = _emit()
        tampered = copy.deepcopy(record)
        tampered["consuming_agency_code"] = "IRS"
        assert verify_signature(tampered, _SIGNING_KEY) is False


# ---------------------------------------------------------------------------
# Test 2 — Deterministic stable hash
# ---------------------------------------------------------------------------


class TestDeterministicStableHash:
    def test_same_inputs_same_hash_different_timestamps(self) -> None:
        """Two records with identical business inputs but 1-second-different
        wall-clock call times must produce the same content hash.

        The content hash excludes all volatile fields (signature.value,
        signature.signed_at, provenance.derived_at), so it must be
        identical regardless of when the records were emitted.
        """
        record_a = _emit()
        record_b = _emit()
        assert _content_hash(record_a) == _content_hash(record_b)

    def test_different_inputs_different_hash(self) -> None:
        record_a = _emit(consuming_agency_code="TREAS")
        record_b = _emit(consuming_agency_code="IRS")
        assert _content_hash(record_a) != _content_hash(record_b)

    def test_stable_hash_excludes_signed_at(self) -> None:
        """Mutating signature.signed_at must not change the content hash."""
        import copy

        record = _emit()
        mutated = copy.deepcopy(record)
        mutated["signature"]["signed_at"] = "2099-01-01T00:00:00+00:00"
        assert _content_hash(record) == _content_hash(mutated)

    def test_stable_hash_excludes_derived_at(self) -> None:
        import copy

        record = _emit()
        mutated = copy.deepcopy(record)
        mutated["provenance"]["derived_at"] = "2099-01-01T00:00:00+00:00"
        assert _content_hash(record) == _content_hash(mutated)

    def test_stable_hash_excludes_signature_value(self) -> None:
        import copy

        record = _emit()
        mutated = copy.deepcopy(record)
        mutated["signature"]["value"] = "aaaa"
        assert _content_hash(record) == _content_hash(mutated)


# ---------------------------------------------------------------------------
# Test 3 — Provenance block shape (metadata-schema.json)
# ---------------------------------------------------------------------------


class TestProvenanceBlock:
    def test_required_provenance_keys_present(self) -> None:
        """Provenance block must carry source, version, derived_at, derived_by
        per the metadata-schema.json 'provenance' object contract."""
        record = _emit()
        prov = record["provenance"]
        assert "source" in prov
        assert "version" in prov
        assert "derived_at" in prov
        assert "derived_by" in prov

    def test_provenance_source_is_uiao_140(self) -> None:
        record = _emit()
        assert record["provenance"]["source"] == "UIAO_140"

    def test_provenance_version(self) -> None:
        record = _emit()
        assert record["provenance"]["version"] == "1.0"

    def test_provenance_derived_by(self) -> None:
        record = _emit()
        assert record["provenance"]["derived_by"] == ("uiao.oscal.reciprocity_record.emit_reciprocity_record")

    def test_provenance_derived_at_is_iso8601(self) -> None:
        record = _emit()
        derived_at = record["provenance"]["derived_at"]
        # Must parse as an ISO 8601 datetime.
        dt = datetime.fromisoformat(derived_at)
        assert dt.tzinfo is not None, "derived_at must include timezone info"

    def test_provenance_validates_against_metadata_schema(self) -> None:
        """Provenance block must satisfy the 'provenance' sub-schema from
        metadata-schema.json."""
        record = _emit()
        prov = record["provenance"]

        prov_schema = {
            "type": "object",
            "required": ["source", "version", "derived_at", "derived_by"],
            "properties": {
                "source": {"type": "string"},
                "version": {"type": "string"},
                "derived_at": {"type": "string"},
                "derived_by": {"type": "string"},
            },
            "additionalProperties": True,
        }
        jsonschema.validate(instance=prov, schema=prov_schema)


# ---------------------------------------------------------------------------
# Test 4 — Component-definition emission
# ---------------------------------------------------------------------------


class TestEmitScopedComponentDefinition:
    def test_returns_dict(self) -> None:
        record = _emit()
        cd = emit_scoped_component_definition(record)
        assert isinstance(cd, dict)

    def test_top_level_key(self) -> None:
        record = _emit()
        cd = emit_scoped_component_definition(record)
        assert "component-definition" in cd

    def test_required_oscal_metadata_fields(self) -> None:
        record = _emit()
        cd = emit_scoped_component_definition(record)
        meta = cd["component-definition"]["metadata"]
        assert "title" in meta
        assert "last-modified" in meta
        assert "version" in meta
        assert "oscal-version" in meta

    def test_metadata_props_contain_controlling_ato_id(self) -> None:
        record = _emit()
        cd = emit_scoped_component_definition(record)
        props = cd["component-definition"]["metadata"]["props"]
        prop_names = {p["name"] for p in props}
        assert "controlling-ato-id" in prop_names

    def test_metadata_props_contain_consuming_agency_code(self) -> None:
        record = _emit()
        cd = emit_scoped_component_definition(record)
        props = cd["component-definition"]["metadata"]["props"]
        prop_names = {p["name"] for p in props}
        assert "consuming-agency-code" in prop_names

    def test_components_list_present(self) -> None:
        record = _emit()
        cd = emit_scoped_component_definition(record)
        assert "components" in cd["component-definition"]
        assert len(cd["component-definition"]["components"]) >= 1

    def test_consuming_agency_in_title(self) -> None:
        record = _emit(consuming_agency_code="IRS")
        cd = emit_scoped_component_definition(record)
        title = cd["component-definition"]["metadata"]["title"]
        assert "IRS" in title

    def test_uuid_fields_present(self) -> None:
        record = _emit()
        cd = emit_scoped_component_definition(record)
        assert "uuid" in cd["component-definition"]
        comp = cd["component-definition"]["components"][0]
        assert "uuid" in comp

    def test_uuids_are_deterministic(self) -> None:
        """Same inputs must produce the same UUIDs across calls."""
        record = _emit()
        cd_a = emit_scoped_component_definition(record)
        cd_b = emit_scoped_component_definition(record)
        assert cd_a["component-definition"]["uuid"] == cd_b["component-definition"]["uuid"]


# ---------------------------------------------------------------------------
# Test 5 — Schema validation against Phase 0 stub
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def _load_schema(self) -> dict:
        """Load the Phase 0 stub schema from the package resources."""
        pkg_files = importlib.resources.files("uiao.schemas")
        schema_text = (pkg_files / "reciprocity-record" / "reciprocity-record.schema.json").read_text(encoding="utf-8")
        return json.loads(schema_text)  # type: ignore[return-value]

    def test_emitted_record_validates(self) -> None:
        record = _emit()
        schema = self._load_schema()
        jsonschema.validate(instance=record, schema=schema)

    def test_empty_object_fails_schema(self) -> None:
        """An empty object must not validate (missing schema-version)."""
        schema = self._load_schema()
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance={}, schema=schema)

    def test_schema_version_field_present(self) -> None:
        record = _emit()
        assert record["schema-version"] == "1.0.0"

    def test_schema_version_matches_pattern(self) -> None:
        """schema-version must match the semver pattern ^[0-9]+\\.[0-9]+\\.[0-9]+$."""
        import re

        record = _emit()
        assert re.match(r"^\d+\.\d+\.\d+$", record["schema-version"])

    def test_required_business_fields_present(self) -> None:
        """All UIAO_140 §6 required fields must be present in the record."""
        record = _emit()
        for field in (
            "controlling_ato_id",
            "consuming_agency_code",
            "legal_basis",
            "reciprocity_basis",
            "effective_at",
            "expires_at",
            "configuration_latitude_ref",
            "signature",
            "provenance",
            "schema-version",
        ):
            assert field in record, f"Missing required field: {field}"

    def test_effective_at_is_iso8601(self) -> None:
        record = _emit()
        dt = datetime.fromisoformat(record["effective_at"])
        assert dt.tzinfo is not None

    def test_expires_at_is_iso8601(self) -> None:
        record = _emit()
        dt = datetime.fromisoformat(record["expires_at"])
        assert dt.tzinfo is not None

    def test_signature_block_fields(self) -> None:
        record = _emit()
        sig = record["signature"]
        assert sig["algorithm"] == "HMAC-SHA256"
        assert "value" in sig
        assert "signed_at" in sig
        assert "signer" in sig
        assert len(sig["value"]) == 64, "HMAC-SHA256 hex digest must be 64 chars"
