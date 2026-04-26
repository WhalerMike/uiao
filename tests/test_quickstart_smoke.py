"""Smoke test: the 10-minute quickstart runs end-to-end.

Exercises the exact commands published in `docs/docs/quickstart.md`
against the shipped fixture at `examples/quickstart/scuba-normalized.json`.
If this test fails, the quickstart docs have rotted and new contributors
will hit the rot on their first five minutes with the repo.

Covered steps from the quickstart:
  2. uiao ir scuba-transform <fixture>
  3. uiao ir auditor-bundle <fixture> --out-dir <tmp>
  5. uiao ir diff <fixture> <fixture-with-edits>
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()

FIXTURE = Path("examples/quickstart/scuba-normalized.json")


def test_fixture_exists_and_is_valid_json() -> None:
    """The quickstart fixture must ship with the repo and parse as JSON."""
    assert FIXTURE.exists(), f"quickstart fixture missing at {FIXTURE}"
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert "ksi_results" in payload
    assert len(payload["ksi_results"]) >= 1


def test_quickstart_step2_scuba_transform() -> None:
    """Step 2 of quickstart: uiao ir scuba-transform runs and reports KSI counts."""
    result = runner.invoke(app, ["ir", "scuba-transform", str(FIXTURE)])
    assert result.exit_code == 0, f"stdout={result.stdout}"
    assert "SCuBA Transform" in result.stdout
    assert "Total KSI results" in result.stdout


def test_quickstart_step3_auditor_bundle(tmp_path: Path) -> None:
    """Step 3 of quickstart: uiao ir auditor-bundle writes the six expected artifacts."""
    out_dir = tmp_path / "uiao-quickstart"
    result = runner.invoke(
        app,
        ["ir", "auditor-bundle", str(FIXTURE), "--out-dir", str(out_dir)],
    )
    assert result.exit_code == 0, f"stdout={result.stdout}"
    assert out_dir.is_dir()

    expected = {
        "evidence-bundle.json",
        "governance-report.md",
        "lineage.json",
        "manifest.json",
        "poam.json",
        "ssp-narrative.md",
    }
    actual = {p.name for p in out_dir.iterdir()}
    missing = expected - actual
    assert not missing, f"bundle missing: {missing}"


def test_quickstart_step5_ir_diff(tmp_path: Path) -> None:
    """Step 5 of quickstart: uiao ir diff compares two SCuBA runs."""
    run_a = FIXTURE
    # Construct run B by flipping KSI-IA-02 FAIL -> PASS.
    payload = json.loads(run_a.read_text(encoding="utf-8"))
    for ksi in payload["ksi_results"]:
        if ksi.get("ksi_id") == "KSI-IA-02":
            ksi["status"] = "PASS"
    run_b = tmp_path / "run-b.json"
    run_b.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(app, ["ir", "diff", str(run_a), str(run_b)])
    assert result.exit_code == 0, f"stdout={result.stdout}"
    # A diff output should contain either KSI-IA-02 or a status-count row;
    # the exact format is diff-engine-specific, so we check for both.
    combined = result.stdout.lower()
    assert "ksi-ia-02" in combined or "status" in combined
