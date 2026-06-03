"""Tests for uiao.adapters.zta.triage and .applicability."""

from __future__ import annotations

from pathlib import Path

from uiao.adapters.zta.applicability import Applicability, derive_applicability, is_premium_gated
from uiao.adapters.zta.ingest import load_report
from uiao.adapters.zta.triage import build_triage, id_namespace

FIXTURES = Path(__file__).parent / "fixtures" / "zta"
MINI_JSON = FIXTURES / "sample-mini.json"


def _triage(**kwargs):
    return build_triage(load_report(MINI_JSON), **kwargs)


def test_status_counts_recomputed_not_from_summary():
    t = _triage()
    # The fixture's TestResultSummary claims 999s — must be ignored.
    assert t.status_counts == {
        "Failed": 2,
        "Investigate": 1,
        "Skipped": 2,
        "Planned": 1,
        "Passed": 1,
    }
    assert 999 not in t.status_counts.values()


def test_actionable_skipped_planned_totals():
    t = _triage()
    assert t.actionable_total == 3  # 2 Failed + 1 Investigate
    assert t.skipped_total == 2
    assert t.planned_total == 1


def test_high_worklist_excludes_skipped_even_when_high_risk():
    t = _triage()  # default risk=High, status Failed/Investigate
    ids = {x.test_id for x in t.worklist}
    assert ids == {"21001", "20606e75-05c4-48c0-9d97-add6daa2109a", "24006"}
    # 22002 and 22003 are High but Skipped -> excluded.
    assert "22002" not in ids
    assert "22003" not in ids


def test_worklist_risk_filter_widens():
    t = _triage(risks=("High", "Medium"))
    # Adds no new actionable rows (the Medium item is Planned, not a finding).
    assert {x.test_id for x in t.worklist} == {
        "21001",
        "20606e75-05c4-48c0-9d97-add6daa2109a",
        "24006",
    }


def test_namespace_counts():
    t = _triage()
    assert t.namespace_counts == {"numeric": 6, "guid": 1}


def test_id_namespace_classifier():
    assert id_namespace("21001") == "numeric"
    assert id_namespace("20606e75-05c4-48c0-9d97-add6daa2109a") == "guid"
    assert id_namespace("") == "other"


def test_premium_gating():
    t = _triage()
    assert t.premium_gated_total == 2  # Entra_Premium_Private_Access + AAD_PREMIUM_P2
    assert t.premium_gated_in_worklist == 0


def test_applicability_derivation():
    report = load_report(MINI_JSON)
    by_id = {x.test_id: x for x in report.tests}
    assert derive_applicability(by_id["22002"]) == Applicability.NOT_APPLICABLE
    assert derive_applicability(by_id["22003"]) == Applicability.LICENSE_GATED
    assert derive_applicability(by_id["21001"]) == Applicability.APPLICABLE
    # Passed but premium-gated -> license-gated tag.
    assert derive_applicability(by_id["24005"]) == Applicability.LICENSE_GATED
    assert is_premium_gated(by_id["24005"]) is True
    assert is_premium_gated(by_id["21001"]) is False


def test_pillar_crosstab_shape():
    t = _triage()
    assert t.pillar_crosstab["Network"]["Skipped"] == 2
    assert t.pillar_crosstab["Identity"]["Failed"] == 1
    assert t.pillar_crosstab["Infrastructure"]["Failed"] == 1
