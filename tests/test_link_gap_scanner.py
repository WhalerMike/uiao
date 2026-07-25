"""Tests for link-gap detection (UIAO_145 §7 / ADR-132 Phase 2).

Covers the package core (uiao.evidence.link_gaps) and the thin CLI
wrapper (scripts/scan_link_gaps.py):
- The scan reports the known, intended migration debt against the real
  canon (unrecorded agreements, unanchored artifacts, doc-library
  evidence residue) and nothing spurious
- Review dates: the shipped registry declares next-review, so
  GAP-REVIEW-MISSING is burned down; past-due detection works with an
  injected `today` on both sides of the boundary
- Overlay-with-no-pack detection on an injected registry
- gap_summary() counts deterministically
- Script: advisory mode exits 0 with gaps; --strict exits 1; --json
  parses; output identical to the package scan
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from uiao.evidence.link_gaps import Gap, gap_summary, scan

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "scan_link_gaps.py"


# ---------------------------------------------------------------------------
# Package core
# ---------------------------------------------------------------------------


def test_scan_reports_known_migration_debt() -> None:
    gaps = scan()
    kinds = {g.kind for g in gaps}
    unrecorded = [g for g in gaps if g.kind == "GAP-AGREEMENT-UNRECORDED"]
    assert {g.link_id for g in unrecorded} == {
        "opm-apim-federal-gateway",
        "hr-inbound-provisioning",
        "conmon-reporting-egress",
    }
    anchor_gaps = {g.link_id for g in gaps if g.kind == "GAP-NOT-ANCHORED"}
    assert "federal-hrit-integration" not in anchor_gaps
    assert len(anchor_gaps) == 4
    # Registration declared next-review on every link, so the review
    # gap class is burned down — and nothing is past due yet.
    assert "GAP-REVIEW-MISSING" not in kinds
    assert "GAP-REVIEW-PAST-DUE" not in kinds
    assert "GAP-CONTROL-UNKNOWN" not in kinds


def test_scan_flags_remaining_doc_library_evidence() -> None:
    # CA-3 still carries document-library locators for its diagram
    # evidence; that residue is tracked, not hidden.
    doc_lib = {g.link_id for g in scan() if g.kind == "GAP-EVIDENCE-DOC-LIBRARY"}
    assert "CA-3" in doc_lib


def test_shipped_registry_past_due_boundary() -> None:
    # The declared next-review is 2027-07-25: not due the day before,
    # due the day after.
    before = scan(today=datetime.date(2027, 7, 24))
    assert not [g for g in before if g.kind == "GAP-REVIEW-PAST-DUE"]
    after = scan(today=datetime.date(2027, 7, 26))
    past_due = {g.link_id for g in after if g.kind == "GAP-REVIEW-PAST-DUE"}
    assert len(past_due) == 5


def _synthetic_registry(**agreement_overrides: Any) -> dict[str, Any]:
    agreement = {
        "type": "mou",
        "artifact-location": "src/x.md",
        "provenance-anchored": True,
        **agreement_overrides,
    }
    return {
        "links": [
            {
                "id": "synthetic-link",
                "name": "x",
                "counterparty": {"name": "X", "class": "state"},
                "direction": "inbound",
                "ssot-stance": "they-are-source",
                "status": "active",
                "agreement": agreement,
                "authorized-by": ["src/x.md"],
            }
        ]
    }


def test_review_missing_on_injected_registry() -> None:
    registry = _synthetic_registry()
    registry["links"][0]["agreement"].pop("next-review", None)
    gaps = scan(registry=registry)
    assert any(g.kind == "GAP-REVIEW-MISSING" for g in gaps)


def test_past_due_on_injected_registry() -> None:
    registry = _synthetic_registry(**{"next-review": "2026-01-01"})
    gaps = scan(today=datetime.date(2026, 7, 25), registry=registry)
    assert any(g.kind == "GAP-REVIEW-PAST-DUE" and g.link_id == "synthetic-link" for g in gaps)
    early = scan(today=datetime.date(2025, 12, 31), registry=registry)
    assert not any(g.kind == "GAP-REVIEW-PAST-DUE" for g in early)


def test_overlay_without_pack_gaps() -> None:
    registry = _synthetic_registry()
    registry["links"][0]["regime-overlays"] = ["hipaa"]
    gaps = scan(registry=registry)
    assert any(g.kind == "GAP-OVERLAY-NO-PACK" and "hipaa" in g.detail for g in gaps)


def test_gap_summary_counts() -> None:
    gaps = [Gap("A", "x", ""), Gap("B", "y", ""), Gap("A", "z", "")]
    assert gap_summary(gaps) == {"A": 2, "B": 1}


# ---------------------------------------------------------------------------
# Script wrapper
# ---------------------------------------------------------------------------


@pytest.fixture()
def script_mod():
    spec = importlib.util.spec_from_file_location("scan_link_gaps_cli", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["scan_link_gaps_cli"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("scan_link_gaps_cli", None)


def test_advisory_exits_zero_strict_exits_one(script_mod, capsys) -> None:
    assert script_mod.main([]) == 0
    capsys.readouterr()
    assert script_mod.main(["--strict"]) == 1


def test_json_output_matches_package_scan(script_mod, capsys) -> None:
    assert script_mod.main(["--json"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert all({"kind", "link_id", "detail"} <= set(g) for g in data)
    assert len(data) == len(scan())
