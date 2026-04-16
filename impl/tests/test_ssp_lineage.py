from __future__ import annotations

from uiao_impl.coverage.coverage import CoverageLink
from uiao_impl.governance.actions import GovernanceAction
from uiao_impl.ssp.lineage import build_lineage_index


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
        description="REMEDIATE IA-2",
        evidence_id=evidence_id,
    )


def test_lineage_basic_structure():
    idx = build_lineage_index([_link()], [_action()])
    assert "IA-2" in idx
    entry = idx["IA-2"]
    assert entry["ksis"] == ["KSI-IA-01"]
    assert entry["scuba_policies"] == ["SCUBA-IA-01"]
    assert entry["evidence"][0] == {"id": "e1", "hash": "hash-e1"}
    assert entry["governance_actions"][0]["action_type"] == "remediate"
    assert entry["governance_actions"][0]["owner"] == "team-identity@contoso.gov"
    assert entry["governance_actions"][0]["sla_days"] == 14


def test_lineage_no_actions():
    idx = build_lineage_index([_link()], [])
    assert idx["IA-2"]["governance_actions"] == []


def test_lineage_multiple_ksis_merged():
    links = [
        _link("IA-2", "KSI-IA-01", "e1"),
        _link("IA-2", "KSI-IA-02", "e2"),
    ]
    idx = build_lineage_index(links, [])
    assert sorted(idx["IA-2"]["ksis"]) == ["KSI-IA-01", "KSI-IA-02"]
    assert len(idx["IA-2"]["evidence"]) == 2


def test_lineage_multiple_controls():
    links = [_link("IA-2", "KSI-IA-01", "e1"), _link("SC-8", "KSI-SC-01", "e2")]
    idx = build_lineage_index(links, [])
    assert set(idx.keys()) == {"IA-2", "SC-8"}


def test_lineage_ksis_deduplicated():
    links = [_link("IA-2", "KSI-IA-01", "e1"), _link("IA-2", "KSI-IA-01", "e2")]
    idx = build_lineage_index(links, [])
    assert idx["IA-2"]["ksis"] == ["KSI-IA-01"]
    assert len(idx["IA-2"]["evidence"]) == 2

