"""Tests for governance/identity/servicenow_ticket.py — ticket payload and dry-run."""

from __future__ import annotations

import pytest

from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.governance.identity.jml import detect_events
from uiao.governance.identity.routing import compute_routing
from uiao.governance.identity.servicenow_ticket import (
    build_payload,
    create_ticket,
    create_tickets_for_event_set,
)


def _make_record(**kwargs) -> HRRecord:
    defaults = dict(
        employee_id="E001",
        first_name="Alice",
        last_name="Smith",
        department="IT",
        hire_date="2022-01-01",
        worker_type="FullTimeEmployee",
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
        resolved_orgpath="NCR.IT.Identity.Engineer",
    )
    defaults.update(kwargs)
    return HRRecord(**defaults)


class TestBuildPayload:
    def test_payload_has_required_fields(self):
        es = detect_events([_make_record()])
        event = es.joiners[0]
        routing = compute_routing(event)
        payload = build_payload(event, routing)
        d = payload.to_dict()
        assert "short_description" in d
        assert "description" in d
        assert "u_uiao_employee_id" in d
        assert d["u_uiao_employee_id"] == "E001"

    def test_joiner_category(self):
        es = detect_events([_make_record()])
        event = es.joiners[0]
        routing = compute_routing(event)
        payload = build_payload(event, routing)
        assert payload.category == "GOV-JOINER"

    def test_leaver_category(self):
        es = detect_events([_make_record(employment_status="Terminated", termination_date="2026-06-01")])
        event = es.leavers[0]
        routing = compute_routing(event)
        payload = build_payload(event, routing)
        assert payload.category == "GOV-LEAVER"

    def test_mover_category(self):
        prior = [_make_record(department="Finance")]
        current = [_make_record(department="IT")]
        es = detect_events(current, prior)
        event = es.movers[0]
        routing = compute_routing(event)
        payload = build_payload(event, routing)
        assert payload.category == "GOV-MOVER"

    def test_group_map_overrides_default(self):
        es = detect_events([_make_record()])
        event = es.joiners[0]
        routing = compute_routing(event)
        custom = {"division-manager:Identity": "My-Custom-Group"}
        payload = build_payload(event, routing, group_map=custom)
        assert payload.assignment_group == "My-Custom-Group"

    def test_orgpath_in_payload(self):
        es = detect_events([_make_record(resolved_orgpath="NCR.IT.Identity.Engineer")])
        event = es.joiners[0]
        routing = compute_routing(event)
        payload = build_payload(event, routing)
        assert payload.u_uiao_orgpath == "NCR.IT.Identity.Engineer"


class TestCreateTicketDryRun:
    def test_dry_run_returns_success(self):
        es = detect_events([_make_record()])
        result = create_ticket(es.joiners[0], dry_run=True)
        assert result.success is True
        assert result.dry_run is True
        assert result.ticket_number is None

    def test_dry_run_has_payload(self):
        es = detect_events([_make_record()])
        result = create_ticket(es.joiners[0], dry_run=True)
        assert result.payload is not None
        assert "u_uiao_employee_id" in result.payload

    def test_dry_run_false_without_url_raises(self):
        es = detect_events([_make_record()])
        with pytest.raises(ValueError, match="instance_url required"):
            create_ticket(es.joiners[0], dry_run=False, instance_url="")

    def test_result_to_dict(self):
        es = detect_events([_make_record()])
        result = create_ticket(es.joiners[0], dry_run=True)
        d = result.to_dict()
        assert d["success"] is True
        assert d["dry_run"] is True

    def test_create_tickets_for_event_set(self):
        current = [
            _make_record(employee_id="E001"),
            _make_record(employee_id="E002", employment_status="Terminated", termination_date="2026-06-01"),
        ]
        es = detect_events(current)
        results = create_tickets_for_event_set(es, dry_run=True)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_leaver_urgency_is_high(self):
        es = detect_events([_make_record(employment_status="Terminated", termination_date="2026-06-01")])
        result = create_ticket(es.leavers[0], dry_run=True)
        assert result.payload["urgency"] == "1"
