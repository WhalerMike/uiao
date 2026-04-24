"""Tests for UIAO_113 component-definition graph augmentation + cross-emitter
OSCAL back-matter graph link resources.

Closes the two remaining Phase 2 follow-ups tracked in roadmap §1.4:

1. ``build_component_definition`` / ``build_oscal`` ``graph=`` pathway.
2. First-class ``back-matter.resources[]`` graph link resources surfaced
   from SAR, SSP, POA&M, and component-definition emitters with
   matching ``links: [{rel: "graph-evidence", href: "#<uuid>"}]`` on
   each per-control item, so OSCAL consumers can navigate from a
   control implementation back to the graph trace by UUID.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from uiao.evidence.graph import (
    ControlNode,
    EvidenceGraph,
    EvidenceNode,
    FindingNode,
    IRObjectNode,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_scheduler_run(
    tmp_path: Path,
    adapters: list[dict[str, Any]],
    run_id: str = "schedrun-20260424T130000Z-deadbeef",
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
            "timestamp": "2026-04-24T13:00:00+00:00",
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
        if "drift_severity" in spec:
            (adir / "drift.json").write_text(
                json.dumps(
                    {
                        "drift_type": "schema",
                        "severity": spec["drift_severity"],
                        "first_observed": "2026-04-24T13:00:00+00:00",
                        "last_observed": "2026-04-24T13:00:00+00:00",
                        "details": {"change": "probe"},
                        "remediation": None,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
    return run_dir


def _component_def_context() -> dict[str, Any]:
    """Minimal context that lands AC-2 in a control-implementation."""
    return {
        "leadership_briefing": {"title": "UIAO Component Test"},
        "control_planes": [
            {
                "id": "identity",
                "name": "Identity Plane",
                "description": "Identity plane",
                "components": [],
            }
        ],
        "unified_compliance_matrix": [
            {
                "category": "Access Control",
                "pillar": "identity",
                "cisa_maturity": "Advanced",
                "nist_controls": ["AC-2"],
                "impact_statement": "Account management",
            }
        ],
        "fedramp_20x_config": {"core_mappings": []},
    }


# ---------------------------------------------------------------------------
# resource_uuid_for_control — deterministic across emitters
# ---------------------------------------------------------------------------


class TestResourceUuid:
    def test_deterministic_per_control(self):
        a = EvidenceGraph.resource_uuid_for_control("AC-2")
        b = EvidenceGraph.resource_uuid_for_control("AC-2")
        assert a == b

    def test_distinct_for_distinct_controls(self):
        a = EvidenceGraph.resource_uuid_for_control("AC-2")
        b = EvidenceGraph.resource_uuid_for_control("IA-2")
        assert a != b

    def test_format_is_uuid(self):
        import uuid as _uuid

        s = EvidenceGraph.resource_uuid_for_control("AC-2")
        # Must round-trip through uuid.UUID without raising.
        assert str(_uuid.UUID(s)) == s


# ---------------------------------------------------------------------------
# back_matter_resource_for_control — single-control resource shape
# ---------------------------------------------------------------------------


class TestBackMatterResource:
    def test_returns_none_when_no_coverage(self):
        g = EvidenceGraph()
        assert g.back_matter_resource_for_control("AC-2") is None

    def test_resource_carries_control_id_and_props(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_ir_object(IRObjectNode(id="ir:AC-2"))
        g.add_evidence(EvidenceNode(id="EV-1", source="manual", control_id="AC-2", hash="abc"))
        g.link_implements("AC-2", "ir:AC-2")
        g.link_validated_by("ir:AC-2", "EV-1")
        res = g.back_matter_resource_for_control("AC-2")
        assert res is not None
        assert res["uuid"] == EvidenceGraph.resource_uuid_for_control("AC-2")
        prop_names = {p["name"] for p in res["props"]}
        assert "control-id" in prop_names
        assert "graph-evidence-id" in prop_names
        # All graph props use the graph namespace.
        for p in res["props"]:
            assert p["ns"] == "https://uiao.gov/ns/oscal/graph"

    def test_rlinks_when_scheduler_metadata_present(self, tmp_path):
        run_dir = _write_scheduler_run(
            tmp_path,
            [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
        )
        g = EvidenceGraph.from_scheduler_run(run_dir)
        res = g.back_matter_resource_for_control("AC-2")
        assert res is not None
        assert "rlinks" in res
        href = res["rlinks"][0]["href"]
        assert href.startswith("schedrun://")
        assert "scubagear" in href

    def test_no_rlinks_when_evidence_lacks_scheduler_metadata(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_ir_object(IRObjectNode(id="ir:AC-2"))
        g.add_evidence(EvidenceNode(id="EV-1", source="manual", control_id="AC-2", hash="abc"))
        g.link_implements("AC-2", "ir:AC-2")
        g.link_validated_by("ir:AC-2", "EV-1")
        res = g.back_matter_resource_for_control("AC-2")
        assert res is not None
        assert "rlinks" not in res

    def test_finding_only_resource(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_finding(FindingNode(id="F-1", severity="High", control_id="AC-2"))
        g.link_violated_by("AC-2", "F-1")
        res = g.back_matter_resource_for_control("AC-2")
        assert res is not None
        prop_names = {p["name"] for p in res["props"]}
        assert "graph-finding-id" in prop_names
        assert "graph-finding-severity" in prop_names


# ---------------------------------------------------------------------------
# back_matter_resources_for_controls — many-control batch
# ---------------------------------------------------------------------------


class TestBackMatterResources:
    def test_drops_uncovered_controls(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_finding(FindingNode(id="F-1", severity="High", control_id="AC-2"))
        g.link_violated_by("AC-2", "F-1")
        result = g.back_matter_resources_for_controls(["AC-2", "IA-2", "SC-7"])
        assert set(result.keys()) == {"AC-2"}

    def test_dedupes_repeated_input(self):
        g = EvidenceGraph()
        g.add_control(ControlNode(id="AC-2"))
        g.add_finding(FindingNode(id="F-1", severity="Medium", control_id="AC-2"))
        g.link_violated_by("AC-2", "F-1")
        result = g.back_matter_resources_for_controls(["AC-2", "AC-2", "AC-2"])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# build_component_definition — graph augmentation
# ---------------------------------------------------------------------------


class TestComponentDefinitionGraph:
    def test_without_graph_no_back_matter_or_links(self):
        from uiao.generators.oscal import build_component_definition

        cd = build_component_definition(_component_def_context())
        comp = cd["components"][0]
        assert comp["control-implementations"]
        imp_req = comp["control-implementations"][0]["implemented-requirements"][0]
        assert "links" not in imp_req
        # No back-matter when no graph.
        assert "back-matter" not in cd

    def test_with_graph_attaches_props_links_and_back_matter(self, tmp_path):
        from uiao.generators.oscal import build_component_definition

        run_dir = _write_scheduler_run(
            tmp_path,
            [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
        )
        graph = EvidenceGraph.from_scheduler_run(run_dir)
        cd = build_component_definition(_component_def_context(), graph=graph)

        imp_req = cd["components"][0]["control-implementations"][0]["implemented-requirements"][0]
        prop_names = {p["name"] for p in imp_req["props"]}
        assert "graph-adapter-id" in prop_names
        assert "graph-scheduler-run-id" in prop_names

        assert "links" in imp_req
        link = imp_req["links"][0]
        assert link["rel"] == "graph-evidence"
        expected_uuid = EvidenceGraph.resource_uuid_for_control("AC-2")
        assert link["href"] == f"#{expected_uuid}"

        # Back-matter resource exists with the matching UUID.
        assert "back-matter" in cd
        resources = cd["back-matter"]["resources"]
        assert len(resources) == 1
        assert resources[0]["uuid"] == expected_uuid

    def test_graph_with_no_coverage_leaves_legacy_shape(self):
        from uiao.generators.oscal import build_component_definition

        graph = EvidenceGraph()
        graph.add_control(ControlNode(id="IA-2"))  # unrelated control
        cd = build_component_definition(_component_def_context(), graph=graph)
        imp_req = cd["components"][0]["control-implementations"][0]["implemented-requirements"][0]
        assert "links" not in imp_req
        assert "back-matter" not in cd

    def test_build_oscal_threads_graph(self, tmp_path):
        from uiao.generators.oscal import build_oscal

        graph = EvidenceGraph()
        out = build_oscal(
            canon_path=tmp_path / "nonexistent.yaml",
            data_dir=tmp_path,
            output_dir=tmp_path / "out",
            graph=graph,
        )
        assert out.exists()
        with out.open() as fh:
            data = json.load(fh)
        assert "component-definition" in data


# ---------------------------------------------------------------------------
# Cross-emitter back-matter consistency
# ---------------------------------------------------------------------------


def _ssp_context_with_ac2() -> dict[str, Any]:
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


def _poam_context_with_ac2_gap() -> dict[str, Any]:
    return {
        "unified_compliance_matrix": [
            {
                "category": "Access Control",
                "cisa_maturity": "Initial",
                "nist_controls": ["AC-2"],
            }
        ],
    }


def _minimal_evidence_bundle():
    from uiao.evidence.bundle import EvidenceBundle
    from uiao.ir.models.core import Evidence, ProvenanceRecord

    provenance = ProvenanceRecord(
        source="test",
        timestamp="2026-04-24T13:00:00+00:00",
        version="1.0",
        content_hash="probe",
        actor="test",
    )
    evidence = Evidence(
        id="EV-TEST-1",
        source="test",
        control_id="AC-2",
        timestamp="2026-04-24T13:00:00+00:00",
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


def test_all_four_emitters_share_one_resource_uuid_per_control(tmp_path):
    """Same graph → all four OSCAL artifacts emit identical back-matter
    resource UUIDs and links for the same control. This is what makes
    cross-artifact navigation work in trestle and similar tooling.
    """
    from uiao.generators.oscal import build_component_definition
    from uiao.generators.poam import build_poam
    from uiao.generators.sar import build_sar
    from uiao.generators.ssp import build_ssp_skeleton

    run_dir = _write_scheduler_run(
        tmp_path,
        [{"id": "scubagear", "ksi_id": "ksi:AC-2", "drift_severity": "P1"}],
    )
    graph = EvidenceGraph.from_scheduler_run(run_dir)
    expected = EvidenceGraph.resource_uuid_for_control("AC-2")

    sar = build_sar(_minimal_evidence_bundle(), graph=graph)
    ssp = build_ssp_skeleton(_ssp_context_with_ac2(), data_dir=tmp_path, graph=graph)
    poam = build_poam(_poam_context_with_ac2_gap(), graph=graph)
    cd = build_component_definition(_component_def_context(), graph=graph)

    # SAR observation links.
    sar_obs = sar["assessment-results"]["results"][0]["observations"][0]
    assert sar_obs["links"][0]["href"] == f"#{expected}"

    # SAR back-matter contains the resource (alongside per-evidence resources).
    sar_resource_uuids = {r["uuid"] for r in sar["assessment-results"]["back-matter"]["resources"]}
    assert expected in sar_resource_uuids

    # SSP requirement link.
    ac2_req = next(r for r in ssp["control-implementation"]["implemented-requirements"] if r["control-id"] == "AC-2")
    assert ac2_req["links"][0]["href"] == f"#{expected}"
    ssp_resource_uuids = {r["uuid"] for r in ssp["back-matter"]["resources"]}
    assert expected in ssp_resource_uuids

    # POA&M item link.
    poam_item = poam["poam-items"][0]
    assert poam_item["links"][0]["href"] == f"#{expected}"
    poam_resource_uuids = {r["uuid"] for r in poam["back-matter"]["resources"]}
    assert expected in poam_resource_uuids

    # Component-definition implemented-requirement link.
    imp_req = cd["components"][0]["control-implementations"][0]["implemented-requirements"][0]
    assert imp_req["links"][0]["href"] == f"#{expected}"
    cd_resource_uuids = {r["uuid"] for r in cd["back-matter"]["resources"]}
    assert expected in cd_resource_uuids


def test_legacy_emitters_unchanged_without_graph(tmp_path):
    """Regression: callers that don't pass graph= see no back-matter
    resources or links from the graph machinery."""
    from uiao.generators.oscal import build_component_definition
    from uiao.generators.poam import build_poam
    from uiao.generators.sar import build_sar
    from uiao.generators.ssp import build_ssp_skeleton

    sar = build_sar(_minimal_evidence_bundle())
    ssp = build_ssp_skeleton(_ssp_context_with_ac2(), data_dir=tmp_path)
    poam = build_poam(_poam_context_with_ac2_gap())
    cd = build_component_definition(_component_def_context())

    # No graph-evidence links anywhere.
    sar_obs = sar["assessment-results"]["results"][0]["observations"][0]
    assert "links" not in sar_obs
    ac2_req = next(r for r in ssp["control-implementation"]["implemented-requirements"] if r["control-id"] == "AC-2")
    assert "links" not in ac2_req
    assert "links" not in poam["poam-items"][0]
    cd_imp_req = cd["components"][0]["control-implementations"][0]["implemented-requirements"][0]
    assert "links" not in cd_imp_req
    assert "back-matter" not in cd
    assert "back-matter" not in poam
