"""Tests for the HR-feed quarantine gate (hrit/quarantine.py).

The gate holds resolved HR records that are unsafe to provision from:

  1. Clean record clears the gate
  2. Staleness → DRIFT-PROVENANCE hold
  3. Fresh record within the bound is not stale
  4. Null placement → DRIFT-IDENTITY hold
  5. Improbable delta: top-level org change → DRIFT-SEMANTIC hold
  6. Improbable delta: too many segments changed
  7. Improbable delta: depth jump beyond threshold
  8. Plausible move (shared ancestor, small change) clears
  9. Joiner with no prior placement skips the delta check
 10. Multiple reasons stack on one record
 11. Report aggregation (held / cleared / reason_counts)
 12. Trailing-delimiter tolerance in OrgPath comparison
 13. Unparseable / empty extracted_at does not crash or false-positive
 14. Config overrides move the thresholds
 15. Error codes are GOV-HRQ-NNN, unique and sequential
 16. Determinism — repeated evaluation is identical
 17. Public surface exports

All synthetic in-memory records; no live HR-system connection.
"""

from __future__ import annotations

from typing import Optional

from uiao.adapters.modernization.hrit import (
    QUARANTINE_IMPROBABLE_DELTA,
    QUARANTINE_NULL_PLACEMENT,
    QUARANTINE_STALE,
    HRRecord,
    QuarantineConfig,
    QuarantineDecision,
    QuarantineReport,
    evaluate_hr_quarantine,
)

_NOW = "2026-05-13T12:00:00Z"
_FRESH = "2026-05-13T00:00:00Z"  # 12h before _NOW
_STALE = "2026-05-10T00:00:00Z"  # ~84h before _NOW


def _record(
    employee_id: str = "E-1000",
    *,
    department: str = "Office of the CFO",
    division: Optional[str] = "Finance",
    organization_code: Optional[str] = "ORG-FIN-001",
    cost_center: Optional[str] = "CC-1001",
    extracted_at: str = _FRESH,
    resolved_orgpath: Optional[str] = "AGENCY/CFO/FINANCE/",
) -> HRRecord:
    return HRRecord(
        employee_id=employee_id,
        first_name="Alice",
        last_name="Example",
        department=department,
        hire_date="2026-01-15",
        worker_type="FullTimeEmployee",
        location_code="DC-HQ-001",
        country="US",
        employment_status="Active",
        extracted_at=extracted_at,
        division=division,
        organization_code=organization_code,
        cost_center=cost_center,
        resolved_orgpath=resolved_orgpath,
    )


# 1 -------------------------------------------------------------------
def test_clean_record_clears_the_gate() -> None:
    report = evaluate_hr_quarantine([_record()], now=_NOW)
    assert report.held == []
    assert report.evaluated_count == 1
    assert report.cleared_count == 1
    assert report.decisions[0].quarantined is False
    assert report.decisions[0].reasons == ()
    assert report.findings == []


# 2 -------------------------------------------------------------------
def test_stale_snapshot_is_held_as_provenance() -> None:
    report = evaluate_hr_quarantine([_record(extracted_at=_STALE)], now=_NOW)
    assert report.held == ["E-1000"]
    d = report.decisions[0]
    assert QUARANTINE_STALE in d.reasons
    (finding,) = [f for f in d.findings if "GOV-HRQ" in f.error_code]
    assert finding.drift_class == "DRIFT-PROVENANCE"
    assert finding.severity == "P2"
    assert finding.object_type == "HRRecord"


# 3 -------------------------------------------------------------------
def test_fresh_snapshot_is_not_stale() -> None:
    report = evaluate_hr_quarantine([_record(extracted_at=_FRESH)], now=_NOW)
    assert report.held == []


# 4 -------------------------------------------------------------------
def test_null_placement_is_held_as_identity() -> None:
    rec = _record(
        department="",
        division=None,
        organization_code=None,
        cost_center=None,
        resolved_orgpath=None,
    )
    report = evaluate_hr_quarantine([rec], now=_NOW)
    assert report.held == ["E-1000"]
    d = report.decisions[0]
    assert d.reasons == (QUARANTINE_NULL_PLACEMENT,)
    assert d.findings[0].drift_class == "DRIFT-IDENTITY"
    assert d.findings[0].severity == "P1"


# 5 -------------------------------------------------------------------
def test_improbable_delta_top_level_org_change() -> None:
    rec = _record(resolved_orgpath="OTHERAGENCY/OPS/TEAM/")
    report = evaluate_hr_quarantine(
        [rec], now=_NOW, prior_placements={"E-1000": "AGENCY/CFO/FINANCE/"}
    )
    assert report.held == ["E-1000"]
    d = report.decisions[0]
    assert d.reasons == (QUARANTINE_IMPROBABLE_DELTA,)
    assert d.findings[0].drift_class == "DRIFT-SEMANTIC"
    assert "top-level org changed" in d.findings[0].detail


# 6 -------------------------------------------------------------------
def test_improbable_delta_too_many_segments_changed() -> None:
    rec = _record(resolved_orgpath="AGENCY/OPS/LOGISTICS/EAST/")
    report = evaluate_hr_quarantine(
        [rec], now=_NOW, prior_placements={"E-1000": "AGENCY/CFO/FINANCE/BUDGET/"}
    )
    d = report.decisions[0]
    assert QUARANTINE_IMPROBABLE_DELTA in d.reasons
    assert "segments changed" in d.findings[0].detail


# 7 -------------------------------------------------------------------
def test_improbable_delta_depth_jump() -> None:
    # Shares the root, one segment differs at depth 2, but depth jumps by 3.
    rec = _record(resolved_orgpath="AGENCY/CFO/FINANCE/A/B/C/")
    report = evaluate_hr_quarantine(
        [rec],
        now=_NOW,
        prior_placements={"E-1000": "AGENCY/CFO/FINANCE/"},
        config=QuarantineConfig(max_changed_segments=5, max_depth_jump=2),
    )
    d = report.decisions[0]
    assert QUARANTINE_IMPROBABLE_DELTA in d.reasons
    assert "depth jumped" in d.findings[0].detail


# 8 -------------------------------------------------------------------
def test_plausible_move_clears() -> None:
    # Same top-level + division, only the leaf branch changes.
    rec = _record(resolved_orgpath="AGENCY/CFO/ACCOUNTING/")
    report = evaluate_hr_quarantine(
        [rec], now=_NOW, prior_placements={"E-1000": "AGENCY/CFO/FINANCE/"}
    )
    assert report.held == []
    assert report.decisions[0].quarantined is False


# 9 -------------------------------------------------------------------
def test_joiner_without_prior_placement_skips_delta_check() -> None:
    rec = _record(resolved_orgpath="OTHERAGENCY/OPS/TEAM/")
    report = evaluate_hr_quarantine([rec], now=_NOW, prior_placements={})
    assert report.held == []


# 10 ------------------------------------------------------------------
def test_multiple_reasons_stack() -> None:
    # Stale AND an improbable top-level move at once.
    rec = _record(extracted_at=_STALE, resolved_orgpath="OTHER/OPS/TEAM/")
    report = evaluate_hr_quarantine(
        [rec], now=_NOW, prior_placements={"E-1000": "AGENCY/CFO/FINANCE/"}
    )
    d = report.decisions[0]
    assert set(d.reasons) == {QUARANTINE_STALE, QUARANTINE_IMPROBABLE_DELTA}
    assert len(d.findings) == 2
    # Held once even though two reasons tripped.
    assert report.held == ["E-1000"]


# 11 ------------------------------------------------------------------
def test_report_aggregation_and_reason_counts() -> None:
    records = [
        _record("E-1", extracted_at=_STALE),  # stale
        _record("E-2"),  # clean
        _record(
            "E-3",
            department="",
            division=None,
            organization_code=None,
            cost_center=None,
            resolved_orgpath=None,
        ),  # null placement
    ]
    report = evaluate_hr_quarantine(records, now=_NOW)
    assert report.evaluated_count == 3
    assert report.held_count == 2
    assert report.cleared_count == 1
    assert set(report.held) == {"E-1", "E-3"}
    counts = report.reason_counts()
    assert counts[QUARANTINE_STALE] == 1
    assert counts[QUARANTINE_NULL_PLACEMENT] == 1
    assert counts[QUARANTINE_IMPROBABLE_DELTA] == 0


# 12 ------------------------------------------------------------------
def test_trailing_delimiter_tolerated_in_delta() -> None:
    # Prior has no trailing delimiter, current does — must still compare equal.
    rec = _record(resolved_orgpath="AGENCY/CFO/FINANCE/")
    report = evaluate_hr_quarantine(
        [rec], now=_NOW, prior_placements={"E-1000": "AGENCY/CFO/FINANCE"}
    )
    assert report.held == []


# 13 ------------------------------------------------------------------
def test_unparseable_extracted_at_does_not_crash_or_false_positive() -> None:
    report = evaluate_hr_quarantine([_record(extracted_at="not-a-date")], now=_NOW)
    # Cannot compute age → not flagged stale (and no exception).
    assert report.decisions[0].reasons == ()


def test_empty_now_does_not_flag_stale() -> None:
    report = evaluate_hr_quarantine([_record(extracted_at=_STALE)], now="")
    assert QUARANTINE_STALE not in report.decisions[0].reasons


# 14 ------------------------------------------------------------------
def test_config_override_tightens_staleness() -> None:
    # 12h-old record held when the bound is 6h.
    report = evaluate_hr_quarantine(
        [_record(extracted_at=_FRESH)],
        now=_NOW,
        config=QuarantineConfig(max_age_hours=6.0),
    )
    assert report.held == ["E-1000"]


def test_config_override_allows_whole_org_moves() -> None:
    rec = _record(resolved_orgpath="OTHER/OPS/TEAM/")
    report = evaluate_hr_quarantine(
        [rec],
        now=_NOW,
        prior_placements={"E-1000": "AGENCY/CFO/FINANCE/"},
        config=QuarantineConfig(
            top_level_change_is_improbable=False,
            max_changed_segments=99,
            max_depth_jump=99,
        ),
    )
    assert report.held == []


# 15 ------------------------------------------------------------------
def test_error_codes_are_unique_and_sequential() -> None:
    rec = _record(extracted_at=_STALE, resolved_orgpath="OTHER/OPS/TEAM/")
    report = evaluate_hr_quarantine(
        [rec], now=_NOW, prior_placements={"E-1000": "AGENCY/CFO/FINANCE/"}
    )
    codes = [f.error_code for f in report.findings]
    assert codes == ["GOV-HRQ-001", "GOV-HRQ-002"]
    assert len(set(codes)) == len(codes)


# 16 ------------------------------------------------------------------
def test_evaluation_is_deterministic() -> None:
    records = [_record("E-1", extracted_at=_STALE), _record("E-2")]
    r1 = evaluate_hr_quarantine(records, now=_NOW)
    r2 = evaluate_hr_quarantine(records, now=_NOW)
    assert r1.held == r2.held
    assert [f.error_code for f in r1.findings] == [f.error_code for f in r2.findings]
    assert [f.detail for f in r1.findings] == [f.detail for f in r2.findings]


# 17 ------------------------------------------------------------------
def test_public_surface_exports() -> None:
    assert isinstance(QuarantineConfig(), QuarantineConfig)
    decision = QuarantineDecision(employee_id="E", quarantined=False)
    assert decision.reasons == ()
    report = QuarantineReport()
    assert report.evaluated_count == 0
    assert report.reason_counts() == {
        QUARANTINE_STALE: 0,
        QUARANTINE_NULL_PLACEMENT: 0,
        QUARANTINE_IMPROBABLE_DELTA: 0,
    }
