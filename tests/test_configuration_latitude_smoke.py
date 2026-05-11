"""Configuration-latitude drift detector smoke tests (WS-A9).

Verifies the WS-A7 detect_latitude_drift function against the WS-A8 fixture
data:
  - Treasury config (conforming) → zero findings
  - IRS config (one violation) → exactly one finding with verdict
    OUT_OF_LATITUDE, severity P2, setting_key=password_minimum_length,
    drift_class=DRIFT-SCHEMA

All WS-A7 imports are done inside each test via importlib so that a missing
module results in a pytest.skip rather than a collection error.

References
----------
- UIAO_140 §5 — DRIFT-SCHEMA when tenant config not in SSP latitude table
- ADR-058 §Consequences — configuration-latitude drift finding triggers P1
  substrate-drift surface
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §WS-A7, §WS-A8, §WS-A9
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module / fixture paths
# ---------------------------------------------------------------------------

_LATITUDE_MODULE = "uiao.governance.config_latitude"

_FIXTURE_DIR = Path(__file__).parent.parent / "examples" / "hrit" / "opm-treas-irs"
_SSP_LATITUDE_TABLE = _FIXTURE_DIR / "ssp-latitude-table.yaml"
_TENANT_TREAS_CONFIG = _FIXTURE_DIR / "tenant-treas-config.yaml"
_TENANT_IRS_CONFIG = _FIXTURE_DIR / "tenant-irs-config.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_latitude_module():  # type: ignore[return]
    """Import the config_latitude module or skip with an informative message."""
    try:
        return importlib.import_module(_LATITUDE_MODULE)
    except ImportError:
        pytest.skip(f"{_LATITUDE_MODULE} not yet merged (pre-Phase-2)")


def _load_yaml(path: Path) -> dict:
    """Load a YAML file; skip if PyYAML unavailable or file missing."""
    if not path.exists():
        pytest.skip(f"WS-A8 fixture not yet merged: {path}")
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        pytest.skip("PyYAML not installed — cannot parse HRIT fixture files")
    return yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _build_ssp_latitude_table(mod, raw: dict):  # type: ignore[return]
    """Construct a SspLatitudeTable from a raw fixture dict using *mod* classes."""
    entries = []
    for item in raw.get("latitude_settings", []):
        entries.append(
            mod.LatitudeTableEntry(
                setting_key=item["key"],
                allowed_values=item.get("allowed_values"),
                allowed_pattern=item.get("allowed_pattern"),
                notes=item.get("description"),
            )
        )
    return mod.SspLatitudeTable(
        controlling_ato_id=raw["controlling_ato_id"],
        entries=entries,
    )


def _build_tenant_config(mod, raw: dict):  # type: ignore[return]
    """Construct a TenantConfig from a raw fixture dict using *mod* classes."""
    entries = [
        mod.TenantConfigEntry(setting_key=k, observed_value=str(v)) for k, v in raw.get("configuration", {}).items()
    ]
    return mod.TenantConfig(
        consuming_agency_code=raw["consuming_agency_code"],
        entries=entries,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTreasuryConformingConfig:
    """Treasury config is fully conforming — expect zero findings."""

    def test_fixture_file_exists(self) -> None:
        """WS-A8 Treasury fixture must be present."""
        if not _TENANT_TREAS_CONFIG.exists():
            pytest.skip(f"WS-A8 fixture not yet merged: {_TENANT_TREAS_CONFIG}")
        assert _TENANT_TREAS_CONFIG.exists()

    def test_zero_findings(self) -> None:
        """All ten TREAS configuration settings conform to the SSP latitude table."""
        mod = _import_latitude_module()
        raw_table = _load_yaml(_SSP_LATITUDE_TABLE)
        raw_treas = _load_yaml(_TENANT_TREAS_CONFIG)

        ssp_table = _build_ssp_latitude_table(mod, raw_table)
        treas_config = _build_tenant_config(mod, raw_treas)

        findings = mod.detect_latitude_drift(ssp_table, treas_config)
        assert findings == [], (
            f"Expected zero findings for conforming TREAS config; "
            f"got {len(findings)}: {[f.model_dump() for f in findings]}"
        )

    def test_treas_consuming_agency_code(self) -> None:
        """Raw fixture has the correct consuming_agency_code."""
        raw = _load_yaml(_TENANT_TREAS_CONFIG)
        assert raw.get("consuming_agency_code") == "TREAS"

    def test_treas_controlling_ato_id(self) -> None:
        """Raw fixture references the correct controlling ATO."""
        raw = _load_yaml(_TENANT_TREAS_CONFIG)
        assert raw.get("controlling_ato_id") == "OPM-HRIT-2026-001"


class TestIrsOneViolation:
    """IRS config has one intentional violation — expect exactly one finding."""

    def test_fixture_file_exists(self) -> None:
        """WS-A8 IRS fixture must be present."""
        if not _TENANT_IRS_CONFIG.exists():
            pytest.skip(f"WS-A8 fixture not yet merged: {_TENANT_IRS_CONFIG}")
        assert _TENANT_IRS_CONFIG.exists()

    def test_exactly_one_finding(self) -> None:
        """IRS config produces exactly one DRIFT-SCHEMA finding."""
        mod = _import_latitude_module()
        raw_table = _load_yaml(_SSP_LATITUDE_TABLE)
        raw_irs = _load_yaml(_TENANT_IRS_CONFIG)

        ssp_table = _build_ssp_latitude_table(mod, raw_table)
        irs_config = _build_tenant_config(mod, raw_irs)

        findings = mod.detect_latitude_drift(ssp_table, irs_config)
        assert len(findings) == 1, (
            f"Expected exactly 1 finding for IRS; got {len(findings)}: {[f.model_dump() for f in findings]}"
        )

    def test_finding_verdict_out_of_latitude(self) -> None:
        """The single IRS finding has verdict OUT_OF_LATITUDE."""
        mod = _import_latitude_module()
        raw_table = _load_yaml(_SSP_LATITUDE_TABLE)
        raw_irs = _load_yaml(_TENANT_IRS_CONFIG)

        ssp_table = _build_ssp_latitude_table(mod, raw_table)
        irs_config = _build_tenant_config(mod, raw_irs)

        findings = mod.detect_latitude_drift(ssp_table, irs_config)
        assert len(findings) >= 1
        finding = findings[0]
        assert finding.verdict == "OUT_OF_LATITUDE", f"Expected OUT_OF_LATITUDE; got {finding.verdict}"

    def test_finding_severity_p2(self) -> None:
        """The IRS finding has severity P2 (per UIAO_140 §5 default)."""
        mod = _import_latitude_module()
        raw_table = _load_yaml(_SSP_LATITUDE_TABLE)
        raw_irs = _load_yaml(_TENANT_IRS_CONFIG)

        ssp_table = _build_ssp_latitude_table(mod, raw_table)
        irs_config = _build_tenant_config(mod, raw_irs)

        findings = mod.detect_latitude_drift(ssp_table, irs_config)
        assert len(findings) >= 1
        assert findings[0].severity == "P2"

    def test_finding_setting_key_password_minimum_length(self) -> None:
        """The IRS finding is for setting_key=password_minimum_length."""
        mod = _import_latitude_module()
        raw_table = _load_yaml(_SSP_LATITUDE_TABLE)
        raw_irs = _load_yaml(_TENANT_IRS_CONFIG)

        ssp_table = _build_ssp_latitude_table(mod, raw_table)
        irs_config = _build_tenant_config(mod, raw_irs)

        findings = mod.detect_latitude_drift(ssp_table, irs_config)
        assert len(findings) >= 1
        assert findings[0].setting_key == "password_minimum_length", (
            f"Expected setting_key='password_minimum_length'; got '{findings[0].setting_key}'"
        )

    def test_finding_drift_class_drift_schema(self) -> None:
        """The IRS finding has drift_class=DRIFT-SCHEMA."""
        mod = _import_latitude_module()
        raw_table = _load_yaml(_SSP_LATITUDE_TABLE)
        raw_irs = _load_yaml(_TENANT_IRS_CONFIG)

        ssp_table = _build_ssp_latitude_table(mod, raw_table)
        irs_config = _build_tenant_config(mod, raw_irs)

        findings = mod.detect_latitude_drift(ssp_table, irs_config)
        assert len(findings) >= 1
        assert findings[0].drift_class == "DRIFT-SCHEMA"

    def test_irs_consuming_agency_code(self) -> None:
        """Raw fixture has the correct consuming_agency_code."""
        raw = _load_yaml(_TENANT_IRS_CONFIG)
        assert raw.get("consuming_agency_code") == "IRS"


class TestDriftDetectorUnit:
    """Unit tests for detect_latitude_drift using inline fixtures (no file I/O)."""

    def test_key_not_in_table_produces_not_enumerated(self) -> None:
        """A setting not in the latitude table produces a NOT_ENUMERATED finding."""
        mod = _import_latitude_module()

        ssp_table = mod.SspLatitudeTable(
            controlling_ato_id="TEST-ATO-001",
            entries=[
                mod.LatitudeTableEntry(
                    setting_key="allowed_key",
                    allowed_values=["yes"],
                )
            ],
        )
        tenant_config = mod.TenantConfig(
            consuming_agency_code="TST",
            entries=[
                mod.TenantConfigEntry(setting_key="unknown_key", observed_value="val"),
            ],
        )
        findings = mod.detect_latitude_drift(ssp_table, tenant_config)
        assert len(findings) == 1
        assert findings[0].verdict == "NOT_ENUMERATED"
        assert findings[0].setting_key == "unknown_key"

    def test_value_in_allowed_values_produces_no_finding(self) -> None:
        """A setting whose observed value is in allowed_values produces no finding."""
        mod = _import_latitude_module()

        ssp_table = mod.SspLatitudeTable(
            controlling_ato_id="TEST-ATO-001",
            entries=[
                mod.LatitudeTableEntry(
                    setting_key="mfa_required",
                    allowed_values=["true"],
                )
            ],
        )
        tenant_config = mod.TenantConfig(
            consuming_agency_code="TST",
            entries=[
                mod.TenantConfigEntry(setting_key="mfa_required", observed_value="true"),
            ],
        )
        findings = mod.detect_latitude_drift(ssp_table, tenant_config)
        assert findings == []

    def test_value_not_in_allowed_values_produces_out_of_latitude(self) -> None:
        """A setting with a disallowed value produces OUT_OF_LATITUDE, P2."""
        mod = _import_latitude_module()

        ssp_table = mod.SspLatitudeTable(
            controlling_ato_id="TEST-ATO-001",
            entries=[
                mod.LatitudeTableEntry(
                    setting_key="mfa_required",
                    allowed_values=["true"],
                )
            ],
        )
        tenant_config = mod.TenantConfig(
            consuming_agency_code="TST",
            entries=[
                mod.TenantConfigEntry(setting_key="mfa_required", observed_value="false"),
            ],
        )
        findings = mod.detect_latitude_drift(ssp_table, tenant_config)
        assert len(findings) == 1
        assert findings[0].verdict == "OUT_OF_LATITUDE"
        assert findings[0].severity == "P2"
        assert findings[0].drift_class == "DRIFT-SCHEMA"

    def test_value_matching_allowed_pattern_produces_no_finding(self) -> None:
        """A value matching allowed_pattern produces no finding."""
        mod = _import_latitude_module()

        ssp_table = mod.SspLatitudeTable(
            controlling_ato_id="TEST-ATO-001",
            entries=[
                mod.LatitudeTableEntry(
                    setting_key="password_minimum_length",
                    allowed_pattern=r"^(1[2-9]|[2-9][0-9])$",
                )
            ],
        )
        tenant_config = mod.TenantConfig(
            consuming_agency_code="TST",
            entries=[
                mod.TenantConfigEntry(setting_key="password_minimum_length", observed_value="14"),
            ],
        )
        findings = mod.detect_latitude_drift(ssp_table, tenant_config)
        assert findings == []

    def test_value_not_matching_allowed_pattern_produces_out_of_latitude(self) -> None:
        """A value not matching allowed_pattern produces OUT_OF_LATITUDE."""
        mod = _import_latitude_module()

        ssp_table = mod.SspLatitudeTable(
            controlling_ato_id="TEST-ATO-001",
            entries=[
                mod.LatitudeTableEntry(
                    setting_key="password_minimum_length",
                    allowed_pattern=r"^(1[2-9]|[2-9][0-9])$",
                )
            ],
        )
        tenant_config = mod.TenantConfig(
            consuming_agency_code="TST",
            entries=[
                mod.TenantConfigEntry(setting_key="password_minimum_length", observed_value="10"),
            ],
        )
        findings = mod.detect_latitude_drift(ssp_table, tenant_config)
        assert len(findings) == 1
        assert findings[0].verdict == "OUT_OF_LATITUDE"
        assert findings[0].setting_key == "password_minimum_length"

    def test_empty_tenant_config_produces_no_findings(self) -> None:
        """A tenant with no configuration entries produces zero findings."""
        mod = _import_latitude_module()

        ssp_table = mod.SspLatitudeTable(
            controlling_ato_id="TEST-ATO-001",
            entries=[
                mod.LatitudeTableEntry(
                    setting_key="mfa_required",
                    allowed_values=["true"],
                )
            ],
        )
        tenant_config = mod.TenantConfig(
            consuming_agency_code="TST",
            entries=[],
        )
        findings = mod.detect_latitude_drift(ssp_table, tenant_config)
        assert findings == []

    def test_multiple_violations_all_reported(self) -> None:
        """Multiple violations in one tenant config all appear in findings."""
        mod = _import_latitude_module()

        ssp_table = mod.SspLatitudeTable(
            controlling_ato_id="TEST-ATO-001",
            entries=[
                mod.LatitudeTableEntry(setting_key="mfa_required", allowed_values=["true"]),
                mod.LatitudeTableEntry(
                    setting_key="session_timeout_minutes",
                    allowed_values=["15", "30", "60"],
                ),
            ],
        )
        tenant_config = mod.TenantConfig(
            consuming_agency_code="TST",
            entries=[
                mod.TenantConfigEntry(setting_key="mfa_required", observed_value="false"),
                mod.TenantConfigEntry(setting_key="session_timeout_minutes", observed_value="999"),
            ],
        )
        findings = mod.detect_latitude_drift(ssp_table, tenant_config)
        assert len(findings) == 2
        keys = {f.setting_key for f in findings}
        assert "mfa_required" in keys
        assert "session_timeout_minutes" in keys
