"""Tests for uiao.evidence.links and the `uiao evidence links` CLI
(UIAO_145 / ADR-132 Phase 2).

Covers:
- The packaged canon registry loads via importlib.resources
- The inventory binds the backfilled links to their declared controls
- Unknown controls raise (a typo must not render a false-empty table)
- include_inactive gates proposed/retired links
- Markdown rendering is deterministic and carries the agreement state
- CLI happy path (table + json + --output), failure mode (bad control)
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from uiao.cli.evidence import evidence_app
from uiao.evidence.links import (
    LINK_EVIDENCE_CONTROLS,
    link_evidence_inventory,
    load_link_registry,
    render_markdown,
)

runner = CliRunner()


def test_packaged_registry_loads() -> None:
    doc = load_link_registry()
    assert isinstance(doc.get("links"), list)
    assert len(doc["links"]) >= 5


def test_inventory_binds_backfilled_links() -> None:
    inventory = link_evidence_inventory()
    assert set(inventory) == set(LINK_EVIDENCE_CONTROLS)
    ca3_ids = [row["id"] for row in inventory["CA-3"]]
    assert "opm-apim-federal-gateway" in ca3_ids
    assert "conmon-reporting-egress" in ca3_ids
    sa9_ids = [row["id"] for row in inventory["SA-9"]]
    assert "sailpoint-nerm-nonemployee" in sa9_ids
    # Sorted by link id — deterministic output.
    assert ca3_ids == sorted(ca3_ids)


def test_unknown_control_raises() -> None:
    with pytest.raises(ValueError, match="not a link-evidence control"):
        link_evidence_inventory(("XX-1",))


def test_include_inactive_gates_non_active_links() -> None:
    registry = {
        "links": [
            {
                "id": "proposed-link",
                "status": "proposed",
                "controls": ["CA-3"],
                "counterparty": {"name": "X", "class": "state"},
            }
        ]
    }
    active_only = link_evidence_inventory(("CA-3",), registry=registry)
    assert active_only["CA-3"] == []
    with_inactive = link_evidence_inventory(("CA-3",), registry=registry, include_inactive=True)
    assert [row["id"] for row in with_inactive["CA-3"]] == ["proposed-link"]


def test_render_markdown_shape() -> None:
    rendered = render_markdown(link_evidence_inventory())
    assert rendered.startswith("# External Interconnection Inventory")
    assert "## CA-3" in rendered
    assert "`opm-apim-federal-gateway`" in rendered
    # AC-20 has no bound links today — the empty state must be explicit.
    assert "_No registered interconnection evidences this control._" in rendered
    # Agreement state is part of the evidence.
    assert "unrecorded" in rendered


def test_cli_table_happy_path() -> None:
    result = runner.invoke(evidence_app, ["links"])
    assert result.exit_code == 0
    assert "External Interconnection Inventory" in result.output


def test_cli_json_and_output(tmp_path) -> None:
    out = tmp_path / "links.json"
    result = runner.invoke(evidence_app, ["links", "--format", "json", "--output", str(out)])
    assert result.exit_code == 0
    data = json.loads(out.read_text())
    assert set(data) == set(LINK_EVIDENCE_CONTROLS)


def test_cli_unknown_control_fails() -> None:
    result = runner.invoke(evidence_app, ["links", "--control", "XX-1"])
    assert result.exit_code == 1
    assert "not a link-evidence control" in result.output
