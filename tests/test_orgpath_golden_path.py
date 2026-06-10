"""Anti-rot smoke test for the OrgPath Governance Golden Path.

Runs the four stages of ``examples/orgtree/golden-path/`` end-to-end against the
committed sample data and asserts the structural invariants the walkthrough
(`docs/docs/orgpath-golden-path.qmd`) promises:

  1. assess    — AD identity plane -> per-user facet derivation + findings
  2. inventory — Entra + Arc device plane -> capture status + backfill + snapshot
  3. govern    — one governance pass -> classified drift, dry-run, halt-on-critical
  4. ir bundle — AD survey -> signed bundle (hash+sig) + OSCAL Assessment Results

Why structural, not exact-count, assertions for drift: severity totals track the
canonical codebook (UIAO_151) and move as it evolves. We pin the counts we
*own* (the sample records) and assert the contract for the rest (drift present,
criticals present, halted, dry-run). This catches CLI regressions and
data-file drift without coupling to canon codebook content.

Acceptance: no network, no credentials, runs in <60s, always collected by
`pytest tests/`.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()

_REPO_ROOT = Path(__file__).parent.parent
_GP_DIR = _REPO_ROOT / "examples" / "orgtree" / "golden-path"
_AD_USERS = _GP_DIR / "ad-users.json"
_ENTRA_DEVICES = _GP_DIR / "entra-devices.json"
_ARC_MACHINES = _GP_DIR / "arc-machines.json"
_OWNER_MAP = _GP_DIR / "owner-map.json"
_SURVEY = _REPO_ROOT / "examples" / "orgtree" / "synthetic-forest-export.json"


# ---------------------------------------------------------------------------
# Sample data is committed and parseable
# ---------------------------------------------------------------------------


def test_golden_path_sample_data_present() -> None:
    """All sample-data files the walkthrough references must be committed."""
    for path in (_AD_USERS, _ENTRA_DEVICES, _ARC_MACHINES, _OWNER_MAP, _SURVEY):
        assert path.exists(), f"golden-path sample file missing: {path}"
        json.loads(path.read_text(encoding="utf-8"))  # parses
    assert (_GP_DIR / "run.sh").exists(), "run.sh driver script missing"
    assert (_GP_DIR / "README.md").exists(), "golden-path README missing"


# ---------------------------------------------------------------------------
# Stage 1 — assess
# ---------------------------------------------------------------------------


def test_stage1_assess(tmp_path: Path) -> None:
    out = tmp_path / "assignments.json"
    result = runner.invoke(app, ["orgtree", "assess", "--from-export", str(_AD_USERS), "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    assert "OrgPath assessment" in result.stdout

    data: list[dict[str, Any]] = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 5, "sample ad-users.json must drive exactly 5 users"

    by_id = {r["target_id"]: r for r in data}
    alice = next(r for k, r in by_id.items() if "alice.eng" in k)
    # Clean mapping derives known codebook values.
    assert alice["facet_values"]["department"] == "Engineering"
    assert alice["facet_values"]["region"] == "EASTUS"
    assert alice["target_type"] == "user"

    # carol.unknown seeds unmapped values -> must produce findings.
    carol = next(r for k, r in by_id.items() if "carol.unknown" in k)
    assert carol["findings"], "carol.unknown should surface mapping findings"

    # Aggregate: facets derived and findings both present across the set.
    total_facets = sum(len(r["facet_values"]) for r in data)
    total_findings = sum(len(r["findings"]) for r in data)
    assert total_facets > 0 and total_findings > 0


# ---------------------------------------------------------------------------
# Stage 2 — inventory
# ---------------------------------------------------------------------------


def test_stage2_inventory(tmp_path: Path) -> None:
    snapshot = tmp_path / "inventory-snapshot.json"
    worklist = tmp_path / "worklist.json"
    result = runner.invoke(
        app,
        [
            "orgtree",
            "inventory",
            "--devices-export",
            str(_ENTRA_DEVICES),
            "--machines-export",
            str(_ARC_MACHINES),
            "--owner-map",
            str(_OWNER_MAP),
            "--snapshot-out",
            str(snapshot),
            "--worklist-out",
            str(worklist),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert snapshot.exists() and worklist.exists()

    summary = json.loads(worklist.read_text(encoding="utf-8"))["summary"]
    # Known answers from the committed device spread (4 Entra + 2 Arc).
    assert summary["total"] == 6
    assert summary["entra"] == 4
    assert summary["arm"] == 2
    assert summary["partial"] == 3
    assert summary["absent"] == 3
    assert summary["needs_backfill"] == 6
    # WS-HR-03's owner-map entry covers every missing facet -> exactly one resolved.
    assert summary["resolved"] == 1
    assert summary["unresolved"] == 5

    # Snapshot is govern-compatible: device principals with current slots only.
    snap = json.loads(snapshot.read_text(encoding="utf-8"))
    assert "principals" in snap and len(snap["principals"]) == 6
    assert all(p["principal_type"] == "device" for p in snap["principals"])


# ---------------------------------------------------------------------------
# Stage 3 — govern
# ---------------------------------------------------------------------------


def test_stage3_govern(tmp_path: Path) -> None:
    # Produce the snapshot via stage 2 first (chained, as the walkthrough does).
    snapshot = tmp_path / "inventory-snapshot.json"
    runner.invoke(
        app,
        [
            "orgtree",
            "inventory",
            "--devices-export",
            str(_ENTRA_DEVICES),
            "--machines-export",
            str(_ARC_MACHINES),
            "--owner-map",
            str(_OWNER_MAP),
            "--snapshot-out",
            str(snapshot),
        ],
    )
    assert snapshot.exists()

    report_out = tmp_path / "drift-report.json"
    result = runner.invoke(
        app,
        ["orgtree", "govern", str(snapshot), "--detection-only", "--out", str(report_out)],
    )
    assert result.exit_code == 0, result.stdout
    assert "OrgPath governance pass" in result.stdout

    report = json.loads(report_out.read_text(encoding="utf-8"))
    # The contract (not brittle totals): drift present, a critical present,
    # halted on critical, dry-run, and detection-only plans nothing.
    assert report["drift_count"] > 0
    assert report["severity_counts"].get("P1", 0) > 0
    assert report["halted"] is True
    assert report["dry_run"] is True
    assert report["planned_count"] == 0
    assert len(report["findings"]) == report["drift_count"]
    assert len(report["events"]) >= report["drift_count"]


# ---------------------------------------------------------------------------
# Stage 4 — signed bundle + OSCAL
# ---------------------------------------------------------------------------


def test_stage4_signed_bundle_and_oscal(tmp_path: Path) -> None:
    # The OSCAL emitter imports trestle at module load; it ships in [api] and is
    # present in CI. Skip cleanly on a --no-deps local install without it.
    import pytest

    pytest.importorskip("trestle.oscal.assessment_results")

    bundle_dir = tmp_path / "bundle"
    oscal_dir = tmp_path / "oscal"
    env_ci = {k: v for k, v in os.environ.items() if k != "UIAO_BUNDLE_HMAC_KEY"}

    result = runner.invoke(
        app,
        [
            "ir",
            "orgtree-readiness-bundle",
            str(_SURVEY),
            "--out-dir",
            str(bundle_dir),
            "--oscal-out",
            str(oscal_dir),
            "--insecure-dev-key",
        ],
        env=env_ci,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.stdout

    bundle_json = bundle_dir / "bundle.json"
    bundle_hash = (bundle_dir / "bundle.hash").read_text().strip()
    bundle_sig = (bundle_dir / "bundle.sig").read_text().strip()

    assert bundle_json.exists()
    assert len(bundle_hash) == 64 and all(c in "0123456789abcdef" for c in bundle_hash)
    assert len(bundle_sig) == 64 and all(c in "0123456789abcdef" for c in bundle_sig)

    bundle_doc = json.loads(bundle_json.read_text(encoding="utf-8"))
    assert bundle_doc["provenance"]["signature"] == bundle_sig

    oscal_file = oscal_dir / "orgtree-evidence.json"
    assert oscal_file.exists(), "OSCAL Assessment Results not emitted"
    oscal_doc = json.loads(oscal_file.read_text(encoding="utf-8"))
    assert "assessment-results" in oscal_doc
    assert len(oscal_doc["assessment-results"]["results"]) >= 1


# ---------------------------------------------------------------------------
# End-to-end runtime guard
# ---------------------------------------------------------------------------


def test_golden_path_runtime_under_60s(tmp_path: Path) -> None:
    """The four CLI stages together must complete well under 60s (no network)."""
    start = time.monotonic()

    runner.invoke(app, ["orgtree", "assess", "--from-export", str(_AD_USERS), "--out", str(tmp_path / "a.json")])
    snap = tmp_path / "snap.json"
    runner.invoke(
        app,
        [
            "orgtree",
            "inventory",
            "--devices-export",
            str(_ENTRA_DEVICES),
            "--machines-export",
            str(_ARC_MACHINES),
            "--owner-map",
            str(_OWNER_MAP),
            "--snapshot-out",
            str(snap),
        ],
    )
    runner.invoke(app, ["orgtree", "govern", str(snap), "--detection-only"])

    elapsed = time.monotonic() - start
    assert elapsed < 60.0, f"golden path stages 1-3 took {elapsed:.1f}s — expected <60s"
