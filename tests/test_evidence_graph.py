"""tests/test_evidence_graph.py — UIAO_113 Evidence Graph tests."""

from __future__ import annotations
from uiao.evidence.graph import (
    ControlNode,
    EvidenceNode,
    FindingNode,
    IRObjectNode,
    POAMEntryNode,
    ProvenanceNode,
    EvidenceGraph,
)


def _graph() -> EvidenceGraph:
    g = EvidenceGraph()
    g.add_control(ControlNode(id="AC-2", family="AC", baseline="moderate"))
    g.add_control(ControlNode(id="IA-2", family="IA", baseline="moderate"))
    g.add_ir_object(IRObjectNode(id="IR-ACCT-MFA-001", description="MFA IR object"))
    g.add_ir_object(IRObjectNode(id="IR-ACCT-MFA-002", description="MFA IR object 2"))
    g.add_evidence(EvidenceNode(id="EV-001", source="scuba", control_id="AC-2", verdict="pass", status="satisfied"))
    g.add_evidence(EvidenceNode(id="EV-002", source="scuba", control_id="AC-2", verdict="fail", status="not-satisfied"))
    g.add_evidence(EvidenceNode(id="EV-003", source="scuba", control_id="IA-2", verdict="pass", status="satisfied"))
    g.add_provenance(ProvenanceNode(id="PROV-001", source="scuba-run", timestamp="2026-04-20T00:00:00Z"))
    g.add_finding(FindingNode(id="FIND-001", severity="High", control_id="AC-2", status="Open"))
    g.add_finding(FindingNode(id="FIND-002", severity="Medium", control_id="AC-2", status="Closed"))
    g.add_poam_entry(POAMEntryNode(id="POAM-001", status="Open", remediation_sla_days=30))
    g.link_implements("AC-2", "IR-ACCT-MFA-001")
    g.link_implements("AC-2", "IR-ACCT-MFA-002")
    g.link_validated_by("IR-ACCT-MFA-001", "EV-001")
    g.link_validated_by("IR-ACCT-MFA-002", "EV-002")
    g.link_provenance_of("EV-001", "PROV-001")
    g.link_violated_by("AC-2", "FIND-001")
    g.link_violated_by("AC-2", "FIND-002")
    g.link_remediated_by("FIND-001", "POAM-001")
    return g


class TestNodeRegistration:
    def test_nodes_stored(self):
        g = _graph()
        assert g.get("AC-2") is not None
        assert g.get("EV-001") is not None
        assert g.get("PROV-001") is not None
        assert g.get("FIND-001") is not None
        assert g.get("POAM-001") is not None

    def test_node_types(self):
        g = _graph()
        assert g.get("AC-2").node_type == "control"
        assert g.get("EV-001").node_type == "evidence"
        assert g.get("PROV-001").node_type == "provenance"
        assert g.get("FIND-001").node_type == "finding"
        assert g.get("POAM-001").node_type == "poam"

    def test_nodes_of_type(self):
        g = _graph()
        controls = g.nodes_of_type("control")
        assert len(controls) == 2
        evidence = g.nodes_of_type("evidence")
        assert len(evidence) == 3


class TestEdges:
    def test_implements_edge(self):
        g = _graph()
        edges = [e for e in g._out["AC-2"] if e.edge_type == "implements"]
        assert len(edges) == 2

    def test_validated_by_edge(self):
        g = _graph()
        edges = [e for e in g._out["IR-ACCT-MFA-001"] if e.edge_type == "validated-by"]
        assert len(edges) == 1
        assert edges[0].to_id == "EV-001"

    def test_provenance_of_edge(self):
        g = _graph()
        edges = [e for e in g._out["EV-001"] if e.edge_type == "provenance-of"]
        assert len(edges) == 1
        assert edges[0].to_id == "PROV-001"

    def test_violated_by_edge(self):
        g = _graph()
        edges = [e for e in g._out["AC-2"] if e.edge_type == "violated-by"]
        assert len(edges) == 2

    def test_remediated_by_edge(self):
        g = _graph()
        edges = [e for e in g._out["FIND-001"] if e.edge_type == "remediated-by"]
        assert len(edges) == 1
        assert edges[0].to_id == "POAM-001"


class TestTraversals:
    def test_evidence_for_control_via_ir(self):
        g = _graph()
        ev = g.evidence_for_control("AC-2")
        ids = [e.id for e in ev]
        assert "EV-001" in ids
        assert "EV-002" in ids

    def test_evidence_for_control_direct(self):
        g = _graph()
        ev = g.evidence_for_control("IA-2")
        assert any(e.id == "EV-003" for e in ev)

    def test_evidence_for_unknown_control(self):
        g = _graph()
        assert g.evidence_for_control("ZZ-99") == []

    def test_findings_for_control(self):
        g = _graph()
        findings = g.findings_for_control("AC-2")
        assert len(findings) == 2
        ids = [f.id for f in findings]
        assert "FIND-001" in ids
        assert "FIND-002" in ids

    def test_findings_for_control_no_findings(self):
        g = _graph()
        assert g.findings_for_control("IA-2") == []

    def test_trace_control_structure(self):
        g = _graph()
        trace = g.trace_control("AC-2")
        assert trace["control_id"] == "AC-2"
        assert trace["control"] is not None
        assert len(trace["ir_objects"]) == 2
        assert len(trace["findings"]) == 2
        # Check evidence nested in IR objects
        ir_with_ev = next(ir for ir in trace["ir_objects"] if ir["id"] == "IR-ACCT-MFA-001")
        assert len(ir_with_ev["evidence"]) == 1
        # Check POAM nested in finding
        f = next(f for f in trace["findings"] if f["id"] == "FIND-001")
        assert len(f["poam_entries"]) == 1

    def test_trace_unknown_control(self):
        g = _graph()
        trace = g.trace_control("ZZ-99")
        assert trace["control"] is None
        assert trace["ir_objects"] == []

    def test_open_findings_with_poam(self):
        g = _graph()
        results = g.open_findings_with_poam()
        assert len(results) == 1
        assert results[0]["id"] == "FIND-001"
        assert len(results[0]["poam_entries"]) == 1


class TestStats:
    def test_stats_counts(self):
        g = _graph()
        s = g.stats()
        assert s["total_nodes"] == 11
        assert s["total_edges"] == 8
        assert s["nodes_by_type"]["control"] == 2
        assert s["nodes_by_type"]["evidence"] == 3
        assert s["edges_by_type"]["implements"] == 2
        assert s["edges_by_type"]["validated-by"] == 2
