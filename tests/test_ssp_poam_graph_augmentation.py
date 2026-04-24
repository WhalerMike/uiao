"""Tests for UIAO_113 graph augmentation of SSP and POA&M generators (§2.1/§2.2).

Covers the new ``graph=`` pathway through :func:`build_ssp_skeleton`,
:func:`build_ssp`, :func:`build_poam`, and :func:`build_poam_export`, plus
the new :func:`EvidenceGraph.poam_props_for_control` helper.

The SAR side of the same pattern lives in
``tests/test_evidence_graph_scheduler.py``; this file is its sibling for
the SSP / POA&M generators.
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
    FindingNode,
    IRObjectNode,
    POAMEntryNode,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic scheduler-run on disk (mirrors test_evidence_graph_scheduler)
# ---------------------------------------------------------------------------


def _write_scheduler_run(
    tmp_path: Path,
    adapters: list[dict[str, Any]],
    run_id: str = "schedrun-20260424T120000Z-cafef00d",
) -> Path:
    run_dir = tmp_path / run_id
    adapters_dir = run_dir / "adapters"
    adapters_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "schema_version": "1.0.0", "adapters_total": len(adapters)}),
        encoding="utf-8",
    )
    for spec in adapters:
        adapter_id = spec["id"]
        adir = adapters_dir / adapter_id
        adir.mkdir()
        evidence_payload = {
            "ksi_id": spec.get("ksi_id", f"ksi:{adapter_id}"),
            "source": adapter_id,
            "timestamp": "2026-04-24T12:00:00+00:00",
            "raw_data": {"probe": True},
            "normalized_data": {"probe": True},
            "provenance": {
                "adapter_id": adapter_id,
                "hash": "a" * 64,
                "version": "1.0",
            },
            "freshness_valid": True,
        }
        (adir / "evidence.json").write_text(json.dumps(evidence_payload, sort_keys=True), encoding="utf-8")
        if "drift_severity" in spec or "drift_details" in spec:
            (adir / "drift.json").write_text(
                json.dumps(
                    {
                        "drift_type": spec.get("drift_type", "schema"),
                        "severity": spec.get("drift_severity", ""),
                        "first_observed": "2026-04-24T12:00:00+00:00",
                        "last_observed": "2026-04-24T12:00:00+00:00",
                        "details": spec.get("drift_details", {"change": "probe"}),
                        "remediation": None,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
    return run_dir


def _ssp_context_with_ac2() -> dict[str, Any]:
    """Minimal SSP context wired so AC-2 lands in implemented-requirements."""
    return {
        "leadership_briefing": {"title": "Test SSP", "overview": "test"},
        "control_planes": [],
        "unified_compliance_matrix": [
            {
                "category": "Access Control",
                "pillar": "identity",
                "cisa_maturity": "Advanced",
                "nist_controls": ["AC-2"],
                "impact_statement": "Account management",
            }
        ],
        "ksi_mappings": [],
    }


# ---------------------------------------------------------------------------
# poam_props_for_control — graph helper
# ---------------------------------------------------------------------------


class TestPoamPropsForControl:
    def test_empty_when_control_missing(self):
        g = EvidenceGraph()
        assert g.poam_props_for_control("AC-2") == {}

    def test_finding_only_returns_finding_props(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_finding(
            FindingNode(id="F-1", severity="High", control_id="AC-2", drift_class="DRIFT-SEMANTIC", status="Open")
        )
        g.link_violated_by("AC-2", "F-1")
        props = g.poam_props_for_control("AC-2")
        assert props["graph-finding-id"] == "F-1"
        assert props["graph-finding-severity"] == "High"
        assert props["graph-finding-status"] == "Open"
        assert props["graph-finding-drift-class"] == "DRIFT-SEMANTIC"
        # No evidence attached → no evidence-derived keys.
        assert "graph-evidence-id" not in props
        assert "graph-poam-entry-id" not in props

    def test_picks_highest_severity_finding(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_finding(FindingNode(id="F-low", severity="Low", control_id="AC-2"))
        g.add_finding(FindingNode(id="F-high", severity="High", control_id="AC-2"))
        g.add_finding(FindingNode(id="F-medium", severity="Medium", control_id="AC-2"))
        for fid in ("F-low", "F-high", "F-medium"):
            g.link_violated_by("AC-2", fid)
        props = g.poam_props_for_control("AC-2")
        assert props["graph-finding-id"] == "F-high"
        assert props["graph-finding-severity"] == "High"

    def test_surfaces_poam_entry_link(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_finding(FindingNode(id="F-1", severity="High", control_id="AC-2"))
        g.add_poam_entry(POAMEntryNode(id="POAM-001", status="In-Progress"))
        g.link_violated_by("AC-2", "F-1")
        g.link_remediated_by("F-1", "POAM-001")
        props = g.poam_props_for_control("AC-2")
        assert props["graph-poam-entry-id"] == "POAM-001"
        assert props["graph-poam-status"] == "In-Progress"

    def test_surfaces_scheduler_metadata_when_evidence_carries_extra(self, tmp_path):
        run_dir = _write_scheduler_run(
            tmp_path,
            [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
        )
        g = EvidenceGraph.from_scheduler_run(run_dir)
        props = g.poam_props_for_control("AC-2")
        assert props["graph-finding-severity"] == "High"
        assert props["graph-adapter-id"] == "scubagear"
        assert "schedrun-" in props["graph-scheduler-run-id"]
        assert props["graph-evidence-id"]

    def test_evidence_only_returns_witness_props(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_ir_object(IRObjectNode(id="ir:AC-2"))
        g.add_evidence(EvidenceNode(id="EV-1", source="manual", control_id="AC-2", hash="abc"))
        g.link_implements("AC-2", "ir:AC-2")
        g.link_validated_by("ir:AC-2", "EV-1")
        props = g.poam_props_for_control("AC-2")
        assert props["graph-evidence-id"] == "EV-1"
        # No findings → no finding keys.
        assert "graph-finding-id" not in props


# ---------------------------------------------------------------------------
# build_ssp_skeleton — graph augmentation
# ---------------------------------------------------------------------------


class TestSspGraphAugmentation:
    def test_without_graph_no_graph_props(self, tmp_path):
        from uiao.generators.ssp import build_ssp_skeleton

        ssp = build_ssp_skeleton(_ssp_context_with_ac2(), data_dir=tmp_path)
        reqs = ssp["control-implementation"]["implemented-requirements"]
        ac2 = next(r for r in reqs if r["control-id"] == "AC-2")
        names = {p["name"] for p in ac2.get("props", [])}
        assert not any(n.startswith("graph-") for n in names)

    def test_with_graph_attaches_provenance_props(self, tmp_path):
        from uiao.generators.ssp import build_ssp_skeleton

        run_dir = _write_scheduler_run(
            tmp_path,
            [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
        )
        graph = EvidenceGraph.from_scheduler_run(run_dir)
        ssp = build_ssp_skeleton(_ssp_context_with_ac2(), data_dir=tmp_path, graph=graph)
        reqs = ssp["control-implementation"]["implemented-requirements"]
        ac2 = next(r for r in reqs if r["control-id"] == "AC-2")
        graph_props = {p["name"]: p for p in ac2.get("props", []) if p["name"].startswith("graph-")}
        assert "graph-evidence-id" in graph_props
        assert "graph-adapter-id" in graph_props
        assert "graph-scheduler-run-id" in graph_props
        assert "graph-top-severity" in graph_props
        assert graph_props["graph-top-severity"]["value"] == "High"
        assert graph_props["graph-top-severity"]["ns"] == "https://uiao.gov/ns/oscal/graph"

    def test_graph_with_no_coverage_leaves_requirement_unchanged(self, tmp_path):
        from uiao.generators.ssp import build_ssp_skeleton

        # Graph for an unrelated control; AC-2 not present.
        graph = EvidenceGraph()
        graph.add_control(ControlNode(id="IA-2"))
        ssp = build_ssp_skeleton(_ssp_context_with_ac2(), data_dir=tmp_path, graph=graph)
        ac2 = next(r for r in ssp["control-implementation"]["implemented-requirements"] if r["control-id"] == "AC-2")
        names = {p["name"] for p in ac2.get("props", [])}
        assert not any(n.startswith("graph-") for n in names)

    def test_existing_props_are_preserved(self, tmp_path):
        from uiao.generators.ssp import build_ssp_skeleton

        run_dir = _write_scheduler_run(
            tmp_path,
            [{"id": "scubagear", "ksi_id": "ksi:AC-2"}],
        )
        graph = EvidenceGraph.from_scheduler_run(run_dir)
        ctx = _ssp_context_with_ac2()
        ctx["ksi_mappings"] = [{"ksi_id": "KSI.IDA.06", "control_ids": ["AC-2"], "evidence_source": "scuba"}]
        ssp = build_ssp_skeleton(ctx, data_dir=tmp_path, graph=graph)
        ac2 = next(r for r in ssp["control-implementation"]["implemented-requirements"] if r["control-id"] == "AC-2")
        names = {p["name"] for p in ac2.get("props", [])}
        # Pre-existing ksi-id prop not clobbered.
        assert "ksi-id" in names
        # Graph props added alongside.
        assert "graph-evidence-id" in names

    def test_build_ssp_writes_graph_props_to_disk(self, tmp_path):
        from uiao.generators.ssp import build_ssp

        run_dir = _write_scheduler_run(
            tmp_path,
            [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
        )
        graph = EvidenceGraph.from_scheduler_run(run_dir)
        out = tmp_path / "ssp.json"
        build_ssp(
            canon_path=tmp_path / "nonexistent.yaml",
            data_dir=tmp_path,
            output=out,
            graph=graph,
        )
        # build_ssp uses load_context which requires real files; the missing
        # canon path falls back to an empty context, so AC-2 won't appear.
        # Just verify the kwarg threads through and the file is valid OSCAL.
        with out.open() as fh:
            data = json.load(fh)
        assert "system-security-plan" in data


# ---------------------------------------------------------------------------
# build_poam — graph augmentation
# ---------------------------------------------------------------------------


def _poam_context_with_ac2_gap() -> dict[str, Any]:
    """Context that produces exactly one gap touching AC-2 via low maturity."""
    return {
        "unified_compliance_matrix": [
            {
                "category": "Access Control",
                "cisa_maturity": "Initial",
                "nist_controls": ["AC-2"],
            }
        ],
    }


class TestPoamGraphAugmentation:
    def test_without_graph_no_graph_props(self):
        from uiao.generators.poam import build_poam

        poam = build_poam(_poam_context_with_ac2_gap())
        assert len(poam["poam-items"]) == 1
        item = poam["poam-items"][0]
        names = {p["name"] for p in item["props"]}
        assert not any(n.startswith("graph-") for n in names)

    def test_with_graph_attaches_finding_and_provenance_props(self, tmp_path):
        from uiao.generators.poam import build_poam

        run_dir = _write_scheduler_run(
            tmp_path,
            [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
        )
        graph = EvidenceGraph.from_scheduler_run(run_dir)
        poam = build_poam(_poam_context_with_ac2_gap(), graph=graph)
        item = poam["poam-items"][0]
        graph_props = {p["name"]: p for p in item["props"] if p["name"].startswith("graph-")}
        assert "graph-finding-id" in graph_props
        assert graph_props["graph-finding-severity"]["value"] == "High"
        assert graph_props["graph-finding-status"]["value"] == "Open"
        assert "graph-adapter-id" in graph_props
        assert graph_props["graph-adapter-id"]["value"] == "scubagear"
        assert all(p["ns"] == "https://uiao.gov/ns/oscal/graph" for p in graph_props.values())

    def test_with_graph_surfaces_linked_poam_entry(self):
        from uiao.generators.poam import build_poam

        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_finding(FindingNode(id="F-1", severity="High", control_id="AC-2"))
        g.add_poam_entry(POAMEntryNode(id="POAM-AC-2", status="In-Progress"))
        g.link_violated_by("AC-2", "F-1")
        g.link_remediated_by("F-1", "POAM-AC-2")
        poam = build_poam(_poam_context_with_ac2_gap(), graph=g)
        item = poam["poam-items"][0]
        graph_props = {p["name"]: p["value"] for p in item["props"] if p["name"].startswith("graph-")}
        assert graph_props["graph-poam-entry-id"] == "POAM-AC-2"
        assert graph_props["graph-poam-status"] == "In-Progress"

    def test_graph_with_no_coverage_does_not_pollute_props(self):
        from uiao.generators.poam import build_poam

        g = EvidenceGraph()
        g.add_control(ControlNode(id="IA-2"))  # different control
        poam = build_poam(_poam_context_with_ac2_gap(), graph=g)
        item = poam["poam-items"][0]
        names = {p["name"] for p in item["props"]}
        assert not any(n.startswith("graph-") for n in names)

    def test_build_poam_export_threads_graph(self, tmp_path):
        from uiao.generators.poam import build_poam_export

        # No real canon ⇒ empty context ⇒ no detected gaps. We just verify
        # the kwarg is accepted and the file is written.
        graph = EvidenceGraph()
        out = build_poam_export(
            canon_path=tmp_path / "nonexistent.yaml",
            data_dir=tmp_path,
            output_dir=tmp_path / "out",
            graph=graph,
        )
        assert out.exists()
        with out.open() as fh:
            data = json.load(fh)
        assert "plan-of-action-and-milestones" in data


# ---------------------------------------------------------------------------
# End-to-end: scheduler run → graph → SSP + POA&M both augmented
# ---------------------------------------------------------------------------


def test_e2e_scheduler_run_to_graph_to_ssp_and_poam(tmp_path):
    """One graph, two OSCAL artifacts — both pick up the same provenance."""
    from uiao.generators.poam import build_poam
    from uiao.generators.ssp import build_ssp_skeleton

    run_dir = _write_scheduler_run(
        tmp_path,
        [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
    )
    graph = EvidenceGraph.from_scheduler_run(run_dir)

    ssp = build_ssp_skeleton(_ssp_context_with_ac2(), data_dir=tmp_path, graph=graph)
    poam = build_poam(_poam_context_with_ac2_gap(), graph=graph)

    ac2_req = next(r for r in ssp["control-implementation"]["implemented-requirements"] if r["control-id"] == "AC-2")
    ssp_run = next(p["value"] for p in ac2_req["props"] if p["name"] == "graph-scheduler-run-id")
    poam_run = next(p["value"] for p in poam["poam-items"][0]["props"] if p["name"] == "graph-scheduler-run-id")
    # Same scheduler run id appears in both artifacts — the graph is the
    # single source of provenance truth across the OSCAL surface.
    assert ssp_run == poam_run
    assert ssp_run.startswith("schedrun-")


# ---------------------------------------------------------------------------
# Backwards compatibility — graph kwarg is opt-in and defaults to None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(
            lambda tmp_path: __import__("uiao.generators.ssp", fromlist=["build_ssp_skeleton"]).build_ssp_skeleton(
                _ssp_context_with_ac2(), data_dir=tmp_path
            ),
            id="ssp_skeleton",
        ),
        pytest.param(
            lambda tmp_path: __import__("uiao.generators.poam", fromlist=["build_poam"]).build_poam(
                _poam_context_with_ac2_gap()
            ),
            id="poam",
        ),
    ],
)
def test_legacy_calls_without_graph_still_work(tmp_path, factory):
    """Regression: callers who don't know about the graph kwarg are unaffected."""
    out = factory(tmp_path)
    assert isinstance(out, dict)
