"""Tests for UIAO_113 v1.2 — ato-decision + reciprocity-record node types (WS-A3).

Covers:
- Frontmatter version bump to "1.2"
- Presence of the two new node-type sections in the spec markdown
- Presence of the three new edge types in the spec markdown
- ATODecisionNode and ReciprocityRecordNode dataclasses exist and are
  constructible
- link_authorizes_reciprocity / link_scopes_to_agency / link_derives_from_ssp
  helper methods create correctly-typed edges
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SPEC_PATH = Path(__file__).parent.parent / "src" / "uiao" / "canon" / "specs" / "graph-schema.md"


def _load_spec_text() -> str:
    return _SPEC_PATH.read_text(encoding="utf-8")


def _load_frontmatter() -> dict:
    text = _load_spec_text()
    parts = text.split("---")
    # parts[0] is empty (before the opening ---), parts[1] is the frontmatter
    assert len(parts) >= 3, "graph-schema.md must contain YAML frontmatter delimited by ---"
    return yaml.safe_load(parts[1])


# ---------------------------------------------------------------------------
# Frontmatter assertions
# ---------------------------------------------------------------------------


def test_frontmatter_version_is_1_2() -> None:
    """UIAO_113 frontmatter must report version 1.2 after WS-A3 amendment."""
    fm = _load_frontmatter()
    assert fm.get("version") == "1.2", (
        f"Expected version '1.2', got {fm.get('version')!r}. Did the frontmatter bump land in graph-schema.md?"
    )


def test_frontmatter_document_id() -> None:
    fm = _load_frontmatter()
    assert fm.get("document_id") == "UIAO_113"


def test_frontmatter_updated_at() -> None:
    """updated_at must be >= created_at (monotonic constraint from metadata schema)."""
    fm = _load_frontmatter()
    assert fm.get("updated_at") >= fm.get("created_at"), "updated_at must not precede created_at"


# ---------------------------------------------------------------------------
# Node-type section assertions
# ---------------------------------------------------------------------------


def test_spec_contains_ato_decision_section() -> None:
    """graph-schema.md must contain a Node Type 12: ato-decision section."""
    text = _load_spec_text()
    assert "### 12. ATO Decision" in text or re.search(r"###\s+Node Type 12.*ato-decision", text, re.IGNORECASE), (
        "Expected a '### 12. ATO Decision' section in graph-schema.md"
    )
    assert "ato-decision" in text


def test_spec_contains_reciprocity_record_section() -> None:
    """graph-schema.md must contain a Node Type 13: reciprocity-record section."""
    text = _load_spec_text()
    assert "### 13. Reciprocity Record" in text or re.search(
        r"###\s+Node Type 13.*reciprocity-record", text, re.IGNORECASE
    ), "Expected a '### 13. Reciprocity Record' section in graph-schema.md"
    assert "reciprocity-record" in text


def test_spec_ato_decision_fields() -> None:
    """ato-decision section must enumerate the required fields."""
    text = _load_spec_text()
    for field in (
        "controlling_ato_id",
        "authorizing_official",
        "decision_date",
        "expires_at",
        "ssp_ref",
        "provenance",
    ):
        assert field in text, f"Field '{field}' missing from graph-schema.md ato-decision section"


def test_spec_reciprocity_record_fields() -> None:
    """reciprocity-record section must enumerate the required fields."""
    text = _load_spec_text()
    for field in (
        "record_id",
        "controlling_ato_id",
        "consuming_agency_code",
        "effective_at",
        "expires_at",
        "legal_basis",
        "record_hash",
        "signature_ref",
    ):
        assert field in text, f"Field '{field}' missing from graph-schema.md reciprocity-record section"


# ---------------------------------------------------------------------------
# Edge-type assertions
# ---------------------------------------------------------------------------


def test_spec_contains_authorizes_reciprocity_edge() -> None:
    text = _load_spec_text()
    assert "authorizes-reciprocity" in text, "Edge type 'authorizes-reciprocity' missing from graph-schema.md"


def test_spec_contains_scopes_to_agency_edge() -> None:
    text = _load_spec_text()
    assert "scopes-to-agency" in text, "Edge type 'scopes-to-agency' missing from graph-schema.md"


def test_spec_contains_derives_from_ssp_edge() -> None:
    text = _load_spec_text()
    assert "derives-from-ssp" in text, "Edge type 'derives-from-ssp' missing from graph-schema.md"


# ---------------------------------------------------------------------------
# Provenance-log section assertion
# ---------------------------------------------------------------------------


def test_spec_contains_provenance_entry() -> None:
    """v1.1 → v1.2 provenance entry must cite ADR-058 and UIAO_140."""
    text = _load_spec_text()
    assert "ADR-058" in text, "Provenance entry must cite ADR-058"
    assert "UIAO_140" in text, "Provenance entry must cite UIAO_140"


# ---------------------------------------------------------------------------
# Runtime — ATODecisionNode dataclass
# ---------------------------------------------------------------------------


def test_ato_decision_node_constructible() -> None:
    """ATODecisionNode must be importable and constructible from evidence.graph."""
    from uiao.evidence.graph import ATODecisionNode

    node = ATODecisionNode(
        id="ATO-OPM-HRIT-2026-001",
        controlling_ato_id="OPM-HRIT-2026-001",
        authorizing_official="OPM CISO",
        decision_date="2026-01-15T00:00:00Z",
        expires_at="2029-01-15T00:00:00Z",
        ssp_ref="550e8400-e29b-41d4-a716-446655440000",
    )
    assert node.node_type == "ato-decision"
    assert node.controlling_ato_id == "OPM-HRIT-2026-001"
    assert node.ssp_ref == "550e8400-e29b-41d4-a716-446655440000"


# ---------------------------------------------------------------------------
# Runtime — ReciprocityRecordNode dataclass
# ---------------------------------------------------------------------------


def test_reciprocity_record_node_constructible() -> None:
    """ReciprocityRecordNode must be importable and constructible."""
    from uiao.evidence.graph import ReciprocityRecordNode

    node = ReciprocityRecordNode(
        id="RECIP-OPM-HRIT-2026-001/TREAS",
        record_id="OPM-HRIT-2026-001/TREAS",
        controlling_ato_id="OPM-HRIT-2026-001",
        consuming_agency_code="TREAS",
        effective_at="2026-02-01T00:00:00Z",
        expires_at="2029-01-15T00:00:00Z",
        legal_basis="interagency-mou",
        record_hash="a" * 64,
        signature_ref="sig-001",
    )
    assert node.node_type == "reciprocity-record"
    assert node.consuming_agency_code == "TREAS"
    assert node.legal_basis == "interagency-mou"


# ---------------------------------------------------------------------------
# Runtime — EvidenceGraph edge helpers
# ---------------------------------------------------------------------------


def test_link_authorizes_reciprocity_creates_edge() -> None:
    """link_authorizes_reciprocity must create an 'authorizes-reciprocity' edge."""
    from uiao.evidence.graph import ATODecisionNode, EvidenceGraph, ReciprocityRecordNode

    g = EvidenceGraph()
    ato = ATODecisionNode(id="ATO-001", controlling_ato_id="OPM-HRIT-2026-001")
    rec = ReciprocityRecordNode(id="RECIP-001", controlling_ato_id="OPM-HRIT-2026-001")
    g.add_ato_decision(ato)
    g.add_reciprocity_record(rec)
    g.link_authorizes_reciprocity("ATO-001", "RECIP-001")

    edges = g._out.get("ATO-001", [])
    assert any(e.edge_type == "authorizes-reciprocity" for e in edges), (
        "Expected 'authorizes-reciprocity' edge from ATO-001"
    )


def test_link_scopes_to_agency_creates_edge() -> None:
    """link_scopes_to_agency must create a 'scopes-to-agency' edge."""
    from uiao.evidence.graph import EvidenceGraph, ReciprocityRecordNode

    g = EvidenceGraph()
    rec = ReciprocityRecordNode(id="RECIP-001", consuming_agency_code="TREAS")
    g.add_reciprocity_record(rec)
    g.link_scopes_to_agency("RECIP-001", "AGENCY-TREAS")

    edges = g._out.get("RECIP-001", [])
    assert any(e.edge_type == "scopes-to-agency" for e in edges), "Expected 'scopes-to-agency' edge from RECIP-001"


def test_link_derives_from_ssp_creates_edge() -> None:
    """link_derives_from_ssp must create a 'derives-from-ssp' edge."""
    from uiao.evidence.graph import EvidenceGraph, ReciprocityRecordNode

    g = EvidenceGraph()
    rec = ReciprocityRecordNode(id="RECIP-001", controlling_ato_id="ATO-001")
    g.add_reciprocity_record(rec)
    g.link_derives_from_ssp("RECIP-001", "SSP-001")

    edges = g._out.get("RECIP-001", [])
    assert any(e.edge_type == "derives-from-ssp" for e in edges), "Expected 'derives-from-ssp' edge from RECIP-001"


def test_full_reciprocity_subgraph() -> None:
    """End-to-end: build an ato-decision → reciprocity-record subgraph and verify stats."""
    from uiao.evidence.graph import ATODecisionNode, EvidenceGraph, ReciprocityRecordNode

    g = EvidenceGraph()

    ato = ATODecisionNode(
        id="ATO-OPM-2026",
        controlling_ato_id="OPM-HRIT-2026-001",
        authorizing_official="OPM CISO",
        decision_date="2026-01-15T00:00:00Z",
        expires_at="2029-01-15T00:00:00Z",
        ssp_ref="ssp-uuid-001",
    )
    treas = ReciprocityRecordNode(
        id="RECIP-OPM/TREAS",
        record_id="OPM-HRIT-2026-001/TREAS",
        controlling_ato_id="OPM-HRIT-2026-001",
        consuming_agency_code="TREAS",
        legal_basis="interagency-mou",
    )
    irs = ReciprocityRecordNode(
        id="RECIP-OPM/IRS",
        record_id="OPM-HRIT-2026-001/IRS",
        controlling_ato_id="OPM-HRIT-2026-001",
        consuming_agency_code="IRS",
        legal_basis="interagency-mou",
    )

    g.add_ato_decision(ato)
    g.add_reciprocity_record(treas)
    g.add_reciprocity_record(irs)

    g.link_authorizes_reciprocity("ATO-OPM-2026", "RECIP-OPM/TREAS")
    g.link_authorizes_reciprocity("ATO-OPM-2026", "RECIP-OPM/IRS")
    g.link_scopes_to_agency("RECIP-OPM/TREAS", "AGENCY-TREAS")
    g.link_scopes_to_agency("RECIP-OPM/IRS", "AGENCY-IRS")
    g.link_derives_from_ssp("RECIP-OPM/TREAS", "SSP-OPM")
    g.link_derives_from_ssp("RECIP-OPM/IRS", "SSP-OPM")

    stats = g.stats()
    assert stats["total_nodes"] == 3  # 1 ato + 2 reciprocity
    assert stats["total_edges"] == 6

    assert stats["nodes_by_type"]["ato-decision"] == 1
    assert stats["nodes_by_type"]["reciprocity-record"] == 2

    assert stats["edges_by_type"]["authorizes-reciprocity"] == 2
    assert stats["edges_by_type"]["scopes-to-agency"] == 2
    assert stats["edges_by_type"]["derives-from-ssp"] == 2

    # nodes_of_type helper
    ato_nodes = g.nodes_of_type("ato-decision")
    assert len(ato_nodes) == 1
    assert ato_nodes[0].controlling_ato_id == "OPM-HRIT-2026-001"
