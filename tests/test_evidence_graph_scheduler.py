"""Tests for UIAO_113 ↔ UIAO_100 scheduler-run ingestion and SAR augmentation.

Scope: ``EvidenceGraph.from_scheduler_run()`` + ``sar_props_for_evidence()``
+ the ``graph=`` pathway through ``build_sar()``. Existing graph-model
coverage lives in ``tests/test_evidence_graph.py``; this file covers the
new bridge between the orchestrator scheduler and the graph / SAR stack.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from uiao.evidence.graph import (
    ControlNode,
    EvidenceGraph,
    EvidenceNode,
    IRObjectNode,
    _normalize_severity,
)


# ---------------------------------------------------------------------------
# Fixtures — build a scheduler-run directory on disk
# ---------------------------------------------------------------------------


def _write_scheduler_run(
    tmp_path: Path,
    adapters: list[dict[str, Any]],
    run_id: str = "schedrun-20260423T120000Z-deadbeef",
) -> Path:
    """Write a synthetic scheduler run tree to ``tmp_path``.

    ``adapters`` is a list of dicts::

        {
          "id": "scubagear",
          "ksi_id": "ksi:AC-2",        # optional
          "drift_severity": "P1",      # optional — omit to skip drift.json
          "drift_details": {...},
          "drift_type": "schema",
        }
    """
    run_dir = tmp_path / run_id
    adapters_dir = run_dir / "adapters"
    adapters_dir.mkdir(parents=True)

    # manifest.json — scheduler-style metadata
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "schema_version": "1.0.0", "adapters_total": len(adapters)}),
        encoding="utf-8",
    )

    for spec in adapters:
        adapter_id = spec["id"]
        adapter_dir = adapters_dir / adapter_id
        adapter_dir.mkdir()
        evidence_payload = {
            "ksi_id": spec.get("ksi_id", f"ksi:{adapter_id}"),
            "source": adapter_id,
            "timestamp": "2026-04-23T12:00:00+00:00",
            "raw_data": {"probe": True},
            "normalized_data": {"probe": True},
            "provenance": {
                "adapter_id": adapter_id,
                "hash": spec.get("hash", "a" * 64),
                "version": spec.get("version", "1.0"),
            },
            "freshness_valid": True,
        }
        (adapter_dir / "evidence.json").write_text(json.dumps(evidence_payload, sort_keys=True), encoding="utf-8")

        if "drift_severity" in spec or "drift_details" in spec:
            drift_payload = {
                "drift_type": spec.get("drift_type", "schema"),
                "severity": spec.get("drift_severity", ""),
                "first_observed": "2026-04-23T12:00:00+00:00",
                "last_observed": "2026-04-23T12:00:00+00:00",
                "details": spec.get("drift_details", {"change": "probe"}),
                "remediation": None,
            }
            (adapter_dir / "drift.json").write_text(json.dumps(drift_payload, sort_keys=True), encoding="utf-8")
    return run_dir


# ---------------------------------------------------------------------------
# _normalize_severity — drift severity vocabulary bridge
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("P1", "High"),
        ("p2", "High"),
        ("critical", "High"),
        ("HIGH", "High"),
        ("P3", "Medium"),
        ("Warn", "Medium"),
        ("P5", "Low"),
        ("info", "Low"),
        ("bananas", "Medium"),  # unknown → Medium default
        ("", "Medium"),
        (None, "Medium"),
    ],
)
def test_normalize_severity(raw, expected):
    assert _normalize_severity(raw) == expected


# ---------------------------------------------------------------------------
# from_scheduler_run — structural
# ---------------------------------------------------------------------------


def test_from_scheduler_run_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        EvidenceGraph.from_scheduler_run(tmp_path / "nope")


def test_from_scheduler_run_empty_adapters_root_is_noop(tmp_path):
    run_dir = tmp_path / "empty-run"
    (run_dir / "adapters").mkdir(parents=True)
    g = EvidenceGraph.from_scheduler_run(run_dir)
    assert g.stats()["total_nodes"] == 0


def test_from_scheduler_run_builds_evidence_and_provenance_without_drift(tmp_path):
    run_dir = _write_scheduler_run(tmp_path, [{"id": "scubagear", "ksi_id": "ksi:AC-2"}])
    g = EvidenceGraph.from_scheduler_run(run_dir)
    counts = g.stats()["nodes_by_type"]
    # evidence + provenance + control + ir-object, no finding (drift absent)
    assert counts.get("evidence") == 1
    assert counts.get("provenance") == 1
    assert counts.get("control") == 1
    assert counts.get("ir-object") == 1
    assert counts.get("finding", 0) == 0
    # Evidence node carries scheduler metadata under extra.
    (ev,) = g.nodes_of_type("evidence")
    assert isinstance(ev, EvidenceNode)
    assert ev.extra["adapter_id"] == "scubagear"
    assert ev.extra["ksi_id"] == "ksi:AC-2"
    assert ev.control_id == "AC-2"


def test_from_scheduler_run_materializes_finding_for_drift(tmp_path):
    run_dir = _write_scheduler_run(
        tmp_path,
        [
            {"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"},
            {"id": "entra-id", "ksi_id": "ksi:IA-2", "drift_severity": "P3"},
        ],
    )
    g = EvidenceGraph.from_scheduler_run(run_dir)
    findings = g.nodes_of_type("finding")
    assert len(findings) == 2
    severities = sorted(f.severity for f in findings)
    assert severities == ["High", "Medium"]
    # High-severity finding must link to AC-2 via violated-by.
    ac2_findings = g.findings_for_control("AC-2")
    assert len(ac2_findings) == 1
    assert ac2_findings[0].severity == "High"


def test_from_scheduler_run_skips_empty_drift(tmp_path):
    """Adapters that emit drift.json with no severity + no details → no Finding."""
    run_dir = _write_scheduler_run(
        tmp_path,
        [
            {
                "id": "quiet-adapter",
                "ksi_id": "ksi:AC-2",
                "drift_severity": "",
                "drift_details": {},
            }
        ],
    )
    g = EvidenceGraph.from_scheduler_run(run_dir)
    assert g.stats()["nodes_by_type"].get("finding", 0) == 0


def test_from_scheduler_run_handles_missing_evidence(tmp_path):
    """Adapter dir with only drift.json (no evidence.json) is skipped silently."""
    run_dir = tmp_path / "run"
    (run_dir / "adapters" / "broken").mkdir(parents=True)
    (run_dir / "adapters" / "broken" / "drift.json").write_text(
        json.dumps({"drift_type": "schema", "severity": "P1"}),
        encoding="utf-8",
    )
    g = EvidenceGraph.from_scheduler_run(run_dir)
    assert g.stats()["total_nodes"] == 0


def test_from_scheduler_run_without_manifest_falls_back_to_dirname(tmp_path):
    run_dir = _write_scheduler_run(
        tmp_path,
        [{"id": "scubagear", "ksi_id": "ksi:AC-2"}],
        run_id="custom-run-dir",
    )
    (run_dir / "manifest.json").unlink()
    g = EvidenceGraph.from_scheduler_run(run_dir)
    ev = g.nodes_of_type("evidence")[0]
    assert ev.extra["run_id"] == "custom-run-dir"


def test_from_scheduler_run_ksi_without_control_family_skips_control(tmp_path):
    """Non-NIST-style KSI → no ControlNode hop; evidence still lands."""
    run_dir = _write_scheduler_run(tmp_path, [{"id": "terraform", "ksi_id": "ksi:free-form-subject"}])
    g = EvidenceGraph.from_scheduler_run(run_dir)
    counts = g.stats()["nodes_by_type"]
    assert counts.get("evidence") == 1
    assert counts.get("control", 0) == 0
    assert counts.get("ir-object", 0) == 0


def test_from_scheduler_run_multi_adapter_stats_deterministic(tmp_path):
    run_dir = _write_scheduler_run(
        tmp_path,
        [
            {"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"},
            {"id": "entra-id", "ksi_id": "ksi:IA-2"},
            {"id": "intune", "ksi_id": "ksi:SI-4", "drift_severity": "P5"},
        ],
    )
    g = EvidenceGraph.from_scheduler_run(run_dir)
    s = g.stats()
    assert s["nodes_by_type"]["evidence"] == 3
    assert s["nodes_by_type"]["provenance"] == 3
    assert s["nodes_by_type"]["control"] == 3
    assert s["nodes_by_type"]["finding"] == 2  # intune (P5→Low) + scubagear (P1→High)
    assert s["edges_by_type"]["implements"] == 3
    assert s["edges_by_type"]["validated-by"] == 3
    assert s["edges_by_type"]["provenance-of"] == 3
    assert s["edges_by_type"]["violated-by"] == 2


# ---------------------------------------------------------------------------
# sar_props_for_evidence — graph's SAR wire
# ---------------------------------------------------------------------------


def test_sar_props_for_evidence_empty_when_control_missing():
    g = EvidenceGraph()
    assert g.sar_props_for_evidence("AC-2") == {}


def test_sar_props_for_evidence_surfaces_scheduler_metadata(tmp_path):
    run_dir = _write_scheduler_run(
        tmp_path,
        [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
    )
    g = EvidenceGraph.from_scheduler_run(run_dir)
    props = g.sar_props_for_evidence("AC-2")
    assert props["graph-adapter-id"] == "scubagear"
    assert props["graph-scheduler-run-id"] == "schedrun-20260423T120000Z-deadbeef"
    assert props["graph-evidence-source"] == "scubagear"
    assert props["graph-top-severity"] == "High"
    assert props["graph-open-findings"] == "1"


def test_sar_props_for_evidence_no_drift_omits_finding_props(tmp_path):
    run_dir = _write_scheduler_run(tmp_path, [{"id": "scubagear", "ksi_id": "ksi:AC-2"}])
    g = EvidenceGraph.from_scheduler_run(run_dir)
    props = g.sar_props_for_evidence("AC-2")
    assert "graph-top-severity" not in props
    assert "graph-open-findings" not in props
    assert props["graph-adapter-id"] == "scubagear"


def test_sar_props_for_evidence_works_with_hand_built_graph():
    """The SAR hook does not depend on scheduler-run ingestion."""
    g = EvidenceGraph()
    g.add_control(ControlNode(id="AC-2"))
    g.add_ir_object(IRObjectNode(id="ir:AC-2"))
    g.add_evidence(
        EvidenceNode(
            id="EV-999",
            source="manual",
            control_id="AC-2",
            hash="abc",
            verdict="pass",
        )
    )
    g.link_implements("AC-2", "ir:AC-2")
    g.link_validated_by("ir:AC-2", "EV-999")
    props = g.sar_props_for_evidence("AC-2")
    assert props["graph-evidence-id"] == "EV-999"
    assert props["graph-evidence-source"] == "manual"
    # No scheduler metadata → no run-id / adapter-id keys.
    assert "graph-scheduler-run-id" not in props
    assert "graph-adapter-id" not in props


# ---------------------------------------------------------------------------
# SAR integration — augments observation props without changing core output
# ---------------------------------------------------------------------------


def _minimal_evidence_bundle():
    """Build a tiny EvidenceBundle usable by build_sar without SCuBA fixtures."""
    from uiao.evidence.bundle import EvidenceBundle
    from uiao.ir.models.core import Evidence, ProvenanceRecord

    provenance = ProvenanceRecord(
        source="test",
        timestamp="2026-04-23T12:00:00+00:00",
        version="1.0",
        content_hash="probe",
        actor="test",
    )
    evidence = Evidence(
        id="EV-TEST-1",
        source="test",
        control_id="AC-2",
        timestamp="2026-04-23T12:00:00+00:00",
        data={"ksi_id": "ksi:AC-2", "status": "PASS", "details": "ok"},
        evaluation={"passed": True, "canonical_hash": "deadbeef" * 2},
        provenance=provenance,
    )
    return EvidenceBundle(
        run_id="bundle-run",
        provenance=provenance,
        evidence=[evidence],
        drift_states=[],
        controls=[],
        policies=[],
        unmapped_ksi_ids=[],
    )


def test_build_sar_without_graph_matches_legacy_shape(tmp_path):
    """Regression: graph=None must leave observation props exactly as before."""
    from uiao.generators.sar import build_sar

    bundle = _minimal_evidence_bundle()
    sar = build_sar(bundle)
    obs = sar["assessment-results"]["results"][0]["observations"][0]
    prop_names = {p["name"] for p in obs["subjects"][0]["props"]}
    assert prop_names == {"ksi-id", "status", "evidence-hash"}


def test_build_sar_with_graph_augments_observation_props(tmp_path):
    from uiao.generators.sar import build_sar

    run_dir = _write_scheduler_run(
        tmp_path,
        [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
    )
    graph = EvidenceGraph.from_scheduler_run(run_dir)
    bundle = _minimal_evidence_bundle()
    sar = build_sar(bundle, graph=graph)
    obs = sar["assessment-results"]["results"][0]["observations"][0]
    prop_names = {p["name"] for p in obs["subjects"][0]["props"]}
    # Legacy props still present.
    assert {"ksi-id", "status", "evidence-hash"}.issubset(prop_names)
    # Graph-derived props attached.
    assert "graph-evidence-id" in prop_names
    assert "graph-scheduler-run-id" in prop_names
    assert "graph-top-severity" in prop_names
    top = next(p for p in obs["subjects"][0]["props"] if p["name"] == "graph-top-severity")
    assert top["value"] == "High"
    assert top["ns"] == "https://uiao.gov/ns/oscal/graph"


# ---------------------------------------------------------------------------
# End-to-end: scheduler run directory → graph → augmented SAR
# ---------------------------------------------------------------------------


def test_e2e_scheduler_run_to_graph_to_sar(tmp_path):
    """Closes the UIAO_100 → UIAO_113 → OSCAL SAR loop."""
    from uiao.generators.sar import build_sar

    run_dir = _write_scheduler_run(
        tmp_path,
        [
            {"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"},
            {"id": "entra-id", "ksi_id": "ksi:IA-2"},
        ],
    )
    graph = EvidenceGraph.from_scheduler_run(run_dir)

    # Graph shape is as advertised.
    assert graph.stats()["nodes_by_type"]["evidence"] == 2
    assert len(graph.findings_for_control("AC-2")) == 1
    assert len(graph.findings_for_control("IA-2")) == 0

    # SAR consumes the graph; every observation gets a graph-derived link.
    bundle = _minimal_evidence_bundle()
    sar = build_sar(bundle, graph=graph)
    obs_props = {
        p["name"]: p["value"]
        for p in sar["assessment-results"]["results"][0]["observations"][0]["subjects"][0]["props"]
    }
    assert obs_props["graph-adapter-id"] == "scubagear"
    assert obs_props["graph-scheduler-run-id"] == "schedrun-20260423T120000Z-deadbeef"
    assert obs_props["graph-top-severity"] == "High"
