"""Integration tests for the ScuBAGear adapter ↔ UIAO_100 scheduler wiring.

Mirrors ``tests/test_terraform_scheduler_integration.py`` (§1.5). Proves the
scheduler can dispatch the real ``uiao.adapters.scubagear_adapter.ScubaGearAdapter``
end to end without injected mocks, and that the emitted evidence + drift
artifacts match the shapes consumed by the §1.4 evidence graph and §1.1
DRIFT-SEMANTIC evaluator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from uiao.adapters.scubagear_adapter import ScubaGearAdapter
from uiao.orchestrator.scheduler import (
    OrchestratorScheduler,
    _default_adapter_factory,
)


# ---------------------------------------------------------------------------
# Factory resolution
# ---------------------------------------------------------------------------


def test_default_factory_returns_scubagear_adapter():
    adapter = _default_adapter_factory("scubagear")
    assert adapter is not None
    assert isinstance(adapter, ScubaGearAdapter)


# ---------------------------------------------------------------------------
# Scheduler dispatch — single adapter
# ---------------------------------------------------------------------------


def _mini_registry(tmp_path: Path) -> Path:
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        yaml.safe_dump(
            {
                "schema-version": "1.0.0",
                "registry-class": "conformance",
                "updated": "2026-04-23",
                "adapters": [
                    {
                        "id": "scubagear",
                        "status": "active",
                        "freshness-window-hours": 168,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return reg


def test_scheduler_dispatch_one_against_real_scubagear_adapter(tmp_path):
    reg = _mini_registry(tmp_path)
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    run = scheduler.dispatch_one("scubagear")
    assert run.adapter_id == "scubagear"
    assert run.status == "success", f"dispatch failed: {run.error}"
    assert run.evidence_path is not None
    assert run.drift_path is not None
    assert Path(run.evidence_path).is_file()
    assert Path(run.drift_path).is_file()


def test_scheduler_evidence_json_has_expected_shape(tmp_path):
    reg = _mini_registry(tmp_path)
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    run = scheduler.dispatch_one("scubagear")
    payload = json.loads(Path(run.evidence_path).read_text(encoding="utf-8"))
    # Keys consumed by EvidenceGraph.from_scheduler_run() + DRIFT-SEMANTIC.
    assert payload["source"] == "scubagear"
    assert "timestamp" in payload
    assert "ksi_id" in payload
    assert "provenance" in payload
    assert payload["provenance"]["adapter_id"] == "scubagear"


def test_scheduler_drift_json_has_expected_shape(tmp_path):
    reg = _mini_registry(tmp_path)
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    run = scheduler.dispatch_one("scubagear")
    drift = json.loads(Path(run.drift_path).read_text(encoding="utf-8"))
    # Scaffold drift varies by adapter; require only the structural fields
    # the scheduler + downstream normalizer consume.
    assert "drift_type" in drift
    assert "severity" in drift
    assert "details" in drift


# ---------------------------------------------------------------------------
# Canon smoke — the actual registry entry must stay wired
# ---------------------------------------------------------------------------


def test_canon_adapter_registry_declares_scubagear_freshness_window():
    """Guards against accidental removal of the freshness window seeded in §1.1."""
    repo_root = Path(__file__).resolve().parent.parent
    data: dict[str, Any] = yaml.safe_load(
        (repo_root / "src" / "uiao" / "canon" / "adapter-registry.yaml").read_text(encoding="utf-8")
    )
    scubagear = next(a for a in data["adapters"] if a["id"] == "scubagear")
    assert scubagear.get("freshness-window-hours") == 168
    assert scubagear.get("status") == "active"
