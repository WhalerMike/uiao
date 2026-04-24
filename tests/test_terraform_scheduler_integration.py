"""Integration tests for the TerraformAdapter ↔ scheduler wiring (§1.5).

Proves the UIAO_100 scheduler can dispatch the real
``uiao.adapters.terraform_adapter.TerraformAdapter`` through its default
factory map and persist usable evidence + drift artifacts, without
requiring a live Terraform state file or a running backend.

Scope (complementary to ``tests/test_terraform_adapter.py``, which covers
the adapter's internal methods in isolation):
    - Factory resolution: ``_default_adapter_factory("terraform")``
      returns a TerraformAdapter instance.
    - Scheduler dispatch: ``OrchestratorScheduler.dispatch_one("terraform")``
      produces on-disk evidence.json + drift.json whose shapes match the
      downstream consumers (EvidenceGraph.from_scheduler_run,
      DRIFT-SEMANTIC evaluator).
    - Full ``dispatch_all`` run with a registry that includes terraform.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from uiao.adapters.terraform_adapter import TerraformAdapter
from uiao.orchestrator.scheduler import (
    OrchestratorScheduler,
    _default_adapter_factory,
)


# ---------------------------------------------------------------------------
# Factory resolution
# ---------------------------------------------------------------------------


def test_default_factory_returns_terraform_adapter():
    adapter = _default_adapter_factory("terraform")
    assert adapter is not None
    assert isinstance(adapter, TerraformAdapter)
    assert adapter.ADAPTER_ID == "terraform"


def test_default_factory_unknown_adapter_returns_none():
    """Preserves the 'not-wired' semantics so unrelated IDs still report cleanly."""
    assert _default_adapter_factory("ghost-adapter-does-not-exist") is None


# ---------------------------------------------------------------------------
# Scheduler dispatch — single adapter
# ---------------------------------------------------------------------------


def _mini_registry(tmp_path: Path) -> Path:
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        yaml.safe_dump(
            {
                "schema-version": "1.0.0",
                "registry-class": "modernization",
                "updated": "2026-04-23",
                "adapters": [
                    {
                        "id": "terraform",
                        "status": "active",
                        "freshness-window-hours": 24,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return reg


def test_scheduler_dispatch_one_against_real_terraform_adapter(tmp_path):
    reg = _mini_registry(tmp_path)
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    run = scheduler.dispatch_one("terraform")
    assert run.adapter_id == "terraform"
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
    run = scheduler.dispatch_one("terraform")
    payload = json.loads(Path(run.evidence_path).read_text(encoding="utf-8"))
    # These keys are what EvidenceGraph.from_scheduler_run() and the
    # DRIFT-SEMANTIC evaluator both consume.
    assert payload["source"] == "terraform"
    assert "timestamp" in payload
    assert "ksi_id" in payload
    assert "provenance" in payload
    assert payload["provenance"]["adapter_id"] == "terraform"


def test_scheduler_drift_json_has_expected_shape(tmp_path):
    reg = _mini_registry(tmp_path)
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    run = scheduler.dispatch_one("terraform")
    drift = json.loads(Path(run.drift_path).read_text(encoding="utf-8"))
    assert drift["drift_type"] == "terraform-state"
    # Scaffold drift is 'info' severity — scheduler records it without panic.
    assert drift["severity"] in {"info", "low"}


# ---------------------------------------------------------------------------
# Scheduler dispatch — full dispatch_all with terraform mixed in
# ---------------------------------------------------------------------------


def test_dispatch_all_runs_terraform_alongside_other_active_adapters(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        yaml.safe_dump(
            {
                "schema-version": "1.0.0",
                "registry-class": "modernization",
                "updated": "2026-04-23",
                "adapters": [
                    {"id": "terraform", "status": "active", "freshness-window-hours": 24},
                    # Unregistered adapter should record as not-wired without
                    # stopping the terraform run.
                    {"id": "not-wired-yet", "status": "active"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    manifest = scheduler.dispatch_all()
    by_id = {r.adapter_id: r for r in manifest.runs}
    assert by_id["terraform"].status == "success"
    assert by_id["not-wired-yet"].status == "not-wired"
    assert manifest.adapters_successful == 1
    assert manifest.adapters_not_wired == 1
    assert manifest.adapters_failed == 0


# ---------------------------------------------------------------------------
# Canon smoke — the actual registry entry must stay wired
# ---------------------------------------------------------------------------


def test_canon_modernization_registry_declares_terraform_freshness_window():
    """Guards against accidental removal of the freshness window seeded in §1.5."""
    repo_root = Path(__file__).resolve().parent.parent
    data = yaml.safe_load(
        (repo_root / "src" / "uiao" / "canon" / "modernization-registry.yaml").read_text(encoding="utf-8")
    )
    terraform = next(a for a in data["adapters"] if a["id"] == "terraform")
    assert terraform.get("freshness-window-hours") == 24
    assert terraform.get("status") == "active"
