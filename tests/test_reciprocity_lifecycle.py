"""Reciprocity record lifecycle tests (WS-A9).

Covers the four scenarios specified in ADR-054 §Implementation (deferred test
cases) and the WS-A9 acceptance criteria:

1. Happy path — emit, verify signature, schema-validate.
2. Lapsed ATO — record with expires_at in the past; cadence check asserts FAIL
   on Reauthorization-30.
3. Tamper detection — modify controlling_ato_id after signing; verify fails.
4. Legal-basis validation — invalid enum value fails JSON schema.

All WS-A2/A5 imports are done inside each test via importlib so that a missing
module results in a pytest.skip rather than a collection error.

References
----------
- ADR-054 §Implementation line 163 — deferred happy-path + lapsed-ATO test cases
- ADR-058 §Consequences — 8 blocking CI gates, smoke runs in <60s
- UIAO_143 §7 — ConMon SLA enforcement (30/45/30-day thresholds)
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §WS-A9
"""

from __future__ import annotations

import copy
import importlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Skip helpers — gracefully skip when Batch A modules are not yet merged
# ---------------------------------------------------------------------------

_EMITTER_MODULE = "uiao.oscal.reciprocity_record"
_CADENCE_MODULE = "uiao.monitoring.ato_cadence"
_SCHEMA_PATH = (
    Path(__file__).parent.parent / "src" / "uiao" / "schemas" / "reciprocity-record" / "reciprocity-record.schema.json"
)


def _import_or_skip(module_path: str):  # type: ignore[return]
    """Import *module_path* or skip the current test with an informative message."""
    try:
        return importlib.import_module(module_path)
    except ImportError:
        pytest.skip(f"{module_path} not yet merged (pre-Phase-2)")


def _emit_test_record(
    *,
    consuming_agency_code: str = "TREAS",
    legal_basis: str = "interagency-mou",
    effective_at: datetime | None = None,
    expires_at: datetime | None = None,
    signing_key: bytes = b"test-signing-key-ws-a9-lifecycle",
) -> dict:
    """Helper: emit a reciprocity record using defaults suitable for tests."""
    mod = _import_or_skip(_EMITTER_MODULE)
    emit = mod.emit_reciprocity_record

    now = datetime.now(tz=timezone.utc)
    return emit(
        controlling_ato_id="OPM-HRIT-2026-001",
        consuming_agency_code=consuming_agency_code,
        legal_basis=legal_basis,
        reciprocity_basis=(
            f"{consuming_agency_code} consumes the OPM HRIT platform under "
            "the single controlling ATO issued by OPM CIO (WS-A9 test)."
        ),
        effective_at=effective_at or now,
        expires_at=expires_at or (now + timedelta(days=365)),
        configuration_latitude_ref=f"OPM-HRIT-2026-001#latitude/{consuming_agency_code.lower()}-tier-1",
        signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
        signing_key=signing_key,
    )


# ---------------------------------------------------------------------------
# Shared signing key for lifecycle tests
# ---------------------------------------------------------------------------

_KEY = b"test-signing-key-ws-a9-lifecycle"


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    """Emit a record with valid inputs; verify signature; schema-validate."""

    def test_emit_returns_dict(self) -> None:
        """emit_reciprocity_record returns a non-empty dict."""
        record = _emit_test_record(signing_key=_KEY)
        assert isinstance(record, dict)
        assert record  # non-empty

    def test_required_fields_present(self) -> None:
        """All required top-level fields are present in the emitted record."""
        record = _emit_test_record(signing_key=_KEY)
        required = {
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
        missing = required - set(record.keys())
        assert not missing, f"Missing required fields: {missing}"

    def test_signature_passes(self) -> None:
        """Signature verifies immediately after emission."""
        mod = _import_or_skip(_EMITTER_MODULE)
        record = _emit_test_record(signing_key=_KEY)
        assert mod.verify_signature(record, _KEY) is True

    def test_schema_validates(self) -> None:
        """Emitted record validates against the WS-A1 JSON schema."""
        jsonschema = pytest.importorskip("jsonschema")
        if not _SCHEMA_PATH.exists():
            pytest.skip(f"WS-A1 schema not yet merged: {_SCHEMA_PATH}")

        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        record = _emit_test_record(signing_key=_KEY)
        errors = list(validator.iter_errors(record))
        assert errors == [], f"Schema validation errors: {[e.message for e in errors]}"

    def test_signature_object_fields(self) -> None:
        """Signature sub-object contains all four required fields."""
        record = _emit_test_record(signing_key=_KEY)
        sig = record["signature"]
        for field in ("algorithm", "value", "signed_at", "signer"):
            assert field in sig, f"Signature missing field: {field}"
        assert sig["algorithm"] == "HMAC-SHA256"
        # value must be a 64-char hex string
        assert len(sig["value"]) == 64
        assert all(c in "0123456789abcdef" for c in sig["value"])

    def test_provenance_fields(self) -> None:
        """Provenance sub-object contains all four required fields."""
        record = _emit_test_record(signing_key=_KEY)
        prov = record["provenance"]
        for field in ("source", "version", "derived_at", "derived_by"):
            assert field in prov, f"Provenance missing field: {field}"


# ---------------------------------------------------------------------------
# 2. Lapsed ATO
# ---------------------------------------------------------------------------


class TestLapsedAto:
    """Record with expires_at in the past; cadence check yields FAIL."""

    def test_lapsed_record_emits_successfully(self) -> None:
        """A record with an already-expired expires_at can still be emitted."""
        past = datetime.now(tz=timezone.utc) - timedelta(days=100)
        record = _emit_test_record(
            expires_at=past,
            signing_key=_KEY,
        )
        # Record was emitted; signature should still be valid
        mod = _import_or_skip(_EMITTER_MODULE)
        assert mod.verify_signature(record, _KEY) is True

    def test_lapsed_ato_cadence_fails_reauth_30(self) -> None:
        """evaluate_ato_cadence reports FAIL on Reauthorization-30 when ATO has lapsed."""
        cadence_mod = _import_or_skip(_CADENCE_MODULE)
        AtoCadenceInput = cadence_mod.AtoCadenceInput
        evaluate_ato_cadence = cadence_mod.evaluate_ato_cadence

        award = date(2026, 1, 1)
        expired_ato = date(2026, 3, 1)  # ATO expired > 30 days ago
        now_dt = datetime(2026, 5, 11, tzinfo=timezone.utc)  # well past expiry

        inp = AtoCadenceInput(
            award_date=award,
            ssp_draft_submitted_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            ssp_final_submitted_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            current_ato_expires_at=expired_ato,
            now=now_dt,
        )
        report = evaluate_ato_cadence(inp)

        reauth_verdict = next(v for v in report.verdicts if v.name == "Reauthorization-30")
        assert reauth_verdict.verdict == "FAIL", (
            f"Expected FAIL on Reauthorization-30 for lapsed ATO; "
            f"got {reauth_verdict.verdict}: {reauth_verdict.message}"
        )
        assert report.overall == "FAIL"

    def test_lapsed_record_schema_validates(self) -> None:
        """A lapsed record (past expires_at) still schema-validates — schema does not enforce future dates."""
        jsonschema = pytest.importorskip("jsonschema")
        if not _SCHEMA_PATH.exists():
            pytest.skip(f"WS-A1 schema not yet merged: {_SCHEMA_PATH}")

        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)

        past = datetime.now(tz=timezone.utc) - timedelta(days=100)
        record = _emit_test_record(expires_at=past, signing_key=_KEY)
        errors = list(validator.iter_errors(record))
        assert errors == [], f"Lapsed record should still schema-validate; got: {[e.message for e in errors]}"


# ---------------------------------------------------------------------------
# 3. Tamper detection
# ---------------------------------------------------------------------------


class TestTamperDetection:
    """Modifying a signed field invalidates the signature."""

    def test_tamper_controlling_ato_id_fails_verification(self) -> None:
        """Changing controlling_ato_id after signing causes verify_signature to return False."""
        mod = _import_or_skip(_EMITTER_MODULE)
        record = _emit_test_record(signing_key=_KEY)

        # Confirm original signature is valid
        assert mod.verify_signature(record, _KEY) is True

        # Tamper with a stable field
        tampered = copy.deepcopy(record)
        tampered["controlling_ato_id"] = "TAMPERED-ATO-ID-99"

        assert mod.verify_signature(tampered, _KEY) is False

    def test_tamper_consuming_agency_code_fails_verification(self) -> None:
        """Changing consuming_agency_code after signing invalidates the signature."""
        mod = _import_or_skip(_EMITTER_MODULE)
        record = _emit_test_record(signing_key=_KEY)

        tampered = copy.deepcopy(record)
        tampered["consuming_agency_code"] = "TAMRD"

        assert mod.verify_signature(tampered, _KEY) is False

    def test_tamper_legal_basis_fails_verification(self) -> None:
        """Changing legal_basis after signing invalidates the signature."""
        mod = _import_or_skip(_EMITTER_MODULE)
        record = _emit_test_record(signing_key=_KEY)

        tampered = copy.deepcopy(record)
        tampered["legal_basis"] = "statute"

        assert mod.verify_signature(tampered, _KEY) is False

    def test_wrong_key_fails_verification(self) -> None:
        """Verifying with a different key returns False."""
        mod = _import_or_skip(_EMITTER_MODULE)
        record = _emit_test_record(signing_key=_KEY)

        wrong_key = b"wrong-key-not-used-during-emission"
        assert mod.verify_signature(record, wrong_key) is False

    def test_volatile_field_change_does_not_break_verification(self) -> None:
        """Changing a volatile field (signature.signed_at) does NOT invalidate the signature.

        Per the stable-hash contract, signed_at is excluded from the content hash.
        """
        mod = _import_or_skip(_EMITTER_MODULE)
        record = _emit_test_record(signing_key=_KEY)

        # Volatile field change — should still verify
        mutated = copy.deepcopy(record)
        mutated["signature"]["signed_at"] = "2099-01-01T00:00:00+00:00"

        assert mod.verify_signature(mutated, _KEY) is True


# ---------------------------------------------------------------------------
# 4. Legal-basis validation
# ---------------------------------------------------------------------------


class TestLegalBasisValidation:
    """Records with invalid legal_basis fail JSON schema validation."""

    def _validate(self, record: dict) -> list:
        jsonschema = pytest.importorskip("jsonschema")
        if not _SCHEMA_PATH.exists():
            pytest.skip(f"WS-A1 schema not yet merged: {_SCHEMA_PATH}")
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        return list(jsonschema.Draft202012Validator(schema).iter_errors(record))

    def test_invalid_legal_basis_fails_schema(self) -> None:
        """A record with legal_basis='invalid-value' fails schema validation."""
        record = _emit_test_record(signing_key=_KEY)
        record["legal_basis"] = "invalid-value"
        errors = self._validate(record)
        assert errors, "Expected schema validation failure for invalid legal_basis"

    def test_empty_legal_basis_fails_schema(self) -> None:
        """A record with legal_basis='' fails schema validation."""
        record = _emit_test_record(signing_key=_KEY)
        record["legal_basis"] = ""
        errors = self._validate(record)
        assert errors, "Expected schema validation failure for empty legal_basis"

    def test_none_legal_basis_fails_schema(self) -> None:
        """A record with legal_basis omitted fails schema validation."""
        record = _emit_test_record(signing_key=_KEY)
        del record["legal_basis"]
        errors = self._validate(record)
        assert errors, "Expected schema validation failure for missing legal_basis"

    @pytest.mark.parametrize(
        "valid_basis",
        [
            "privacy-act-sorn-routine-use",
            "cmppa-matching-agreement",
            "statute",
            "customer-consent",
            "interagency-mou",
        ],
    )
    def test_valid_legal_basis_passes_schema(self, valid_basis: str) -> None:
        """Each valid enum value passes schema validation."""
        record = _emit_test_record(signing_key=_KEY)
        # Re-emit with the desired legal_basis (emitter signs with it)
        record["legal_basis"] = valid_basis
        # Reset the signature to avoid stale-sig confusion
        # (the schema does not verify the HMAC, only the shape)
        errors = self._validate(record)
        # legal_basis is valid; any remaining errors are unrelated
        legal_basis_errors = [e for e in errors if "legal_basis" in e.json_path]
        assert not legal_basis_errors, (
            f"Unexpected schema error for legal_basis={valid_basis!r}: {[e.message for e in legal_basis_errors]}"
        )
