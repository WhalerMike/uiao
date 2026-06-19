"""Tests for the AI System JML lifecycle engine (UIAO_197, ADR-114)."""

from __future__ import annotations


from uiao.governance.ai_inventory.drift import (
    DRIFT_AI_AGENTIC_UNGOVERNED,
    DRIFT_AI_NO_ORGPATH,
    DRIFT_AI_STALENESS,
)
from uiao.governance.ai_inventory.jml import (
    MOVER_TRIGGER_FIELDS,
    STALENESS_THRESHOLD_DAYS,
    JMLEventType,
    _diff_fields,
    detect_events,
)
from uiao.governance.ai_inventory.schema import (
    AgentClass,
    AISystemRecord,
    ATOStatus,
    DevStage,
)
from uiao.governance.drift_core import Posture, Severity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _record(
    omg_id: str = "OMB-001",
    agency: str = "DOD",
    bureau: str = "DISA",
    stage: DevStage = DevStage.DEPLOYED,
    agent_class: AgentClass = AgentClass.ML,
    ato_status: ATOStatus = ATOStatus.YES,
    contact_email: str | None = "owner@agency.gov",
    has_pii: bool = False,
    pia_url: str | None = None,
    is_high_impact: bool = False,
) -> AISystemRecord:
    """Minimal AISystemRecord for testing."""
    orgpath = f"{agency}:{bureau}" if bureau else agency
    return AISystemRecord(
        omg_id=omg_id,
        use_case_name=f"Test System {omg_id}",
        agency=agency,
        agency_name="Test Agency",
        agency_bureau=bureau,
        development_stage=stage,
        agent_class=agent_class,
        operational_date=None,
        ato_status=ato_status,
        system_name_ato=omg_id,
        vendor_name=None,
        contact_email=contact_email,
        has_pii=has_pii,
        pia_url=pia_url,
        is_high_impact=is_high_impact,
        hi_testing_conducted=None,
        hi_assessment_completed=None,
        hi_independent_review=None,
        hi_ongoing_monitoring=None,
        hi_failsafe_presence=None,
        hi_appeal_process=None,
        orgpath=orgpath,
    )


# ---------------------------------------------------------------------------
# Joiner detection
# ---------------------------------------------------------------------------


class TestJoiner:
    def test_new_deployed_system_is_joiner(self):
        current = [_record("NEW-001", stage=DevStage.DEPLOYED)]
        result = detect_events(current, prior_vintage=[])
        assert len(result.joiners) == 1
        assert result.joiners[0].event_type == JMLEventType.JOINER
        assert result.joiners[0].record.omg_id == "NEW-001"

    def test_new_pilot_system_is_joiner(self):
        current = [_record("NEW-002", stage=DevStage.PILOT)]
        result = detect_events(current, prior_vintage=[])
        assert len(result.joiners) == 1

    def test_new_pre_deployment_system_is_not_joiner(self):
        current = [_record("PRE-001", stage=DevStage.PRE_DEPLOYMENT)]
        result = detect_events(current, prior_vintage=[])
        assert len(result.joiners) == 0

    def test_new_retired_system_is_not_joiner(self):
        current = [_record("RET-001", stage=DevStage.RETIRED)]
        result = detect_events(current, prior_vintage=[])
        assert len(result.joiners) == 0

    def test_joiner_actions_include_j1_through_j6(self):
        current = [_record("SYS-001")]
        result = detect_events(current, prior_vintage=[])
        steps = {a.step for a in result.joiners[0].actions}
        for step in ("J-1", "J-2", "J-3", "J-4", "J-5", "J-6"):
            assert step in steps, f"Expected {step} in joiner actions"

    def test_j3_owner_assignment_is_never_autofix(self):
        current = [_record("SYS-001")]
        result = detect_events(current, prior_vintage=[])
        j3 = next(a for a in result.joiners[0].actions if a.step == "J-3")
        assert j3.posture == Posture.NEVER_AUTOFIX
        assert j3.requires_confirmation is True

    def test_joiner_with_no_prior_vintage(self):
        """When prior_vintage is None, all live systems are joiners."""
        current = [_record("A"), _record("B")]
        result = detect_events(current, prior_vintage=None)
        assert len(result.joiners) == 2

    def test_agentic_joiner_without_ato_emits_p1_finding(self):
        current = [_record("AGENTIC-001", agent_class=AgentClass.AGENTIC, ato_status=ATOStatus.NO)]
        result = detect_events(current, prior_vintage=[])
        assert len(result.joiners) == 1
        event = result.joiners[0]
        drift_classes = {f.drift_class for f in event.findings}
        assert DRIFT_AI_AGENTIC_UNGOVERNED in drift_classes
        finding = next(f for f in event.findings if f.drift_class == DRIFT_AI_AGENTIC_UNGOVERNED)
        assert finding.severity == Severity.P1

    def test_joiner_with_no_orgpath_emits_no_orgpath_finding(self):
        record = _record("NO-ORG-001", agency="DOD", bureau="")
        record.orgpath = None
        result = detect_events([record], prior_vintage=[])
        drift_classes = {f.drift_class for f in result.joiners[0].findings}
        assert DRIFT_AI_NO_ORGPATH in drift_classes

    def test_clean_joiner_emits_no_findings(self):
        current = [_record("CLEAN-001", agent_class=AgentClass.ML, ato_status=ATOStatus.YES)]
        result = detect_events(current, prior_vintage=[])
        assert result.joiners[0].findings == []


# ---------------------------------------------------------------------------
# Mover detection
# ---------------------------------------------------------------------------


class TestMover:
    def test_unchanged_system_is_not_mover(self):
        rec = _record("SAME-001")
        result = detect_events([rec], prior_vintage=[rec])
        assert len(result.movers) == 0

    def test_contact_email_change_is_mover(self):
        prior = _record("SYS-001", contact_email="old@agency.gov")
        current = _record("SYS-001", contact_email="new@agency.gov")
        result = detect_events([current], prior_vintage=[prior])
        assert len(result.movers) == 1
        assert "contact_email" in result.movers[0].changed_fields

    def test_bureau_change_is_mover(self):
        prior = _record("SYS-001", bureau="DISA")
        current = _record("SYS-001", bureau="NSA")
        result = detect_events([current], prior_vintage=[prior])
        assert len(result.movers) == 1
        assert "agency_bureau" in result.movers[0].changed_fields

    def test_agent_class_to_agentic_emits_p1_finding(self):
        prior = _record("SYS-001", agent_class=AgentClass.ML, ato_status=ATOStatus.NO)
        current = _record("SYS-001", agent_class=AgentClass.AGENTIC, ato_status=ATOStatus.NO)
        result = detect_events([current], prior_vintage=[prior])
        assert len(result.movers) == 1
        drift_classes = {f.drift_class for f in result.movers[0].findings}
        assert DRIFT_AI_AGENTIC_UNGOVERNED in drift_classes

    def test_is_high_impact_newly_true_triggers_action(self):
        prior = _record("SYS-001", is_high_impact=False)
        current = _record("SYS-001", is_high_impact=True)
        result = detect_events([current], prior_vintage=[prior])
        assert len(result.movers) == 1
        steps = {a.step for a in result.movers[0].actions}
        assert "M-is_high_impact" in steps

    def test_ato_status_no_triggers_mover_action(self):
        prior = _record("SYS-001", ato_status=ATOStatus.YES)
        current = _record("SYS-001", ato_status=ATOStatus.NO)
        result = detect_events([current], prior_vintage=[prior])
        steps = {a.step for a in result.movers[0].actions}
        assert "M-ato_status-gap" in steps

    def test_ato_status_cleared_triggers_mover_action(self):
        prior = _record("SYS-001", ato_status=ATOStatus.NO)
        current = _record("SYS-001", ato_status=ATOStatus.YES)
        result = detect_events([current], prior_vintage=[prior])
        steps = {a.step for a in result.movers[0].actions}
        assert "M-ato_status-cleared" in steps

    def test_pilot_to_deployed_triggers_scope_expansion_action(self):
        prior = _record("SYS-001", stage=DevStage.PILOT)
        current = _record("SYS-001", stage=DevStage.DEPLOYED)
        result = detect_events([current], prior_vintage=[prior])
        steps = {a.step for a in result.movers[0].actions}
        assert "M-development_stage" in steps
        scope_action = next(a for a in result.movers[0].actions if a.step == "M-development_stage")
        assert scope_action.posture == Posture.NEVER_AUTOFIX

    def test_multiple_changed_fields_all_produce_actions(self):
        prior = _record("SYS-001", bureau="DISA", contact_email="old@a.gov")
        current = _record("SYS-001", bureau="NSA", contact_email="new@a.gov")
        result = detect_events([current], prior_vintage=[prior])
        steps = {a.step for a in result.movers[0].actions}
        assert "M-agency_bureau" in steps
        assert "M-contact_email" in steps


# ---------------------------------------------------------------------------
# Leaver detection
# ---------------------------------------------------------------------------


class TestLeaver:
    def test_retired_in_current_vintage_is_confirmed_leaver(self):
        prior = _record("SYS-001", stage=DevStage.DEPLOYED)
        current = _record("SYS-001", stage=DevStage.RETIRED)
        result = detect_events([current], prior_vintage=[prior])
        assert len(result.leavers) == 1
        assert result.leavers[0].event_type == JMLEventType.LEAVER
        assert result.leavers[0].candidate_leaver is False

    def test_confirmed_leaver_has_8_steps(self):
        prior = _record("SYS-001", stage=DevStage.DEPLOYED)
        current = _record("SYS-001", stage=DevStage.RETIRED)
        result = detect_events([current], prior_vintage=[prior])
        steps = {a.step for a in result.leavers[0].actions}
        for step in ("L-1", "L-2", "L-3", "L-4", "L-5", "L-6", "L-7", "L-8"):
            assert step in steps

    def test_l4_l5_are_always_never_autofix(self):
        prior = _record("SYS-001", stage=DevStage.DEPLOYED)
        current = _record("SYS-001", stage=DevStage.RETIRED)
        result = detect_events([current], prior_vintage=[prior])
        for step_code in ("L-4", "L-5"):
            action = next(a for a in result.leavers[0].actions if a.step == step_code)
            assert action.posture == Posture.NEVER_AUTOFIX
            assert action.requires_confirmation is True

    def test_l1_l2_fire_at_day_0(self):
        prior = _record("SYS-001", stage=DevStage.DEPLOYED)
        current = _record("SYS-001", stage=DevStage.RETIRED)
        result = detect_events([current], prior_vintage=[prior])
        for step_code in ("L-1", "L-2"):
            action = next(a for a in result.leavers[0].actions if a.step == step_code)
            assert action.timeline_days == 0

    def test_absent_from_vintage_is_candidate_leaver(self):
        prior = [_record("SYS-001", stage=DevStage.DEPLOYED)]
        current: list[AISystemRecord] = []
        result = detect_events(current, prior_vintage=prior)
        assert len(result.candidate_leavers) == 1
        assert result.candidate_leavers[0].candidate_leaver is True

    def test_candidate_leaver_l3_to_l8_require_confirmation(self):
        prior = [_record("SYS-001", stage=DevStage.DEPLOYED)]
        result = detect_events([], prior_vintage=prior)
        held_steps = {
            a.step
            for a in result.candidate_leavers[0].actions
            if a.requires_confirmation and a.step not in ("L-4", "L-5")
        }
        for step in ("L-3", "L-6", "L-7", "L-8"):
            assert step in held_steps

    def test_candidate_leaver_l1_l2_do_not_require_confirmation(self):
        prior = [_record("SYS-001", stage=DevStage.DEPLOYED)]
        result = detect_events([], prior_vintage=prior)
        for step_code in ("L-1", "L-2"):
            action = next(a for a in result.candidate_leavers[0].actions if a.step == step_code)
            assert action.requires_confirmation is False

    def test_pre_deployment_absent_from_vintage_is_not_candidate_leaver(self):
        """Only live (deployed/pilot) systems become candidate leavers."""
        prior = [_record("PRE-001", stage=DevStage.PRE_DEPLOYMENT)]
        result = detect_events([], prior_vintage=prior)
        assert len(result.candidate_leavers) == 0

    def test_already_retired_absent_from_vintage_is_not_candidate_leaver(self):
        prior = [_record("RET-001", stage=DevStage.RETIRED)]
        result = detect_events([], prior_vintage=prior)
        assert len(result.candidate_leavers) == 0


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------


class TestStaleness:
    def test_over_threshold_emits_staleness_finding(self):
        rec = _record("STALE-001")
        result = detect_events(
            [rec],
            prior_vintage=[rec],
            days_since_last_mover={"STALE-001": STALENESS_THRESHOLD_DAYS + 1},
        )
        assert len(result.staleness_findings) == 1
        assert result.staleness_findings[0].drift_class == DRIFT_AI_STALENESS

    def test_exactly_at_threshold_does_not_emit(self):
        rec = _record("SYS-001")
        result = detect_events(
            [rec],
            prior_vintage=[rec],
            days_since_last_mover={"SYS-001": STALENESS_THRESHOLD_DAYS},
        )
        assert len(result.staleness_findings) == 0

    def test_below_threshold_does_not_emit(self):
        rec = _record("SYS-001")
        result = detect_events(
            [rec],
            prior_vintage=[rec],
            days_since_last_mover={"SYS-001": 100},
        )
        assert len(result.staleness_findings) == 0

    def test_staleness_finding_is_p3(self):
        rec = _record("STALE-001")
        result = detect_events(
            [rec],
            prior_vintage=[rec],
            days_since_last_mover={"STALE-001": STALENESS_THRESHOLD_DAYS + 1},
        )
        assert result.staleness_findings[0].severity == Severity.P3

    def test_staleness_finding_is_per_policy(self):
        rec = _record("STALE-001")
        result = detect_events(
            [rec],
            prior_vintage=[rec],
            days_since_last_mover={"STALE-001": STALENESS_THRESHOLD_DAYS + 1},
        )
        assert result.staleness_findings[0].posture == Posture.PER_POLICY

    def test_no_days_map_produces_no_staleness(self):
        rec = _record("SYS-001")
        result = detect_events([rec], prior_vintage=[rec])
        assert len(result.staleness_findings) == 0

    def test_non_live_system_not_checked_for_staleness(self):
        rec = _record("PRE-001", stage=DevStage.PRE_DEPLOYMENT)
        result = detect_events(
            [rec],
            prior_vintage=[rec],
            days_since_last_mover={"PRE-001": STALENESS_THRESHOLD_DAYS + 100},
        )
        assert len(result.staleness_findings) == 0


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------


class TestDiffFields:
    def test_identical_records_produce_no_diff(self):
        rec = _record("SYS-001")
        assert _diff_fields(rec, rec) == []

    def test_contact_email_change_detected(self):
        a = _record("SYS-001", contact_email="a@b.com")
        b = _record("SYS-001", contact_email="c@d.com")
        assert "contact_email" in _diff_fields(b, a)

    def test_non_trigger_field_not_in_diff(self):
        a = _record("SYS-001")
        b = _record("SYS-001")
        b.use_case_name = "Something Different"
        assert _diff_fields(b, a) == []

    def test_all_trigger_fields_are_checked(self):
        """Each field in MOVER_TRIGGER_FIELDS is individually detectable."""
        base = _record("SYS-001")
        for f in MOVER_TRIGGER_FIELDS:
            modified = _record("SYS-001")
            original_val = getattr(modified, f)
            # Swap to a different value that is not the same type — use None
            # for optional fields, or a known different enum value
            if original_val is None:
                object.__setattr__(modified, f, "CHANGED")
            elif isinstance(original_val, bool):
                object.__setattr__(modified, f, not original_val)
            elif isinstance(original_val, str):
                object.__setattr__(modified, f, original_val + "-CHANGED")
            else:
                # Enum — pick a different value if possible
                enum_type = type(original_val)
                others = [v for v in enum_type if v != original_val]
                if others:
                    object.__setattr__(modified, f, others[0])
                else:
                    continue
            assert f in _diff_fields(modified, base), f"Expected {f} to appear in diff when changed"


# ---------------------------------------------------------------------------
# JMLEventSet helpers
# ---------------------------------------------------------------------------


class TestJMLEventSet:
    def test_all_events_combines_all_buckets(self):
        prior = [_record("A", stage=DevStage.DEPLOYED)]
        current = [_record("B", stage=DevStage.DEPLOYED)]
        result = detect_events(current, prior_vintage=prior)
        assert len(result.all_events) == len(result.joiners) + len(result.candidate_leavers)

    def test_to_json_is_valid_json(self):
        import json

        rec = _record("SYS-001")
        result = detect_events([rec], prior_vintage=[])
        parsed = json.loads(result.to_json())
        assert "joiners" in parsed

    def test_summary_returns_string(self):
        result = detect_events([], prior_vintage=[])
        s = result.summary()
        assert isinstance(s, str)
        assert "joiner" in s
