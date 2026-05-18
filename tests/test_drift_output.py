"""Tests for src/uiao/governance/drift_output.py (UIAO_179)."""

from __future__ import annotations

from datetime import datetime, timezone

from uiao.governance.drift_output import (
    FACET_DEFAULT_CLASS,
    DriftRecord,
    drift_record_from_report,
    facet_to_drift_class,
    records_to_dicts,
)


def test_facet_to_drift_class_returns_canonical_defaults():
    assert facet_to_drift_class("identity") == "DRIFT-IDENTITY"
    assert facet_to_drift_class("access") == "DRIFT-AUTHZ"
    assert facet_to_drift_class("tag") == "DRIFT-SCHEMA"
    assert facet_to_drift_class("boundary") == "DRIFT-BOUNDARY"
    assert facet_to_drift_class("semantic") == "DRIFT-SEMANTIC"


def test_facet_default_class_covers_all_seven_facets():
    assert set(FACET_DEFAULT_CLASS.keys()) == {
        "identity",
        "access",
        "resource",
        "tag",
        "device",
        "boundary",
        "semantic",
    }


def test_drift_record_to_dict_contains_all_uiao_179_fields():
    rec = DriftRecord(
        object_id="user-1",
        drift_class="DRIFT-AUTHZ",
        object_facet="access",
        expected_value=["GroupA"],
        actual_value=["GroupA", "GroupB"],
        severity="high",
        recommended_action="remove-extra-group",
        source_adapter="entra-adapter",
        correlation_id="req-123",
    )
    d = rec.to_dict()
    required = {
        "object_id",
        "drift_class",
        "object_facet",
        "expected_value",
        "actual_value",
        "severity",
        "recommended_action",
        "source_adapter",
        "first_observed",
        "last_observed",
        "correlation_id",
    }
    assert set(d.keys()) == required
    assert d["correlation_id"] == "req-123"


def test_drift_record_timestamps_serialise_iso8601():
    rec = DriftRecord(
        object_id="obj",
        drift_class="DRIFT-SCHEMA",
        object_facet="tag",
        expected_value=None,
        actual_value=None,
        severity="low",
        recommended_action="noop",
        source_adapter="x",
    )
    d = rec.to_dict()
    # ISO 8601: 'YYYY-MM-DDTHH:MM:SS' prefix is sufficient
    assert d["first_observed"].startswith("20")
    assert "T" in d["first_observed"]


class _LegacyReport:
    """Minimal stand-in for DriftReport from database_base.py."""

    drift_type = "schema_change"
    severity = "high"
    first_observed = datetime(2026, 5, 1, tzinfo=timezone.utc)
    last_observed = datetime(2026, 5, 2, tzinfo=timezone.utc)
    details = {"column": "user_id"}
    remediation = "alter table"


def test_drift_record_from_report_derives_class_from_facet():
    rec = drift_record_from_report(
        _LegacyReport(),
        object_id="db-1",
        object_facet="tag",
        source_adapter="bluecat-adapter",
        expected_value="canonical",
    )
    # facet 'tag' default -> DRIFT-SCHEMA
    assert rec.drift_class == "DRIFT-SCHEMA"
    assert rec.severity == "high"
    assert rec.recommended_action == "alter table"
    assert rec.first_observed == datetime(2026, 5, 1, tzinfo=timezone.utc)


def test_drift_record_from_report_keeps_drift_dash_prefixed_type():
    class CanonicalLegacy:
        drift_type = "DRIFT-AUTHZ"
        severity = "medium"
        first_observed = datetime(2026, 5, 1, tzinfo=timezone.utc)
        last_observed = datetime(2026, 5, 2, tzinfo=timezone.utc)
        details = {}
        remediation = None

    rec = drift_record_from_report(
        CanonicalLegacy(),
        object_id="obj",
        object_facet="access",
        source_adapter="x",
    )
    assert rec.drift_class == "DRIFT-AUTHZ"


def test_records_to_dicts_round_trips_list():
    rec = DriftRecord(
        object_id="o",
        drift_class="DRIFT-IDENTITY",
        object_facet="identity",
        expected_value="present",
        actual_value=None,
        severity="critical",
        recommended_action="recreate",
        source_adapter="x",
    )
    out = records_to_dicts([rec, rec])
    assert len(out) == 2
    assert out[0]["drift_class"] == "DRIFT-IDENTITY"
