"""Tests for uiao.governance: ownership, SLA, actions, report."""

from __future__ import annotations

from datetime import datetime, timezone


from uiao.governance.actions import (
    build_governance_actions,
    classify_action_type,
)
from uiao.governance.ownership import resolve_owner_for_ksi
from uiao.governance.report import format_governance_report, summarize_actions
from uiao.governance.sla import resolve_sla_days
from uiao.ir.models.core import DriftState, Evidence, ProvenanceRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test-suite",
        timestamp=datetime(2026, 4, 8, tzinfo=timezone.utc).isoformat(),
        version="0.0.1-test",
        content_hash=None,
        actor="pytest",
    )


def _evidence(
    eid: str = "e1",
    ksi_id: str = "KSI-IA-01",
    status: str = "FAIL",
    severity: str = "Critical",
    resource_id: str = "res-1",
    policy_id: str = "policy:ksi:KSI-IA-01:default",
) -> Evidence:
    return Evidence(
        id=eid,
        source="scuba:test-run",
        control_id=ksi_id,
        policy_id=policy_id,
        timestamp="2026-04-08T00:00:00Z",
        data={
            "ksi_id": ksi_id,
            "status": status,
            "severity": severity,
            "resource_id": resource_id,
        },
        evaluation={"passed": status == "PASS", "failed": status == "FAIL", "warning": status == "WARN"},
        provenance=_prov(),
    )


def _drift(
    resource_id: str = "res-1",
    policy_ref: str = "policy:ksi:KSI-IA-01:default",
    classification: str = "unauthorized",
) -> DriftState:
    return DriftState(
        id=f"drift:{resource_id}:{policy_ref}",
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash="aaa",
        actual_hash="bbb",
        drift_detected=True,
        classification=classification,
        delta={"added": [], "removed": [], "changed": ["x"]},
        provenance=_prov(),
    )


# ---------------------------------------------------------------------------
# SLA tests
# ---------------------------------------------------------------------------
class TestSLA:
    def test_critical_sla(self) -> None:
        assert resolve_sla_days("Critical") == 7

    def test_high_sla(self) -> None:
        assert resolve_sla_days("High") == 14

    def test_medium_sla(self) -> None:
        assert resolve_sla_days("Medium") == 30

    def test_low_sla(self) -> None:
        assert resolve_sla_days("Low") == 60

    def test_unknown_sla_defaults(self) -> None:
        assert resolve_sla_days("Unknown") == 30


# ---------------------------------------------------------------------------
# Ownership tests
# ---------------------------------------------------------------------------
class TestOwnership:
    def test_ksi_ia_prefix(self) -> None:
        assert resolve_owner_for_ksi("KSI-IA-01") == "team-identity@contoso.gov"

    def test_ksi_ac_prefix(self) -> None:
        assert resolve_owner_for_ksi("KSI-AC-02") == "team-access@contoso.gov"

    def test_ksi_au_prefix(self) -> None:
        assert resolve_owner_for_ksi("KSI-AU-01") == "team-audit@contoso.gov"

    def test_ksi_sc_prefix(self) -> None:
        assert resolve_owner_for_ksi("KSI-SC-01") == "team-sec-arch@contoso.gov"

    def test_unknown_prefix_defaults(self) -> None:
        assert resolve_owner_for_ksi("KSI-XX-99") == "team-compliance@contoso.gov"


# ---------------------------------------------------------------------------
# classify_action_type tests
# ---------------------------------------------------------------------------
class TestClassifyActionType:
    def test_unauthorized_drift_always_escalates(self) -> None:
        assert classify_action_type("Critical", "unauthorized") == "escalate"
        assert classify_action_type("Low", "unauthorized") == "escalate"

    def test_critical_no_drift_remediates(self) -> None:
        assert classify_action_type("Critical", "benign") == "remediate"
        assert classify_action_type("Critical", None) == "remediate"

    def test_high_no_drift_remediates(self) -> None:
        assert classify_action_type("High", None) == "remediate"

    def test_medium_monitors(self) -> None:
        assert classify_action_type("Medium", None) == "monitor"
        assert classify_action_type("Medium", "risky") == "monitor"

    def test_low_monitors(self) -> None:
        assert classify_action_type("Low", None) == "monitor"

    def test_unknown_severity_reviews(self) -> None:
        assert classify_action_type("Unknown", None) == "review"


# ---------------------------------------------------------------------------
# build_governance_actions tests
# ---------------------------------------------------------------------------
class TestBuildGovernanceActions:
    def test_single_evidence_no_drift(self) -> None:
        e = _evidence(severity="High")
        actions = build_governance_actions([e], [])
        assert len(actions) == 1
        a = actions[0]
        assert a.ksi_id == "KSI-IA-01"
        assert a.action_type == "remediate"
        assert a.sla_days == 14
        assert a.owner == "team-identity@contoso.gov"
        assert a.drift_classification is None

    def test_unauthorized_drift_escalates(self) -> None:
        e = _evidence(severity="Critical")
        d = _drift(classification="unauthorized")
        actions = build_governance_actions([e], [d])
        assert actions[0].action_type == "escalate"
        assert actions[0].drift_classification == "unauthorized"

    def test_benign_drift_still_remediates_critical(self) -> None:
        e = _evidence(severity="Critical")
        d = _drift(classification="benign")
        actions = build_governance_actions([e], [d])
        assert actions[0].action_type == "remediate"

    def test_empty_evidence_returns_empty(self) -> None:
        actions = build_governance_actions([], [])
        assert actions == []

    def test_multiple_evidence_objects(self) -> None:
        e1 = _evidence("e1", "KSI-IA-01", "FAIL", "Critical", "res-1", "policy:ksi:KSI-IA-01:default")
        e2 = _evidence("e2", "KSI-AC-01", "FAIL", "Medium", "res-2", "policy:ksi:KSI-AC-01:default")
        actions = build_governance_actions([e1, e2], [])
        assert len(actions) == 2
        by_ksi = {a.ksi_id: a for a in actions}
        assert by_ksi["KSI-IA-01"].action_type == "remediate"
        assert by_ksi["KSI-AC-01"].action_type == "monitor"

    def test_deterministic_output(self) -> None:
        """Same inputs always produce identical GovernanceAction lists."""
        e = _evidence()
        d = _drift()
        run_a = build_governance_actions([e], [d])
        run_b = build_governance_actions([e], [d])
        assert run_a == run_b

    def test_pass_evidence_still_produces_action(self) -> None:
        """build_governance_actions processes all evidence regardless of status."""
        e = _evidence(status="PASS", severity="Low")
        actions = build_governance_actions([e], [])
        assert len(actions) == 1
        assert actions[0].action_type == "monitor"


# ---------------------------------------------------------------------------
# summarize_actions + format_governance_report tests
# ---------------------------------------------------------------------------
class TestReport:
    def test_summarize_counts_by_type(self) -> None:
        e1 = _evidence("e1", severity="Critical")
        e2 = _evidence(
            "e2", "KSI-AC-01", severity="Medium", resource_id="res-2", policy_id="policy:ksi:KSI-AC-01:default"
        )
        actions = build_governance_actions([e1, e2], [])
        summary = summarize_actions(actions)
        assert summary["remediate"] == 1
        assert summary["monitor"] == 1

    def test_format_report_contains_headers(self) -> None:
        e = _evidence()
        actions = build_governance_actions([e], [])
        report = format_governance_report(actions)
        assert "UIAO Governance Report" in report
        assert "By action type:" in report
        assert "Top actions:" in report

    def test_format_report_contains_action_line(self) -> None:
        e = _evidence()
        actions = build_governance_actions([e], [_drift()])
        report = format_governance_report(actions)
        assert "ESCALATE" in report
        assert "KSI-IA-01" in report

    def test_empty_actions_report(self) -> None:
        report = format_governance_report([])
        assert "UIAO Governance Report" in report
        assert "Top actions:" in report

