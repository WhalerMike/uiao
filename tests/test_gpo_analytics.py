"""Tests for the Phase-1 GPO settings-level analyzer.

Covers gpreport.xml parsing, setting-class + portability classification,
scope-link extraction, finding emission, the Backup-GPO tree walker, and
JSON-Schema conformance of the emitted output. All offline — no live AD,
no Graph.

Canon reference: GPO settings analyzer (Phase 1).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from uiao.adapters.modernization.active_directory.gpo_analytics import (
    ANALYSIS_VERSION,
    PORTABILITY_CLASSES,
    GpoReport,
    analyze_backup,
    classify_extension,
    parse_gpo_report,
    parse_gpo_report_file,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "gpo" / "backup"
_ADMIN = _FIXTURES / "{A1111111-1111-1111-1111-111111111111}" / "gpreport.xml"
_SECURITY = _FIXTURES / "{B2222222-2222-2222-2222-222222222222}" / "gpreport.xml"
_PREFS = _FIXTURES / "{C3333333-3333-3333-3333-333333333333}" / "gpreport.xml"
_EMPTY = _FIXTURES / "{D4444444-4444-4444-4444-444444444444}" / "gpreport.xml"
_MIXED = _FIXTURES / "{E5555555-5555-5555-5555-555555555555}" / "gpreport.xml"


# ---------------------------------------------------------------------------
# Single-report parsing
# ---------------------------------------------------------------------------


def test_admin_template_report_parses_identity_and_links() -> None:
    report = parse_gpo_report_file(_ADMIN)
    assert report.guid == "{A1111111-1111-1111-1111-111111111111}"
    assert report.name == "Finance Workstations Policy"
    assert report.computer_enabled is True
    assert report.user_enabled is False
    assert report.modified_time == "2023-06-01T12:30:00"
    assert len(report.links) == 1
    link = report.links[0]
    assert link.som_name == "Finance"
    assert link.som_path == "corp.contoso.com/Finance"
    assert link.enabled is True
    assert link.enforced is False


def test_admin_template_settings_are_csp_mappable() -> None:
    report = parse_gpo_report_file(_ADMIN)
    assert report.setting_count == 3
    names = {s.setting_name for s in report.settings}
    assert "Configure Automatic Updates" in names
    assert all(s.setting_class == "admin-template" for s in report.settings)
    assert all(s.portability_class == "csp-mappable" for s in report.settings)
    assert all(s.scope == "Computer" for s in report.settings)
    one = next(s for s in report.settings if s.setting_name == "Turn off Autoplay")
    assert one.state == "Enabled"
    assert one.category == "Windows Components/AutoPlay Policies"
    assert report.hardest_portability == "csp-mappable"


def test_security_settings_classified_partial() -> None:
    report = parse_gpo_report_file(_SECURITY)
    assert report.setting_count == 3
    assert all(s.setting_class == "security" for s in report.settings)
    assert all(s.portability_class == "partial" for s in report.settings)
    names = {s.setting_name for s in report.settings}
    assert {"MinimumPasswordLength", "PasswordComplexity", "SeRemoteInteractiveLogonRight"} == names
    # Enforced domain-root link.
    assert report.links[0].enforced is True


def test_preferences_and_scripts_need_platform_scripts() -> None:
    report = parse_gpo_report_file(_PREFS)
    # 1 script + 2 drive maps, all User scope.
    assert report.setting_count == 3
    assert all(s.scope == "User" for s in report.settings)
    classes = {s.setting_class for s in report.settings}
    assert classes == {"script", "preference"}
    assert all(s.portability_class == "needs-platform-script" for s in report.settings)
    # Drive name comes from the @name attribute fallback.
    drive_names = {s.setting_name for s in report.settings if s.setting_class == "preference"}
    assert drive_names == {"H: (Home)", "S: (Shared)"}
    # WMI filter captured.
    assert report.wmi_filter == "Workstations Only (WMI)"
    assert len(report.links) == 2


def test_mixed_gpo_flags_unknown_extension_and_picks_hardest() -> None:
    report = parse_gpo_report_file(_MIXED)
    # admin-template (1) + unknown vendor widget (1) + folder-redirection (1).
    assert report.setting_count == 3
    by_class = report.counts_by_class()
    assert by_class["admin-template"] == 1
    assert by_class["unknown"] == 1
    assert by_class["folder-redirection"] == 1
    # Unknown extension surfaces a GOV-GPO-001 finding carrying the GUID.
    codes = {f.code for f in report.findings}
    assert "GOV-GPO-001" in codes
    assert any(f.gpo_guid == report.guid for f in report.findings if f.code == "GOV-GPO-001")
    # review-required is the hardest class present.
    assert report.hardest_portability == "review-required"


def test_empty_gpo_emits_no_settings_finding() -> None:
    report = parse_gpo_report_file(_EMPTY)
    assert report.setting_count == 0
    assert "GOV-GPO-002" in {f.code for f in report.findings}
    # Empty GPO degrades gracefully to the easiest headline class.
    assert report.hardest_portability == "csp-mappable"


# ---------------------------------------------------------------------------
# Classification unit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("type_local", "ns", "expected_class", "expected_port"),
    [
        ("RegistrySettings", "http://x/Settings/Registry", "admin-template", "csp-mappable"),
        ("SecuritySettings", "http://x/Settings/Security", "security", "partial"),
        ("Scripts", "http://x/Settings/Scripts", "script", "needs-platform-script"),
        ("SoftwareInstallationSettings", "http://x/Settings/Sw", "software-install", "no-csp"),
        ("InternetExplorerSettings", "http://x/Settings/IE", "ie-maintenance", "deprecated"),
        # Preferences namespace wins even when the local name collides with a policy type.
        ("RegistrySettings", "http://x/Settings/Preferences/Registry", "preference", "needs-platform-script"),
        ("WhoKnowsSettings", "http://x/Settings/Other", "unknown", "review-required"),
    ],
)
def test_classify_extension(type_local: str, ns: str, expected_class: str, expected_port: str) -> None:
    setting_class, portability = classify_extension(type_local, ns)
    assert setting_class == expected_class
    assert portability == expected_port
    if portability != "review-required":
        assert portability in PORTABILITY_CLASSES


def test_malformed_xml_raises_in_single_parse() -> None:
    import xml.etree.ElementTree as ET

    with pytest.raises(ET.ParseError):
        parse_gpo_report("<GPO><Computer></GPO>")


# ---------------------------------------------------------------------------
# Backup-tree walk
# ---------------------------------------------------------------------------


def test_analyze_backup_walks_tree_and_isolates_bad_report() -> None:
    analysis = analyze_backup(_FIXTURES)
    assert analysis.version == ANALYSIS_VERSION
    # Five well-formed GPOs parse; the malformed/ one becomes a finding.
    assert analysis.gpo_count == 5
    guids = {r.guid for r in analysis.reports}
    assert "{A1111111-1111-1111-1111-111111111111}" in guids
    # The malformed backup is isolated, not fatal.
    assert "GOV-GPO-003" in {f.code for f in analysis.findings}
    # Portability rollup aggregates across GPOs.
    rollup = analysis.rollup_by_portability()
    assert rollup["csp-mappable"] >= 3
    assert rollup["partial"] == 3
    assert rollup["needs-platform-script"] == 3
    assert analysis.total_settings == sum(r.setting_count for r in analysis.reports)


def test_analyze_backup_empty_directory(tmp_path: Path) -> None:
    analysis = analyze_backup(tmp_path)
    assert analysis.gpo_count == 0
    assert "GOV-GPO-004" in {f.code for f in analysis.findings}


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------


def _schema() -> dict:
    # The schema dir name (gpo-analytics) is not a valid Python package name,
    # so it is read by filesystem path rather than importlib.resources.
    schema_path = (
        Path(__file__).parent.parent / "src" / "uiao" / "schemas" / "gpo-analytics" / "gpo-analytics.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_schema_is_valid_draft7() -> None:
    jsonschema.Draft7Validator.check_schema(_schema())


def test_analysis_output_validates_against_schema() -> None:
    analysis = analyze_backup(_FIXTURES)
    jsonschema.validate(instance=analysis.to_dict(), schema=_schema())


def test_single_report_dict_round_trips() -> None:
    report: GpoReport = parse_gpo_report_file(_ADMIN)
    payload = report.to_dict()
    assert payload["summary"]["setting_count"] == 3
    assert payload["summary"]["hardest_portability"] == "csp-mappable"
    # to_dict is JSON-serializable.
    assert json.loads(json.dumps(payload))["guid"] == report.guid
