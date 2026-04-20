"""Tests for the POA&M → ServiceNow remediation workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.remediation import (
    poam_findings_to_change_requests,
    generate_remediation_report,
)
from uiao.adapters.adapter_to_oscal import drift_to_poam_findings
from uiao.adapters.terraform_adapter import TerraformAdapter


@pytest.fixture
def terraform_drift_findings() -> list:
    adapter = TerraformAdapter({"workspace": "prod"})
    plan = json.loads(
        (Path(__file__).parent / "fixtures" / "terraform-plan.json").read_text()
    )
    drift = adapter.consume_terraform_plan(plan)
    return drift_to_poam_findings(drift, "terraform", ["CM-2", "CM-3"])


class TestPoamToChangeRequests:
    def test_creates_change_requests(self, terraform_drift_findings: list) -> None:
        crs = poam_findings_to_change_requests(terraform_drift_findings)
        assert len(crs) == 3  # create + update + delete

    def test_change_request_format(self, terraform_drift_findings: list) -> None:
        crs = poam_findings_to_change_requests(terraform_drift_findings)
        for cr in crs:
            assert "sys_id" in cr
            assert "short_description" in cr
            assert "priority" in cr
            assert cr["category"] == "Security"
            assert cr["subcategory"] == "Remediation"
            assert cr["source"] == "uiao-poam-auto"

    def test_high_risk_gets_priority_1(self, terraform_drift_findings: list) -> None:
        crs = poam_findings_to_change_requests(terraform_drift_findings)
        high_crs = [cr for cr in crs if cr["risk_level"] == "high"]
        assert len(high_crs) >= 1
        assert high_crs[0]["priority"] == "1"

    def test_custom_assignee(self, terraform_drift_findings: list) -> None:
        crs = poam_findings_to_change_requests(
            terraform_drift_findings, assignee="infra-team"
        )
        for cr in crs:
            assert cr["assigned_to"] == "infra-team"

    def test_controls_in_description(self, terraform_drift_findings: list) -> None:
        crs = poam_findings_to_change_requests(terraform_drift_findings)
        for cr in crs:
            assert "CM-2" in cr["description"] or "CM-3" in cr["description"]

    def test_empty_findings_empty_crs(self) -> None:
        crs = poam_findings_to_change_requests([])
        assert len(crs) == 0


class TestRemediationReport:
    def test_generates_report(self, terraform_drift_findings: list) -> None:
        crs = poam_findings_to_change_requests(terraform_drift_findings)
        report = generate_remediation_report(terraform_drift_findings, crs)
        assert report["total_findings"] == 3
        assert report["total_change_requests"] == 3
        assert "by_risk_level" in report
        assert len(report["change_request_ids"]) == 3

    def test_risk_breakdown(self, terraform_drift_findings: list) -> None:
        crs = poam_findings_to_change_requests(terraform_drift_findings)
        report = generate_remediation_report(terraform_drift_findings, crs)
        assert report["by_risk_level"].get("high", 0) >= 1


class TestEndToEndRemediationPipeline:
    """Full pipeline: terraform plan → drift → POA&M → change requests → report."""

    def test_full_pipeline(self) -> None:
        # Step 1: Parse plan
        adapter = TerraformAdapter({"workspace": "prod"})
        plan = json.loads(
            (Path(__file__).parent / "fixtures" / "terraform-plan.json").read_text()
        )
        drift = adapter.consume_terraform_plan(plan)

        # Step 2: Convert to POA&M findings
        findings = drift_to_poam_findings(drift, "terraform", ["CM-3"])
        assert len(findings) == 3

        # Step 3: Generate change requests
        crs = poam_findings_to_change_requests(findings, assignee="terraform-team")
        assert len(crs) == 3

        # Step 4: Generate report
        report = generate_remediation_report(findings, crs)
        assert report["status"] == "pending_review"
        assert report["assignee"] == "terraform-team"

        # Step 5: Feed CRs back through ServiceNow adapter (round-trip)
        from uiao.adapters.servicenow_adapter import ServiceNowAdapter
        sn = ServiceNowAdapter({"instance": "contoso-gov", "token": "test"})
        claims = sn.normalize(crs)
        assert len(claims.claims) == 3
        for claim in claims.claims:
            assert claim.source == "servicenow"
