"""Tests for the DRIFT-SEMANTIC freshness evaluator (roadmap §1.1).

Scope:
    - ``load_adapter_windows()`` pulls ``freshness-window-hours`` from
      canonical adapter registries.
    - ``resolve_policy()`` applies the registry → family-default → global
      fallback chain.
    - ``evaluate_evidence_payload()`` produces correct status + severity
      for fresh / stale-soon / stale / missing-timestamp / future-dated
      inputs.
    - ``evaluate_scheduler_run()`` closes the end-to-end loop from a
      scheduler run directory (UIAO_100 output) to DRIFT-SEMANTIC
      findings (UIAO_016).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from uiao.freshness import (
    DEFAULT_WINDOW_HOURS,
    DEFAULT_WINDOW_HOURS_BY_FAMILY,
    DRIFT_TYPE,
    AdapterFreshnessPolicy,
    FreshnessFinding,
    drift_semantic_findings,
    evaluate_evidence_payload,
    evaluate_scheduler_run,
    load_adapter_windows,
    resolve_policy,
    summarize,
    write_findings,
)


_NOW = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_registry(path: Path, adapters: list[dict[str, Any]]) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema-version": "1.0.0",
                "registry-class": "modernization",
                "updated": "2026-04-23",
                "adapters": adapters,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_scheduler_run(
    root: Path,
    adapters: list[dict[str, Any]],
    *,
    run_id: str = "schedrun-20260423T190000Z-abcd",
) -> Path:
    run_dir = root / run_id
    adapters_dir = run_dir / "adapters"
    adapters_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "schema_version": "1.0.0"}),
        encoding="utf-8",
    )
    for spec in adapters:
        adapter_id = spec["id"]
        d = adapters_dir / adapter_id
        d.mkdir()
        payload = {
            "ksi_id": spec.get("ksi_id", f"ksi:{adapter_id}"),
            "source": adapter_id,
            "timestamp": spec.get("timestamp", "2026-04-23T18:00:00+00:00"),
            "provenance": {"adapter_id": adapter_id, "hash": "a" * 64},
        }
        if spec.get("no_timestamp"):
            payload.pop("timestamp", None)
        (d / "evidence.json").write_text(json.dumps(payload), encoding="utf-8")
    return run_dir


# ---------------------------------------------------------------------------
# load_adapter_windows
# ---------------------------------------------------------------------------


def test_load_adapter_windows_collects_declared_values(tmp_path):
    reg = _write_registry(
        tmp_path / "modernization-registry.yaml",
        [
            {"id": "entra-id", "status": "active", "freshness-window-hours": 24},
            {"id": "quiet", "status": "active"},  # no declaration
            {"id": "bad", "status": "active", "freshness-window-hours": "nope"},  # wrong type
        ],
    )
    windows = load_adapter_windows([reg])
    assert windows == {"entra-id": 24}


def test_load_adapter_windows_merges_across_registries(tmp_path):
    mod = _write_registry(
        tmp_path / "mod.yaml",
        [{"id": "entra-id", "status": "active", "freshness-window-hours": 24}],
    )
    conf = _write_registry(
        tmp_path / "conf.yaml",
        [{"id": "scubagear", "status": "active", "freshness-window-hours": 168}],
    )
    windows = load_adapter_windows([mod, conf])
    assert windows == {"entra-id": 24, "scubagear": 168}


def test_load_adapter_windows_later_registry_overrides(tmp_path):
    a = _write_registry(
        tmp_path / "a.yaml",
        [{"id": "entra-id", "status": "active", "freshness-window-hours": 24}],
    )
    b = _write_registry(
        tmp_path / "b.yaml",
        [{"id": "entra-id", "status": "active", "freshness-window-hours": 6}],
    )
    assert load_adapter_windows([a, b]) == {"entra-id": 6}


def test_load_adapter_windows_missing_registry_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_adapter_windows([tmp_path / "nope.yaml"])


def test_canonical_registries_include_freshness_for_shipped_adapters():
    """Smoke-guard: the two adapters we seeded in this PR (entra-id in
    modernization-registry, scubagear in adapter-registry) must declare
    ``freshness-window-hours``. Blocks accidental removal."""
    repo_root = Path(__file__).resolve().parent.parent
    windows = load_adapter_windows(
        [
            repo_root / "src" / "uiao" / "canon" / "modernization-registry.yaml",
            repo_root / "src" / "uiao" / "canon" / "adapter-registry.yaml",
        ]
    )
    assert "entra-id" in windows
    assert "scubagear" in windows
    assert windows["entra-id"] == 24
    assert windows["scubagear"] == 168


# ---------------------------------------------------------------------------
# resolve_policy
# ---------------------------------------------------------------------------


def test_resolve_policy_prefers_registry_value():
    p = resolve_policy("entra-id", windows={"entra-id": 24}, ksi_id="ksi:IA-2")
    assert p == AdapterFreshnessPolicy(adapter_id="entra-id", window_hours=24, source="registry", family_hint=None)


def test_resolve_policy_falls_back_to_family_default():
    p = resolve_policy("unknown", windows={}, ksi_id="ksi:AU-12")
    assert p.source == "family-default"
    assert p.family_hint == "AU"
    assert p.window_hours == DEFAULT_WINDOW_HOURS_BY_FAMILY["AU"]


def test_resolve_policy_falls_back_to_global_default():
    p = resolve_policy("unknown", windows={}, ksi_id="ksi:free-form")
    assert p.source == "global-default"
    assert p.window_hours == DEFAULT_WINDOW_HOURS


def test_resolve_policy_registry_wins_even_with_family_available():
    p = resolve_policy("entra-id", windows={"entra-id": 1}, ksi_id="ksi:IA-2")
    assert p.source == "registry"
    assert p.window_hours == 1


# ---------------------------------------------------------------------------
# evaluate_evidence_payload — classification + severity
# ---------------------------------------------------------------------------


def _policy(window: int = 24) -> AdapterFreshnessPolicy:
    return AdapterFreshnessPolicy(adapter_id="probe", window_hours=window, source="registry")


def test_fresh_evidence_classifies_as_fresh_and_P5():
    ts = (_NOW - timedelta(hours=2)).isoformat()
    f = evaluate_evidence_payload({"timestamp": ts}, adapter_id="probe", run_id="r1", policy=_policy(24), now=_NOW)
    assert f.status == "fresh"
    assert f.severity == "P5"
    assert 1.99 <= f.age_hours <= 2.01


def test_stale_soon_classifies_at_P3():
    # Between 1x and 1.5x window.
    ts = (_NOW - timedelta(hours=30)).isoformat()  # 30h vs 24h window = 1.25x
    f = evaluate_evidence_payload({"timestamp": ts}, adapter_id="probe", run_id="r1", policy=_policy(24), now=_NOW)
    assert f.status == "stale-soon"
    assert f.severity == "P3"


def test_stale_classifies_at_P2():
    ts = (_NOW - timedelta(hours=60)).isoformat()  # 60h vs 24h window = 2.5x
    f = evaluate_evidence_payload({"timestamp": ts}, adapter_id="probe", run_id="r1", policy=_policy(24), now=_NOW)
    assert f.status == "stale"
    assert f.severity == "P2"
    assert f.drift_type == DRIFT_TYPE


def test_missing_timestamp_emits_P1_with_reason():
    f = evaluate_evidence_payload({}, adapter_id="probe", run_id="r1", policy=_policy(24), now=_NOW)
    assert f.status == "missing-timestamp"
    assert f.severity == "P1"
    assert f.age_hours == float("inf")
    assert "no timestamp" in f.details["reason"]


def test_future_dated_evidence_recorded_as_fresh_with_anomaly():
    ts = (_NOW + timedelta(hours=1)).isoformat()
    f = evaluate_evidence_payload({"timestamp": ts}, adapter_id="probe", run_id="r1", policy=_policy(24), now=_NOW)
    assert f.status == "fresh"
    assert "anomaly" in f.details
    assert f.age_hours == 0.0


def test_finding_to_dict_is_json_serializable():
    ts = (_NOW - timedelta(hours=60)).isoformat()
    f = evaluate_evidence_payload({"timestamp": ts}, adapter_id="probe", run_id="r1", policy=_policy(24), now=_NOW)
    roundtrip = json.loads(json.dumps(f.to_dict(), default=str))
    assert roundtrip["status"] == "stale"
    assert roundtrip["severity"] == "P2"
    assert roundtrip["drift_type"] == DRIFT_TYPE


# ---------------------------------------------------------------------------
# evaluate_scheduler_run — end-to-end against a fake run directory
# ---------------------------------------------------------------------------


def test_evaluate_scheduler_run_uses_registry_window(tmp_path):
    """Adapter with registry-declared 2h window becomes stale fast."""
    reg = _write_registry(
        tmp_path / "registry.yaml",
        [{"id": "fast", "status": "active", "freshness-window-hours": 2}],
    )
    run_dir = _write_scheduler_run(
        tmp_path,
        [{"id": "fast", "ksi_id": "ksi:AC-2", "timestamp": (_NOW - timedelta(hours=10)).isoformat()}],
    )
    findings = evaluate_scheduler_run(run_dir, registries=[reg], now=_NOW)
    assert len(findings) == 1
    assert findings[0].status == "stale"
    assert findings[0].severity == "P2"
    assert findings[0].window_hours == 2
    assert findings[0].policy_source == "registry"


def test_evaluate_scheduler_run_falls_back_to_family_default(tmp_path):
    """Adapter without registry declaration picks family default from KSI."""
    reg = _write_registry(
        tmp_path / "registry.yaml",
        [{"id": "unknown-adapter", "status": "active"}],
    )
    # IA family default = 24*30 = 720h. Evidence 30h old → fresh.
    run_dir = _write_scheduler_run(
        tmp_path,
        [
            {
                "id": "unknown-adapter",
                "ksi_id": "ksi:IA-2",
                "timestamp": (_NOW - timedelta(hours=30)).isoformat(),
            }
        ],
    )
    findings = evaluate_scheduler_run(run_dir, registries=[reg], now=_NOW)
    assert findings[0].status == "fresh"
    assert findings[0].policy_source == "family-default"


def test_evaluate_scheduler_run_multi_adapter(tmp_path):
    reg = _write_registry(
        tmp_path / "registry.yaml",
        [
            {"id": "fast", "status": "active", "freshness-window-hours": 2},
            {"id": "slow", "status": "active", "freshness-window-hours": 168},
        ],
    )
    run_dir = _write_scheduler_run(
        tmp_path,
        [
            {"id": "fast", "timestamp": (_NOW - timedelta(hours=10)).isoformat()},  # stale
            {"id": "slow", "timestamp": (_NOW - timedelta(hours=10)).isoformat()},  # fresh
            {"id": "missing", "no_timestamp": True},  # missing-timestamp
        ],
    )
    findings = evaluate_scheduler_run(run_dir, registries=[reg], now=_NOW)
    by_id = {f.adapter_id: f for f in findings}
    assert by_id["fast"].status == "stale"
    assert by_id["slow"].status == "fresh"
    assert by_id["missing"].status == "missing-timestamp"


def test_evaluate_scheduler_run_missing_dir_raises(tmp_path):
    reg = _write_registry(tmp_path / "r.yaml", [])
    with pytest.raises(FileNotFoundError):
        evaluate_scheduler_run(tmp_path / "nope", registries=[reg])


def test_evaluate_scheduler_run_empty_adapters_root_returns_empty(tmp_path):
    run_dir = tmp_path / "empty-run"
    (run_dir / "adapters").mkdir(parents=True)
    reg = _write_registry(tmp_path / "r.yaml", [])
    assert evaluate_scheduler_run(run_dir, registries=[reg]) == []


def test_evaluate_scheduler_run_skips_malformed_evidence_json(tmp_path):
    reg = _write_registry(tmp_path / "r.yaml", [])
    run_dir = tmp_path / "run"
    adapter_dir = run_dir / "adapters" / "broken"
    adapter_dir.mkdir(parents=True)
    (adapter_dir / "evidence.json").write_text("{not-json", encoding="utf-8")
    assert evaluate_scheduler_run(run_dir, registries=[reg], now=_NOW) == []


# ---------------------------------------------------------------------------
# Filter + summary + persistence
# ---------------------------------------------------------------------------


def test_drift_semantic_findings_filters_out_fresh():
    def _fin(status: str, sev: str) -> FreshnessFinding:
        return FreshnessFinding(
            adapter_id="a",
            run_id="r",
            drift_type=DRIFT_TYPE,
            severity=sev,
            age_hours=1.0,
            window_hours=2,
            status=status,
            evidence_timestamp=None,
            evaluated_at=_NOW.isoformat(),
            policy_source="registry",
        )

    fs = [
        _fin("fresh", "P5"),
        _fin("stale-soon", "P3"),
        _fin("stale", "P2"),
        _fin("missing-timestamp", "P1"),
    ]
    routed = drift_semantic_findings(fs)
    assert [f.status for f in routed] == ["stale-soon", "stale", "missing-timestamp"]


def test_summarize_counts_status_and_severity():
    def _fin(status: str, sev: str) -> FreshnessFinding:
        return FreshnessFinding(
            adapter_id="a",
            run_id="r",
            drift_type=DRIFT_TYPE,
            severity=sev,
            age_hours=0.0,
            window_hours=2,
            status=status,
            evidence_timestamp=None,
            evaluated_at=_NOW.isoformat(),
            policy_source="registry",
        )

    fs = [_fin("fresh", "P5"), _fin("fresh", "P5"), _fin("stale", "P2")]
    s = summarize(fs)
    assert s["total"] == 3
    assert s["by_status"] == {"fresh": 2, "stale": 1}
    assert s["by_severity"] == {"P2": 1, "P5": 2}


def test_write_findings_roundtrips_through_json(tmp_path):
    reg = _write_registry(
        tmp_path / "registry.yaml",
        [{"id": "fast", "status": "active", "freshness-window-hours": 2}],
    )
    run_dir = _write_scheduler_run(
        tmp_path,
        [{"id": "fast", "timestamp": (_NOW - timedelta(hours=10)).isoformat()}],
    )
    findings = evaluate_scheduler_run(run_dir, registries=[reg], now=_NOW)
    out = write_findings(findings, tmp_path / "out" / "drift-semantic.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0.0"
    assert data["drift_type"] == DRIFT_TYPE
    assert data["summary"]["by_severity"]["P2"] == 1
    assert len(data["findings"]) == 1
    assert data["findings"][0]["adapter_id"] == "fast"


# ---------------------------------------------------------------------------
# End-to-end: scheduler run → DRIFT-SEMANTIC loop
# ---------------------------------------------------------------------------


def test_e2e_scheduler_run_to_drift_semantic_findings(tmp_path):
    reg = _write_registry(
        tmp_path / "registry.yaml",
        [
            {"id": "entra-id", "status": "active", "freshness-window-hours": 24},
            {"id": "scubagear", "status": "active", "freshness-window-hours": 168},
        ],
    )
    # entra-id evidence 48h old vs 24h window → stale (P2)
    # scubagear evidence 48h old vs 168h window → fresh
    run_dir = _write_scheduler_run(
        tmp_path,
        [
            {"id": "entra-id", "timestamp": (_NOW - timedelta(hours=48)).isoformat()},
            {"id": "scubagear", "timestamp": (_NOW - timedelta(hours=48)).isoformat()},
        ],
    )
    findings = evaluate_scheduler_run(run_dir, registries=[reg], now=_NOW)
    routed = drift_semantic_findings(findings)
    assert len(findings) == 2
    assert len(routed) == 1
    assert routed[0].adapter_id == "entra-id"
    assert routed[0].severity == "P2"
    assert routed[0].drift_type == DRIFT_TYPE
    # Ensure summary shape is usable by downstream consumers.
    s = summarize(findings)
    assert s["by_status"] == {"fresh": 1, "stale": 1}
