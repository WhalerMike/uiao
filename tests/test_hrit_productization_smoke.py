"""Smoke tests for HRIT Single-ATO Productization (WS-A9).

Verifies that each runtime module introduced in Batch A is either importable
with its expected public attribute, or skipped gracefully when the workstream
has not yet merged (pre-Phase-2).

A full lifecycle integration test (Phase 2+) is included but marked to skip
individually if any required module is unavailable.

References
----------
- ADR-054 §Implementation (deferred test cases now closed by this module)
- ADR-058 — HRIT Productization mission theme
- UIAO_144 §4–9 — Operational spec for each runtime component
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §WS-A9
"""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Module / attribute importability checks (always run, skip on ImportError)
# ---------------------------------------------------------------------------

_MODULE_ATTRS = [
    ("uiao.oscal.reciprocity_record", "emit_reciprocity_record"),
    ("uiao.oscal.reciprocity_bundle", "aggregate_per_agency_bundle"),
    ("uiao.monitoring.ato_cadence", "evaluate_ato_cadence"),
    ("uiao.governance.config_latitude", "detect_latitude_drift"),
    ("uiao.cli.reciprocity", "reciprocity_app"),
]


@pytest.mark.parametrize("module_path,attr", _MODULE_ATTRS)
def test_module_attribute_is_importable_or_skipped(module_path: str, attr: str) -> None:
    """Each Batch A module is importable with its expected public attribute.

    Skips cleanly when the module is not yet merged (pre-Phase-2).
    """
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        pytest.skip(f"{module_path} not yet merged (pre-Phase-2)")
    assert hasattr(mod, attr), f"{module_path} missing {attr}"


# ---------------------------------------------------------------------------
# Fixtures — resolve paths to WS-A8 example files
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent.parent / "examples" / "hrit" / "opm-treas-irs"
_SSP_LATITUDE_TABLE = _FIXTURE_DIR / "ssp-latitude-table.yaml"
_TENANT_TREAS_CONFIG = _FIXTURE_DIR / "tenant-treas-config.yaml"
_TENANT_IRS_CONFIG = _FIXTURE_DIR / "tenant-irs-config.yaml"
_SCHEMA_PATH = (
    Path(__file__).parent.parent / "src" / "uiao" / "schemas" / "reciprocity-record" / "reciprocity-record.schema.json"
)


def _all_hrit_modules_available() -> bool:
    """Return True only when every Batch A module is importable."""
    for module_path, _ in _MODULE_ATTRS:
        try:
            importlib.import_module(module_path)
        except ImportError:
            return False
    return True


# ---------------------------------------------------------------------------
# Helpers — parse YAML fixture files without requiring PyYAML at import time
# ---------------------------------------------------------------------------


def _load_yaml_fixture(path: Path) -> dict:  # type: ignore[type-arg]
    """Load a YAML fixture file.  Skips the test if PyYAML is unavailable."""
    try:
        import yaml  # type: ignore[import-untyped]  # noqa: PLC0415
    except ImportError:
        pytest.skip("PyYAML not installed — cannot parse HRIT fixture files")
    return yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _build_ssp_latitude_table(raw: dict) -> Any:  # type: ignore[type-arg]
    """Construct a SspLatitudeTable from the raw fixture dict."""
    from uiao.governance.config_latitude import (  # noqa: PLC0415
        LatitudeTableEntry,
        SspLatitudeTable,
    )

    entries = []
    for item in raw.get("latitude_settings", []):
        entries.append(
            LatitudeTableEntry(
                setting_key=item["key"],
                allowed_values=item.get("allowed_values"),
                allowed_pattern=item.get("allowed_pattern"),
                notes=item.get("description"),
            )
        )
    return SspLatitudeTable(
        controlling_ato_id=raw["controlling_ato_id"],
        entries=entries,
    )


def _build_tenant_config(raw: dict) -> Any:  # type: ignore[type-arg]
    """Construct a TenantConfig from the raw fixture dict."""
    from uiao.governance.config_latitude import TenantConfig, TenantConfigEntry  # noqa: PLC0415

    entries = [TenantConfigEntry(setting_key=k, observed_value=str(v)) for k, v in raw.get("configuration", {}).items()]
    return TenantConfig(
        consuming_agency_code=raw["consuming_agency_code"],
        entries=entries,
    )


# ---------------------------------------------------------------------------
# Phase-2 integration test — full lifecycle once all modules are merged
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _all_hrit_modules_available() or not _SSP_LATITUDE_TABLE.exists(),
    reason="One or more Batch A modules or WS-A8 fixtures not yet merged (pre-Phase-2)",
)
class TestHritProductizationLifecycle:
    """Full lifecycle smoke against the WS-A8 OPM/TREAS/IRS fixture.

    Exercises each runtime piece in sequence:
        1. Load SSP latitude table from fixture
        2. Treasury config — expect zero findings
        3. IRS config — expect exactly 1 DRIFT-SCHEMA P2 finding
        4. Emit a reciprocity record for TREAS
        5. Verify the signature
        6. Aggregate the bundle to tmp_path
        7. Verify the bundle
    """

    _SIGNING_KEY = b"test-hmac-signing-key-ws-a9-smoke"

    def test_fixture_files_exist(self) -> None:
        """All WS-A8 fixture files must exist."""
        for path in (_SSP_LATITUDE_TABLE, _TENANT_TREAS_CONFIG, _TENANT_IRS_CONFIG):
            assert path.exists(), f"Fixture file missing: {path}"

    def test_schema_file_exists(self) -> None:
        """WS-A1 schema file must exist."""
        assert _SCHEMA_PATH.exists(), f"Schema missing: {_SCHEMA_PATH}"

    def test_treas_config_zero_findings(self) -> None:
        """Treasury config (conforming) produces zero latitude-drift findings."""
        from uiao.governance.config_latitude import detect_latitude_drift  # noqa: PLC0415

        raw_table = _load_yaml_fixture(_SSP_LATITUDE_TABLE)
        raw_treas = _load_yaml_fixture(_TENANT_TREAS_CONFIG)
        ssp_table = _build_ssp_latitude_table(raw_table)
        treas_config = _build_tenant_config(raw_treas)

        findings = detect_latitude_drift(ssp_table, treas_config)
        assert findings == [], f"Expected zero findings for TREAS; got: {[f.model_dump() for f in findings]}"

    def test_irs_config_one_drift_finding(self) -> None:
        """IRS config (one violation) produces exactly one DRIFT-SCHEMA P2 finding."""
        from uiao.governance.config_latitude import detect_latitude_drift  # noqa: PLC0415

        raw_table = _load_yaml_fixture(_SSP_LATITUDE_TABLE)
        raw_irs = _load_yaml_fixture(_TENANT_IRS_CONFIG)
        ssp_table = _build_ssp_latitude_table(raw_table)
        irs_config = _build_tenant_config(raw_irs)

        findings = detect_latitude_drift(ssp_table, irs_config)
        assert len(findings) == 1, (
            f"Expected exactly 1 finding for IRS; got {len(findings)}: {[f.model_dump() for f in findings]}"
        )
        finding = findings[0]
        assert finding.verdict == "OUT_OF_LATITUDE"
        assert finding.severity == "P2"
        assert finding.setting_key == "password_minimum_length"
        assert finding.drift_class == "DRIFT-SCHEMA"

    def test_emit_treas_reciprocity_record(self) -> None:
        """Emitting a TREAS reciprocity record returns a schema-valid dict."""
        from uiao.oscal.reciprocity_record import emit_reciprocity_record  # noqa: PLC0415

        now = datetime.now(tz=timezone.utc)
        record = emit_reciprocity_record(
            controlling_ato_id="OPM-HRIT-2026-001",
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis=(
                "Treasury consumes the OPM HRIT platform under the single "
                "controlling ATO issued by OPM CIO pursuant to PWS §5.1.1 #5."
            ),
            effective_at=now,
            expires_at=now + timedelta(days=365),
            configuration_latitude_ref="OPM-HRIT-2026-001#latitude/treas-tier-1",
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=self._SIGNING_KEY,
        )
        assert record["consuming_agency_code"] == "TREAS"
        assert record["controlling_ato_id"] == "OPM-HRIT-2026-001"
        assert record["legal_basis"] == "interagency-mou"
        assert "signature" in record
        assert record["signature"]["algorithm"] == "HMAC-SHA256"

    def test_verify_treas_signature(self) -> None:
        """Signature on the TREAS reciprocity record verifies with the same key."""
        from uiao.oscal.reciprocity_record import (  # noqa: PLC0415
            emit_reciprocity_record,
            verify_signature,
        )

        now = datetime.now(tz=timezone.utc)
        record = emit_reciprocity_record(
            controlling_ato_id="OPM-HRIT-2026-001",
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis="Treasury consumes OPM HRIT under single ATO.",
            effective_at=now,
            expires_at=now + timedelta(days=365),
            configuration_latitude_ref="OPM-HRIT-2026-001#latitude/treas-tier-1",
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=self._SIGNING_KEY,
        )
        assert verify_signature(record, self._SIGNING_KEY) is True

    def test_record_schema_validates(self) -> None:
        """Emitted TREAS record validates against the WS-A1 JSON schema."""
        jsonschema = pytest.importorskip("jsonschema")
        from uiao.oscal.reciprocity_record import emit_reciprocity_record  # noqa: PLC0415

        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)

        now = datetime.now(tz=timezone.utc)
        record = emit_reciprocity_record(
            controlling_ato_id="OPM-HRIT-2026-001",
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis="Treasury consumes OPM HRIT under single ATO.",
            effective_at=now,
            expires_at=now + timedelta(days=365),
            configuration_latitude_ref="OPM-HRIT-2026-001#latitude/treas-tier-1",
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=self._SIGNING_KEY,
        )
        errors = list(validator.iter_errors(record))
        assert errors == [], f"Schema validation errors: {[e.message for e in errors]}"

    def test_aggregate_treas_bundle(self, tmp_path: Path) -> None:
        """Bundle aggregation for TREAS writes all expected files and verifies ok."""
        from uiao.oscal.reciprocity_bundle import (  # noqa: PLC0415
            aggregate_per_agency_bundle,
            verify_bundle,
        )
        from uiao.oscal.reciprocity_record import (  # noqa: PLC0415
            emit_reciprocity_record,
            emit_scoped_component_definition,
        )

        now = datetime.now(tz=timezone.utc)
        record = emit_reciprocity_record(
            controlling_ato_id="OPM-HRIT-2026-001",
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis="Treasury consumes OPM HRIT under single ATO.",
            effective_at=now,
            expires_at=now + timedelta(days=365),
            configuration_latitude_ref="OPM-HRIT-2026-001#latitude/treas-tier-1",
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=self._SIGNING_KEY,
        )
        component_def = emit_scoped_component_definition(record)
        assessment_results: dict[str, Any] = {
            "assessment-results": {
                "uuid": "00000000-0000-0000-0000-000000000001",
                "metadata": {"title": "TREAS Assessment Results (smoke)", "version": "1.0.0"},
                "import-ap": {"href": "#"},
                "results": [],
            }
        }

        bundle_dir = aggregate_per_agency_bundle(
            controlling_ato_id="OPM-HRIT-2026-001",
            consuming_agency_code="TREAS",
            reciprocity_record=record,
            component_definition=component_def,
            assessment_results=assessment_results,
            output_dir=tmp_path,
        )

        assert bundle_dir.is_dir()
        result = verify_bundle(bundle_dir)
        assert result["ok"] is True, f"Bundle verification failed: {result['errors']}"
