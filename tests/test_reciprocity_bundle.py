"""Tests for uiao.oscal.reciprocity_bundle (WS-A6).

Acceptance criteria
-------------------
1. Round-trip: emit a bundle with synthetic dicts → verify_bundle returns ok=True.
2. Tamper: modify one byte of ``reciprocity-record.json`` → ok=False with the
   right error string.
3. Missing-file: delete ``component-definition.json`` → ok=False.
4. Provenance manifest contains ``source: UIAO_140``, ``version: 1.0``,
   ``derived_at`` populated.
5. Bundle dir layout matches expected file set exactly (no extras, no missing).
"""

from __future__ import annotations

import json
from pathlib import Path

from uiao.oscal.reciprocity_bundle import aggregate_per_agency_bundle, verify_bundle

# ---------------------------------------------------------------------------
# Synthetic test fixtures (mock WS-A2 outputs)
# ---------------------------------------------------------------------------

_RECIPROCITY_RECORD: dict = {
    "controlling_ato_id": "OPM-HRIT-2026-001",
    "consuming_agency_code": "TREAS",
    "reciprocity_basis": "single-ato-reciprocity",
    "legal_basis": "interagency-mou",
    "effective_at": "2026-01-01T00:00:00Z",
    "expires_at": "2027-01-01T00:00:00Z",
    "configuration_latitude_ref": "opm-hrit-config-latitude-v1",
    "signature": {
        "algorithm": "HMAC-SHA256",
        "value": "deadbeefcafe0000",
        "signed_at": "2026-01-01T00:00:00Z",
        "signer": "opm-uiao-pipeline",
    },
    "provenance": {
        "source": "UIAO_140",
        "version": "1.0",
        "derived_at": "2026-01-01T00:00:00Z",
    },
}

_COMPONENT_DEFINITION: dict = {
    "component-definition": {
        "uuid": "11111111-0000-0000-0000-000000000001",
        "metadata": {
            "title": "HRIT Component Definition — TREAS",
            "last-modified": "2026-01-01T00:00:00Z",
            "version": "1.0",
            "oscal-version": "1.0.4",
        },
        "components": [
            {
                "uuid": "22222222-0000-0000-0000-000000000002",
                "type": "software",
                "title": "OPM HRIT Platform (TREAS scope)",
                "description": "Synthetic component for test.",
            }
        ],
    }
}

_ASSESSMENT_RESULTS: dict = {
    "assessment-results": {
        "uuid": "33333333-0000-0000-0000-000000000003",
        "metadata": {
            "title": "HRIT Assessment Results — TREAS",
            "last-modified": "2026-01-01T00:00:00Z",
            "version": "1.0",
            "oscal-version": "1.0.4",
        },
        "import-ap": {"href": "#"},
        "results": [
            {
                "uuid": "44444444-0000-0000-0000-000000000004",
                "title": "TREAS reciprocity assessment",
                "description": "Synthetic result for test.",
                "start": "2026-01-01T00:00:00Z",
                "reviewed-controls": {
                    "control-selections": [{"include-all": {}}],
                },
            }
        ],
    }
}

_EXPECTED_FILES: frozenset[str] = frozenset(
    {
        "reciprocity-record.json",
        "component-definition.json",
        "assessment-results.json",
        "provenance-manifest.json",
        "BUNDLE-MANIFEST.txt",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bundle(tmp_path: Path, agency: str = "TREAS") -> Path:
    """Create a bundle in tmp_path and return the bundle directory."""
    return aggregate_per_agency_bundle(
        controlling_ato_id="OPM-HRIT-2026-001",
        consuming_agency_code=agency,
        reciprocity_record=_RECIPROCITY_RECORD,
        component_definition=_COMPONENT_DEFINITION,
        assessment_results=_ASSESSMENT_RESULTS,
        output_dir=tmp_path,
    )


# ---------------------------------------------------------------------------
# Test 1 — Round-trip
# ---------------------------------------------------------------------------


def test_round_trip_ok(tmp_path: Path) -> None:
    """Acceptance #1: emit then verify returns ok=True with no errors."""
    bundle_dir = _make_bundle(tmp_path)
    result = verify_bundle(bundle_dir)
    assert result["ok"] is True, f"Expected ok=True, got errors: {result['errors']}"
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# Test 2 — Tamper detection
# ---------------------------------------------------------------------------


def test_tamper_reciprocity_record(tmp_path: Path) -> None:
    """Acceptance #2: modifying reciprocity-record.json causes ok=False."""
    bundle_dir = _make_bundle(tmp_path)

    rr_path = bundle_dir / "reciprocity-record.json"
    original = rr_path.read_bytes()
    # Flip the last non-newline byte to introduce a single-byte change.
    tampered = bytearray(original)
    tampered[-2] ^= 0x01  # XOR last content byte
    rr_path.write_bytes(bytes(tampered))

    result = verify_bundle(bundle_dir)
    assert result["ok"] is False
    # At least one error should mention reciprocity-record.json
    error_text = " ".join(result["errors"])
    assert "reciprocity-record.json" in error_text, (
        f"Expected error mentioning reciprocity-record.json, got: {result['errors']}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Missing file
# ---------------------------------------------------------------------------


def test_missing_component_definition(tmp_path: Path) -> None:
    """Acceptance #3: deleting component-definition.json causes ok=False."""
    bundle_dir = _make_bundle(tmp_path)
    (bundle_dir / "component-definition.json").unlink()

    result = verify_bundle(bundle_dir)
    assert result["ok"] is False
    error_text = " ".join(result["errors"])
    assert "component-definition.json" in error_text, (
        f"Expected error mentioning component-definition.json, got: {result['errors']}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Provenance manifest contents
# ---------------------------------------------------------------------------


def test_provenance_manifest_fields(tmp_path: Path) -> None:
    """Acceptance #4: provenance manifest has source, version, derived_at."""
    bundle_dir = _make_bundle(tmp_path)
    prov_path = bundle_dir / "provenance-manifest.json"
    assert prov_path.exists(), "provenance-manifest.json must exist"

    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    provenance_block = prov["provenance"]

    assert provenance_block["source"] == "UIAO_140", f"Expected source='UIAO_140', got {provenance_block['source']!r}"
    assert provenance_block["version"] == "1.0", f"Expected version='1.0', got {provenance_block['version']!r}"
    derived_at = provenance_block.get("derived_at", "")
    assert derived_at, "provenance.derived_at must be non-empty"
    # derived_at should look like an ISO-8601 timestamp
    assert "T" in derived_at or "-" in derived_at, f"derived_at does not look like a timestamp: {derived_at!r}"
    # ADR reference must be present
    assert provenance_block.get("adr_ref") == "ADR-054", (
        f"Expected adr_ref='ADR-054', got {provenance_block.get('adr_ref')!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Bundle layout: exact file set
# ---------------------------------------------------------------------------


def test_bundle_dir_layout(tmp_path: Path) -> None:
    """Acceptance #5: bundle directory contains exactly the expected files."""
    bundle_dir = _make_bundle(tmp_path)
    actual_files = {p.name for p in bundle_dir.iterdir() if p.is_file()}
    assert actual_files == _EXPECTED_FILES, (
        f"File set mismatch.\n  Extra  : {actual_files - _EXPECTED_FILES}\n  Missing: {_EXPECTED_FILES - actual_files}"
    )


# ---------------------------------------------------------------------------
# Additional: verify_bundle on non-existent dir
# ---------------------------------------------------------------------------


def test_verify_missing_manifest(tmp_path: Path) -> None:
    """verify_bundle returns ok=False when the bundle dir is empty."""
    empty = tmp_path / "EMPTY"
    empty.mkdir()
    result = verify_bundle(empty)
    assert result["ok"] is False
    assert any("BUNDLE-MANIFEST.txt" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Additional: agency code becomes the sub-directory name
# ---------------------------------------------------------------------------


def test_bundle_dir_named_by_agency(tmp_path: Path) -> None:
    """The bundle directory name must equal the consuming_agency_code."""
    bundle_dir = _make_bundle(tmp_path, agency="IRS")
    assert bundle_dir.name == "IRS"
    assert bundle_dir.parent.resolve() == tmp_path.resolve()


# ---------------------------------------------------------------------------
# Additional: multiple agencies in the same output_dir are isolated
# ---------------------------------------------------------------------------


def test_multiple_agencies_isolated(tmp_path: Path) -> None:
    """Two bundles for different agencies must not cross-contaminate."""
    dir_treas = _make_bundle(tmp_path, agency="TREAS")
    dir_irs = _make_bundle(tmp_path, agency="IRS")

    assert verify_bundle(dir_treas)["ok"] is True
    assert verify_bundle(dir_irs)["ok"] is True

    treas_files = {p.name for p in dir_treas.iterdir() if p.is_file()}
    irs_files = {p.name for p in dir_irs.iterdir() if p.is_file()}
    assert treas_files == _EXPECTED_FILES
    assert irs_files == _EXPECTED_FILES
