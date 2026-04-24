"""UIAO Evidence Graph (UIAO_113)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Severity normalization for scheduler-originated drift reports.
# Drift reports carry free-form severity strings (P1/P3/High/critical/info).
# We normalize to FindingNode's High/Medium/Low vocabulary so SAR props stay
# consistent with the SCuBA-derived path.
_SEVERITY_MAP = {
    "p1": "High",
    "p2": "High",
    "critical": "High",
    "high": "High",
    "p3": "Medium",
    "medium": "Medium",
    "warn": "Medium",
    "warning": "Medium",
    "p4": "Low",
    "p5": "Low",
    "low": "Low",
    "info": "Low",
    "informational": "Low",
}


def _normalize_severity(value: Optional[str]) -> str:
    if not value:
        return "Medium"
    return _SEVERITY_MAP.get(str(value).strip().lower(), "Medium")


@dataclass
class ControlNode:
    id: str
    family: str = ""
    baseline: str = "moderate"
    priority: str = ""
    description: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    node_type: str = "control"


@dataclass
class IRObjectNode:
    id: str
    description: str = ""
    mapping: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    node_type: str = "ir-object"


@dataclass
class EvidenceNode:
    id: str
    source: str = ""
    field_name: str = ""
    value: Any = None
    hash: str = ""
    timestamp: str = ""
    status: str = ""
    verdict: str = ""
    control_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    node_type: str = "evidence"


@dataclass
class ProvenanceNode:
    id: str
    hash: str = ""
    timestamp: str = ""
    environment: str = ""
    source: str = ""
    version: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    node_type: str = "provenance"


@dataclass
class FindingNode:
    id: str
    severity: str = "Medium"
    description: str = ""
    control_id: str = ""
    drift_class: str = ""
    status: str = "Open"
    extra: Dict[str, Any] = field(default_factory=dict)
    node_type: str = "finding"


@dataclass
class POAMEntryNode:
    id: str
    status: str = "Open"
    milestones: List[str] = field(default_factory=list)
    remediation_sla_days: int = 30
    recommended_action: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    node_type: str = "poam"


@dataclass
class Edge:
    from_id: str
    to_id: str
    edge_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


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

    def add_control(self, node):
        self._add(node)

    def add_ir_object(self, node):
        self._add(node)

    def add_evidence(self, node):
        self._add(node)

    def add_provenance(self, node):
        self._add(node)

    def add_finding(self, node):
        self._add(node)

    def add_poam_entry(self, node):
        self._add(node)

    def _link(self, from_id, to_id, edge_type, **props):
        edge = Edge(from_id=from_id, to_id=to_id, edge_type=edge_type, properties=props)
        self._edges.append(edge)
        self._out.setdefault(from_id, []).append(edge)
        self._in.setdefault(to_id, []).append(edge)

    def link_implements(self, c, i, **p):
        self._link(c, i, "implements", **p)

    def link_validated_by(self, i, e, **p):
        self._link(i, e, "validated-by", **p)

    def link_provenance_of(self, e, pv, **p):
        self._link(e, pv, "provenance-of", **p)

    def link_violated_by(self, c, f, **p):
        self._link(c, f, "violated-by", **p)

    def link_remediated_by(self, f, po, **p):
        self._link(f, po, "remediated-by", **p)

    def get(self, node_id):
        return self._nodes.get(node_id)

    def nodes_of_type(self, t):
        return [n for n in self._nodes.values() if n.node_type == t]

    def evidence_for_control(self, control_id):
        ev = []
        seen = set()
        for e1 in self._out.get(control_id, []):
            if e1.edge_type == "implements":
                for e2 in self._out.get(e1.to_id, []):
                    if e2.edge_type == "validated-by":
                        n = self._nodes.get(e2.to_id)
                        if isinstance(n, EvidenceNode) and n.id not in seen:
                            ev.append(n)
                            seen.add(n.id)
        for n in self._nodes.values():
            if isinstance(n, EvidenceNode) and n.control_id == control_id and n.id not in seen:
                ev.append(n)
                seen.add(n.id)
        return ev

    def findings_for_control(self, control_id):
        return [
            self._nodes[e.to_id]
            for e in self._out.get(control_id, [])
            if e.edge_type == "violated-by" and isinstance(self._nodes.get(e.to_id), FindingNode)
        ]

    def trace_control(self, control_id):
        ctrl = self._nodes.get(control_id)
        iro = []
        ft = []
        for e1 in self._out.get(control_id, []):
            if e1.edge_type == "implements":
                ir = self._nodes.get(e1.to_id)
                if not isinstance(ir, IRObjectNode):
                    continue
                evs = []
                for e2 in self._out.get(e1.to_id, []):
                    if e2.edge_type == "validated-by":
                        ev = self._nodes.get(e2.to_id)
                        if isinstance(ev, EvidenceNode):
                            provs = [
                                self._nodes[e3.to_id].__dict__
                                for e3 in self._out.get(e2.to_id, [])
                                if e3.edge_type == "provenance-of" and self._nodes.get(e3.to_id)
                            ]
                            evs.append({**ev.__dict__, "provenance": provs})
                iro.append({**ir.__dict__, "evidence": evs})
            elif e1.edge_type == "violated-by":
                f = self._nodes.get(e1.to_id)
                if isinstance(f, FindingNode):
                    poams = [
                        self._nodes[e2.to_id].__dict__
                        for e2 in self._out.get(e1.to_id, [])
                        if e2.edge_type == "remediated-by" and self._nodes.get(e2.to_id)
                    ]
                    ft.append({**f.__dict__, "poam_entries": poams})
        return {"control_id": control_id, "control": ctrl.__dict__ if ctrl else None, "ir_objects": iro, "findings": ft}

    def open_findings_with_poam(self):
        res = []
        for n in self._nodes.values():
            if isinstance(n, FindingNode) and n.status == "Open":
                poams = [
                    self._nodes[e.to_id].__dict__
                    for e in self._out.get(n.id, [])
                    if e.edge_type == "remediated-by" and self._nodes.get(e.to_id)
                ]
                res.append({**n.__dict__, "poam_entries": poams})
        return res

    def stats(self):
        tc: Dict[str, int] = {}
        ec: Dict[str, int] = {}
        for n in self._nodes.values():
            tc[n.node_type] = tc.get(n.node_type, 0) + 1
        for e in self._edges:
            ec[e.edge_type] = ec.get(e.edge_type, 0) + 1
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": tc,
            "edges_by_type": ec,
        }

    # ------------------------------------------------------------------
    # Scheduler-run ingestion (UIAO_100 ↔ UIAO_113 bridge)
    # ------------------------------------------------------------------

    @classmethod
    def from_scheduler_run(cls, run_dir: Path | str) -> EvidenceGraph:
        """Build a graph from a UIAO_100 scheduler run directory.

        Consumes the on-disk layout produced by
        ``uiao.orchestrator.scheduler.OrchestratorScheduler.dispatch_all()``::

            <run_dir>/
              manifest.json           # optional — provides scheduler run_id
              adapters/<adapter_id>/
                evidence.json         # EvidenceObject.to_dict()
                drift.json            # DriftReport.to_dict()

        Each adapter contributes:
            - one EvidenceNode  (``ev:<run_id>:<adapter_id>``)
            - one ProvenanceNode (``prov:<run_id>:<adapter_id>``)
            - a ControlNode for the evidence's ``ksi_id`` (if it looks like
              a NIST-style control reference) plus an IRObjectNode/edge
              trio mirroring ``from_evidence_bundle``
            - one FindingNode if ``drift.json`` indicates detected drift

        Missing drift.json is treated as "no drift" (not an error). Missing
        evidence.json skips the adapter entry with no contribution. The
        scheduler's manifest.json is read for the run_id when available; if
        absent, the directory name is used as a stable fallback.
        """
        run_dir_path = Path(run_dir)
        if not run_dir_path.is_dir():
            raise FileNotFoundError(f"Scheduler run directory not found: {run_dir_path}")

        run_id = cls._read_run_id(run_dir_path)
        adapters_root = run_dir_path / "adapters"
        if not adapters_root.is_dir():
            # Nothing to ingest; still return a valid empty graph.
            return cls()

        g = cls()
        for adapter_dir in sorted(adapters_root.iterdir()):
            if not adapter_dir.is_dir():
                continue
            adapter_id = adapter_dir.name
            evidence_json = adapter_dir / "evidence.json"
            drift_json = adapter_dir / "drift.json"
            if not evidence_json.is_file():
                continue
            cls._ingest_adapter(
                g,
                run_id=run_id,
                adapter_id=adapter_id,
                evidence_path=evidence_json,
                drift_path=drift_json if drift_json.is_file() else None,
            )
        return g

    @staticmethod
    def _read_run_id(run_dir: Path) -> str:
        manifest = run_dir / "manifest.json"
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                rid = data.get("run_id")
                if isinstance(rid, str) and rid:
                    return rid
            except (OSError, json.JSONDecodeError):
                pass
        return run_dir.name

    @staticmethod
    def _infer_control_id(ksi_id: str) -> str:
        """Best-effort control-ID derivation from a KSI reference.

        Matches NIST 800-53 shapes like ``ksi:AC-2`` or ``AC-2:identity``.
        Returns an empty string when nothing resembling a control family
        prefix is found — callers attach the evidence without a control hop.
        """
        if not ksi_id:
            return ""
        import re

        m = re.search(r"([A-Z]{2}-\d+(?:\(\d+\))?)", ksi_id)
        return m.group(1) if m else ""

    @classmethod
    def _ingest_adapter(
        cls,
        g: EvidenceGraph,
        *,
        run_id: str,
        adapter_id: str,
        evidence_path: Path,
        drift_path: Optional[Path],
    ) -> None:
        try:
            evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        ksi_id = str(evidence_payload.get("ksi_id") or "")
        control_id = cls._infer_control_id(ksi_id)
        evidence_node_id = f"ev:{run_id}:{adapter_id}"
        provenance_node_id = f"prov:{run_id}:{adapter_id}"

        evidence_hash = ""
        provenance_field = evidence_payload.get("provenance") or {}
        if isinstance(provenance_field, dict):
            evidence_hash = str(provenance_field.get("hash") or "")

        g.add_evidence(
            EvidenceNode(
                id=evidence_node_id,
                source=str(evidence_payload.get("source") or adapter_id),
                field_name="scheduler-run",
                value=None,
                hash=evidence_hash,
                timestamp=str(evidence_payload.get("timestamp") or ""),
                status="collected",
                verdict="inconclusive",
                control_id=control_id,
                extra={
                    "run_id": run_id,
                    "adapter_id": adapter_id,
                    "ksi_id": ksi_id,
                    "freshness_valid": bool(evidence_payload.get("freshness_valid", False)),
                },
            )
        )
        g.add_provenance(
            ProvenanceNode(
                id=provenance_node_id,
                hash=evidence_hash,
                timestamp=str(evidence_payload.get("timestamp") or ""),
                source=str(evidence_payload.get("source") or adapter_id),
                version=str(provenance_field.get("version") or "") if isinstance(provenance_field, dict) else "",
                extra={"run_id": run_id, "adapter_id": adapter_id},
            )
        )
        g.link_provenance_of(evidence_node_id, provenance_node_id)

        if control_id:
            if control_id not in g._nodes:
                g.add_control(ControlNode(id=control_id))
            ir_id = f"ir:{control_id}"
            if ir_id not in g._nodes:
                g.add_ir_object(IRObjectNode(id=ir_id, description=f"IR for {control_id} via {adapter_id}"))
                g.link_implements(control_id, ir_id)
            g.link_validated_by(ir_id, evidence_node_id)

        if drift_path is None:
            return
        try:
            drift_payload = json.loads(drift_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        severity_raw = drift_payload.get("severity")
        drift_type = str(drift_payload.get("drift_type") or "")
        # Only materialize a Finding when the adapter actually reported drift:
        # empty/null severity AND empty details → nothing to record.
        details = drift_payload.get("details") or {}
        if not severity_raw and not details:
            return

        finding_id = f"find:{run_id}:{adapter_id}"
        g.add_finding(
            FindingNode(
                id=finding_id,
                severity=_normalize_severity(severity_raw),
                description=f"Drift in {adapter_id} ({drift_type or 'unspecified'})",
                control_id=control_id,
                drift_class=drift_type,
                status="Open",
                extra={
                    "run_id": run_id,
                    "adapter_id": adapter_id,
                    "severity_raw": severity_raw,
                    "first_observed": drift_payload.get("first_observed"),
                    "last_observed": drift_payload.get("last_observed"),
                },
            )
        )
        if control_id and control_id in g._nodes:
            g.link_violated_by(control_id, finding_id)

    # ------------------------------------------------------------------
    # DRIFT-SEMANTIC ingestion (UIAO_016 ↔ UIAO_113 bridge)
    # ------------------------------------------------------------------

    def ingest_drift_semantic(self, findings) -> int:
        """Fold DRIFT-SEMANTIC findings from the freshness evaluator into the graph.

        Accepts any iterable of objects exposing the
        :class:`uiao.freshness.drift_semantic.FreshnessFinding` attribute
        surface (``status``, ``severity``, ``adapter_id``, ``run_id``,
        ``ksi_id``, ``age_hours``, ``window_hours``, ``evaluated_at``,
        ``policy_source``, ``evidence_timestamp``, ``details``). Duck-typing
        keeps the graph module free of a runtime dependency on the
        ``uiao.freshness`` package.

        Behavior per finding:
            * ``status == "fresh"`` → skipped (nothing to record).
            * otherwise → a new :class:`FindingNode` with
              ``drift_class="DRIFT-SEMANTIC"`` and Finding-vocabulary severity.
              If a NIST-style control can be inferred from ``ksi_id`` and a
              matching :class:`ControlNode` exists in the graph, a
              ``violated-by`` edge is added.

        Returns the number of Finding nodes added. Idempotent under repeat
        ingestion: finding IDs are deterministic from ``run_id + adapter_id``,
        so re-ingesting the same evaluator output does not duplicate nodes.
        """
        severity_map = {
            "P1": "High",
            "P2": "High",
            "P3": "Medium",
            "P4": "Low",
            "P5": "Low",
        }
        added = 0
        for f in findings:
            status = getattr(f, "status", None)
            if not status or status == "fresh":
                continue
            adapter_id = getattr(f, "adapter_id", "") or "unknown"
            run_id = getattr(f, "run_id", "") or "unknown"
            finding_id = f"drift-semantic:{run_id}:{adapter_id}"
            if finding_id in self._nodes:
                continue  # idempotent re-ingest

            control_id = self._infer_control_id(getattr(f, "ksi_id", None) or "")
            raw_severity = getattr(f, "severity", "")
            severity = severity_map.get(str(raw_severity).upper(), "Medium")

            self.add_finding(
                FindingNode(
                    id=finding_id,
                    severity=severity,
                    description=(
                        f"DRIFT-SEMANTIC for {adapter_id}: status={status}, "
                        f"age={getattr(f, 'age_hours', 'unknown')}h, "
                        f"window={getattr(f, 'window_hours', 'unknown')}h"
                    ),
                    control_id=control_id,
                    drift_class="DRIFT-SEMANTIC",
                    status="Open",
                    extra={
                        "run_id": run_id,
                        "adapter_id": adapter_id,
                        "semantic_status": status,
                        "severity_raw": raw_severity,
                        "age_hours": getattr(f, "age_hours", None),
                        "window_hours": getattr(f, "window_hours", None),
                        "evidence_timestamp": getattr(f, "evidence_timestamp", None),
                        "evaluated_at": getattr(f, "evaluated_at", None),
                        "policy_source": getattr(f, "policy_source", None),
                        "ksi_id": getattr(f, "ksi_id", None),
                        "details": getattr(f, "details", None) or {},
                    },
                )
            )
            added += 1
            if control_id and control_id in self._nodes:
                self.link_violated_by(control_id, finding_id)
        return added

    # ------------------------------------------------------------------
    # SAR integration helpers (UIAO_113 ↔ SAR generator)
    # ------------------------------------------------------------------

    def sar_props_for_evidence(self, control_id: str) -> Dict[str, Any]:
        """Return a flat props dict an OSCAL emitter can attach to an
        observation keyed on ``control_id``.

        Empty dict when the graph has no coverage for the control — SAR
        code can treat that as "no graph-derived augmentation available".
        """
        evs = self.evidence_for_control(control_id)
        if not evs:
            return {}
        # Scheduler-originated evidence carries run metadata in ``extra``.
        scheduler_evs = [e for e in evs if getattr(e, "extra", None)]
        target = scheduler_evs[0] if scheduler_evs else evs[0]
        extra = getattr(target, "extra", {}) or {}
        findings = self.findings_for_control(control_id)
        props: Dict[str, Any] = {
            "graph-evidence-id": target.id,
            "graph-evidence-hash": target.hash,
            "graph-evidence-source": target.source,
        }
        if extra.get("run_id"):
            props["graph-scheduler-run-id"] = extra["run_id"]
        if extra.get("adapter_id"):
            props["graph-adapter-id"] = extra["adapter_id"]
        if findings:
            props["graph-open-findings"] = str(len([f for f in findings if f.status == "Open"]))
            props["graph-top-severity"] = max(
                (f.severity for f in findings),
                key=lambda s: {"High": 3, "Medium": 2, "Low": 1}.get(s, 0),
            )
        return props

    @classmethod
    def from_evidence_bundle(cls, bundle):
        g = cls()
        for ev in getattr(bundle, "evidence", []):
            cid = getattr(ev, "control_id", "") or ""
            g.add_evidence(
                EvidenceNode(
                    id=ev.id,
                    source=getattr(ev, "source", ""),
                    control_id=cid,
                    verdict="pass"
                    if ev.evaluation.get("passed")
                    else "fail"
                    if ev.evaluation.get("failed")
                    else "inconclusive",
                    hash=ev.hash() if hasattr(ev, "hash") else "",
                )
            )
            if hasattr(ev, "provenance"):
                pv = ev.provenance
                g.add_provenance(
                    ProvenanceNode(
                        id=f"prov:{ev.id}", source=pv.source, timestamp=str(pv.timestamp), version=pv.version or ""
                    )
                )
                g.link_provenance_of(ev.id, f"prov:{ev.id}")
            if cid:
                if cid not in g._nodes:
                    g.add_control(ControlNode(id=cid))
                iid = f"ir:{cid}"
                if iid not in g._nodes:
                    g.add_ir_object(IRObjectNode(id=iid))
                    g.link_implements(cid, iid)
                g.link_validated_by(iid, ev.id)
        for ds in getattr(bundle, "drift_states", []):
            if not ds.drift_detected:
                continue
            fid = f"find:{ds.id}"
            g.add_finding(
                FindingNode(
                    id=fid,
                    severity="High" if ds.classification == "unauthorized" else "Medium",
                    control_id=ds.policy_ref,
                    drift_class=getattr(ds, "drift_class", "") or "",
                    status="Open",
                )
            )
            if ds.policy_ref in g._nodes:
                g.link_violated_by(ds.policy_ref, fid)
        return g
