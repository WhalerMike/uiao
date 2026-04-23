"""Tests for scripts/conmon/migration_readiness.py (RFC-0026 E8).

Covers the Pathway-1 migration readiness check that guards the Notice
0009 mandatory adoption deadlines for the CCM BIR (2027-04-01) and VDR
BIR (2027-06-01). The check pairs the reserved adapter stubs
(`src/uiao/adapters/{ccm_bir,vdr}_adapter.py`) with the registry
status in `src/uiao/canon/adapter-registry.yaml`, and fires a
breach signal when today is inside the 90-day lead window while the
registry still reports `status: reserved`.

Roadmap reference: docs/docs/uiao-rfc-0026-roadmap.md § E8 (T8.4).
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import pathlib
import sys
from typing import Any, Dict

import pytest

from uiao.adapters import ccm_bir_adapter, vdr_adapter

# ---------------------------------------------------------------------------
# Dynamic import of scripts/conmon/migration_readiness.py
#
# Keep it ergonomic for pytest without forcing a src-layout change to
# the scripts/ directory.
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "scripts" / "conmon" / "migration_readiness.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("migration_readiness", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migration_readiness"] = mod
    spec.loader.exec_module(mod)
    return mod


mr = _load_module()


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _registry(**statuses) -> Dict[str, Any]:
    """Tiny adapter-registry document with the given id -> status map."""
    return {
        "schema-version": "1.0.0",
        "adapters": [
            {"id": adapter_id, "name": f"{adapter_id} stub", "status": status}
            for adapter_id, status in statuses.items()
        ],
    }


# ---------------------------------------------------------------------------
# Adapter stub smoke tests
# ---------------------------------------------------------------------------


class TestAdapterStubs:
    def test_vdr_adapter_constants(self) -> None:
        assert vdr_adapter.ADAPTER_ID == "vdr-bir"
        assert vdr_adapter.STATUS == "reserved"
        assert vdr_adapter.MANDATORY_ADOPTION_DATE == "2027-06-01"
        assert vdr_adapter.READINESS_LEAD_DAYS == 90

    def test_ccm_bir_adapter_constants(self) -> None:
        assert ccm_bir_adapter.ADAPTER_ID == "ccm-bir"
        assert ccm_bir_adapter.STATUS == "reserved"
        assert ccm_bir_adapter.MANDATORY_ADOPTION_DATE == "2027-04-01"
        assert ccm_bir_adapter.READINESS_LEAD_DAYS == 90

    def test_vdr_adapter_instantiation_fails_fast(self) -> None:
        with pytest.raises(vdr_adapter.VdrAdapterNotYetAvailable) as excinfo:
            vdr_adapter.VdrAdapter()
        assert "Notice 0009" in str(excinfo.value)
        assert "2027-06-01" in str(excinfo.value)

    def test_ccm_bir_adapter_instantiation_fails_fast(self) -> None:
        with pytest.raises(ccm_bir_adapter.CcmBirAdapterNotYetAvailable) as excinfo:
            ccm_bir_adapter.CcmBirAdapter()
        assert "Notice 0009" in str(excinfo.value)
        assert "2027-04-01" in str(excinfo.value)

    def test_ccm_deadline_is_earlier_than_vdr_deadline(self) -> None:
        """Notice 0009 sequencing: CCM must land before VDR."""
        ccm_date = dt.date.fromisoformat(ccm_bir_adapter.MANDATORY_ADOPTION_DATE)
        vdr_date = dt.date.fromisoformat(vdr_adapter.MANDATORY_ADOPTION_DATE)
        assert ccm_date < vdr_date


# ---------------------------------------------------------------------------
# evaluate_pathway_readiness behaviour
# ---------------------------------------------------------------------------


class TestEvaluatePathwayReadiness:
    def test_outside_lead_window_is_not_a_breach(self) -> None:
        # Two years before both deadlines
        now = dt.date(2025, 1, 1)
        registry = _registry(**{"vdr-bir": "reserved", "ccm-bir": "reserved"})
        results = mr.evaluate_pathway_readiness(registry, now=now)

        assert len(results) == 2
        for r in results:
            assert r.breach is False
            assert r.breach_window_opened_at is None
            assert r.days_until_mandatory > 90

    def test_inside_ccm_window_with_reserved_status_is_a_breach(self) -> None:
        # CCM window opens 2026-12-31 (90 days before 2027-04-01);
        # pick 2027-01-15 — inside CCM window, not yet inside VDR window
        now = dt.date(2027, 1, 15)
        registry = _registry(**{"vdr-bir": "reserved", "ccm-bir": "reserved"})
        results = mr.evaluate_pathway_readiness(registry, now=now)

        by_id = {r.adapter_id: r for r in results}
        ccm = by_id["ccm-bir"]
        vdr = by_id["vdr-bir"]

        assert ccm.breach is True
        assert ccm.breach_window_opened_at == "2027-01-01"
        assert "Migration must start" in ccm.reason

        # VDR window opens 2027-03-03, so on 2027-01-15 we're still outside
        assert vdr.breach is False

    def test_inside_vdr_window_but_status_moved_to_proposed_is_not_a_breach(self) -> None:
        # Pick 2027-04-15: past CCM deadline (so CCM is deep in breach
        # territory) but only VDR should be breach-relevant now since
        # CCM should have flipped out of "reserved" by then
        now = dt.date(2027, 4, 15)
        registry = _registry(**{"vdr-bir": "proposed", "ccm-bir": "active"})
        results = mr.evaluate_pathway_readiness(registry, now=now)

        for r in results:
            # Both are inside their lead windows
            assert r.breach_window_opened_at is not None
            # Neither is still "reserved", so neither is a breach
            assert r.breach is False

    def test_inside_window_with_status_reserved_sets_breach(self) -> None:
        now = dt.date(2027, 4, 15)
        registry = _registry(**{"vdr-bir": "reserved", "ccm-bir": "active"})
        results = mr.evaluate_pathway_readiness(registry, now=now)
        by_id = {r.adapter_id: r for r in results}
        assert by_id["vdr-bir"].breach is True
        assert by_id["ccm-bir"].breach is False

    def test_missing_from_registry_is_treated_as_breach_inside_window(self) -> None:
        # Inside CCM lead window; ccm-bir is absent from the registry entirely
        now = dt.date(2027, 2, 1)
        registry = _registry(**{"vdr-bir": "reserved"})  # ccm-bir missing
        results = mr.evaluate_pathway_readiness(registry, now=now)
        ccm = next(r for r in results if r.adapter_id == "ccm-bir")
        assert ccm.registry_status is None
        assert ccm.breach is True
        assert "not in the registry at all" in ccm.reason

    def test_empty_registry_is_tolerated_outside_window(self) -> None:
        now = dt.date(2025, 1, 1)
        registry = _registry()  # no adapters at all
        results = mr.evaluate_pathway_readiness(registry, now=now)
        # Outside window + status unknown — silent
        for r in results:
            assert r.registry_status is None
            assert r.breach is False


# ---------------------------------------------------------------------------
# _build_output / CLI surface
# ---------------------------------------------------------------------------


class TestBuildOutputAndCli:
    def test_build_output_sets_any_breach_flag(self) -> None:
        now = dt.date(2027, 1, 15)
        registry = _registry(**{"vdr-bir": "reserved", "ccm-bir": "reserved"})
        results = mr.evaluate_pathway_readiness(registry, now=now)
        payload = mr._build_output(results, now=now)

        assert payload["evaluated_at"] == "2027-01-15"
        assert payload["any_breach"] is True
        assert len(payload["pathways"]) == 2

    def test_main_writes_json_and_exits_zero_without_breach_flag(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Use a tiny registry with both adapters marked active so no breach fires
        reg_file = tmp_path / "adapter-registry.yaml"
        reg_file.write_text(
            """
schema-version: "1.0.0"
adapters:
  - id: vdr-bir
    name: vdr stub
    status: active
  - id: ccm-bir
    name: ccm stub
    status: active
            """.strip(),
            encoding="utf-8",
        )
        out_file = tmp_path / "out.json"

        rc = mr.main(
            [
                "--registry",
                str(reg_file),
                "--output",
                str(out_file),
                "--now",
                "2027-05-01",
                "--fail-on-breach",
            ]
        )
        assert rc == 0
        payload = json.loads(out_file.read_text(encoding="utf-8"))
        assert payload["any_breach"] is False

    def test_main_exits_one_on_breach_when_fail_flag_set(self, tmp_path: pathlib.Path) -> None:
        reg_file = tmp_path / "adapter-registry.yaml"
        reg_file.write_text(
            """
schema-version: "1.0.0"
adapters:
  - id: vdr-bir
    name: vdr stub
    status: reserved
  - id: ccm-bir
    name: ccm stub
    status: reserved
            """.strip(),
            encoding="utf-8",
        )

        rc = mr.main(
            [
                "--registry",
                str(reg_file),
                "--output",
                str(tmp_path / "out.json"),
                "--now",
                "2027-01-15",
                "--fail-on-breach",
            ]
        )
        assert rc == 1  # breach on CCM

    def test_main_exits_zero_on_breach_without_fail_flag(self, tmp_path: pathlib.Path) -> None:
        """Same breach as above but without --fail-on-breach → rc=0."""
        reg_file = tmp_path / "adapter-registry.yaml"
        reg_file.write_text(
            """
schema-version: "1.0.0"
adapters:
  - id: vdr-bir
    name: vdr stub
    status: reserved
  - id: ccm-bir
    name: ccm stub
    status: reserved
            """.strip(),
            encoding="utf-8",
        )
        rc = mr.main(
            [
                "--registry",
                str(reg_file),
                "--output",
                str(tmp_path / "out.json"),
                "--now",
                "2027-01-15",
            ]
        )
        assert rc == 0


class TestRegistryPinIntegration:
    """Guards that the real canon adapter-registry.yaml actually
    registers the two Pathway-1 adapter slots this script depends on.
    Without this guard, a registry edit that silently drops the slot
    would go undetected until a production CI run."""

    def test_real_registry_contains_vdr_and_ccm_slots(self) -> None:
        import yaml

        registry_path = _REPO_ROOT / "src" / "uiao" / "canon" / "adapter-registry.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        ids = {a["id"] for a in registry["adapters"] if isinstance(a, dict) and "id" in a}
        assert "vdr-bir" in ids, "adapter-registry.yaml must register vdr-bir"
        assert "ccm-bir" in ids, "adapter-registry.yaml must register ccm-bir"
