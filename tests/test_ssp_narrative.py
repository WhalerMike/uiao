from __future__ import annotations

from uiao.coverage.coverage import CoverageLink
from uiao.governance.actions import GovernanceAction
from uiao.ssp.narrative import build_control_narratives, format_ssp_markdown


def _link(control: str = "IA-2", ksi: str = "KSI-IA-01", evidence_id: str = "e1") -> CoverageLink:
    return CoverageLink(
        nist_control=control,
        ksi_id=ksi,
        scuba_policy_id="SCUBA-IA-01",
        evidence_id=evidence_id,
        evidence_hash=f"hash-{evidence_id}",
    )


def _action(evidence_id: str = "e1", action_type: str = "remediate") -> GovernanceAction:
    return GovernanceAction(
        ksi_id="KSI-IA-01",
        control_id="KSI-IA-01",
        policy_id="policy:ksi:KSI-IA-01:default",
        severity="High",
        drift_classification="unauthorized",
        owner="team-identity@contoso.gov",
        sla_days=14,
        action_type=action_type,
        description=f"{action_type.upper()} IA-2",
        evidence_id=evidence_id,
    )


def test_single_control_narrative():
    narratives = build_control_narratives([_link()], [_action()])
    assert len(narratives) == 1
    n = narratives[0]
    assert n.nist_control == "IA-2"
    assert "KSI-IA-01" in n.summary
    assert "hash-e1" in n.summary
    assert n.drift_status == "at-risk"
    assert "remediate" in n.governance_action_types


def test_escalate_action_sets_at_risk():
    narratives = build_control_narratives([_link()], [_action(action_type="escalate")])
    assert narratives[0].drift_status == "at-risk"


def test_monitor_action_sets_monitored():
    narratives = build_control_narratives([_link()], [_action(action_type="monitor")])
    assert narratives[0].drift_status == "monitored"


def test_no_actions_drift_status_none():
    narratives = build_control_narratives([_link()], [])
    assert narratives[0].drift_status is None


def test_multiple_controls_sorted():
    links = [_link("SC-8", "KSI-SC-01", "e2"), _link("IA-2", "KSI-IA-01", "e1")]
    narratives = build_control_narratives(links, [])
    assert [n.nist_control for n in narratives] == ["IA-2", "SC-8"]


def test_format_ssp_markdown_headings():
    narratives = build_control_narratives([_link()], [_action()])
    md = format_ssp_markdown(narratives)
    assert "# System Security Plan - Narrative" in md
    assert "## Control IA-2" in md
    assert "KSI-IA-01" in md
    assert "at-risk" in md


def test_format_ssp_markdown_no_drift_section_when_none():
    narratives = build_control_narratives([_link()], [])
    md = format_ssp_markdown(narratives)
    assert "governance status" not in md

