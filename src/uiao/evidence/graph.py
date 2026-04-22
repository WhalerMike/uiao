"""UIAO Evidence Graph (UIAO_113)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ControlNode:
    id: str; family: str = ""; baseline: str = "moderate"; priority: str = ""; description: str = ""; extra: Dict[str, Any] = field(default_factory=dict); node_type: str = "control"

@dataclass
class IRObjectNode:
    id: str; description: str = ""; mapping: str = ""; extra: Dict[str, Any] = field(default_factory=dict); node_type: str = "ir-object"

@dataclass
class EvidenceNode:
    id: str; source: str = ""; field_name: str = ""; value: Any = None; hash: str = ""; timestamp: str = ""; status: str = ""; verdict: str = ""; control_id: str = ""; extra: Dict[str, Any] = field(default_factory=dict); node_type: str = "evidence"

@dataclass
class ProvenanceNode:
    id: str; hash: str = ""; timestamp: str = ""; environment: str = ""; source: str = ""; version: str = ""; extra: Dict[str, Any] = field(default_factory=dict); node_type: str = "provenance"

@dataclass
class FindingNode:
    id: str; severity: str = "Medium"; description: str = ""; control_id: str = ""; drift_class: str = ""; status: str = "Open"; extra: Dict[str, Any] = field(default_factory=dict); node_type: str = "finding"

@dataclass
class POAMEntryNode:
    id: str; status: str = "Open"; milestones: List[str] = field(default_factory=list); remediation_sla_days: int = 30; recommended_action: str = ""; extra: Dict[str, Any] = field(default_factory=dict); node_type: str = "poam"

@dataclass
class Edge:
    from_id: str; to_id: str; edge_type: str; properties: Dict[str, Any] = field(default_factory=dict)

class EvidenceGraph:
    def __init__(self):
        self._nodes: Dict[str, Any] = {}
        self._edges: List[Edge] = []
        self._out: Dict[str, List[Edge]] = {}
        self._in: Dict[str, List[Edge]] = {}

    def _add(self, node):
        self._nodes[node.id] = node
        self._out.setdefault(node.id, [])
        self._in.setdefault(node.id, [])

    def add_control(self, node): self._add(node)
    def add_ir_object(self, node): self._add(node)
    def add_evidence(self, node): self._add(node)
    def add_provenance(self, node): self._add(node)
    def add_finding(self, node): self._add(node)
    def add_poam_entry(self, node): self._add(node)

    def _link(self, from_id, to_id, edge_type, **props):
        edge = Edge(from_id=from_id, to_id=to_id, edge_type=edge_type, properties=props)
        self._edges.append(edge)
        self._out.setdefault(from_id, []).append(edge)
        self._in.setdefault(to_id, []).append(edge)

    def link_implements(self, c, i, **p): self._link(c, i, "implements", **p)
    def link_validated_by(self, i, e, **p): self._link(i, e, "validated-by", **p)
    def link_provenance_of(self, e, pv, **p): self._link(e, pv, "provenance-of", **p)
    def link_violated_by(self, c, f, **p): self._link(c, f, "violated-by", **p)
    def link_remediated_by(self, f, po, **p): self._link(f, po, "remediated-by", **p)

    def get(self, node_id): return self._nodes.get(node_id)
    def nodes_of_type(self, t): return [n for n in self._nodes.values() if n.node_type == t]

    def evidence_for_control(self, control_id):
        ev = []; seen = set()
        for e1 in self._out.get(control_id, []):
            if e1.edge_type == "implements":
                for e2 in self._out.get(e1.to_id, []):
                    if e2.edge_type == "validated-by":
                        n = self._nodes.get(e2.to_id)
                        if isinstance(n, EvidenceNode) and n.id not in seen:
                            ev.append(n); seen.add(n.id)
        for n in self._nodes.values():
            if isinstance(n, EvidenceNode) and n.control_id == control_id and n.id not in seen:
                ev.append(n); seen.add(n.id)
        return ev

    def findings_for_control(self, control_id):
        return [self._nodes[e.to_id] for e in self._out.get(control_id, []) if e.edge_type == "violated-by" and isinstance(self._nodes.get(e.to_id), FindingNode)]

    def trace_control(self, control_id):
        ctrl = self._nodes.get(control_id); iro = []; ft = []
        for e1 in self._out.get(control_id, []):
            if e1.edge_type == "implements":
                ir = self._nodes.get(e1.to_id)
                if not isinstance(ir, IRObjectNode): continue
                evs = []
                for e2 in self._out.get(e1.to_id, []):
                    if e2.edge_type == "validated-by":
                        ev = self._nodes.get(e2.to_id)
                        if isinstance(ev, EvidenceNode):
                            provs = [self._nodes[e3.to_id].__dict__ for e3 in self._out.get(e2.to_id, []) if e3.edge_type == "provenance-of" and self._nodes.get(e3.to_id)]
                            evs.append({**ev.__dict__, "provenance": provs})
                iro.append({**ir.__dict__, "evidence": evs})
            elif e1.edge_type == "violated-by":
                f = self._nodes.get(e1.to_id)
                if isinstance(f, FindingNode):
                    poams = [self._nodes[e2.to_id].__dict__ for e2 in self._out.get(e1.to_id, []) if e2.edge_type == "remediated-by" and self._nodes.get(e2.to_id)]
                    ft.append({**f.__dict__, "poam_entries": poams})
        return {"control_id": control_id, "control": ctrl.__dict__ if ctrl else None, "ir_objects": iro, "findings": ft}

    def open_findings_with_poam(self):
        res = []
        for n in self._nodes.values():
            if isinstance(n, FindingNode) and n.status == "Open":
                poams = [self._nodes[e.to_id].__dict__ for e in self._out.get(n.id, []) if e.edge_type == "remediated-by" and self._nodes.get(e.to_id)]
                res.append({**n.__dict__, "poam_entries": poams})
        return res

    def stats(self):
        tc = {}; ec = {}
        for n in self._nodes.values(): tc[n.node_type] = tc.get(n.node_type, 0) + 1
        for e in self._edges: ec[e.edge_type] = ec.get(e.edge_type, 0) + 1
        return {"total_nodes": len(self._nodes), "total_edges": len(self._edges), "nodes_by_type": tc, "edges_by_type": ec}

    @classmethod
    def from_evidence_bundle(cls, bundle):
        g = cls()
        for ev in getattr(bundle, "evidence", []):
            cid = getattr(ev, "control_id", "") or ""
            g.add_evidence(EvidenceNode(id=ev.id, source=getattr(ev, "source", ""), control_id=cid, verdict="pass" if ev.evaluation.get("passed") else "fail" if ev.evaluation.get("failed") else "inconclusive", hash=ev.hash() if hasattr(ev, "hash") else ""))
            if hasattr(ev, "provenance"):
                pv = ev.provenance
                g.add_provenance(ProvenanceNode(id=f"prov:{ev.id}", source=pv.source, timestamp=str(pv.timestamp), version=pv.version or ""))
                g.link_provenance_of(ev.id, f"prov:{ev.id}")
            if cid:
                if cid not in g._nodes: g.add_control(ControlNode(id=cid))
                iid = f"ir:{cid}"
                if iid not in g._nodes: g.add_ir_object(IRObjectNode(id=iid)); g.link_implements(cid, iid)
                g.link_validated_by(iid, ev.id)
        for ds in getattr(bundle, "drift_states", []):
            if not ds.drift_detected: continue
            fid = f"find:{ds.id}"
            g.add_finding(FindingNode(id=fid, severity="High" if ds.classification=="unauthorized" else "Medium", control_id=ds.policy_ref, drift_class=getattr(ds, "drift_class", "") or "", status="Open"))
            if ds.policy_ref in g._nodes: g.link_violated_by(ds.policy_ref, fid)
        return g
