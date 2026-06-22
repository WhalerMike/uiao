"""Tests for governance/identity/pipeline.py — the gate orchestrator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.governance.identity.pipeline import (
    hrit_records_from_json,
    run_pipeline,
    service_records_from_json,
)
from uiao.governance.identity.service_identity import ServiceIdentityRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HRIT_SAMPLE = Path(__file__).parent.parent.parent / "fixtures" / "hrit" / "hrit-sample.json"
_SVC_SAMPLE = Path(__file__).parent.parent.parent / "fixtures" / "identity" / "services-sample.json"


def _hr(employee_id: str, status: str = "Active", **kwargs) -> HRRecord:
    return HRRecord(
        employee_id=employee_id,
        first_name="Test",
        last_name="User",
        department="IT",
        hire_date="2022-01-01",
        worker_type="FullTimeEmployee",
        location_code="NCR",
        country="US",
        employment_status=status,
        extracted_at="2026-06-22T00:00:00Z",
        **kwargs,
    )


def _svc(principal_id: str, owner: str) -> ServiceIdentityRecord:
    return ServiceIdentityRecord(
        principal_id=principal_id,
        display_name=principal_id,
        account_class="ServicePrincipal",
        department="IT",
        division="CyberOps",
        cost_center="CC-4200",
        owner_employee_id=owner,
        owner_display_name="Owner",
        credential_expiry_date=None,
        last_rotation_date=None,
        purpose="Test",
        orgpath="NCR.IT.CyberOps",
        extracted_at="2026-06-22T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# Fixture loaders
# ---------------------------------------------------------------------------


class TestFixtureLoaders:
    def test_hrit_sample_loads(self):
        records = hrit_records_from_json(_HRIT_SAMPLE)
        assert len(records) == 3
        assert any(r.employee_id == "E002" for r in records)

    def test_service_sample_loads(self):
        records = service_records_from_json(_SVC_SAMPLE)
        assert len(records) == 3
        assert any(r.principal_id == "svc-sentinel-ingest" for r in records)

    def test_hrit_loader_bare_list(self):
        data = [
            {
                "employee_id": "E001",
                "first_name": "A",
                "last_name": "B",
                "department": "IT",
                "hire_date": "2022-01-01",
                "worker_type": "FTE",
                "location_code": "NCR",
                "country": "US",
                "employment_status": "Active",
                "extracted_at": "2026-06-22T00:00:00Z",
            }
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            path = f.name
        records = hrit_records_from_json(path)
        assert len(records) == 1

    def test_service_loader_agd_fixture_format(self):
        data = {
            "principals": [
                {
                    "principal_id": "svc-test",
                    "account_class": "ServicePrincipal",
                    "department": "IT",
                    "extracted_at": "2026-06-22T00:00:00Z",
                }
            ]
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            path = f.name
        records = service_records_from_json(path)
        assert len(records) == 1
        assert records[0].principal_id == "svc-test"


# ---------------------------------------------------------------------------
# Pipeline gate logic
# ---------------------------------------------------------------------------


class TestPipelineGate:
    def test_gate_passes_with_no_p1_findings(self):
        result = run_pipeline([_hr("E001")], [], fail_on_p1=True)
        assert result.gate_passed is True

    def test_gate_fails_when_orphan_detected(self):
        # E001 is a leaver; svc-test is owned by E001 → P1 orphan
        current_hrit = [_hr("E001", status="Terminated", termination_date="2026-06-20")]
        current_svc = [_svc("svc-test", owner="E001")]
        result = run_pipeline(current_hrit, current_svc, fail_on_p1=True)
        assert result.gate_passed is False
        assert result.p1_count >= 1

    def test_no_fail_flag_suppresses_gate_failure(self):
        current_hrit = [_hr("E001", status="Terminated", termination_date="2026-06-20")]
        current_svc = [_svc("svc-test", owner="E001")]
        result = run_pipeline(current_hrit, current_svc, fail_on_p1=False)
        assert result.gate_passed is True
        assert result.p1_count >= 1

    def test_leaver_with_no_service_accounts_passes(self):
        current_hrit = [_hr("E001", status="Terminated", termination_date="2026-06-20")]
        result = run_pipeline(current_hrit, [], fail_on_p1=True)
        # leaver has no service accounts → no P1 orphan findings
        assert result.p1_count == 0
        assert result.gate_passed is True

    def test_pending_leavers_also_trigger_orphan_scan(self):
        # termination_date set but status still Active → pending leaver
        current_hrit = [_hr("E001", status="Active", termination_date="2026-12-31")]
        current_svc = [_svc("svc-pending", owner="E001")]
        result = run_pipeline(current_hrit, current_svc, fail_on_p1=True)
        # Pending leaver → orphan scan → P1
        assert result.p1_count >= 1

    def test_counts_human_and_service_findings_together(self):
        current_hrit = [_hr("E001", status="Terminated", termination_date="2026-06-20")]
        current_svc = [
            _svc("svc-a", owner="E001"),
            _svc("svc-b", owner="E001"),
        ]
        result = run_pipeline(current_hrit, current_svc)
        assert result.p1_count >= 2

    def test_summary_lines_present(self):
        result = run_pipeline([_hr("E001")], [])
        assert len(result.summary_lines) >= 2
        assert any("GATE" in line for line in result.summary_lines)


# ---------------------------------------------------------------------------
# Evidence artifacts and gate report
# ---------------------------------------------------------------------------


class TestEvidenceArtifacts:
    def test_gate_report_written(self):
        current_hrit = [_hr("E001")]
        with tempfile.TemporaryDirectory() as d:
            run_pipeline(current_hrit, [], output_dir=d)
            report = Path(d) / "gate-report.json"
            assert report.exists()
            data = json.loads(report.read_text(encoding="utf-8"))
            assert "gate_passed" in data
            assert "p1_count" in data

    def test_human_and_service_event_logs_written(self):
        current_hrit = [_hr("E001", status="Terminated", termination_date="2026-06-20")]
        current_svc = [_svc("svc-x", owner="E001")]
        with tempfile.TemporaryDirectory() as d:
            run_pipeline(current_hrit, current_svc, output_dir=d)
            names = {f.name for f in Path(d).iterdir()}
            assert "human-jml-event-log.json" in names
            assert "service-identity-event-log.json" in names
            assert "gate-report.json" in names

    def test_gate_result_to_dict(self):
        result = run_pipeline([_hr("E001")], [])
        d = result.to_dict()
        assert "gate_passed" in d
        assert "human" in d
        assert "service" in d


# ---------------------------------------------------------------------------
# Integration: sample fixtures end-to-end
# ---------------------------------------------------------------------------


class TestSampleFixtures:
    def test_sample_hrit_with_leaver_triggers_orphan(self):
        """hrit-sample.json has E002 as Terminated; services-sample.json has
        svc-sentinel-ingest and svc-ai-web-scanner owned by E002.
        The gate MUST fail."""
        hrit = hrit_records_from_json(_HRIT_SAMPLE)
        svcs = service_records_from_json(_SVC_SAMPLE)
        result = run_pipeline(hrit, svcs, fail_on_p1=True)
        assert result.gate_passed is False, (
            "E002 (Bob Jones) is Terminated and owns two service accounts. "
            "Gate must fail with P1 DRIFT-ORPHAN-NHAM findings."
        )
        orphan_ids = {ev.record.principal_id for ev in result.service_events.orphaned}
        assert "svc-sentinel-ingest" in orphan_ids
        assert "svc-ai-web-scanner" in orphan_ids

    def test_sample_fixtures_gate_report_structure(self):
        hrit = hrit_records_from_json(_HRIT_SAMPLE)
        svcs = service_records_from_json(_SVC_SAMPLE)
        with tempfile.TemporaryDirectory() as d:
            run_pipeline(hrit, svcs, output_dir=d)
            report = json.loads((Path(d) / "gate-report.json").read_text())
            assert report["service"]["orphaned"] >= 2
