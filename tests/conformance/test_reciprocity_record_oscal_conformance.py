"""OSCAL output conformance tests for reciprocity records (WS-B4).

Validates that emitted reciprocity records and bundles conform to:
- The WS-A1 JSON schema (reciprocity-record.schema.json)
- Provenance-manifest SHA-256 hash integrity
- Stable content-hash determinism across two emit calls with same inputs

References
----------
- src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json (WS-A1)
- src/uiao/oscal/reciprocity_record.py (WS-A2)
- src/uiao/oscal/reciprocity_bundle.py (WS-A6)
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §WS-B4
"""

from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Schema path
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "uiao"
    / "schemas"
    / "reciprocity-record"
    / "reciprocity-record.schema.json"
)

# ---------------------------------------------------------------------------
# Module availability guards
# ---------------------------------------------------------------------------

_EMITTER_MODULE = "uiao.oscal.reciprocity_record"
_BUNDLE_MODULE = "uiao.oscal.reciprocity_bundle"


def _require_module(path: str) -> Any:
    try:
        return importlib.import_module(path)
    except ImportError:
        pytest.skip(f"{path} not available — skipping OSCAL conformance tests")


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

_SIGNING_KEY = b"test-conformance-key-do-not-use-in-prod"
_ATO_ID = "OPM-HRIT-2026-001"


def _emit_fixture_record(
    consuming_agency_code: str = "TREAS",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return a fresh reciprocity record for conformance assertions."""
    mod = _require_module(_EMITTER_MODULE)
    _now = now or datetime.now(tz=timezone.utc)
    result: dict[str, Any] = mod.emit_reciprocity_record(
        controlling_ato_id=_ATO_ID,
        consuming_agency_code=consuming_agency_code,
        legal_basis="interagency-mou",
        reciprocity_basis=(
            f"{consuming_agency_code} consumes the OPM HRIT platform "
            "under the single controlling ATO — WS-B4 OSCAL conformance."
        ),
        effective_at=_now,
        expires_at=_now + timedelta(days=365),
        configuration_latitude_ref=f"{_ATO_ID}#latitude/{consuming_agency_code.lower()}-tier-1",
        signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
        signing_key=_SIGNING_KEY,
    )
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReciprocityRecordOscalConformance:
    """OSCAL output conformance tests for emit_reciprocity_record."""

    def test_record_validates_against_schema(self) -> None:
        """Emitted record validates against reciprocity-record.schema.json."""
        jsonschema = pytest.importorskip("jsonschema")
        if not _SCHEMA_PATH.exists():
            pytest.skip(f"WS-A1 schema not found at {_SCHEMA_PATH}")

        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        required_fields = schema.get("required", [])
        if not required_fields:
            pytest.skip("WS-A1 schema stub has no required fields yet (pre-Phase-2)")

        record = _emit_fixture_record()
        validator = jsonschema.Draft202012Validator(schema)
        errors = list(validator.iter_errors(record))
        assert errors == [], f"Schema validation errors: {[e.message for e in errors]}"

    def test_empty_object_fails_schema(self) -> None:
        """Empty object {} fails schema validation (required fields are missing)."""
        jsonschema = pytest.importorskip("jsonschema")
        if not _SCHEMA_PATH.exists():
            pytest.skip(f"WS-A1 schema not found at {_SCHEMA_PATH}")

        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        required_fields = schema.get("required", [])
        if not required_fields:
            pytest.skip("WS-A1 schema stub has no required fields yet (pre-Phase-2)")

        validator = jsonschema.Draft202012Validator(schema)
        errors = list(validator.iter_errors({}))
        assert errors, "Expected schema validation errors for empty object; got none"

    def test_scoped_component_definition_emitted(self) -> None:
        """emit_scoped_component_definition returns a non-empty dict if available."""
        mod = _require_module(_EMITTER_MODULE)
        if not hasattr(mod, "emit_scoped_component_definition"):
            pytest.skip("emit_scoped_component_definition not available in emitter module")

        record = _emit_fixture_record()
        comp_def = mod.emit_scoped_component_definition(record)
        assert isinstance(comp_def, dict), "Component definition must be a dict"
        assert comp_def, "Component definition must be non-empty"
        # Must contain the OSCAL component-definition envelope
        assert "component-definition" in comp_def, "Expected 'component-definition' key in scoped component definition"

    def test_provenance_manifest_hashes_match(
        self,
        controlling_ato_data: dict[str, Any],
        hmac_signing_key: bytes,
        tmp_path: Path,
    ) -> None:
        """provenance-manifest.json file hashes match actual on-disk file hashes."""
        bundle_mod = _require_module(_BUNDLE_MODULE)
        emitter_mod = _require_module(_EMITTER_MODULE)

        now = datetime.now(tz=timezone.utc)
        record: dict[str, Any] = emitter_mod.emit_reciprocity_record(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis="TREAS provenance hash conformance test.",
            effective_at=now,
            expires_at=now + timedelta(days=365),
            configuration_latitude_ref=(f"{controlling_ato_data['controlling_ato_id']}#latitude/treas-tier-1"),
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=hmac_signing_key,
        )
        component_def = emitter_mod.emit_scoped_component_definition(record)
        assessment_results: dict[str, Any] = {
            "assessment-results": {
                "uuid": "00000000-0000-0000-0000-000000000010",
                "metadata": {"title": "Provenance Hash Test", "version": "1.0.0"},
                "import-ap": {"href": "#"},
                "results": [],
            }
        }

        bundle_dir = bundle_mod.aggregate_per_agency_bundle(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="TREAS",
            reciprocity_record=record,
            component_definition=component_def,
            assessment_results=assessment_results,
            output_dir=tmp_path,
        )

        prov_path = bundle_dir / "provenance-manifest.json"
        assert prov_path.exists(), "provenance-manifest.json must exist in bundle"

        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        file_entries: dict[str, Any] = prov.get("files", {})
        assert file_entries, "provenance-manifest.json must contain a 'files' map"

        for fname, entry in file_entries.items():
            fpath = bundle_dir / fname
            assert fpath.exists(), f"Referenced file {fname} must exist in bundle"
            expected_sha = entry.get("sha256", "")
            actual_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
            assert actual_sha == expected_sha, (
                f"Hash mismatch for {fname}: "
                f"provenance-manifest says {expected_sha[:16]}…, "
                f"actual is {actual_sha[:16]}…"
            )

    def test_stable_content_hash_is_deterministic(
        self,
        hmac_signing_key: bytes,
    ) -> None:
        """Stable content hash is identical across two emit calls with the same inputs.

        The stable hash excludes volatile fields (signature.value, signature.signed_at,
        provenance.derived_at). Two calls with identical non-volatile inputs must
        produce the same HMAC value.
        """
        mod = _require_module(_EMITTER_MODULE)

        # Use a fixed point-in-time so effective_at / expires_at are identical.
        fixed_now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)

        record_a: dict[str, Any] = mod.emit_reciprocity_record(
            controlling_ato_id=_ATO_ID,
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis="Determinism test.",
            effective_at=fixed_now,
            expires_at=fixed_now + timedelta(days=365),
            configuration_latitude_ref=f"{_ATO_ID}#latitude/treas-tier-1",
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=hmac_signing_key,
        )
        record_b: dict[str, Any] = mod.emit_reciprocity_record(
            controlling_ato_id=_ATO_ID,
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis="Determinism test.",
            effective_at=fixed_now,
            expires_at=fixed_now + timedelta(days=365),
            configuration_latitude_ref=f"{_ATO_ID}#latitude/treas-tier-1",
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=hmac_signing_key,
        )

        # The HMAC values (stable content hash signed) must match.
        assert record_a["signature"]["value"] == record_b["signature"]["value"], (
            "Stable content hash is not deterministic: two emit calls with identical "
            f"inputs produced different HMAC values:\n"
            f"  call A: {record_a['signature']['value']}\n"
            f"  call B: {record_b['signature']['value']}"
        )
