"""Unit tests for the UIAO_100 OrchestratorScheduler (roadmap §1.3).

Scope: pure scheduler logic — registry loading, filter, adapter dispatch,
retry, persistence, manifest, drift aggregation. Real adapter instantiation
(Microsoft Graph, SCuBA, etc.) is out of scope; mock adapters exercise the
contract.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from uiao.adapters.database_base import DriftReport, EvidenceObject
from uiao.orchestrator.scheduler import (
    MANIFEST_SCHEMA_VERSION,
    AdapterRun,
    OrchestratorScheduler,
    ScheduleRunManifest,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _registry(tmp_path: Path, adapters: list[dict]) -> Path:
    path = tmp_path / "adapter-registry.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema-version": "1.0.0",
                "registry-class": "conformance",
                "updated": "2026-04-23",
                "adapters": adapters,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _evidence(ksi_id: str = "ksi:probe") -> EvidenceObject:
    return EvidenceObject(
        ksi_id=ksi_id,
        source="mock-adapter",
        timestamp=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
        raw_data={"probe": True},
        normalized_data={"probe": True},
        provenance={"adapter_id": "mock-adapter", "hash": "deadbeef" * 8},
        freshness_valid=True,
    )


def _drift(severity: str = "info") -> DriftReport:
    return DriftReport(
        drift_type="schema",
        severity=severity,
        first_observed=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
        last_observed=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
        details={"change": "none"},
        remediation=None,
    )


class _MockAdapter:
    """Minimal adapter stub that satisfies the scheduler's calling contract.

    The scheduler only calls ``collect_evidence(ksi_id)`` and ``detect_drift()``.
    We don't need to subclass ``DatabaseAdapterBase`` to satisfy the scheduler.
    """

    def __init__(
        self,
        *,
        evidence: EvidenceObject | None = None,
        drift: DriftReport | None = None,
        fail_attempts: int = 0,
    ) -> None:
        self._evidence = evidence or _evidence()
        self._drift = drift or _drift()
        self._fail_attempts = fail_attempts
        self.collect_calls = 0
        self.drift_calls = 0

    def collect_evidence(self, ksi_id: str) -> EvidenceObject:
        self.collect_calls += 1
        if self.collect_calls <= self._fail_attempts:
            raise RuntimeError(f"mock failure attempt {self.collect_calls}")
        return EvidenceObject(
            ksi_id=ksi_id,
            source=self._evidence.source,
            timestamp=self._evidence.timestamp,
            raw_data=self._evidence.raw_data,
            normalized_data=self._evidence.normalized_data,
            provenance=self._evidence.provenance,
            freshness_valid=self._evidence.freshness_valid,
        )

    def detect_drift(self) -> DriftReport:
        self.drift_calls += 1
        return self._drift


def _fixed_clock() -> datetime:
    return datetime(2026, 4, 23, 19, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Registry loading + filtering
# ---------------------------------------------------------------------------


def test_load_registry_returns_adapter_list(tmp_path):
    reg = _registry(
        tmp_path,
        [
            {"id": "a", "status": "active"},
            {"id": "b", "status": "reserved"},
        ],
    )
    s = OrchestratorScheduler(registry_path=reg, output_root=tmp_path / "out")
    adapters = s.load_registry()
    assert [a["id"] for a in adapters] == ["a", "b"]


def test_filter_adapters_default_keeps_active_only(tmp_path):
    reg = _registry(
        tmp_path,
        [
            {"id": "a", "status": "active"},
            {"id": "b", "status": "reserved"},
            {"id": "c", "status": "deprecated"},
        ],
    )
    s = OrchestratorScheduler(registry_path=reg, output_root=tmp_path / "out")
    kept = s._filter_adapters(s.load_registry())
    assert [a["id"] for a in kept] == ["a"]


def test_filter_adapters_accepts_custom_status_tuple(tmp_path):
    reg = _registry(
        tmp_path,
        [
            {"id": "a", "status": "active"},
            {"id": "b", "status": "reserved"},
            {"id": "c", "status": "beta"},
        ],
    )
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        status_filter=("active", "beta"),
    )
    kept = s._filter_adapters(s.load_registry())
    assert {a["id"] for a in kept} == {"a", "c"}


def test_missing_registry_raises_clear_error(tmp_path):
    s = OrchestratorScheduler(
        registry_path=tmp_path / "nope.yaml",
        output_root=tmp_path / "out",
    )
    with pytest.raises(FileNotFoundError):
        s.load_registry()


# ---------------------------------------------------------------------------
# Dispatch — happy path
# ---------------------------------------------------------------------------


def test_dispatch_all_invokes_each_active_adapter(tmp_path):
    reg = _registry(
        tmp_path,
        [
            {"id": "alpha", "status": "active"},
            {"id": "beta", "status": "active"},
            {"id": "gamma", "status": "reserved"},  # should be filtered out
        ],
    )
    calls: list[str] = []
    adapters: dict[str, _MockAdapter] = {"alpha": _MockAdapter(), "beta": _MockAdapter()}

    def factory(adapter_id: str):
        calls.append(adapter_id)
        return adapters.get(adapter_id)

    out = tmp_path / "out"
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=out,
        adapter_factory=factory,
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    manifest = s.dispatch_all()
    assert calls == ["alpha", "beta"]
    assert manifest.adapters_successful == 2
    assert manifest.adapters_failed == 0
    assert manifest.adapters_total == 2
    for adapter in adapters.values():
        assert adapter.collect_calls == 1
        assert adapter.drift_calls == 1


def test_dispatch_all_persists_evidence_drift_and_manifest(tmp_path):
    reg = _registry(tmp_path, [{"id": "alpha", "status": "active"}])
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=lambda _id: _MockAdapter(),
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    manifest = s.dispatch_all()
    run_dir = Path(manifest.run_dir)
    assert (run_dir / "adapters" / "alpha" / "evidence.json").is_file()
    assert (run_dir / "adapters" / "alpha" / "drift.json").is_file()
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "drift-summary.json").is_file()

    manifest_on_disk = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_on_disk["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest_on_disk["adapters_total"] == 1


def test_dispatch_all_manifest_has_stable_run_id_with_injected_clock(tmp_path):
    reg = _registry(tmp_path, [{"id": "alpha", "status": "active"}])
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=lambda _id: _MockAdapter(),
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    m1 = s.dispatch_all()
    m2 = s.dispatch_all()
    assert m1.run_id == m2.run_id, "fixed clock + identical registry must yield identical run_id"


# ---------------------------------------------------------------------------
# Retry + failure handling
# ---------------------------------------------------------------------------


def test_transient_failure_retries_and_succeeds(tmp_path):
    reg = _registry(tmp_path, [{"id": "flaky", "status": "active"}])
    flaky = _MockAdapter(fail_attempts=1)
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=lambda _id: flaky,
        max_retries=2,
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    manifest = s.dispatch_all()
    assert manifest.adapters_successful == 1
    assert manifest.adapters_failed == 0
    assert manifest.runs[0].retry_count == 1
    assert flaky.collect_calls == 2  # one failure + one success


def test_persistent_failure_records_failed_status(tmp_path):
    reg = _registry(tmp_path, [{"id": "broken", "status": "active"}])
    broken = _MockAdapter(fail_attempts=99)
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=lambda _id: broken,
        max_retries=1,
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    manifest = s.dispatch_all()
    assert manifest.adapters_failed == 1
    assert manifest.runs[0].status == "failed"
    assert manifest.runs[0].retry_count == 1
    assert "mock failure" in (manifest.runs[0].error or "")


def test_not_wired_adapter_recorded_without_fatal_error(tmp_path):
    reg = _registry(tmp_path, [{"id": "ghost", "status": "active"}])
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=lambda _id: None,  # no factory entry
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    manifest = s.dispatch_all()
    assert manifest.adapters_not_wired == 1
    assert manifest.runs[0].status == "not-wired"


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_invoke_adapters_or_write_files(tmp_path):
    reg = _registry(tmp_path, [{"id": "alpha", "status": "active"}])
    adapter = _MockAdapter()
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=lambda _id: adapter,
        clock=_fixed_clock,
    )
    manifest = s.dispatch_all(dry_run=True)
    assert adapter.collect_calls == 0
    assert adapter.drift_calls == 0
    assert manifest.adapters_skipped == 1
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").rglob("*.json"))


# ---------------------------------------------------------------------------
# Drift aggregation
# ---------------------------------------------------------------------------


def test_drift_summary_aggregates_by_severity(tmp_path):
    reg = _registry(
        tmp_path,
        [
            {"id": "a", "status": "active"},
            {"id": "b", "status": "active"},
            {"id": "c", "status": "active"},
        ],
    )
    factory_map = {
        "a": _MockAdapter(drift=_drift(severity="P1")),
        "b": _MockAdapter(drift=_drift(severity="P1")),
        "c": _MockAdapter(drift=_drift(severity="P3")),
    }
    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=lambda aid: factory_map[aid],
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    manifest = s.dispatch_all()
    assert manifest.drift_findings_total == 3
    assert manifest.drift_by_severity == {"P1": 2, "P3": 1}

    summary_path = Path(manifest.run_dir) / "drift-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total"] == 3
    assert summary["by_severity"] == {"P1": 2, "P3": 1}
    assert len(summary["adapters_with_drift"]) == 3


# ---------------------------------------------------------------------------
# dispatch_one
# ---------------------------------------------------------------------------


def test_dispatch_one_targets_a_single_adapter(tmp_path):
    reg = _registry(tmp_path, [{"id": "alpha", "status": "active"}, {"id": "beta", "status": "active"}])
    factory_calls: list[str] = []

    def factory(aid: str):
        factory_calls.append(aid)
        return _MockAdapter()

    s = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        adapter_factory=factory,
        retry_base_seconds=0.0,
        clock=_fixed_clock,
    )
    run = s.dispatch_one("beta")
    assert run.adapter_id == "beta"
    assert run.status == "success"
    assert factory_calls == ["beta"]


# ---------------------------------------------------------------------------
# Schema / serialization
# ---------------------------------------------------------------------------


def test_manifest_to_dict_roundtrips_through_json(tmp_path):
    runs = [
        AdapterRun(
            adapter_id="alpha",
            status="success",
            started_at="2026-04-23T19:00:00Z",
            completed_at="2026-04-23T19:00:01Z",
            duration_secs=1.0,
            retry_count=0,
        )
    ]
    manifest = ScheduleRunManifest(
        run_id="schedrun-test",
        schema_version=MANIFEST_SCHEMA_VERSION,
        started_at="2026-04-23T19:00:00Z",
        completed_at="2026-04-23T19:00:01Z",
        duration_secs=1.0,
        registry_path="reg.yaml",
        output_root="out",
        run_dir="out/schedrun-test",
        adapters_total=1,
        adapters_successful=1,
        adapters_failed=0,
        adapters_skipped=0,
        adapters_not_wired=0,
        drift_findings_total=0,
        drift_by_severity={},
        runs=runs,
    )
    payload = json.dumps(manifest.to_dict(), sort_keys=True)
    reloaded = json.loads(payload)
    assert reloaded["run_id"] == "schedrun-test"
    assert reloaded["runs"][0]["adapter_id"] == "alpha"
