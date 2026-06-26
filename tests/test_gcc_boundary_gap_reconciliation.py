"""Reconciliation between the operational probe register and the
signal-level telemetry-gaps SSOT.

The two registers are intentionally separate (different altitudes), but where
``gcc-boundary-gap-registry.yaml`` declares ``telemetry_gap_refs`` those refs
must resolve to real rows in ``gcc-moderate-telemetry-gaps.yaml`` and the probe
must surface the B.1.3 in-boundary rebuild verdict for them.
"""

from pathlib import Path

import yaml

from uiao.adapters.modernization.gcc_boundary_probe.probe import (
    DEFAULT_TELEMETRY_GAPS_PATH,
    _aggregate_rebuild,
    load_rebuild_verdicts,
)

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "src/uiao/canon/gcc-boundary-gap-registry.yaml"


def _registry_refs() -> set[str]:
    data = yaml.safe_load(REGISTRY.read_text())
    refs: set[str] = set()
    for gap in data.get("gaps", []):
        refs.update(gap.get("telemetry_gap_refs", []) or [])
    return refs


def test_telemetry_gap_refs_resolve_to_ssot_ids() -> None:
    """Every telemetry_gap_ref in the probe registry must exist in the SSOT."""
    verdicts = load_rebuild_verdicts(DEFAULT_TELEMETRY_GAPS_PATH)
    assert verdicts, "telemetry-gaps SSOT should load rebuild verdicts"
    refs = _registry_refs()
    assert refs, "registry should declare at least one telemetry_gap_ref"
    unknown = refs - set(verdicts)
    assert not unknown, f"telemetry_gap_refs not found in SSOT: {sorted(unknown)}"


def test_load_rebuild_verdicts_shape() -> None:
    verdicts = load_rebuild_verdicts(DEFAULT_TELEMETRY_GAPS_PATH)
    row = verdicts["inr-realtime-path-metrics"]
    assert row["verdict"] == "partial-substitute"
    assert row["residual"]


def test_aggregate_rebuild_uniform_mixed_empty() -> None:
    verdicts = {
        "a": {"verdict": "partial-substitute", "residual": "", "path": ""},
        "b": {"verdict": "partial-substitute", "residual": "", "path": ""},
        "c": {"verdict": "fixes", "residual": "", "path": ""},
    }
    verdict, detail = _aggregate_rebuild(["a", "b"], verdicts)
    assert verdict == "partial-substitute"
    assert "2 telemetry-gap row(s)" in detail

    mixed, _ = _aggregate_rebuild(["a", "c"], verdicts)
    assert mixed == "mixed"

    empty_verdict, empty_detail = _aggregate_rebuild([], verdicts)
    assert empty_verdict == ""
    assert empty_detail == ""


def test_missing_ssot_degrades_gracefully(tmp_path: Path) -> None:
    assert load_rebuild_verdicts(tmp_path / "nope.yaml") == {}
