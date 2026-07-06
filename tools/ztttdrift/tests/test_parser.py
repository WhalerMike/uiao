"""Parser: strict ztttdrift-input/1.0 contract validation and register hygiene."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ztttdrift import Stage, load_exceptions, load_run, parse_run
from ztttdrift.parser import ParseError

FIXTURES = Path(__file__).parent / "fixtures"


def _payload(**overrides) -> dict:
    base = {
        "schema": "ztttdrift-input/1.0",
        "assessed_at": "2026-07-01",
        "source": "unit test",
        "items": [{"item_id": "ZT.ID.01", "pillar": "Identity", "stage": "initial"}],
    }
    base.update(overrides)
    return base


def test_load_run_ok() -> None:
    run = load_run(FIXTURES / "run_current.json")
    assert run.assessed_at == date(2026, 7, 1)
    assert "ZTMM" in run.source
    assert len(run.items) == 8
    assert run.by_id()["ZT.ID.01"].stage is Stage.INITIAL
    assert run.by_id()["ZT.DT.01"].target_stage is Stage.OPTIMAL


def test_stage_ordering_is_ztmm_v2() -> None:
    assert [s.rank for s in (Stage.TRADITIONAL, Stage.INITIAL, Stage.ADVANCED, Stage.OPTIMAL)] == [0, 1, 2, 3]
    assert Stage.TRADITIONAL.rank < Stage.INITIAL.rank < Stage.ADVANCED.rank < Stage.OPTIMAL.rank


def test_pillar_is_normalized_case_insensitively() -> None:
    run = parse_run(
        _payload(items=[{"item_id": "ZT.AP.09", "pillar": "applications and workloads", "stage": "OPTIMAL"}])
    )
    assert run.items[0].pillar == "Applications and Workloads"
    assert run.items[0].stage is Stage.OPTIMAL


def test_unknown_schema_rejected() -> None:
    with pytest.raises(ParseError, match="unsupported input schema"):
        parse_run(_payload(schema="ztttdrift-input/2.0"))
    with pytest.raises(ParseError, match="unsupported input schema"):
        parse_run(_payload(schema=None))


def test_unknown_stage_rejected() -> None:
    with pytest.raises(ParseError, match="unknown maturity stage"):
        parse_run(_payload(items=[{"item_id": "X", "pillar": "Identity", "stage": "pass"}]))


def test_unknown_target_stage_rejected() -> None:
    with pytest.raises(ParseError, match="unknown maturity stage"):
        parse_run(_payload(items=[{"item_id": "X", "pillar": "Identity", "stage": "initial", "target_stage": "gold"}]))


def test_unknown_pillar_rejected() -> None:
    with pytest.raises(ParseError, match="unknown pillar"):
        parse_run(_payload(items=[{"item_id": "X", "pillar": "Governance", "stage": "initial"}]))


def test_bad_assessed_at_rejected() -> None:
    with pytest.raises(ParseError, match="assessed_at"):
        parse_run(_payload(assessed_at="07/01/2026"))


def test_missing_item_id_rejected() -> None:
    with pytest.raises(ParseError, match="item_id"):
        parse_run(_payload(items=[{"pillar": "Identity", "stage": "initial"}]))


def test_duplicate_item_id_rejected() -> None:
    dup = {"item_id": "ZT.ID.01", "pillar": "Identity", "stage": "initial"}
    with pytest.raises(ParseError, match="duplicate item_id"):
        parse_run(_payload(items=[dup, dict(dup)]))


def test_items_must_be_a_list() -> None:
    with pytest.raises(ParseError, match="'items' must be a list"):
        parse_run(_payload(items={"ZT.ID.01": {}}))


def test_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match="not found"):
        load_run(tmp_path / "nope.json")


def test_load_exceptions_ok() -> None:
    acc = load_exceptions(FIXTURES / "exceptions.json")
    assert {a.item_id for a in acc} == {"ZT.NW.01", "ZT.DV.01", "ZT.AP.01"}


def test_duplicate_acceptance_rejected(tmp_path: Path) -> None:
    p = tmp_path / "dupes.json"
    p.write_text(
        '[{"item_id":"X","justification":"a","approved_by":"b","approved_date":"2026-01-01","expiry_date":"2026-12-31"},'
        '{"item_id":"X","justification":"c","approved_by":"d","approved_date":"2026-01-01","expiry_date":"2026-12-31"}]'
    )
    with pytest.raises(ParseError, match="duplicate"):
        load_exceptions(p)


def test_malformed_acceptance_date_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        '[{"item_id":"X","approved_date":"nope","expiry_date":"2026-12-31","justification":"j","approved_by":"a"}]'
    )
    with pytest.raises(ParseError, match="malformed date"):
        load_exceptions(p)
