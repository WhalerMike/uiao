"""End-to-end integration test for the SSOT-contention pipeline.

Exercises:

    schema → loader → classifier

on a realistic multi-instance roster (the
``tests/fixtures/ssot-roster-hr-workday-consolidation.yaml`` reference
fixture). Asserts:

    * The fixture validates against the canonical JSON Schema.
    * SSOTRoster.from_yaml() reconstructs the typed dataclass tree
      correctly across all three demoted-instance patterns.
    * classify_write_event_batch() emits the expected mix of severity
      bands against a curated synthetic audit-log stream.

This test is the canonical "is the whole stack wired up?" check for
ADR-074's implementation. When any of the three layers regress, this
test fires first.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List

import jsonschema
import yaml

from uiao.governance.ssot_contention import (
    SSOTRoster,
    WriteEvent,
    classify_write_event_batch,
)
from uiao.ir.models.core import ProvenanceRecord

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "ssot-roster-hr-workday-consolidation.yaml"
SCHEMA = REPO_ROOT / "src" / "uiao" / "schemas" / "ssot-roster" / "ssot-roster.schema.json"


# ---------------------------------------------------------------------------
# Schema validation — the fixture must conform to the canonical schema.
# ---------------------------------------------------------------------------


class TestFixtureConformsToSchema:
    def test_fixture_validates_against_schema(self) -> None:
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.Draft7Validator.check_schema(schema)
        with open(FIXTURE, encoding="utf-8") as f:
            roster_yaml = yaml.safe_load(f)
        jsonschema.Draft7Validator(schema).validate(roster_yaml)


# ---------------------------------------------------------------------------
# Loader — typed dataclass reconstruction.
# ---------------------------------------------------------------------------


class TestLoaderReconstruction:
    def test_loads_all_three_demoted_instances(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        assert roster.domain == "HR"
        assert roster.ratification_date == date(2026, 5, 1)
        assert len(roster.demoted_instances) == 3

    def test_cutover_window_only_on_primary(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        by_id = {d.identifier: d for d in roster.demoted_instances}
        assert by_id["ad-spn::peoplesoft-hr01.corp.example:1433"].cutover_window is not None
        assert by_id["ad-spn::peoplesoft-hr02.corp.example:1433"].cutover_window is None
        assert by_id["ad-spn::peoplesoft-hr-archive.corp.example:1433"].cutover_window is None

    def test_retirement_date_only_on_archive(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        by_id = {d.identifier: d for d in roster.demoted_instances}
        assert by_id["ad-spn::peoplesoft-hr-archive.corp.example:1433"].retirement_date == date(2026, 9, 1)
        assert by_id["ad-spn::peoplesoft-hr01.corp.example:1433"].retirement_date is None

    def test_per_instance_window_override_on_archive(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        by_id = {d.identifier: d for d in roster.demoted_instances}
        # Roster-level default is 30; archive overrides to 7.
        assert roster.remediation_window_days == 30
        assert by_id["ad-spn::peoplesoft-hr-archive.corp.example:1433"].remediation_window_days == 7

    def test_cache_eligible_columns_load_as_frozenset(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        primary = next(d for d in roster.demoted_instances if "hr01" in d.identifier)
        assert isinstance(primary.cache_eligible_columns, frozenset)
        assert "hr.employees.last_synced_at" in primary.cache_eligible_columns
        assert "hr.positions.cache_hash" in primary.cache_eligible_columns


# ---------------------------------------------------------------------------
# Classifier — end-to-end against a curated synthetic event stream.
# ---------------------------------------------------------------------------


def _provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test-ssot-contention-integration",
        timestamp="2026-08-15T23:30:00Z",
        version="0.1.0",
    )


def _events() -> List[WriteEvent]:
    """Curated audit-log stream exercising every severity band.

    Each event is labeled in the comment with its expected outcome.
    """
    return [
        # PRIMARY (peoplesoft-hr01) — inside cutover_window → P3 (risky)
        WriteEvent(
            target_instance="ad-spn::peoplesoft-hr01.corp.example:1433",
            target_table="employees",
            target_column="first_name",
            timestamp=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
            principal="CORP\\svc-hr-cutover",
            source_audit_log="sql-server-audit",
        ),
        # PRIMARY — cache_eligible_column → excluded (no finding)
        WriteEvent(
            target_instance="ad-spn::peoplesoft-hr01.corp.example:1433",
            target_table="employees",
            target_column="cache_hash",
            timestamp=datetime(2026, 8, 15, 23, 35, tzinfo=timezone.utc),
            principal="CORP\\svc-hr-replication",
            source_audit_log="sql-server-audit",
        ),
        # STANDBY (peoplesoft-hr02) — within remediation_window_days → P2 (unauthorized)
        WriteEvent(
            target_instance="ad-spn::peoplesoft-hr02.corp.example:1433",
            target_table="employees",
            target_column="email",
            timestamp=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc),
            principal="CORP\\svc-hr-rogue",
            source_audit_log="sql-server-audit",
        ),
        # ARCHIVE (peoplesoft-hr-archive) — past per-instance window (7d, demotion 2026-04-01)
        # → P1 (unauthorized)
        WriteEvent(
            target_instance="ad-spn::peoplesoft-hr-archive.corp.example:1433",
            target_table="historical_employees",
            target_column="last_position",
            timestamp=datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc),
            principal="CORP\\svc-hr-archive-edit",
            source_audit_log="sql-server-audit",
        ),
        # ARCHIVE — after retirement_date (2026-09-01) → excluded (no finding)
        WriteEvent(
            target_instance="ad-spn::peoplesoft-hr-archive.corp.example:1433",
            target_table="historical_employees",
            target_column="anything",
            timestamp=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
            principal="CORP\\svc-shouldnt-fire",
            source_audit_log="sql-server-audit",
        ),
        # UNRELATED instance not in roster → excluded
        WriteEvent(
            target_instance="ad-spn::some-other-database.corp.example:1433",
            target_table="other_table",
            target_column="other_col",
            timestamp=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
            principal="CORP\\svc-elsewhere",
            source_audit_log="sql-server-audit",
        ),
    ]


class TestEvaluatorEndToEnd:
    def test_batch_emits_three_findings(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(
            roster=roster,
            write_events=_events(),
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        # Expected: primary-cutover (P3), standby-within (P2), archive-past (P1)
        # Excluded: primary-cache, archive-post-retirement, unrelated-instance
        assert len(findings) == 3

    def test_all_findings_carry_ssot_contention_class(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(
            roster=roster,
            write_events=_events(),
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        for f in findings:
            assert f.drift_class == "DRIFT-SSOT-CONTENTION"

    def test_primary_cutover_is_risky_p3(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(
            roster=roster,
            write_events=_events(),
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        primary = next(f for f in findings if "hr01" in f.resource_id)
        # P3 inside cutover window → risky (not unauthorized)
        assert primary.classification == "risky"

    def test_standby_within_window_is_unauthorized_p2(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(
            roster=roster,
            write_events=_events(),
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        standby = next(f for f in findings if "hr02" in f.resource_id)
        # P2 default → unauthorized
        assert standby.classification == "unauthorized"

    def test_archive_past_window_is_unauthorized_p1(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(
            roster=roster,
            write_events=_events(),
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        archive = next(f for f in findings if "archive" in f.resource_id)
        # P1 → unauthorized
        assert archive.classification == "unauthorized"

    def test_policy_ref_carries_domain(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(
            roster=roster,
            write_events=_events(),
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        for f in findings:
            assert f.policy_ref == "ssot-roster::HR"

    def test_drift_id_includes_instance_and_timestamp(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(
            roster=roster,
            write_events=_events(),
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        for f in findings:
            assert "ssot-contention" in f.id
            assert "peoplesoft" in f.id

    def test_no_findings_on_empty_event_stream(self) -> None:
        roster = SSOTRoster.from_yaml(FIXTURE)
        findings = classify_write_event_batch(roster=roster, write_events=[], provenance=_provenance())
        assert findings == []
