"""
tests/test_arc_readiness.py
---------------------------
Unit + fixture tests for the Azure Arc readiness adapter.

Canon reference: computer-object-crosswalk.yaml (XW-009, XW-010), ADR-038
Adapter module:  uiao.adapters.modernization.active_directory.arc_readiness
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from uiao.adapters.modernization.active_directory.arc_readiness import (
    ARC_EGRESS_ENDPOINTS,
    ArcReadinessSummary,
    _is_linux_server_os,
    assess_fleet_arc_readiness,
    assess_server_arc_readiness,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXTURES_PATH = Path(__file__).parent / "fixtures" / "orgtree" / "arc-readiness-servers.json"


def _load_fixtures() -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = json.loads(_FIXTURES_PATH.read_text())
    return raw


# ---------------------------------------------------------------------------
# Egress endpoint matrix smoke test
# ---------------------------------------------------------------------------


class TestEgressEndpoints:
    def test_all_required_categories_present(self) -> None:
        """The endpoint matrix must contain all documented categories."""
        required_categories = {
            "arc_agent_core",
            "azure_management",
            "authentication",
            "arc_obo_proxy",
            "esu_and_hybrid_runbook",
            "agent_download",
        }
        assert required_categories <= set(ARC_EGRESS_ENDPOINTS.keys())

    def test_well_known_endpoints_present(self) -> None:
        all_endpoints = [ep for eps in ARC_EGRESS_ENDPOINTS.values() for ep in eps]
        must_include = [
            "*.guestconfiguration.azure.com",
            "*.his.arc.azure.com",
            "management.azure.com",
            "login.windows.net",
            "login.microsoftonline.com",
            "gbl.his.arc.azure.com",
            "<region>.obo.arc.azure.com",
            "*.servicebus.windows.net",
            "download.microsoft.com",
        ]
        for ep in must_include:
            assert ep in all_endpoints, f"Missing required endpoint: {ep}"

    def test_no_empty_category(self) -> None:
        for category, endpoints in ARC_EGRESS_ENDPOINTS.items():
            assert len(endpoints) > 0, f"Category '{category}' has no endpoints"


# ---------------------------------------------------------------------------
# A3: Linux distro detection robustness — real-world OS string variants
# ---------------------------------------------------------------------------


class TestLinuxDistroNormalization:
    """A3: normalized matcher handles real-world operatingSystem field variants."""

    @pytest.mark.parametrize(
        "os_string",
        [
            # RHEL variants
            "Red Hat Enterprise Linux 8.9",
            "Red Hat Enterprise Linux Server release 8.9 (Ootpa)",
            "RHEL 8.9",
            "RHEL9",
            # Ubuntu variants
            "Ubuntu Server 22.04",
            "Ubuntu Server 22.04 LTS",
            "Ubuntu 22.04 LTS Server",
            "ubuntu-server-22.04",
            # SLES variants
            "SUSE Linux Enterprise Server 15 SP5",
            "SLES 15",
            "SLES15SP4",
            # CentOS variants
            "CentOS 7",
            "CentOS Linux 7 (Core)",
            "CentOS Stream 9",
            # Oracle Linux variants
            "Oracle Linux 8.8",
            "Oracle Linux Server 7.9",
            "OracleLinux8",
            # Rocky Linux variants
            "Rocky Linux 9.2",
            "Rocky Linux release 9.2 (Blue Onyx)",
            "RockyLinux9",
            # AlmaLinux variants
            "AlmaLinux 9.1",
            "AlmaLinux OS 9.1 (Lime Lynx)",
            "Almalinux9",
            # Debian variants
            "Debian 12",
            "Debian GNU/Linux 11 (bullseye)",
            "Debian GNU/Linux 10",
        ],
    )
    def test_linux_server_os_detected(self, os_string: str) -> None:
        assert _is_linux_server_os(os_string), f"Expected server OS detection for: {os_string!r}"

    @pytest.mark.parametrize(
        "os_string",
        [
            "Windows 10 Enterprise",
            "Windows 11 Pro",
            "macOS 14.2",
            "Android 13",
            "FreeBSD 13",  # not in supported list
        ],
    )
    def test_non_linux_server_not_detected(self, os_string: str) -> None:
        assert not _is_linux_server_os(os_string), f"Expected no detection for: {os_string!r}"

    @pytest.mark.parametrize(
        "os_string",
        [
            "Red Hat Enterprise Linux 8.9",
            "Red Hat Enterprise Linux Server release 8.9 (Ootpa)",
            "RHEL 9.2",
            "Ubuntu Server 22.04 LTS",
            "Ubuntu 22.04 LTS Server",
            "ubuntu-server-22.04",
            "SUSE Linux Enterprise Server 15 SP5",
            "SLES 15",
            "Oracle Linux Server 7.9",
            "Rocky Linux release 9.2 (Blue Onyx)",
            "AlmaLinux OS 9.1 (Lime Lynx)",
            "Debian GNU/Linux 11 (bullseye)",
        ],
    )
    def test_real_world_variants_get_ready_verdict(self, os_string: str) -> None:
        result = assess_server_arc_readiness(
            computer_name="LNX-SRV",
            distinguished_name="CN=LNX-SRV,OU=S,DC=corp,DC=com",
            operating_system=os_string,
            network_egress_validated=True,
        )
        assert result.verdict == "READY", (
            f"Expected READY for {os_string!r}, got {result.verdict!r}. Notes: {result.notes}"
        )


# ---------------------------------------------------------------------------
# NOT_SERVER detection
# ---------------------------------------------------------------------------


class TestNotServer:
    @pytest.mark.parametrize(
        "os_version",
        [
            "Windows 10 Enterprise",
            "Windows 11 Pro",
            "macOS 14.2",
            "Mac OS X 12.7",
        ],
    )
    def test_client_os_is_not_server(self, os_version: str) -> None:
        result = assess_server_arc_readiness(
            computer_name="CLIENT-001",
            distinguished_name="CN=CLIENT-001,OU=WS,DC=corp,DC=com",
            operating_system=os_version,
        )
        assert result.verdict == "NOT_SERVER"


# ---------------------------------------------------------------------------
# INELIGIBLE verdicts
# ---------------------------------------------------------------------------


class TestIneligible:
    @pytest.mark.parametrize(
        "os_version",
        [
            "Windows Server 2003 Standard",
            "Windows Server 2008 Enterprise",
            "Windows Server 2008 R2 Enterprise",
        ],
    )
    def test_eol_windows_server_is_ineligible(self, os_version: str) -> None:
        result = assess_server_arc_readiness(
            computer_name="SRV-EOL",
            distinguished_name="CN=SRV-EOL,OU=S,DC=corp,DC=com",
            operating_system=os_version,
            network_egress_validated=True,
        )
        assert result.verdict == "INELIGIBLE"
        assert result.os_gate_reason  # must supply a reason

    def test_domain_controller_by_role_is_ineligible(self) -> None:
        result = assess_server_arc_readiness(
            computer_name="DC01",
            distinguished_name="CN=DC01,OU=DomainControllers,DC=corp,DC=com",
            operating_system="Windows Server 2022 Standard",
            installed_roles=["Active Directory Domain Services", "DNS Server"],
            network_egress_validated=True,
        )
        assert result.verdict == "INELIGIBLE"
        assert "Domain Controller" in result.os_gate_reason

    def test_domain_controller_by_name_is_ineligible(self) -> None:
        result = assess_server_arc_readiness(
            computer_name="DC01",
            distinguished_name="CN=DC01,OU=DomainControllers,DC=corp,DC=com",
            operating_system="Windows Server 2019 Datacenter",
            installed_roles=[],
            network_egress_validated=True,
        )
        assert result.verdict == "INELIGIBLE"

    def test_unknown_windows_server_is_ineligible(self) -> None:
        result = assess_server_arc_readiness(
            computer_name="SRV-FUTURE",
            distinguished_name="CN=SRV-FUTURE,OU=S,DC=corp,DC=com",
            operating_system="Windows Server 2099 Special Edition",
            network_egress_validated=True,
        )
        assert result.verdict == "INELIGIBLE"


# ---------------------------------------------------------------------------
# NEEDS_OS_UPGRADE verdicts
# ---------------------------------------------------------------------------


class TestNeedsOsUpgrade:
    @pytest.mark.parametrize(
        "os_version",
        [
            "Windows Server 2012 Standard",
            "Windows Server 2012 Datacenter",
            "Windows Server 2012 R2 Standard",
            "Windows Server 2012 R2 Datacenter",
        ],
    )
    def test_2012_needs_upgrade(self, os_version: str) -> None:
        result = assess_server_arc_readiness(
            computer_name="SRV-2012",
            distinguished_name="CN=SRV-2012,OU=S,DC=corp,DC=com",
            operating_system=os_version,
            network_egress_validated=True,
        )
        assert result.verdict == "NEEDS_OS_UPGRADE"
        assert "ESU" in result.notes or "upgrade" in result.notes.lower()

    def test_needs_os_upgrade_takes_precedence_over_network(self) -> None:
        """NEEDS_OS_UPGRADE must rank higher than NEEDS_NETWORK_EGRESS."""
        result = assess_server_arc_readiness(
            computer_name="SRV-2012-NOEGRESS",
            distinguished_name="CN=SRV-2012-NOEGRESS,OU=S,DC=corp,DC=com",
            operating_system="Windows Server 2012 R2 Standard",
            network_egress_validated=False,  # would trigger NEEDS_NETWORK_EGRESS if OS were OK
        )
        assert result.verdict == "NEEDS_OS_UPGRADE"


# ---------------------------------------------------------------------------
# NEEDS_NETWORK_EGRESS verdicts
# ---------------------------------------------------------------------------


class TestNeedsNetworkEgress:
    def test_egress_false_downgrades_ready_to_network(self) -> None:
        result = assess_server_arc_readiness(
            computer_name="SRV-2019-NONET",
            distinguished_name="CN=SRV-2019-NONET,OU=S,DC=corp,DC=com",
            operating_system="Windows Server 2019 Standard",
            network_egress_validated=False,
        )
        assert result.verdict == "NEEDS_NETWORK_EGRESS"

    def test_strict_mode_none_egress_downgrades(self) -> None:
        result = assess_server_arc_readiness(
            computer_name="SRV-2022-UNKNOWN",
            distinguished_name="CN=SRV-2022-UNKNOWN,OU=S,DC=corp,DC=com",
            operating_system="Windows Server 2022 Datacenter",
            network_egress_validated=None,
            strict_network_mode=True,
        )
        assert result.verdict == "NEEDS_NETWORK_EGRESS"

    def test_non_strict_mode_none_egress_is_ready(self) -> None:
        """Without strict mode, unknown egress does NOT downgrade."""
        result = assess_server_arc_readiness(
            computer_name="SRV-2022-UNKNOWN",
            distinguished_name="CN=SRV-2022-UNKNOWN,OU=S,DC=corp,DC=com",
            operating_system="Windows Server 2022 Datacenter",
            network_egress_validated=None,
            strict_network_mode=False,
        )
        assert result.verdict == "READY"


# ---------------------------------------------------------------------------
# READY verdicts
# ---------------------------------------------------------------------------


class TestReady:
    @pytest.mark.parametrize(
        "os_version",
        [
            "Windows Server 2016 Standard",
            "Windows Server 2016 Datacenter",
            "Windows Server 2019 Standard",
            "Windows Server 2019 Datacenter",
            "Windows Server 2022 Standard",
            "Windows Server 2022 Datacenter",
            "Windows Server 2025 Standard",
        ],
    )
    def test_supported_windows_server_ready(self, os_version: str) -> None:
        result = assess_server_arc_readiness(
            computer_name="SRV-GOOD",
            distinguished_name="CN=SRV-GOOD,OU=S,DC=corp,DC=com",
            operating_system=os_version,
            network_egress_validated=True,
        )
        assert result.verdict == "READY"

    @pytest.mark.parametrize(
        "os_version",
        [
            "Red Hat Enterprise Linux 8.9",
            "RHEL 9.2",
            "CentOS 7",
            "Ubuntu Server 22.04 LTS",
            "SUSE Linux Enterprise Server 15 SP5",
            "Oracle Linux 8.8",
            "Rocky Linux 9.2",
            "AlmaLinux 9.1",
            "Debian 12",
        ],
    )
    def test_linux_distros_ready(self, os_version: str) -> None:
        result = assess_server_arc_readiness(
            computer_name="LNX-SRV",
            distinguished_name="CN=LNX-SRV,OU=S,DC=corp,DC=com",
            operating_system=os_version,
            network_egress_validated=True,
        )
        assert result.verdict == "READY"


# ---------------------------------------------------------------------------
# Fixture-driven tests — pin every verdict for the fixture file
# ---------------------------------------------------------------------------


class TestFixtureVerdicts:
    """Pin the expected verdict for every record in arc-readiness-servers.json."""

    # Expected verdicts keyed on computer name
    EXPECTED: dict[str, str] = {
        "SRV-APP-2012R2": "NEEDS_OS_UPGRADE",
        "SRV-FILE-2012": "NEEDS_OS_UPGRADE",
        "SRV-WEB-2016": "READY",
        "SRV-SQL-2019": "READY",
        "SRV-APP-2022": "READY",
        "SRV-WEB-2019-NO-EGRESS": "NEEDS_NETWORK_EGRESS",
        "LNX-RHEL-APP01": "READY",
        "LNX-UBUNTU-WEB01": "READY",
        "DC01": "INELIGIBLE",
        "LAPTOP-USR-001": "NOT_SERVER",
        "SRV-LEGACY-2008R2": "INELIGIBLE",
        # null egress without strict mode → READY
        "SRV-APP-2022-UNKNOWN-EGRESS": "READY",
    }

    def test_all_fixture_records_have_expected_verdict(self) -> None:
        records = _load_fixtures()
        assert len(records) >= 10, "Fixture must contain at least 10 records"

    @pytest.mark.parametrize("record", _load_fixtures())
    def test_verdict_per_fixture_record(self, record: dict) -> None:
        name = record["name"]
        expected = self.EXPECTED.get(name)
        assert expected is not None, f"No expected verdict configured for fixture record '{name}'"

        result = assess_server_arc_readiness(
            computer_name=record["name"],
            distinguished_name=record["distinguishedName"],
            operating_system=record["operatingSystem"],
            installed_roles=record.get("installedRoles", []),
            network_egress_validated=record.get("network_egress_validated"),
            strict_network_mode=False,
        )
        assert result.verdict == expected, (
            f"[{name}] expected {expected!r}, got {result.verdict!r}. Notes: {result.notes}"
        )


# ---------------------------------------------------------------------------
# Fleet / batch assessment
# ---------------------------------------------------------------------------


class TestFleetAssessment:
    def test_batch_summary_counts_match_fixture(self) -> None:
        records = _load_fixtures()
        summary: ArcReadinessSummary = assess_fleet_arc_readiness(records, strict_network_mode=False)

        assert summary.total_records == len(records)
        assert summary.not_server == 1  # LAPTOP-USR-001
        assert summary.total_servers == len(records) - 1
        assert summary.ready == 6  # 2016, 2019, 2022, RHEL, Ubuntu, 2022-UNKNOWN-EGRESS (non-strict)
        assert summary.needs_os_upgrade == 2  # 2012R2 + 2012
        assert summary.needs_network_egress == 1  # SRV-WEB-2019-NO-EGRESS
        assert summary.ineligible == 2  # DC01 + 2008R2
        # SRV-APP-2022-UNKNOWN-EGRESS → READY in non-strict mode
        assert (
            summary.ready + summary.needs_os_upgrade + summary.needs_network_egress + summary.ineligible
            == summary.total_servers
        )

    def test_batch_strict_mode_downgrades_unknown_egress(self) -> None:
        records = _load_fixtures()
        summary = assess_fleet_arc_readiness(records, strict_network_mode=True)
        # SRV-APP-2022-UNKNOWN-EGRESS should now be NEEDS_NETWORK_EGRESS
        assert summary.needs_network_egress == 2

    def test_as_dict_is_serialisable(self) -> None:
        records = _load_fixtures()
        summary = assess_fleet_arc_readiness(records)
        d = summary.as_dict()
        assert isinstance(d, dict)
        assert "results" in d
        assert d["arc_enrollable"] == summary.ready

    def test_result_as_dict(self) -> None:
        result = assess_server_arc_readiness(
            computer_name="SRV-TEST",
            distinguished_name="CN=SRV-TEST,OU=S,DC=corp,DC=com",
            operating_system="Windows Server 2022 Standard",
            network_egress_validated=True,
        )
        d = result.as_dict()
        assert d["verdict"] == "READY"
        assert "computer_name" in d
