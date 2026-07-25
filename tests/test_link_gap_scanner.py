"""Tests for scripts/scan_link_gaps.py (UIAO_145 §7 / ADR-132 Phase 2).

Covers:
- The scanner runs against the real repo and reports the known,
  intended migration debt (unrecorded agreements, unanchored artifacts,
  missing review dates) without crashing
- Past-due review detection with an injected `today`
- Overlay-with-no-pack detection on a synthetic registry
- Advisory mode exits 0 with gaps; --strict exits 1; --json parses
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "scan_link_gaps.py"


@pytest.fixture()
def mod():
    spec = importlib.util.spec_from_file_location("scan_link_gaps", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec: @dataclass resolution requires the module to
    # be reachable via sys.modules under Python 3.11+.
    sys.modules["scan_link_gaps"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("scan_link_gaps", None)


def test_scan_reports_known_migration_debt(mod) -> None:
    gaps = mod.scan()
    kinds = {g.kind for g in gaps}
    # The three unrecorded-agreement backfills.
    assert "GAP-AGREEMENT-UNRECORDED" in kinds
    unrecorded = [g for g in gaps if g.kind == "GAP-AGREEMENT-UNRECORDED"]
    assert {g.link_id for g in unrecorded} == {
        "opm-apim-federal-gateway",
        "hr-inbound-provisioning",
        "conmon-reporting-egress",
    }
    # Four links are not provenance-anchored (all but federal-hrit-integration).
    anchor_gaps = {g.link_id for g in gaps if g.kind == "GAP-NOT-ANCHORED"}
    assert "federal-hrit-integration" not in anchor_gaps
    assert len(anchor_gaps) == 4
    # No link cites a control outside the control library.
    assert "GAP-CONTROL-UNKNOWN" not in kinds


def test_scan_flags_remaining_doc_library_evidence(mod) -> None:
    # CA-3 still carries document-library locators for its diagram
    # evidence; that residue is tracked, not hidden.
    gaps = mod.scan()
    doc_lib = {g.link_id for g in gaps if g.kind == "GAP-EVIDENCE-DOC-LIBRARY"}
    assert "CA-3" in doc_lib


def test_past_due_review_detection(mod, tmp_path, monkeypatch) -> None:
    registry = {
        "schema-version": "1.0.0",
        "updated": "2026-07-25",
        "links": [
            {
                "id": "stale-review-link",
                "name": "x",
                "counterparty": {"name": "X", "class": "state"},
                "direction": "inbound",
                "ssot-stance": "they-are-source",
                "status": "active",
                "agreement": {
                    "type": "mou",
                    "artifact-location": "src/x.md",
                    "provenance-anchored": True,
                    "next-review": "2026-01-01",
                },
                "authorized-by": ["src/x.md"],
            }
        ],
    }
    reg = tmp_path / "link-registry.yaml"
    reg.write_text(yaml.safe_dump(registry))
    monkeypatch.setattr(mod, "LINK_REGISTRY", reg)
    import datetime

    gaps = mod.scan(today=datetime.date(2026, 7, 25))
    assert any(g.kind == "GAP-REVIEW-PAST-DUE" and g.link_id == "stale-review-link" for g in gaps)
    # And not past-due when 'today' precedes the review date.
    gaps_early = mod.scan(today=datetime.date(2025, 12, 31))
    assert not any(g.kind == "GAP-REVIEW-PAST-DUE" for g in gaps_early)


def test_overlay_without_pack_gaps(mod, tmp_path, monkeypatch) -> None:
    registry = {
        "links": [
            {
                "id": "hipaa-link",
                "status": "active",
                "counterparty": {"name": "Hospital", "class": "regulated-commercial"},
                "ssot-stance": "they-are-source",
                "agreement": {"type": "baa", "artifact-location": "x", "provenance-anchored": True},
                "regime-overlays": ["hipaa"],
            }
        ]
    }
    reg = tmp_path / "link-registry.yaml"
    reg.write_text(yaml.safe_dump(registry))
    monkeypatch.setattr(mod, "LINK_REGISTRY", reg)
    gaps = mod.scan()
    assert any(g.kind == "GAP-OVERLAY-NO-PACK" and "hipaa" in g.detail for g in gaps)


def test_advisory_exits_zero_strict_exits_one(mod, capsys) -> None:
    assert mod.main([]) == 0
    capsys.readouterr()
    assert mod.main(["--strict"]) == 1


def test_json_output_parses(mod, capsys) -> None:
    assert mod.main(["--json"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert all({"kind", "link_id", "detail"} <= set(g) for g in data)
