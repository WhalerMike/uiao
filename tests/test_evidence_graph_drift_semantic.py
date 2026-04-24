"""Tests for EvidenceGraph.ingest_drift_semantic (UIAO_016 ↔ UIAO_113 bridge).

Folds DRIFT-SEMANTIC FreshnessFinding output from the §1.1 evaluator into
the §1.4 graph as first-class FindingNodes. This completes the compose
loop: UIAO_100 scheduler → §1.1 freshness eval → §1.4 graph → SAR.

Scope:
    - ``ingest_drift_semantic`` skips fresh findings.
    - Non-fresh findings become FindingNode with ``drift_class`` =
      ``"DRIFT-SEMANTIC"``.
    - Severity map P1/P2 → High, P3 → Medium, P4/P5 → Low.
    - Control-to-Finding violated-by edge is added when a NIST-style
      ksi_id resolves to a ControlNode already in the graph.
    - Idempotent under re-ingestion (finding IDs deterministic from
      run_id + adapter_id).
    - Duck-typed: works with any object exposing the FreshnessFinding
      attribute surface, not just the concrete dataclass.
    - End-to-end: scheduler run → freshness eval → graph ingestion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from uiao.evidence.graph import ControlNode, EvidenceGraph
from uiao.freshness.drift_semantic import (
    DRIFT_TYPE,
    FreshnessFinding,
    evaluate_scheduler_run,
)

_NOW = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _finding(
    *,
    adapter_id: str = "entra-id",
    status: str = "stale",
    severity: str = "P2",
    ksi_id: str | None = "ksi:AC-2",
    run_id: str = "schedrun-test",
    age_hours: float = 48.0,
    window_hours: int = 24,
) -> FreshnessFinding:
    return FreshnessFinding(
        adapter_id=adapter_id,
        run_id=run_id,
        drift_type=DRIFT_TYPE,
        severity=severity,
        age_hours=age_hours,
        window_hours=window_hours,
        status=status,
        evidence_timestamp="2026-04-22T12:00:00Z",
        evaluated_at=_NOW.isoformat(),
        policy_source="registry",
        ksi_id=ksi_id,
    )


# ---------------------------------------------------------------------------
# Basic ingest semantics
# ---------------------------------------------------------------------------


def test_fresh_findings_are_skipped():
    g = EvidenceGraph()
    added = g.ingest_drift_semantic([_finding(status="fresh", severity="P5")])
    assert added == 0
    assert g.stats()["total_nodes"] == 0


def test_stale_finding_creates_finding_node_with_drift_class():
    g = EvidenceGraph()
    added = g.ingest_drift_semantic([_finding(status="stale", severity="P2")])
    assert added == 1
    findings = g.nodes_of_type("finding")
    assert len(findings) == 1
    fn = findings[0]
    assert fn.drift_class == "DRIFT-SEMANTIC"
    assert fn.severity == "High"  # P2 → High
    assert fn.status == "Open"
    assert fn.control_id == "AC-2"
    assert fn.extra["semantic_status"] == "stale"
    assert fn.extra["adapter_id"] == "entra-id"


def test_finding_id_is_deterministic_and_ingestion_is_idempotent():
    g = EvidenceGraph()
    f = _finding(run_id="schedrun-xyz", adapter_id="entra-id")
    first = g.ingest_drift_semantic([f])
    second = g.ingest_drift_semantic([f])
    assert first == 1
    assert second == 0
    assert g.stats()["nodes_by_type"]["finding"] == 1
    assert g.get("drift-semantic:schedrun-xyz:entra-id") is not None


def test_control_edge_is_added_when_control_node_present():
    g = EvidenceGraph()
    g.add_control(ControlNode(id="AC-2"))
    g.ingest_drift_semantic([_finding(status="stale", ksi_id="ksi:AC-2")])
    ac2_findings = g.findings_for_control("AC-2")
    assert len(ac2_findings) == 1
    assert ac2_findings[0].drift_class == "DRIFT-SEMANTIC"


def test_control_edge_is_skipped_when_control_absent():
    """Graph lacks the Control node → finding lands but no violated-by edge."""
    g = EvidenceGraph()
    added = g.ingest_drift_semantic([_finding(status="stale", ksi_id="ksi:AC-2")])
    assert added == 1
    # Finding node exists, but the Control wasn't in the graph so no edge.
    assert g.findings_for_control("AC-2") == []
    # And the finding still carries the inferred control_id on the node itself
    # so callers that add the Control later can still correlate via control_id.
    assert g.nodes_of_type("finding")[0].control_id == "AC-2"


def test_non_nist_ksi_records_finding_without_control():
    g = EvidenceGraph()
    added = g.ingest_drift_semantic([_finding(status="stale", ksi_id="ksi:free-form-topic")])
    assert added == 1
    fn = g.nodes_of_type("finding")[0]
    assert fn.control_id == ""


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------


def test_severity_map_p1_and_p2_map_to_high():
    g = EvidenceGraph()
    g.ingest_drift_semantic(
        [
            _finding(status="missing-timestamp", severity="P1", run_id="r", adapter_id="a1"),
            _finding(status="stale", severity="P2", run_id="r", adapter_id="a2"),
        ]
    )
    sevs = {fn.severity for fn in g.nodes_of_type("finding")}
    assert sevs == {"High"}


def test_severity_map_p3_maps_to_medium():
    g = EvidenceGraph()
    g.ingest_drift_semantic([_finding(status="stale-soon", severity="P3", adapter_id="a1")])
    assert g.nodes_of_type("finding")[0].severity == "Medium"


def test_severity_map_unknown_falls_back_to_medium():
    g = EvidenceGraph()
    g.ingest_drift_semantic([_finding(status="stale", severity="BOGUS", adapter_id="a1")])
    assert g.nodes_of_type("finding")[0].severity == "Medium"


# ---------------------------------------------------------------------------
# Duck-typing: accepts any object with the right attribute surface
# ---------------------------------------------------------------------------


@dataclass
class _DuckFinding:
    adapter_id: str
    run_id: str
    drift_type: str
    severity: str
    age_hours: float
    window_hours: int
    status: str
    evidence_timestamp: str | None
    evaluated_at: str
    policy_source: str
    ksi_id: str | None
    details: dict[str, Any] | None = None


def test_ingest_accepts_duck_typed_objects():
    """Graph does not import uiao.freshness at module load time."""
    g = EvidenceGraph()
    duck = _DuckFinding(
        adapter_id="duck",
        run_id="r",
        drift_type=DRIFT_TYPE,
        severity="P2",
        age_hours=100.0,
        window_hours=24,
        status="stale",
        evidence_timestamp="2026-04-22T12:00:00Z",
        evaluated_at=_NOW.isoformat(),
        policy_source="registry",
        ksi_id="ksi:IA-2",
    )
    added = g.ingest_drift_semantic([duck])
    assert added == 1
    fn = g.nodes_of_type("finding")[0]
    assert fn.severity == "High"
    assert fn.extra["adapter_id"] == "duck"


# ---------------------------------------------------------------------------
# End-to-end: scheduler run directory → freshness eval → graph
# ---------------------------------------------------------------------------


def _write_scheduler_run(
    root: Path,
    adapters: list[dict[str, Any]],
    *,
    run_id: str = "schedrun-20260424T120000Z-beef",
) -> Path:
    run_dir = root / run_id
    adapters_dir = run_dir / "adapters"
    adapters_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    for spec in adapters:
        adapter_id = spec["id"]
        d = adapters_dir / adapter_id
        d.mkdir()
        (d / "evidence.json").write_text(
            json.dumps(
                {
                    "ksi_id": spec["ksi_id"],
                    "source": adapter_id,
                    "timestamp": spec["timestamp"],
                    "provenance": {"adapter_id": adapter_id, "hash": "a" * 64},
                }
            ),
            encoding="utf-8",
        )
    return run_dir


def _write_registry(path: Path, adapters: list[dict[str, Any]]) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema-version": "1.0.0",
                "registry-class": "modernization",
                "updated": "2026-04-24",
                "adapters": adapters,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_e2e_scheduler_run_to_graph_via_drift_semantic(tmp_path):
    """Compose §1.1 + §1.4: real scheduler-run-shaped inputs → graph."""
    reg = _write_registry(
        tmp_path / "registry.yaml",
        [
            {"id": "entra-id", "status": "active", "freshness-window-hours": 24},
            {"id": "scubagear", "status": "active", "freshness-window-hours": 168},
        ],
    )
    run_dir = _write_scheduler_run(
        tmp_path,
        [
            # entra-id 48h old vs 24h window → stale (P2) → High
            {
                "id": "entra-id",
                "ksi_id": "ksi:AC-2",
                "timestamp": (_NOW - timedelta(hours=48)).isoformat(),
            },
            # scubagear 48h old vs 168h window → fresh (skipped)
            {
                "id": "scubagear",
                "ksi_id": "ksi:SI-4",
                "timestamp": (_NOW - timedelta(hours=48)).isoformat(),
            },
        ],
    )
    findings = evaluate_scheduler_run(run_dir, registries=[reg], now=_NOW)

    g = EvidenceGraph()
    # Pre-populate the control so the violated-by edge can form.
    g.add_control(ControlNode(id="AC-2"))
    added = g.ingest_drift_semantic(findings)
    assert added == 1  # only the stale entra-id finding; scubagear is fresh

    ac2_findings = g.findings_for_control("AC-2")
    assert len(ac2_findings) == 1
    fn = ac2_findings[0]
    assert fn.drift_class == "DRIFT-SEMANTIC"
    assert fn.severity == "High"
    assert fn.extra["adapter_id"] == "entra-id"
    assert fn.extra["run_id"] == "schedrun-20260424T120000Z-beef"
    assert fn.extra["semantic_status"] == "stale"
    assert fn.extra["window_hours"] == 24
