"""Tests for uiao_core.monitoring and uiao_core.dashboard modules.

Covers:
- EventProcessor: normalise + evaluate
- SentinelHook: parse, map controls, build POA&M entry (with POAM-UIAO- prefix)
- OngoingAuthGenerator: generate OSCAL evidence records
- KSICalculator: score computation
- DashboardExporter: JSON/YAML export
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def monitoring_sources_yml(tmp_path: Path) -> Path:
    data = {
        "monitoring_sources": [
            {
                "name": "Test SIEM",
                "type": "siem",
                "telemetry": [
                    {
                        "signal": "identity_anomaly",
                        "maps_to_control": "AC-2",
                        "description": "Anomalous identity behavior",
                    },
                    {
                        "signal": "mfa_bypass_attempt",
                        "maps_to_control": "IA-2",
                        "description": "MFA bypass detected",
                    },
                ],
            }
        ]
    }
    p = tmp_path / "monitoring-sources.yml"
    p.write_text(yaml.dump(data))
    return p


@pytest.fixture
def ksi_mappings_yml(tmp_path: Path) -> Path:
    data = {
        "ksi_mappings": [
            {
                "ksi_id": "KSI-TEST-1",
                "title": "Test KSI Implemented",
                "control_ids": ["IA-2"],
                "evidence_source": "Entra ID Logs",
                "status": "Implemented",
            },
            {
                "ksi_id": "KSI-TEST-2",
                "title": "Test KSI Partial",
                "control_ids": ["CM-2"],
                "evidence_source": "Intune Reports",
                "status": "Partial",
            },
            {
                "ksi_id": "KSI-TEST-3",
                "title": "Test KSI Planned",
                "control_ids": ["SC-28"],
                "evidence_source": "Purview",
                "status": "Planned",
            },
        ]
    }
    p = tmp_path / "ksi-mappings.yml"
    p.write_text(yaml.dump(data))
    return p


@pytest.fixture
def sentinel_payload() -> dict:
    return {
        "properties": {
            "systemAlertId": "alert-001",
            "alertDisplayName": "Suspicious Sign-In",
            "severity": "High",
            "productName": "Microsoft Sentinel",
            "description": "Unusual login location detected",
            "timeGenerated": "2026-03-24T00:00:00Z",
            "entities": [],
            "tactics": ["InitialAccess"],
            "techniques": ["T1078"],
        }
    }


# ===========================================================================
# EventProcessor tests
# ===========================================================================


class TestEventProcessor:
    def test_normalise_generic_event(self, monitoring_sources_yml: Path) -> None:
        from uiao_core.monitoring.event_processor import EventProcessor

        ep = EventProcessor(monitoring_sources_yml)
        event = ep.normalise_event(
            {"event_id": "e1", "signal": "identity_anomaly", "title": "Test", "severity": "High"},
            source="generic",
        )
        assert event.event_id == "e1"
        assert event.signal == "identity_anomaly"

    def test_evaluate_known_signal_returns_finding(self, monitoring_sources_yml: Path) -> None:
        from uiao_core.monitoring.event_processor import EventProcessor

        ep = EventProcessor(monitoring_sources_yml)
        event = ep.normalise_event(
            {"signal": "identity_anomaly", "title": "Test", "severity": "Medium"},
            source="generic",
        )
        findings = ep.evaluate(event)
        assert len(findings) == 1
        assert findings[0].control_id == "AC-2"

    def test_evaluate_unknown_signal_returns_si4_finding(self, monitoring_sources_yml: Path) -> None:
        from uiao_core.monitoring.event_processor import EventProcessor

        ep = EventProcessor(monitoring_sources_yml)
        event = ep.normalise_event(
            {"signal": "totally_unknown_signal", "title": "Mystery", "severity": "Low"},
            source="generic",
        )
        findings = ep.evaluate(event)
        assert len(findings) == 1
        assert findings[0].control_id == "SI-4"

    def test_to_poam_dict_has_fedramp_fields(self, monitoring_sources_yml: Path) -> None:
        from uiao_core.monitoring.event_processor import EventProcessor

        ep = EventProcessor(monitoring_sources_yml)
        event = ep.normalise_event(
            {"signal": "identity_anomaly", "title": "T", "severity": "High"},
            source="generic",
        )
        findings = ep.evaluate(event)
        poam = findings[0].to_poam_dict()

        # UIAO-MEMORY rule: POAM-UIAO- prefix
        assert poam["id"].startswith("POAM-UIAO-"), f"Bad id: {poam['id']}"
        # UIAO-MEMORY rule: exact FedRAMP enum values
        assert poam["status"] in ("Open", "In-Progress", "Closed")

    def test_process_sentinel_payload(self, monitoring_sources_yml: Path) -> None:
        from uiao_core.monitoring.event_processor import EventProcessor

        ep = EventProcessor(monitoring_sources_yml)
        findings = ep.process(
            {"signal": "mfa_bypass_attempt", "title": "MFA Bypass", "severity": "High"},
            source="generic",
        )
        assert any(f.control_id == "IA-2" for f in findings)

    def test_missing_sources_file_does_not_raise(self, tmp_path: Path) -> None:
        from uiao_core.monitoring.event_processor import EventProcessor

        ep = EventProcessor(tmp_path / "nonexistent.yml")
        findings = ep.process({"signal": "x", "title": "X", "severity": "Low"})
        assert isinstance(findings, list)


# ===========================================================================
# SentinelHook tests
# ===========================================================================


class TestSentinelHook:
    def test_parse_alert_native_schema(self, monitoring_sources_yml: Path, sentinel_payload: dict) -> None:
        from uiao_core.monitoring.sentinel_hook import SentinelHook

        hook = SentinelHook(monitoring_sources_path=monitoring_sources_yml)
        alert = hook.parse_alert(sentinel_payload)
        assert alert.alert_id == "alert-001"
        assert alert.severity == "High"
        assert alert.impact_level == "high"

    def test_build_poam_entry_has_fedramp_fields(self, monitoring_sources_yml: Path, sentinel_payload: dict) -> None:
        from uiao_core.monitoring.sentinel_hook import SentinelHook

        hook = SentinelHook(monitoring_sources_path=monitoring_sources_yml)
        alert = hook.parse_alert(sentinel_payload)
        entry = hook.build_poam_entry(alert, ["AC-2"])

        # UIAO-MEMORY rule: POAM-UIAO- prefix
        assert entry["id"].startswith("POAM-UIAO-"), f"Bad id: {entry['id']}"
        # UIAO-MEMORY rule: exact FedRAMP enum values
        assert entry["status"] in ("Open", "In-Progress", "Closed")
        assert entry["control-ids"] == ["AC-2"]

    def test_map_controls_returns_list(self, monitoring_sources_yml: Path, sentinel_payload: dict) -> None:
        from uiao_core.monitoring.sentinel_hook import SentinelHook

        hook = SentinelHook(monitoring_sources_path=monitoring_sources_yml)
        alert = hook.parse_alert(sentinel_payload)
        controls = hook.map_alert_to_controls(alert)
        assert isinstance(controls, list)

    def test_upsert_poam_entry_writes_file(
        self, monitoring_sources_yml: Path, sentinel_payload: dict, tmp_path: Path
    ) -> None:
        from uiao_core.monitoring.sentinel_hook import SentinelHook

        poam_file = tmp_path / "poam.yml"
        hook = SentinelHook(monitoring_sources_path=monitoring_sources_yml)
        alert = hook.parse_alert(sentinel_payload)
        hook.upsert_poam_entry(alert, poam_path=poam_file)

        assert poam_file.exists()
        findings = yaml.safe_load(poam_file.read_text())
        assert isinstance(findings, list)
        assert len(findings) == 1
        assert findings[0]["id"].startswith("POAM-UIAO-")

    def test_upsert_poam_entry_deduplicates(
        self, monitoring_sources_yml: Path, sentinel_payload: dict, tmp_path: Path
    ) -> None:
        from uiao_core.monitoring.sentinel_hook import SentinelHook

        poam_file = tmp_path / "poam.yml"
        hook = SentinelHook(monitoring_sources_path=monitoring_sources_yml)
        alert = hook.parse_alert(sentinel_payload)
        hook.upsert_poam_entry(alert, poam_path=poam_file)
        hook.upsert_poam_entry(alert, poam_path=poam_file)

        findings = yaml.safe_load(poam_file.read_text())
        # Same alert ID → should not grow beyond 1 entry
        assert len(findings) == 1

    def test_handle_webhook_returns_summary(self, monitoring_sources_yml: Path, sentinel_payload: dict) -> None:
        from uiao_core.monitoring.sentinel_hook import SentinelHook

        hook = SentinelHook(monitoring_sources_path=monitoring_sources_yml)
        result = hook.handle_webhook(sentinel_payload, auto_upsert_poam=False)
        assert "alert_id" in result
        assert "control_ids" in result
        assert result["poam_entry"] is None


# ===========================================================================
# OngoingAuthGenerator tests
# ===========================================================================


class TestOngoingAuthGenerator:
    def test_generate_returns_oscal_structure(self, monitoring_sources_yml: Path, ksi_mappings_yml: Path) -> None:
        from uiao_core.monitoring.ongoing_auth import OngoingAuthGenerator

        gen = OngoingAuthGenerator(monitoring_sources_yml, ksi_mappings_yml)
        doc = gen.generate()
        oa = doc["ongoing-authorization"]
        assert "uuid" in oa
        assert "observations" in oa
        assert len(oa["observations"]) > 0

    def test_observations_have_control_id_prop(self, monitoring_sources_yml: Path, ksi_mappings_yml: Path) -> None:
        from uiao_core.monitoring.ongoing_auth import OngoingAuthGenerator

        gen = OngoingAuthGenerator(monitoring_sources_yml, ksi_mappings_yml)
        doc = gen.generate()
        obs = doc["ongoing-authorization"]["observations"]
        for ob in obs:
            prop_names = [p["name"] for p in ob.get("props", [])]
            assert "control-id" in prop_names, f"Missing control-id prop in {ob['title']}"

    def test_relevant_evidence_has_prop_id(self, monitoring_sources_yml: Path, ksi_mappings_yml: Path) -> None:
        """UIAO-MEMORY rule: every link must have prop:id."""
        from uiao_core.monitoring.ongoing_auth import OngoingAuthGenerator

        gen = OngoingAuthGenerator(monitoring_sources_yml, ksi_mappings_yml)
        doc = gen.generate()
        obs = doc["ongoing-authorization"]["observations"]
        for ob in obs:
            for ev in ob.get("relevant-evidence", []):
                ev_prop_names = [p["name"] for p in ev.get("props", [])]
                assert "prop:id" in ev_prop_names, f"Missing prop:id on relevant-evidence in {ob['title']}"

    def test_export_writes_valid_json(
        self, monitoring_sources_yml: Path, ksi_mappings_yml: Path, tmp_path: Path
    ) -> None:
        from uiao_core.monitoring.ongoing_auth import OngoingAuthGenerator

        gen = OngoingAuthGenerator(monitoring_sources_yml, ksi_mappings_yml)
        out = tmp_path / "oa.json"
        path = gen.export(out)
        assert path.exists()
        doc = json.loads(path.read_text())
        assert "ongoing-authorization" in doc

    def test_missing_files_do_not_raise(self, tmp_path: Path) -> None:
        from uiao_core.monitoring.ongoing_auth import OngoingAuthGenerator

        gen = OngoingAuthGenerator(tmp_path / "no-monitoring.yml", tmp_path / "no-ksi.yml")
        doc = gen.generate()
        assert doc["ongoing-authorization"]["observations"] == []


# ===========================================================================
# KSICalculator tests
# ===========================================================================


class TestKSICalculator:
    def test_score_returns_correct_counts(self, ksi_mappings_yml: Path) -> None:
        from uiao_core.dashboard.ksi import KSICalculator

        calc = KSICalculator(ksi_mappings_yml)
        score = calc.score()
        assert score["total"] == 3
        assert score["implemented"] == 1
        assert score["partial"] == 1
        assert score["planned"] == 1

    def test_score_percentage_calculation(self, ksi_mappings_yml: Path) -> None:
        from uiao_core.dashboard.ksi import KSICalculator

        calc = KSICalculator(ksi_mappings_yml)
        score = calc.score()
        # 1 implemented * 1.0 + 1 partial * 0.5 = 1.5 / 3 = 50%
        assert score["percentage"] == 50.0

    def test_controls_covered_deduplicates(self, ksi_mappings_yml: Path) -> None:
        from uiao_core.dashboard.ksi import KSICalculator

        calc = KSICalculator(ksi_mappings_yml)
        controls = calc.controls_covered()
        assert len(controls) == len(set(controls))

    def test_missing_file_returns_empty_score(self, tmp_path: Path) -> None:
        from uiao_core.dashboard.ksi import KSICalculator

        calc = KSICalculator(tmp_path / "nonexistent.yml")
        score = calc.score()
        assert score["total"] == 0
        assert score["percentage"] == 0.0


# ===========================================================================
# DashboardExporter tests
# ===========================================================================


class TestDashboardExporter:
    def test_export_json_creates_file(self, ksi_mappings_yml: Path, tmp_path: Path) -> None:
        from uiao_core.dashboard.export import DashboardExporter

        exporter = DashboardExporter(ksi_mappings_yml)
        out = tmp_path / "dashboard.json"
        path = exporter.export_json(out)
        assert path.exists()
        data = json.loads(path.read_text())
        assert "ksi_summary" in data
        assert "ksi_items" in data

    def test_export_yaml_creates_file(self, ksi_mappings_yml: Path, tmp_path: Path) -> None:
        from uiao_core.dashboard.export import DashboardExporter

        exporter = DashboardExporter(ksi_mappings_yml)
        out = tmp_path / "dashboard.yml"
        path = exporter.export_yaml(out)
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert "ksi_summary" in data

    def test_report_contains_fedramp_fields(self, ksi_mappings_yml: Path) -> None:
        from uiao_core.dashboard.export import DashboardExporter

        exporter = DashboardExporter(ksi_mappings_yml)
        report = exporter._build_report()
        assert report["oscal_version"] == "1.0.4"
        assert report["fedramp_impact_level"] == "moderate"
        assert "readiness_percentage" in report["ksi_summary"]
