"""Tests for the SSOT-Contention Evaluator (ADR-074 implementation).

Covers the five detection predicates from ADR-074 §2 and the severity
bands from §3. All inputs are constructed in-memory; no live audit-log
or roster file is required.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from uiao.governance.ssot_contention import (
    AuthoritativeInstance,
    CutoverWindow,
    DemotedInstance,
    SSOTRoster,
    WriteEvent,
    classify_ssot_contention,
    classify_write_event_batch,
)
from uiao.ir.models.core import DriftState, ProvenanceRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test-ssot-contention",
        timestamp="2026-05-18T00:00:00Z",
        version="0.1.0",
    )


def _build_roster(
    *,
    demoted_id: str = "demoted-001",
    demotion_date: date = date(2026, 5, 1),
    cache_columns: tuple[str, ...] = (),
    cutover_window: Optional[CutoverWindow] = None,
    retirement_date: Optional[date] = None,
    remediation_window_days: int = 30,
    per_instance_window: Optional[int] = None,
) -> SSOTRoster:
    return SSOTRoster(
        schema_version="1.0.0",
        domain="HR",
        ratification_date=date(2026, 5, 1),
        authoritative_instance=AuthoritativeInstance(
            identifier="workday::tenant-fed-001",
            boundary_classification="gcc-moderate",
            selection_rationale="Test SSOT for HR domain.",
        ),
        demoted_instances=(
            DemotedInstance(
                identifier=demoted_id,
                demotion_date=demotion_date,
                status="demoted",
                cutover_window=cutover_window,
                cache_eligible_columns=frozenset(cache_columns),
                retirement_date=retirement_date,
                remediation_window_days=per_instance_window,
            ),
        ),
        remediation_window_days=remediation_window_days,
    )


def _write_event(
    *,
    target_instance: str = "demoted-001",
    target_table: str = "employees",
    target_column: Optional[str] = "first_name",
    timestamp: Optional[datetime] = None,
    principal: str = "CORP\\svc-app01",
) -> WriteEvent:
    return WriteEvent(
        target_instance=target_instance,
        target_table=target_table,
        target_column=target_column,
        timestamp=timestamp or datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        principal=principal,
        source_audit_log="test",
    )


# ---------------------------------------------------------------------------
# Predicate tests — each of the 5 predicates
# ---------------------------------------------------------------------------


class TestDetectionPredicates:
    def test_predicate_2_no_demoted_instances_returns_none(self) -> None:
        roster = SSOTRoster(
            schema_version="1.0.0",
            domain="HR",
            ratification_date=date(2026, 5, 1),
            authoritative_instance=AuthoritativeInstance(
                identifier="x", boundary_classification="gcc-moderate", selection_rationale="r"
            ),
            demoted_instances=(),
        )
        result = classify_ssot_contention(roster=roster, write_event=_write_event(), provenance=_provenance())
        assert result is None

    def test_predicate_3_write_against_unrelated_instance_returns_none(self) -> None:
        roster = _build_roster(demoted_id="demoted-001")
        event = _write_event(target_instance="some-other-instance")
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is None

    def test_predicate_4_cache_eligible_column_returns_none(self) -> None:
        roster = _build_roster(cache_columns=("employees.cache_hash",))
        event = _write_event(target_column="cache_hash")
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is None

    def test_predicate_4_three_segment_cache_eligible_column_returns_none(self) -> None:
        """Allowlist entries can be schema.table.column; trailing match still applies."""
        roster = _build_roster(cache_columns=("hr.employees.cache_hash",))
        event = _write_event(target_column="cache_hash")
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is None

    def test_predicate_4_non_cache_column_fires(self) -> None:
        roster = _build_roster(cache_columns=("employees.cache_hash",))
        event = _write_event(target_column="first_name")
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is not None
        assert result.drift_class == "DRIFT-SSOT-CONTENTION"

    def test_predicate_4_whole_row_write_fires(self) -> None:
        """A write with no specific column (whole-row) always fires."""
        roster = _build_roster(cache_columns=("employees.cache_hash",))
        event = _write_event(target_column=None)
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is not None

    def test_predicate_5a_write_before_demotion_returns_none(self) -> None:
        """Writes that happened before the demotion date are not contention."""
        roster = _build_roster(demotion_date=date(2026, 5, 15))
        event = _write_event(timestamp=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc))
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is None

    def test_predicate_5b_write_after_retirement_returns_none(self) -> None:
        roster = _build_roster(
            demotion_date=date(2026, 5, 1),
            retirement_date=date(2026, 5, 30),
        )
        event = _write_event(timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc))
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is None


# ---------------------------------------------------------------------------
# Severity-band tests — ADR-074 §3
# ---------------------------------------------------------------------------


class TestSeverityBands:
    def test_inside_cutover_window_emits_p3(self) -> None:
        window = CutoverWindow(
            planned_start=datetime(2026, 8, 15, 22, 0, tzinfo=timezone.utc),
            planned_end=datetime(2026, 8, 16, 6, 0, tzinfo=timezone.utc),
        )
        roster = _build_roster(cutover_window=window)
        event = _write_event(timestamp=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc))
        result = classify_ssot_contention(
            roster=roster,
            write_event=event,
            provenance=_provenance(),
            now=datetime(2026, 8, 15, 23, 30, tzinfo=timezone.utc),
        )
        assert result is not None
        # P3 → risky classification, NOT unauthorized.
        assert result.classification == "risky"

    def test_within_remediation_window_emits_p2(self) -> None:
        roster = _build_roster(demotion_date=date(2026, 5, 1), remediation_window_days=30)
        event = _write_event(timestamp=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc))
        result = classify_ssot_contention(
            roster=roster,
            write_event=event,
            provenance=_provenance(),
            now=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        assert result is not None
        # P2 → unauthorized classification.
        assert result.classification == "unauthorized"

    def test_past_remediation_window_emits_p1(self) -> None:
        roster = _build_roster(demotion_date=date(2026, 5, 1), remediation_window_days=30)
        event = _write_event(timestamp=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc))
        # now is 60 days past demotion, > 30-day window
        result = classify_ssot_contention(
            roster=roster,
            write_event=event,
            provenance=_provenance(),
            now=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert result is not None
        # P1 → unauthorized
        assert result.classification == "unauthorized"

    def test_per_instance_remediation_window_overrides_roster_default(self) -> None:
        """A per-DemotedInstance remediation_window_days takes precedence."""
        roster = _build_roster(
            demotion_date=date(2026, 5, 1),
            remediation_window_days=30,
            per_instance_window=7,  # tighter window than roster default
        )
        event = _write_event(timestamp=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc))
        # now is 14 days past demotion; roster default would say "within window" (P2)
        # but per-instance override says 7 days → "past window" (P1).
        result = classify_ssot_contention(
            roster=roster,
            write_event=event,
            provenance=_provenance(),
            now=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        assert result is not None
        # P1 still maps to 'unauthorized' classification.
        assert result.classification == "unauthorized"


# ---------------------------------------------------------------------------
# DriftState payload tests
# ---------------------------------------------------------------------------


class TestDriftStatePayload:
    def test_drift_class_is_ssot_contention(self) -> None:
        roster = _build_roster()
        result = classify_ssot_contention(roster=roster, write_event=_write_event(), provenance=_provenance())
        assert result is not None
        assert result.drift_class == "DRIFT-SSOT-CONTENTION"

    def test_resource_id_is_demoted_identifier(self) -> None:
        roster = _build_roster(demoted_id="ad-spn::sql01.corp.example:1433")
        event = _write_event(target_instance="ad-spn::sql01.corp.example:1433")
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is not None
        assert result.resource_id == "ad-spn::sql01.corp.example:1433"

    def test_policy_ref_carries_domain(self) -> None:
        roster = _build_roster()
        result = classify_ssot_contention(roster=roster, write_event=_write_event(), provenance=_provenance())
        assert result is not None
        assert result.policy_ref == "ssot-roster::HR"

    def test_policy_ref_with_domain_scope(self) -> None:
        roster = SSOTRoster(
            schema_version="1.0.0",
            domain="HR",
            domain_scope="Civilian-Personnel-Only",
            ratification_date=date(2026, 5, 1),
            authoritative_instance=AuthoritativeInstance(
                identifier="x", boundary_classification="gcc-moderate", selection_rationale="r"
            ),
            demoted_instances=(
                DemotedInstance(
                    identifier="demoted-001",
                    demotion_date=date(2026, 5, 1),
                    status="demoted",
                ),
            ),
        )
        result = classify_ssot_contention(roster=roster, write_event=_write_event(), provenance=_provenance())
        assert result is not None
        assert result.policy_ref == "ssot-roster::HR/Civilian-Personnel-Only"

    def test_drift_id_includes_event_timestamp(self) -> None:
        roster = _build_roster()
        ts = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        event = _write_event(timestamp=ts)
        result = classify_ssot_contention(roster=roster, write_event=event, provenance=_provenance())
        assert result is not None
        assert "ssot-contention" in result.id
        assert "demoted-001" in result.id
        assert ts.isoformat() in result.id

    def test_explicit_drift_id_overrides_default(self) -> None:
        roster = _build_roster()
        result = classify_ssot_contention(
            roster=roster,
            write_event=_write_event(),
            provenance=_provenance(),
            drift_id="custom-id-001",
        )
        assert result is not None
        assert result.id == "custom-id-001"


# ---------------------------------------------------------------------------
# Roster loading tests
# ---------------------------------------------------------------------------


class TestRosterLoading:
    def _sample_roster_yaml(self, tmp_path: Path) -> Path:
        path = tmp_path / "ssot-roster.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "schema-version": "1.0.0",
                    "domain": "HR",
                    "ratification_date": "2026-05-01",
                    "authoritative_instance": {
                        "identifier": "workday::tenant-fed-001",
                        "boundary_classification": "gcc-moderate",
                        "selection_rationale": "Cross-agency Workday consolidation.",
                    },
                    "demoted_instances": [
                        {
                            "identifier": "ad-spn::peoplesoft-hr01.corp.example:1433",
                            "demotion_date": "2026-05-01",
                            "status": "demoted",
                            "cache_eligible_columns": ["hr.employees.last_synced_at"],
                            "cutover_window": {
                                "planned_start": "2026-08-15T22:00:00+00:00",
                                "planned_end": "2026-08-16T06:00:00+00:00",
                            },
                        }
                    ],
                    "remediation_window_days": 30,
                }
            )
        )
        return path

    def test_from_yaml_loads_complete_roster(self, tmp_path: Path) -> None:
        path = self._sample_roster_yaml(tmp_path)
        roster = SSOTRoster.from_yaml(path)
        assert roster.domain == "HR"
        assert roster.ratification_date == date(2026, 5, 1)
        assert roster.authoritative_instance.identifier == "workday::tenant-fed-001"
        assert len(roster.demoted_instances) == 1
        d = roster.demoted_instances[0]
        assert d.identifier == "ad-spn::peoplesoft-hr01.corp.example:1433"
        assert "hr.employees.last_synced_at" in d.cache_eligible_columns
        assert d.cutover_window is not None
        assert d.cutover_window.planned_start == datetime(2026, 8, 15, 22, 0, tzinfo=timezone.utc)

    def test_from_dict_handles_minimal_entries(self) -> None:
        roster = SSOTRoster.from_dict(
            {
                "schema-version": "1.0.0",
                "domain": "Finance",
                "ratification_date": "2026-05-18",
                "authoritative_instance": {
                    "identifier": "oracle-erp::tenant-001",
                    "boundary_classification": "gcc-moderate",
                    "selection_rationale": "Stub.",
                },
                "demoted_instances": [
                    {
                        "identifier": "legacy-gl-01",
                        "demotion_date": "2026-05-18",
                        "status": "demoted",
                    }
                ],
            }
        )
        assert roster.domain == "Finance"
        assert roster.demoted_instances[0].cache_eligible_columns == frozenset()
        assert roster.demoted_instances[0].cutover_window is None
        assert roster.demoted_instances[0].retirement_date is None

    def test_find_demoted_returns_match(self) -> None:
        roster = _build_roster(demoted_id="demoted-001")
        assert roster.find_demoted("demoted-001") is not None
        assert roster.find_demoted("nonexistent") is None


# ---------------------------------------------------------------------------
# Batch wrapper tests
# ---------------------------------------------------------------------------


class TestBatchClassification:
    def test_batch_returns_only_contention_findings(self) -> None:
        roster = _build_roster(cache_columns=("employees.cache_hash",))
        events = [
            _write_event(target_column="first_name"),  # contention
            _write_event(target_column="cache_hash"),  # cache, allowed
            _write_event(target_instance="unrelated-instance", target_column="anything"),  # not demoted
            _write_event(target_column=None),  # whole-row, contention
        ]
        findings = classify_write_event_batch(roster=roster, write_events=events, provenance=_provenance())
        assert len(findings) == 2
        for f in findings:
            assert isinstance(f, DriftState)
            assert f.drift_class == "DRIFT-SSOT-CONTENTION"

    def test_batch_empty_events_returns_empty(self) -> None:
        roster = _build_roster()
        findings = classify_write_event_batch(roster=roster, write_events=[], provenance=_provenance())
        assert findings == []
