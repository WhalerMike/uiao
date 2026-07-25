"""Tests for Link nodes on the Evidence Graph (UIAO_145 / ADR-132 Phase 2).

Covers:
- augment_graph_with_links adds LinkNodes + `evidences` edges from the
  packaged canon registry, auto-creating missing ControlNodes
- Deterministic ordering and stats() attribution (node type "link")
- include_inactive gating on a synthetic registry
- Existing ControlNodes are reused, not duplicated
"""

from __future__ import annotations

from typing import Any

from uiao.evidence.graph import ControlNode, EvidenceGraph, LinkNode
from uiao.evidence.links import augment_graph_with_links


def test_augment_from_packaged_registry() -> None:
    graph = EvidenceGraph()
    added = augment_graph_with_links(graph)
    assert added >= 5
    stats = graph.stats()
    assert stats["nodes_by_type"].get("link", 0) == added
    assert stats["edges_by_type"].get("evidences", 0) >= added
    # Controls auto-created for the bound control ids.
    assert isinstance(graph.get("CA-3"), ControlNode)
    node = graph.get("opm-apim-federal-gateway")
    assert isinstance(node, LinkNode)
    assert node.counterparty_class == "federal-agency"
    assert node.ssot_stance == "they-are-source"


def test_augment_reuses_existing_control_nodes() -> None:
    graph = EvidenceGraph()
    pre_existing = ControlNode(id="CA-3", family="CA", description="pre-seeded")
    graph.add_control(pre_existing)
    augment_graph_with_links(graph)
    assert graph.get("CA-3") is pre_existing


def _synthetic_registry(status: str) -> dict[str, Any]:
    return {
        "links": [
            {
                "id": "synthetic-link",
                "name": "Synthetic",
                "status": status,
                "counterparty": {"name": "X", "class": "state"},
                "direction": "inbound",
                "ssot-stance": "they-are-source",
                "agreement": {"type": "mou", "artifact-location": "x", "provenance-anchored": True},
                "controls": ["CA-3"],
                "authorized-by": ["src/x.md"],
            }
        ]
    }


def test_inactive_links_gated_by_flag() -> None:
    graph = EvidenceGraph()
    assert augment_graph_with_links(graph, registry=_synthetic_registry("proposed")) == 0
    assert graph.get("synthetic-link") is None

    graph2 = EvidenceGraph()
    assert augment_graph_with_links(graph2, registry=_synthetic_registry("proposed"), include_inactive=True) == 1
    assert isinstance(graph2.get("synthetic-link"), LinkNode)


def test_link_extra_carries_agreement_location_not_payload() -> None:
    graph = EvidenceGraph()
    augment_graph_with_links(graph)
    node = graph.get("federal-hrit-integration")
    assert isinstance(node, LinkNode)
    assert node.provenance_anchored is True
    assert node.extra["agreement-location"] == "src/uiao/canon/reciprocal-consumption-registry.yaml"
