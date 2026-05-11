"""
tests/test_config_latitude_drift.py
-------------------------------------
Acceptance tests for the configuration-latitude drift detector (WS-A7).

Covers:
1. NOT_ENUMERATED — tenant key absent from SSP latitude table
2. WITHIN_LATITUDE — tenant value in allowed list → no finding emitted
3. OUT_OF_LATITUDE (enum) — tenant value not in allowed list
4. OUT_OF_LATITUDE (pattern) — tenant value fails regex pattern
5. Empty tenant config + non-empty SSP latitude table → zero findings
6. CQL query YAML parses and validates against the CQL parser
7. findings_to_oscal_observations returns dicts with required OSCAL fields

References: UIAO_140 §5, ADR-054, ADR-058, WS-A7 acceptance criteria.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from uiao.governance.config_latitude import (
    LatitudeTableEntry,
    SspLatitudeTable,
    TenantConfig,
    TenantConfigEntry,
    detect_latitude_drift,
    findings_to_oscal_observations,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CONTROLLING_ATO_ID = "OPM-HRIT-2026-001"
AGENCY_CODE = "TREAS"

QUERY_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "uiao"
    / "canon"
    / "queries"
    / "configuration-latitude-violations.yaml"
)


def make_ssp(entries: list[LatitudeTableEntry]) -> SspLatitudeTable:
    return SspLatitudeTable(controlling_ato_id=CONTROLLING_ATO_ID, entries=entries)


def make_tenant(*pairs: tuple[str, str]) -> TenantConfig:
    return TenantConfig(
        consuming_agency_code=AGENCY_CODE,
        entries=[TenantConfigEntry(setting_key=k, observed_value=v) for k, v in pairs],
    )


# ---------------------------------------------------------------------------
# Test 1: NOT_ENUMERATED
# ---------------------------------------------------------------------------


def test_not_enumerated_when_key_absent_from_table() -> None:
    """Tenant has setting_key X; SSP latitude table has no entry for X.

    Expect exactly one finding with verdict=NOT_ENUMERATED, severity=P2,
    drift_class=DRIFT-SCHEMA.
    """
    ssp = make_ssp(
        [
            LatitudeTableEntry(setting_key="mfa_policy", allowed_values=["FIDO2", "PIV"]),
        ]
    )
    tenant = make_tenant(("unknown_setting", "some_value"))

    findings = detect_latitude_drift(ssp, tenant)

    assert len(findings) == 1
    f = findings[0]
    assert f.setting_key == "unknown_setting"
    assert f.observed_value == "some_value"
    assert f.verdict == "NOT_ENUMERATED"
    assert f.severity == "P2"
    assert f.drift_class == "DRIFT-SCHEMA"
    assert CONTROLLING_ATO_ID in f.message


# ---------------------------------------------------------------------------
# Test 2: WITHIN_LATITUDE (no finding emitted)
# ---------------------------------------------------------------------------


def test_within_latitude_no_finding_for_allowed_value() -> None:
    """Tenant has X=value1, SSP allows [value1, value2] → zero findings."""
    ssp = make_ssp(
        [
            LatitudeTableEntry(
                setting_key="mfa_policy",
                allowed_values=["value1", "value2"],
            )
        ]
    )
    tenant = make_tenant(("mfa_policy", "value1"))

    findings = detect_latitude_drift(ssp, tenant)

    assert findings == []


# ---------------------------------------------------------------------------
# Test 3: OUT_OF_LATITUDE — allowed_values list violation
# ---------------------------------------------------------------------------


def test_out_of_latitude_enum_when_value_not_in_allowed_list() -> None:
    """Tenant has X=value3, SSP allows [value1, value2] → OUT_OF_LATITUDE."""
    ssp = make_ssp(
        [
            LatitudeTableEntry(
                setting_key="mfa_policy",
                allowed_values=["value1", "value2"],
            )
        ]
    )
    tenant = make_tenant(("mfa_policy", "value3"))

    findings = detect_latitude_drift(ssp, tenant)

    assert len(findings) == 1
    f = findings[0]
    assert f.setting_key == "mfa_policy"
    assert f.observed_value == "value3"
    assert f.verdict == "OUT_OF_LATITUDE"
    assert f.severity == "P2"
    assert f.drift_class == "DRIFT-SCHEMA"


# ---------------------------------------------------------------------------
# Test 4: OUT_OF_LATITUDE — regex pattern violation
# ---------------------------------------------------------------------------


def test_out_of_latitude_pattern_when_value_fails_regex() -> None:
    """Tenant has X=abc, SSP pattern is ^[0-9]+$ → OUT_OF_LATITUDE."""
    ssp = make_ssp(
        [
            LatitudeTableEntry(
                setting_key="session_timeout",
                allowed_pattern=r"^[0-9]+$",
            )
        ]
    )
    tenant = make_tenant(("session_timeout", "abc"))

    findings = detect_latitude_drift(ssp, tenant)

    assert len(findings) == 1
    f = findings[0]
    assert f.setting_key == "session_timeout"
    assert f.observed_value == "abc"
    assert f.verdict == "OUT_OF_LATITUDE"
    assert f.severity == "P2"
    assert f.drift_class == "DRIFT-SCHEMA"


def test_within_latitude_when_value_matches_regex() -> None:
    """Tenant has X=42, SSP pattern is ^[0-9]+$ → no finding."""
    ssp = make_ssp(
        [
            LatitudeTableEntry(
                setting_key="session_timeout",
                allowed_pattern=r"^[0-9]+$",
            )
        ]
    )
    tenant = make_tenant(("session_timeout", "42"))

    findings = detect_latitude_drift(ssp, tenant)

    assert findings == []


# ---------------------------------------------------------------------------
# Test 5: Empty tenant config + non-empty SSP latitude → zero findings
# ---------------------------------------------------------------------------


def test_zero_findings_for_empty_tenant_config() -> None:
    """Empty tenant config produces zero findings regardless of SSP contents."""
    ssp = make_ssp(
        [
            LatitudeTableEntry(setting_key="mfa_policy", allowed_values=["FIDO2"]),
            LatitudeTableEntry(setting_key="session_timeout", allowed_pattern=r"^[0-9]+$"),
        ]
    )
    tenant = TenantConfig(consuming_agency_code=AGENCY_CODE, entries=[])

    findings = detect_latitude_drift(ssp, tenant)

    assert findings == []


# ---------------------------------------------------------------------------
# Test 6: CQL query YAML parses and validates against the CQL parser
# ---------------------------------------------------------------------------


def test_cql_query_yaml_parses_and_validates() -> None:
    """CQL query YAML file exists, parses as valid YAML, and is accepted by
    the CQL parser without raising CQLParseError.
    """
    from uiao.governance.cql import parse_query

    assert QUERY_PATH.exists(), f"CQL query YAML not found at {QUERY_PATH}"

    raw = yaml.safe_load(QUERY_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), "CQL query YAML must be a mapping"

    # Must parse without error
    query = parse_query(raw)

    assert query.source == "findings"
    # where clause must include drift_class = DRIFT-SCHEMA
    where_map = {p.field: p.value for p in query.where}
    assert where_map.get("drift_class") == "DRIFT-SCHEMA"
    assert where_map.get("tag") == "configuration-latitude"


# ---------------------------------------------------------------------------
# Test 7: findings_to_oscal_observations returns OSCAL observation dicts
# ---------------------------------------------------------------------------


def test_findings_to_oscal_observations_required_fields() -> None:
    """findings_to_oscal_observations returns dicts with uuid, title, description."""
    ssp = make_ssp(
        [
            LatitudeTableEntry(setting_key="mfa_policy", allowed_values=["FIDO2"]),
        ]
    )
    tenant = make_tenant(("unknown_key", "bad_value"), ("mfa_policy", "SMS"))

    findings = detect_latitude_drift(ssp, tenant)
    assert len(findings) == 2  # NOT_ENUMERATED + OUT_OF_LATITUDE

    observations = findings_to_oscal_observations(findings, AGENCY_CODE)

    assert len(observations) == 2
    for obs in observations:
        assert "uuid" in obs, "OSCAL observation must have 'uuid'"
        assert "title" in obs, "OSCAL observation must have 'title'"
        assert "description" in obs, "OSCAL observation must have 'description'"
        # Validate UUID is a string (not empty)
        assert isinstance(obs["uuid"], str) and obs["uuid"]
        # props must include consuming-agency-code
        prop_names = {p["name"] for p in obs.get("props", [])}
        assert "consuming-agency-code" in prop_names
        assert "drift-class" in prop_names
        assert "tag" in prop_names


def test_findings_to_oscal_observations_empty_input() -> None:
    """Empty findings list → empty observations list."""
    result = findings_to_oscal_observations([], AGENCY_CODE)
    assert result == []


# ---------------------------------------------------------------------------
# Integration: multiple settings, mixed verdicts
# ---------------------------------------------------------------------------


def test_mixed_verdict_multiple_settings() -> None:
    """Multiple settings produce correct mix of findings."""
    ssp = make_ssp(
        [
            LatitudeTableEntry(setting_key="mfa_policy", allowed_values=["FIDO2", "PIV"]),
            LatitudeTableEntry(setting_key="session_timeout", allowed_pattern=r"^[0-9]+$"),
            LatitudeTableEntry(setting_key="audit_level", allowed_values=["FULL"]),
        ]
    )
    tenant = make_tenant(
        ("mfa_policy", "FIDO2"),  # WITHIN_LATITUDE — no finding
        ("session_timeout", "abc"),  # OUT_OF_LATITUDE (pattern)
        ("audit_level", "PARTIAL"),  # OUT_OF_LATITUDE (enum)
        ("unknown_key", "anything"),  # NOT_ENUMERATED
    )

    findings = detect_latitude_drift(ssp, tenant)

    assert len(findings) == 3
    verdicts = {f.setting_key: f.verdict for f in findings}
    assert verdicts["session_timeout"] == "OUT_OF_LATITUDE"
    assert verdicts["audit_level"] == "OUT_OF_LATITUDE"
    assert verdicts["unknown_key"] == "NOT_ENUMERATED"
