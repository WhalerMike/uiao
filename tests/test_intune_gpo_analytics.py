"""Tests for the Phase-2 Intune Group Policy Analytics adapter + verdict join.

The Graph-calling methods are exercised with an offline recorder transport
(canned ``groupPolicySettingMappings`` JSON, including ``@odata.nextLink``
pagination). The :func:`apply_mdm_verdicts` join is pure and needs no
transport.

Canon reference: GPO settings analyzer (Phase 2).
"""

from __future__ import annotations

import base64
from pathlib import Path

from uiao.adapters.intune_gpo_analytics import (
    IntuneGpoAnalyticsAdapter,
    SettingMapping,
    apply_mdm_verdicts,
    summarize_mappings,
)
from uiao.adapters.modernization.active_directory.gpo_analytics import parse_gpo_report_file

_FIXTURES = Path(__file__).parent / "fixtures" / "gpo" / "backup"
_ADMIN = _FIXTURES / "{A1111111-1111-1111-1111-111111111111}" / "gpreport.xml"


class _RecorderTransport:
    """A fake ``(method, path, body) -> dict`` transport with scripted replies."""

    def __init__(self, replies: dict[tuple[str, str], dict]) -> None:
        self._replies = replies
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict:
        self.calls.append((method, path, body))
        return self._replies[(method, path)]


# ---------------------------------------------------------------------------
# Graph-calling methods (offline recorder)
# ---------------------------------------------------------------------------


def test_create_migration_report_base64_encodes_and_returns_id() -> None:
    transport = _RecorderTransport(
        {("POST", "/deviceManagement/groupPolicyMigrationReports/createMigrationReport"): {"id": "report-123"}}
    )
    adapter = IntuneGpoAnalyticsAdapter(transport)
    report_id = adapter.create_migration_report("<GPO>x</GPO>", ou_dn="OU=Finance,DC=corp")
    assert report_id == "report-123"
    method, path, body = transport.calls[0]
    assert method == "POST"
    assert body is not None
    file_block = body["groupPolicyObjectFile"]
    assert file_block["ouDistinguishedName"] == "OU=Finance,DC=corp"
    # Content is base64 of the raw XML.
    assert base64.b64decode(file_block["content"]).decode() == "<GPO>x</GPO>"


def test_fetch_setting_mappings_follows_pagination() -> None:
    base = "/deviceManagement/groupPolicyMigrationReports/r1/groupPolicySettingMappings"
    transport = _RecorderTransport(
        {
            ("GET", base): {
                "value": [{"settingName": "Configure Automatic Updates", "isMdmSupported": True}],
                "@odata.nextLink": base + "?$skiptoken=2",
            },
            ("GET", base + "?$skiptoken=2"): {
                "value": [{"settingName": "Turn off Autoplay", "isMdmSupported": False}],
            },
        }
    )
    adapter = IntuneGpoAnalyticsAdapter(transport)
    mappings = adapter.fetch_setting_mappings("r1")
    assert [m.setting_name for m in mappings] == ["Configure Automatic Updates", "Turn off Autoplay"]
    assert [m.is_mdm_supported for m in mappings] == [True, False]
    # Two GETs: page 1 + nextLink page 2.
    assert sum(1 for c in transport.calls if c[0] == "GET") == 2


def test_page_cap_bounds_runaway_pagination() -> None:
    base = "/deviceManagement/groupPolicyMigrationReports/loop/groupPolicySettingMappings"
    # A pathological tenant that always returns a nextLink to itself.
    transport = _RecorderTransport({("GET", base): {"value": [], "@odata.nextLink": base}})
    adapter = IntuneGpoAnalyticsAdapter(transport, page_cap=3)
    mappings = adapter.fetch_setting_mappings("loop")
    assert mappings == []
    assert sum(1 for c in transport.calls if c[0] == "GET") == 3


def test_setting_mapping_from_graph_tolerates_missing_fields() -> None:
    m = SettingMapping.from_graph({"settingName": "X", "isMdmSupported": True})
    assert m.mdm_setting_uri == ""
    assert m.setting_category == ""
    assert m.is_mdm_supported is True


# ---------------------------------------------------------------------------
# The pure verdict join
# ---------------------------------------------------------------------------


def test_apply_mdm_verdicts_overrides_heuristic() -> None:
    report = parse_gpo_report_file(_ADMIN)
    # Pre-join: heuristic says everything is csp-mappable, verdict heuristic.
    assert all(s.verdict_source == "heuristic" for s in report.settings)

    mappings = [
        SettingMapping("Configure Automatic Updates", True, mdm_setting_uri="./Device/Vendor/MSFT/Policy/AU"),
        SettingMapping("Turn off Autoplay", False),
        # Whitespace / case differences must still match.
        SettingMapping("specify   intranet microsoft update service location", True),
    ]
    enriched = apply_mdm_verdicts(report, mappings)

    by_name = {s.setting_name: s for s in enriched.settings}
    au = by_name["Configure Automatic Updates"]
    assert au.verdict_source == "intune-gpa"
    assert au.mdm_supported is True
    assert au.portability_class == "csp-mappable"
    assert au.mdm_uri == "./Device/Vendor/MSFT/Policy/AU"

    autoplay = by_name["Turn off Autoplay"]
    assert autoplay.mdm_supported is False
    assert autoplay.portability_class == "no-csp"
    assert autoplay.verdict_source == "intune-gpa"

    intranet = by_name["Specify intranet Microsoft update service location"]
    assert intranet.verdict_source == "intune-gpa"
    assert intranet.portability_class == "csp-mappable"


def test_apply_mdm_verdicts_leaves_unmatched_settings_untouched() -> None:
    report = parse_gpo_report_file(_ADMIN)
    enriched = apply_mdm_verdicts(report, [SettingMapping("Some Unrelated Setting", True)])
    assert all(s.verdict_source == "heuristic" for s in enriched.settings)
    # Original report is not mutated (pure).
    assert all(s.mdm_supported is None for s in report.settings)


def test_summarize_mappings_rollup() -> None:
    summary = summarize_mappings(
        [
            SettingMapping("a", True),
            SettingMapping("b", True),
            SettingMapping("c", False),
        ]
    )
    assert summary.total == 3
    assert summary.supported == 2
    assert summary.unsupported == 1
    assert summary.support_pct == 66.7
    assert summary.to_dict()["support_pct"] == 66.7


def test_summarize_empty_is_zero_pct() -> None:
    assert summarize_mappings([]).support_pct == 0.0
