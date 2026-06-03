"""Tests for uiao.adapters.zta.remediation and its renderer."""

from __future__ import annotations

import csv
from pathlib import Path

from uiao.adapters.zta.ingest import load_report
from uiao.adapters.zta.remediation import (
    build_cards,
    card_for,
    fix_surface,
    learn_links,
    split_remediation,
)
from uiao.adapters.zta.render.remediation import render_playbook, write_remediation

FIXTURES = Path(__file__).parent / "fixtures" / "zta"
MINI_JSON = FIXTURES / "sample-mini.json"


def _by_id():
    return {t.test_id: t for t in load_report(MINI_JSON).tests}


def test_fix_surface_from_portal_links():
    tests = _by_id()
    # entra.microsoft.com deep link in TestResult -> Entra admin center
    assert fix_surface(tests["21001"]) == ("Microsoft Entra admin center", "https://entra.microsoft.com")
    # portal.azure.com deep link -> Azure portal
    assert fix_surface(tests["20606e75-05c4-48c0-9d97-add6daa2109a"]) == ("Azure portal", "https://portal.azure.com")


def test_fix_surface_pillar_fallback_when_no_links():
    tests = _by_id()
    # 24006 (Devices, Investigate) has no portal links -> pillar fallback to Intune
    assert fix_surface(tests["24006"]) == ("Microsoft Intune admin center", "https://intune.microsoft.com")


def test_split_remediation():
    tests = _by_id()
    rationale, remediation = split_remediation(tests["21001"])
    assert "Legacy auth" in rationale
    assert "Manage authentication methods" in remediation
    # A test without a Remediation action heading -> empty remediation block.
    _, none = split_remediation(tests["22002"])
    assert none == ""


def test_learn_links_extracted_and_deduped():
    tests = _by_id()
    links = learn_links(tests["21001"])
    assert links == [
        (
            "Manage authentication methods",
            "https://learn.microsoft.com/entra/identity/authentication/concept-authentication-methods",
        )
    ]


def test_build_cards_failed_only_sorted():
    cards = build_cards(load_report(MINI_JSON))  # default: Failed
    assert {c.test_id for c in cards} == {"21001", "20606e75-05c4-48c0-9d97-add6daa2109a"}
    # grouped by pillar (Identity before Infrastructure)
    assert [c.pillar for c in cards] == ["Identity", "Infrastructure"]


def test_card_carries_severity_and_console():
    card = card_for(_by_id()["21001"])
    assert card.severity == 100
    assert card.bucket == "P1"
    assert card.console == "Microsoft Entra admin center"


def test_render_playbook_has_sections_and_guidance():
    report = load_report(MINI_JSON)
    md = render_playbook(report, build_cards(report))
    assert "# Zero Trust Assessment — Remediation Playbook" in md
    assert "## Identity" in md and "## Infrastructure" in md
    assert "How to fix — Microsoft's remediation action" in md
    assert "Manage authentication methods" in md
    assert "Controlled" in md  # boundary caveat present


def test_write_remediation_outputs(tmp_path: Path):
    report = load_report(MINI_JSON)
    out = write_remediation(report, tmp_path)
    assert out.count == 2
    assert out.playbook.exists() and out.playbook.stat().st_size > 0
    rows = list(csv.DictReader(out.tracker.open(encoding="utf-8-sig")))
    assert len(rows) == 2
    assert {"Status", "Owner", "Notes", "Console", "PrimaryReference"} <= set(rows[0])
    assert all(r["Status"] == "" for r in rows)  # blank for the team to fill
