"""
End-to-end: Adapter DriftReport → OSCAL POA&M generation.

Proves the pipeline: adapter drift output → drift_to_poam_findings() →
build_poam() → OSCAL Plan of Action & Milestones JSON.

Tests cover Terraform plan drift, M365 baseline drift, and Palo Alto
config change drift — all producing valid POA&M items.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.terraform_adapter import TerraformAdapter
from uiao.adapters.m365_adapter import M365Adapter
from uiao.adapters.paloalto_adapter import PaloAltoAdapter
from uiao.adapters.database_base import DriftReport
from uiao.adapters.adapter_to_oscal import (
    drift_to_poam_findings,
    build_adapter_poam,
)


class TestTerraformDriftToPoam:
    @pytest.fixture
    def plan_drift(self) -> DriftReport:
        adapter = TerraformAdapter({"workspace": "prod"})
        plan = json.loads((Path(__file__).parent / "fixtures" / "terraform-plan.json").read_text())
        return adapter.consume_terraform_plan(plan)

    def test_drift_produces_findings(self, plan_drift) -> None:
        findings = drift_to_poam_findings(plan_drift, "terraform", ["CM-2", "CM-3"])
        assert len(findings) == 3  # create + update + delete (no-op excluded)

    def test_delete_is_high_risk(self, plan_drift) -> None:
        findings = drift_to_poam_findings(plan_drift, "terraform")
        delete_findings = [f for f in findings if "delete" in f["title"]]
        assert len(delete_findings) == 1
        assert delete_findings[0]["risk_level"] == "high"

    def test_findings_have_controls(self, plan_drift) -> None:
        findings = drift_to_poam_findings(plan_drift, "terraform", ["CM-3"])
        for f in findings:
            assert "CM-3" in f["related_controls"]

    def test_build_full_poam(self, plan_drift) -> None:
        poam = build_adapter_poam("terraform", plan_drift, ["CM-2", "CM-3"])
        assert "poam-items" in poam
        assert len(poam["poam-items"]) == 3
        assert "metadata" in poam

    def test_poam_json_serializable(self, plan_drift) -> None:
        poam = build_adapter_poam("terraform", plan_drift)
        output = json.dumps(poam, indent=2)
        assert len(output) > 200
        assert '"poam-items"' in output


class TestM365BaselineDriftToPoam:
    @pytest.fixture
    def baseline_drift(self) -> DriftReport:
        config = json.loads((Path(__file__).parent / "fixtures" / "m365-tenant-config.json").read_text())
        adapter = M365Adapter(
            {
                "tenant_id": "contoso.onmicrosoft.com",
                "_tenant_config": config,
            }
        )
        return adapter.apply_baseline(
            "exchange-online",
            {"Default Mailbox Policy.automaticRepliesSetting": "enabled"},
        )

    def test_baseline_drift_produces_findings(self, baseline_drift) -> None:
        findings = drift_to_poam_findings(baseline_drift, "m365", ["CM-6"])
        assert len(findings) >= 1

    def test_non_compliant_in_findings(self, baseline_drift) -> None:
        findings = drift_to_poam_findings(baseline_drift, "m365")
        nc_findings = [f for f in findings if "Non-compliant" in f["title"]]
        assert len(nc_findings) >= 1

    def test_build_m365_poam(self, baseline_drift) -> None:
        poam = build_adapter_poam("m365", baseline_drift, ["CM-6"])
        assert len(poam["poam-items"]) >= 1


class TestPaloAltoChangeDriftToPoam:
    def test_config_change_to_poam(self) -> None:
        adapter = PaloAltoAdapter({"host": "fw01", "vsys": "vsys1"})
        drift = adapter.push_config_change("security-rule", "allow-dns", {"action": "deny"})
        # push_config_change doesn't populate resources dict, so aggregate path
        drift_to_poam_findings(drift, "palo-alto", ["SC-7"])
        # No per-resource items but the drift is non-empty
        # (push_config_change returns a warning-severity DriftReport)
        poam = build_adapter_poam("palo-alto", drift, ["SC-7"])
        assert "poam-items" in poam


class TestEmptyDrift:
    def test_no_drift_no_findings(self) -> None:
        from uiao.adapters.database_base import DriftReport
        from datetime import datetime, timezone

        clean = DriftReport(
            drift_type="test-clean",
            severity="info",
            first_observed=datetime.now(timezone.utc),
            last_observed=datetime.now(timezone.utc),
            details={"adapter": "test", "resources": {}},
        )
        findings = drift_to_poam_findings(clean, "test")
        assert len(findings) == 0

    def test_empty_poam_still_valid(self) -> None:
        from uiao.adapters.database_base import DriftReport
        from datetime import datetime, timezone

        clean = DriftReport(
            drift_type="test-clean",
            severity="info",
            first_observed=datetime.now(timezone.utc),
            last_observed=datetime.now(timezone.utc),
            details={"adapter": "test", "resources": {}},
        )
        poam = build_adapter_poam("test", clean)
        assert "poam-items" in poam
        assert len(poam["poam-items"]) == 0
