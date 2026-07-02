"""Parser: real ScubaGear shapes, field aliases, and register hygiene."""

from __future__ import annotations

from pathlib import Path

import pytest

from scubadrift import Result, load_exceptions, load_run, parse_run
from scubadrift.parser import ParseError

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_run_flat_shape() -> None:
    run = load_run(FIXTURES / "run_current.json")
    assert run.product == "AAD"
    assert run.scubagear_version == "1.5.1"
    assert len(run.results) == 6
    assert run.by_id()["MS.AAD.1.1v1"].result is Result.FAIL
    assert run.by_id()["MS.AAD.2.1v1"].result is Result.PASS


def test_version_suffix_is_preserved() -> None:
    # SCuBA versions the same logical policy v1/v2/v3; the suffix is part of the key.
    run = load_run(FIXTURES / "run_current.json")
    assert "MS.AAD.1.1v1" in run.by_id()
    assert "MS.AAD.1.1" not in run.by_id()


def test_full_scubaresults_shape_with_product_map_and_aliases() -> None:
    payload = {
        "MetaData": {"ProductName": "EXO", "ScubaGearVersion": "1.6.0"},
        "Results": {
            "EXO": [
                {
                    "Control ID": "MS.EXO.1.1v1",
                    "Requirement": "No auto-forward.",
                    "Result": "Fail",
                    "Criticality": "Shall",
                }
            ]
        },
    }
    run = parse_run(payload)
    assert run.product == "EXO"
    assert run.results[0].policy_id == "MS.EXO.1.1v1"
    assert run.results[0].description == "No auto-forward."
    assert run.results[0].result is Result.FAIL


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Pass", Result.PASS),
        ("fail", Result.FAIL),
        ("Warning", Result.WARNING),
        ("Manual", Result.MANUAL),
        ("N/A", Result.NA),
        ("Omitted", Result.OMITTED),
        ("weird", Result.UNKNOWN),
    ],
)
def test_result_parse(raw: str, expected: Result) -> None:
    assert Result.parse(raw) is expected


def test_load_exceptions_ok() -> None:
    acc = load_exceptions(FIXTURES / "exceptions.json")
    assert {a.policy_id for a in acc} == {"MS.AAD.3.1v1", "MS.AAD.5.4v1", "MS.AAD.7.1v1"}


def test_duplicate_acceptance_rejected(tmp_path: Path) -> None:
    p = tmp_path / "dupes.json"
    p.write_text(
        '[{"policy_id":"X","justification":"a","approved_by":"b","approved_date":"2026-01-01","expiry_date":"2026-12-31"},'
        '{"policy_id":"X","justification":"c","approved_by":"d","approved_date":"2026-01-01","expiry_date":"2026-12-31"}]'
    )
    with pytest.raises(ParseError, match="duplicate"):
        load_exceptions(p)


def test_malformed_date_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        '[{"policy_id":"X","approved_date":"nope","expiry_date":"2026-12-31","justification":"j","approved_by":"a"}]'
    )
    with pytest.raises(ParseError, match="malformed date"):
        load_exceptions(p)


def test_missing_results_key_rejected() -> None:
    with pytest.raises(ParseError, match="no 'results'"):
        parse_run({"metadata": {}})


def test_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match="not found"):
        load_run(tmp_path / "nope.json")
