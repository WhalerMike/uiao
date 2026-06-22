"""Tests for governance/identity/jml.py — human identity JML lifecycle detection."""

from __future__ import annotations

import json
import tempfile


from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.governance.identity.jml import (
    MOVER_TRIGGER_FIELDS,
    HumanJMLEventType,
    detect_events,
    write_evidence_artifacts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(**kwargs) -> HRRecord:
    defaults = dict(
        employee_id="E001",
        first_name="Alice",
        last_name="Smith",
        department="IT",
        hire_date="2022-01-01",
        worker_type="FTE",
        location_code="NCR",
        country="US",
        employment_status="Active",
        extracted_at="2026-06-22T00:00:00Z",
        division="Identity",
        organization_code="IT-IDENT",
        cost_center="CC-4100",
        job_title="Engineer",
        manager_employee_id="E002",
        termination_date=None,
        resolved_orgpath=None,
    )
    defaults.update(kwargs)
    return HRRecord(**defaults)


# ---------------------------------------------------------------------------
# Joiner tests
# ---------------------------------------------------------------------------


class TestJoiners:
    def test_new_record_is_joiner(self):
        current = [_make_record()]
        es = detect_events(current)
        assert len(es.joiners) == 1
        assert es.joiners[0].event_type == HumanJMLEventType.JOINER

    def test_joiner_carries_employee_id(self):
        current = [_make_record(employee_id="E999")]
        es = detect_events(current)
        assert es.joiners[0].record.employee_id == "E999"

    def test_prehire_to_active_is_joiner(self):
        prior = [_make_record(employment_status="PreHire")]
        current = [_make_record(employment_status="Active")]
        es = detect_events(current, prior)
        assert len(es.joiners) == 1

    def test_prehire_stays_prehire_not_joiner(self):
        prior = [_make_record(employment_status="PreHire")]
        current = [_make_record(employment_status="PreHire")]
        es = detect_events(current, prior)
        assert len(es.joiners) == 0

    def test_joiner_without_orgpath_emits_finding(self):
        current = [_make_record(resolved_orgpath=None)]
        es = detect_events(current)
        assert len(es.joiners[0].findings) == 1
        assert "no-orgpath" in es.joiners[0].findings[0].name

    def test_joiner_with_orgpath_no_findings(self):
        current = [_make_record(resolved_orgpath="NCR.IT.Identity.Engineer")]
        es = detect_events(current)
        assert len(es.joiners[0].findings) == 0

    def test_joiner_actions_present(self):
        current = [_make_record()]
        es = detect_events(current)
        steps = [a.step for a in es.joiners[0].actions]
        assert "J-1" in steps
        assert "J-2" in steps

    def test_orgpath_index_resolves_orgpath_for_joiner(self):
        current = [_make_record(organization_code="IT-IDENT")]
        idx = {"IT-IDENT": "NCR.IT.Identity.Engineer"}
        es = detect_events(current, orgpath_index=idx)
        assert es.joiners[0].resolved_orgpath == "NCR.IT.Identity.Engineer"
        assert len(es.joiners[0].findings) == 0


# ---------------------------------------------------------------------------
# Mover tests
# ---------------------------------------------------------------------------


class TestMovers:
    def test_department_change_is_mover(self):
        prior = [_make_record(department="IT")]
        current = [_make_record(department="Finance")]
        es = detect_events(current, prior)
        assert len(es.movers) == 1
        assert es.movers[0].event_type == HumanJMLEventType.MOVER

    def test_changed_fields_recorded(self):
        prior = [_make_record(department="IT", cost_center="CC-4100")]
        current = [_make_record(department="Finance", cost_center="CC-6000")]
        es = detect_events(current, prior)
        assert "department" in es.movers[0].changed_fields
        assert "cost_center" in es.movers[0].changed_fields

    def test_mover_actions_for_department_change(self):
        prior = [_make_record(department="IT")]
        current = [_make_record(department="Finance")]
        es = detect_events(current, prior)
        steps = [a.step for a in es.movers[0].actions]
        assert "M-placement" in steps
        assert "M-access-review" in steps

    def test_manager_change_triggers_mover(self):
        prior = [_make_record(manager_employee_id="E002")]
        current = [_make_record(manager_employee_id="E007")]
        es = detect_events(current, prior)
        assert len(es.movers) == 1
        assert "manager_employee_id" in es.movers[0].changed_fields

    def test_no_change_produces_no_mover(self):
        prior = [_make_record()]
        current = [_make_record()]
        es = detect_events(current, prior)
        assert len(es.movers) == 0

    def test_all_mover_trigger_fields_covered(self):
        for f in MOVER_TRIGGER_FIELDS:
            prior = [_make_record(**{f: "OLD"})]
            current = [_make_record(**{f: "NEW"})]
            es = detect_events(current, prior)
            assert len(es.movers) == 1, f"field {f!r} did not trigger mover"


# ---------------------------------------------------------------------------
# Leaver tests
# ---------------------------------------------------------------------------


class TestLeavers:
    def test_terminated_is_leaver(self):
        current = [_make_record(employment_status="Terminated", termination_date="2026-06-01")]
        es = detect_events(current)
        assert len(es.leavers) == 1
        assert es.leavers[0].event_type == HumanJMLEventType.LEAVER

    def test_leaver_without_termdate_emits_finding(self):
        current = [_make_record(employment_status="Terminated", termination_date=None)]
        es = detect_events(current)
        assert len(es.leavers) == 1
        assert len(es.leavers[0].findings) == 1
        assert "no-termdate" in es.leavers[0].findings[0].name

    def test_leaver_with_termdate_no_findings(self):
        current = [_make_record(employment_status="Terminated", termination_date="2026-06-01")]
        es = detect_events(current)
        assert len(es.leavers[0].findings) == 0

    def test_leaver_actions_present(self):
        current = [_make_record(employment_status="Terminated", termination_date="2026-06-01")]
        es = detect_events(current)
        steps = [a.step for a in es.leavers[0].actions]
        assert "L-1" in steps
        assert "L-6" in steps

    def test_rescinded_is_leaver(self):
        current = [_make_record(employment_status="Rescinded", termination_date="2026-06-01")]
        es = detect_events(current)
        assert len(es.leavers) == 1


# ---------------------------------------------------------------------------
# Pending leaver tests
# ---------------------------------------------------------------------------


class TestPendingLeavers:
    def test_termdate_set_with_active_status_is_pending(self):
        current = [_make_record(termination_date="2026-12-31", employment_status="Active")]
        es = detect_events(current)
        assert len(es.pending_leavers) == 1
        assert es.pending_leavers[0].event_type == HumanJMLEventType.PENDING_LEAVER
        assert es.pending_leavers[0].pending_leaver is True

    def test_absent_from_current_but_was_active_is_pending(self):
        prior = [_make_record(employee_id="E001")]
        current = []
        es = detect_events(current, prior)
        assert len(es.pending_leavers) == 1

    def test_absent_prehire_not_pending(self):
        prior = [_make_record(employee_id="E001", employment_status="PreHire")]
        current = []
        es = detect_events(current, prior)
        assert len(es.pending_leavers) == 0


# ---------------------------------------------------------------------------
# Evidence artifacts
# ---------------------------------------------------------------------------


class TestEvidenceArtifacts:
    def test_writes_two_files(self):
        current = [
            _make_record(employee_id="E001"),
            _make_record(employee_id="E002", employment_status="Terminated", termination_date="2026-06-01"),
        ]
        es = detect_events(current)
        with tempfile.TemporaryDirectory() as d:
            paths = write_evidence_artifacts(es, d)
            assert len(paths) == 2
            names = {p.name for p in paths}
            assert "human-jml-event-log.json" in names
            assert "human-jml-action-log.json" in names

    def test_event_log_is_valid_json(self):
        current = [_make_record()]
        es = detect_events(current)
        with tempfile.TemporaryDirectory() as d:
            paths = write_evidence_artifacts(es, d)
            event_log = next(p for p in paths if "event-log" in p.name)
            data = json.loads(event_log.read_text(encoding="utf-8"))
            assert "events" in data
            assert len(data["events"]) == 1

    def test_action_log_has_employee_id(self):
        current = [_make_record(employee_id="E001")]
        es = detect_events(current)
        with tempfile.TemporaryDirectory() as d:
            paths = write_evidence_artifacts(es, d)
            action_log = next(p for p in paths if "action-log" in p.name)
            data = json.loads(action_log.read_text(encoding="utf-8"))
            assert any(a["employee_id"] == "E001" for a in data["actions"])

    def test_summary_string(self):
        current = [_make_record()]
        es = detect_events(current)
        s = es.summary()
        assert "joiner" in s
        assert "1" in s


# ---------------------------------------------------------------------------
# Multi-record integration
# ---------------------------------------------------------------------------


class TestMultiRecord:
    def test_mixed_events_from_one_diff(self):
        prior = [
            _make_record(employee_id="E001"),
            _make_record(employee_id="E002", department="Finance"),
        ]
        current = [
            _make_record(employee_id="E001"),
            _make_record(employee_id="E002", department="IT"),
            _make_record(employee_id="E003"),
        ]
        es = detect_events(current, prior)
        assert len(es.joiners) == 1
        assert es.joiners[0].record.employee_id == "E003"
        assert len(es.movers) == 1
        assert es.movers[0].record.employee_id == "E002"
