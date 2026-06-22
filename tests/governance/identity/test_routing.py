"""Tests for governance/identity/routing.py — approval routing decisions."""

from __future__ import annotations


from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.governance.identity.jml import detect_events
from uiao.governance.identity.routing import (
    AUTHORITY_GRC_MANAGER,
    AUTHORITY_IDENTITY_TEAM,
    ApprovalTier,
    compute_routing,
    stamp_routing,
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
        resolved_orgpath=None,
    )
    defaults.update(kwargs)
    return HRRecord(**defaults)


class TestRoutingRules:
    def test_service_worker_type_routes_to_identity_team(self):
        current = [_make_record(worker_type="Service")]
        es = detect_events(current)
        decision = compute_routing(es.joiners[0])
        assert decision.authority == AUTHORITY_IDENTITY_TEAM

    def test_privileged_orgpath_routes_to_grc_manager(self):
        current = [_make_record(resolved_orgpath="NCR.IT.Identity.Privileged")]
        es = detect_events(current)
        decision = compute_routing(es.joiners[0])
        assert decision.authority == AUTHORITY_GRC_MANAGER

    def test_standard_employee_routes_to_division_manager(self):
        current = [_make_record(division="Identity")]
        es = detect_events(current)
        decision = compute_routing(es.joiners[0])
        assert decision.authority == "division-manager:Identity"

    def test_placement_change_routes_to_new_division_manager(self):
        prior = [_make_record(department="Finance", division="Finance")]
        current = [_make_record(department="IT", division="Identity")]
        es = detect_events(current, prior)
        decision = compute_routing(es.movers[0])
        assert decision.authority == "division-manager:Identity"

    def test_all_decisions_are_l3_gated(self):
        current = [_make_record()]
        es = detect_events(current)
        decision = compute_routing(es.joiners[0])
        assert decision.tier == ApprovalTier.GATED

    def test_stamp_routing_sets_routing_key_on_event(self):
        current = [_make_record(division="Identity")]
        es = detect_events(current)
        event = es.joiners[0]
        assert event.routing_key is None
        stamp_routing(event)
        assert event.routing_key == "division-manager:Identity"

    def test_decision_to_dict(self):
        current = [_make_record()]
        es = detect_events(current)
        d = compute_routing(es.joiners[0]).to_dict()
        assert "authority" in d
        assert "tier" in d
        assert "rationale" in d
