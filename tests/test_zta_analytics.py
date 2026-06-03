"""Tests for uiao.adapters.zta.analytics — severity scoring + remediation priority."""

from __future__ import annotations

from pathlib import Path

from uiao.adapters.zta.analytics import (
    FACT_COLUMNS,
    build_facts,
    effort_weight,
    fact_record,
    findings,
    priority_bucket,
    severity_score,
)
from uiao.adapters.zta.ingest import load_report

FIXTURES = Path(__file__).parent / "fixtures" / "zta"
MINI_JSON = FIXTURES / "sample-mini.json"


def _by_id():
    return {t.test_id: t for t in load_report(MINI_JSON).tests}


def test_severity_only_findings_score():
    tests = _by_id()
    assert severity_score(tests["21001"]) == 100  # High + Failed
    assert severity_score(tests["24006"]) == 60  # High + Investigate (0.6)
    assert severity_score(tests["22002"]) == 0  # High but Skipped -> not a finding
    assert severity_score(tests["23004"]) == 0  # Medium Planned
    assert severity_score(tests["24005"]) == 0  # Low Passed


def test_effort_weight():
    tests = _by_id()
    assert effort_weight(tests["20606e75-05c4-48c0-9d97-add6daa2109a"]) == 1  # Low
    assert effort_weight(tests["21001"]) == 2  # Medium
    assert effort_weight(tests["22003"]) == 3  # High


def test_priority_bucket_thresholds():
    assert priority_bucket(100) == "P1"
    assert priority_bucket(50) == "P1"
    assert priority_bucket(30) == "P2"
    assert priority_bucket(15) == "P3"
    assert priority_bucket(1) == "P4"
    assert priority_bucket(0) == "—"


def test_build_facts_sorted_findings_first():
    facts = build_facts(load_report(MINI_JSON))
    assert [f.is_finding for f in facts[:3]] == [True, True, True]
    # Highest priority first: the guid (sev100/eff1=100) leads.
    assert facts[0].test_id == "20606e75-05c4-48c0-9d97-add6daa2109a"


def test_buckets_reconcile_with_findings():
    facts = build_facts(load_report(MINI_JSON))
    fnd = findings(facts)
    assert len(fnd) == 3
    bucketed = [f for f in facts if f.bucket != "—"]
    # Every bucketed row is a finding and vice-versa (Error/Skipped/Planned score 0).
    assert {f.test_id for f in bucketed} == {f.test_id for f in fnd}


def test_premium_finding_flagged():
    facts = {f.test_id: f for f in build_facts(load_report(MINI_JSON))}
    # 24005 is premium-gated (AAD_PREMIUM_P2) but Passed -> not a finding, no bucket.
    assert facts["24005"].premium_gated is True
    assert facts["24005"].applicability_note != ""


def test_fact_record_matches_columns():
    fact = build_facts(load_report(MINI_JSON))[0]
    record = fact_record(fact)
    assert tuple(record.keys()) == FACT_COLUMNS
