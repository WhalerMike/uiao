"""Integration tests for the Entra ID adapter ↔ UIAO_100 scheduler wiring.

Mirrors ``tests/test_terraform_scheduler_integration.py`` (§1.5). Proves the
scheduler can dispatch the real ``uiao.adapters.entra_adapter.EntraAdapter``
end to end without injected mocks, and that the emitted evidence + drift
artifacts match the shapes consumed by the §1.4 evidence graph and §1.1
DRIFT-SEMANTIC evaluator.

The Entra adapter depends on Microsoft Graph client libraries (azure-identity,
httpx) for live API calls. In sandbox / CI runs without those libraries
installed the adapter still dispatches cleanly — its ``EntraCollector``
skips HTTP calls with a warning and returns empty record sets. These tests
exercise that path; the "with-credentials" path is out of scope and lives
under the tier-1 live-tenant job wired via the M365 Developer Program
(roadmap §0.1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from uiao.adapters.entra_adapter import EntraAdapter
from uiao.orchestrator.scheduler import (
    OrchestratorScheduler,
    _default_adapter_factory,
)


# ---------------------------------------------------------------------------
# Factory resolution
# ---------------------------------------------------------------------------


def test_default_factory_returns_entra_adapter():
    adapter = _default_adapter_factory("entra-id")
    assert adapter is not None
    assert isinstance(adapter, EntraAdapter)


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
                        "id": "entra-id",
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


def test_scheduler_dispatch_one_against_real_entra_adapter(tmp_path):
    reg = _mini_registry(tmp_path)
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    run = scheduler.dispatch_one("entra-id")
    assert run.adapter_id == "entra-id"
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
    run = scheduler.dispatch_one("entra-id")
    payload = json.loads(Path(run.evidence_path).read_text(encoding="utf-8"))
    # Keys consumed by EvidenceGraph.from_scheduler_run() + DRIFT-SEMANTIC.
    assert payload["source"] == "entra-id"
    assert "timestamp" in payload
    assert "ksi_id" in payload
    assert "provenance" in payload
    assert payload["provenance"]["adapter_id"] == "entra-id"


def test_scheduler_drift_json_has_expected_shape(tmp_path):
    reg = _mini_registry(tmp_path)
    scheduler = OrchestratorScheduler(
        registry_path=reg,
        output_root=tmp_path / "out",
        retry_base_seconds=0.0,
    )
    run = scheduler.dispatch_one("entra-id")
    drift = json.loads(Path(run.drift_path).read_text(encoding="utf-8"))
    assert "drift_type" in drift
    assert "severity" in drift
    assert "details" in drift


# ---------------------------------------------------------------------------
# dispatch_all — ScuBAGear + Entra ID + Terraform together
# ---------------------------------------------------------------------------


def test_dispatch_all_mixes_all_three_wired_adapters(tmp_path):
    """Closes the full-factory picture: every wired adapter in one run."""
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        yaml.safe_dump(
            {
                "schema-version": "1.0.0",
                "registry-class": "modernization",
                "updated": "2026-04-23",
                "adapters": [
                    {"id": "entra-id", "status": "active", "freshness-window-hours": 24},
                    {"id": "scubagear", "status": "active", "freshness-window-hours": 168},
                    {"id": "terraform", "status": "active", "freshness-window-hours": 24},
                    {"id": "future-adapter", "status": "active"},  # not-wired
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
    for wired in ("entra-id", "scubagear", "terraform"):
        assert by_id[wired].status == "success", f"{wired}: {by_id[wired].error}"
    assert by_id["future-adapter"].status == "not-wired"
    assert manifest.adapters_successful == 3
    assert manifest.adapters_not_wired == 1
    assert manifest.adapters_failed == 0


# ---------------------------------------------------------------------------
# Canon smoke — the actual registry entry must stay wired
# ---------------------------------------------------------------------------


def test_canon_modernization_registry_declares_entra_id_freshness_window():
    """Guards against accidental removal of the freshness window seeded in §1.1."""
    repo_root = Path(__file__).resolve().parent.parent
    data: dict[str, Any] = yaml.safe_load(
        (repo_root / "src" / "uiao" / "canon" / "modernization-registry.yaml").read_text(encoding="utf-8")
    )
    entra = next(a for a in data["adapters"] if a["id"] == "entra-id")
    assert entra.get("freshness-window-hours") == 24
    assert entra.get("status") == "active"
