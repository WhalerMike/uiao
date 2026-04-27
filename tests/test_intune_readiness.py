"""
tests/test_intune_readiness.py
-------------------------------
Unit tests for UIAO WS-A2: AD Computer → Intune readiness assessment.

Canon ref: computer-object-crosswalk.yaml (XW-INI-*), Appendix GAE, ADR-038
Module:    uiao.adapters.modernization.active_directory.intune_readiness
"""

from __future__ import annotations

import json
from pathlib import Path

from uiao.adapters.modernization.active_directory.intune_readiness import (
    WIN10_MIN_BUILD,
    WIN11_MIN_BUILD,
    WINSERVER_MIN_BUILD,
    IntuneReadinessResult,
    assess_intune_readiness,
    assess_intune_readiness_batch,
    build_intune_plan,
    crosswalk_ad_to_intune,
    verdict_summary,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "orgtree" / "intune-readiness-devices.json"


def _load_fixture() -> list[dict[str, object]]:
    """Load the intune-readiness-devices.json fixture."""
    data: list[dict[str, object]] = json.loads(_FIXTURE_PATH.read_text())["devices"]
    return data


# ---------------------------------------------------------------------------
# OS build constants
# ---------------------------------------------------------------------------


def test_win10_min_build_is_22h2() -> None:
    assert WIN10_MIN_BUILD == 19045, "Win10 minimum must be 22H2 (build 19045)"


def test_win11_min_build() -> None:
    assert WIN11_MIN_BUILD == 22000


def test_winserver_min_build_is_2019() -> None:
    assert WINSERVER_MIN_BUILD == 17763, "Server minimum must be 2019 (build 17763)"


# ---------------------------------------------------------------------------
# Individual verdict tests — pinned to fixture state
# ---------------------------------------------------------------------------


def test_verdict_ready_win11() -> None:
    """LAPTOP-READY-001: Win11, TPM 2.0, HVCI on → READY."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "LAPTOP-READY-001")
    result = assess_intune_readiness(device)
    assert result.verdict == "READY"
    assert result.rationale == []


def test_verdict_ready_win10_22h2_exact() -> None:
    """LAPTOP-WIN10-22H2-012: Win10 exact 22H2 build (19045), TPM 2.0, HVCI on → READY."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "LAPTOP-WIN10-22H2-012")
    result = assess_intune_readiness(device)
    assert result.verdict == "READY"
    assert result.os_build == 19045


def test_verdict_ready_win11_second_device() -> None:
    """DESKTOP-READY-002: another Win11 device → READY."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "DESKTOP-READY-002")
    result = assess_intune_readiness(device)
    assert result.verdict == "READY"


def test_verdict_needs_os_upgrade_win10_21h2() -> None:
    """LAPTOP-OLDOS-003: Win10 build 19044 (21H2) → NEEDS_OS_UPGRADE."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "LAPTOP-OLDOS-003")
    result = assess_intune_readiness(device)
    assert result.verdict == "NEEDS_OS_UPGRADE"
    assert len(result.rationale) == 1
    assert "19044" in result.rationale[0]
    assert str(WIN10_MIN_BUILD) in result.rationale[0]


def test_verdict_needs_os_upgrade_win10_20h2() -> None:
    """DESKTOP-OLDOS-004: Win10 build 19042 (20H2) → NEEDS_OS_UPGRADE (HVCI off, but OS gate wins)."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "DESKTOP-OLDOS-004")
    result = assess_intune_readiness(device)
    assert result.verdict == "NEEDS_OS_UPGRADE"


def test_verdict_needs_tpm_tpm12() -> None:
    """LAPTOP-TPM12-005: Win10 22H2 but TPM 1.2 → NEEDS_TPM."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "LAPTOP-TPM12-005")
    result = assess_intune_readiness(device)
    assert result.verdict == "NEEDS_TPM"
    assert "1.2" in result.rationale[0]


def test_verdict_needs_tpm_missing_tpm() -> None:
    """DESKTOP-NOTPM-006: Win11 but empty tpmVersion → NEEDS_TPM."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "DESKTOP-NOTPM-006")
    result = assess_intune_readiness(device)
    assert result.verdict == "NEEDS_TPM"


def test_verdict_needs_hvci_win10() -> None:
    """LAPTOP-NOHVCI-007: Win10 22H2, TPM 2.0, HVCI off → NEEDS_HVCI."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "LAPTOP-NOHVCI-007")
    result = assess_intune_readiness(device)
    assert result.verdict == "NEEDS_HVCI"
    assert len(result.rationale) == 1


def test_verdict_needs_hvci_win11() -> None:
    """DESKTOP-NOHVCI-008: Win11, TPM 2.0, HVCI off → NEEDS_HVCI."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "DESKTOP-NOHVCI-008")
    result = assess_intune_readiness(device)
    assert result.verdict == "NEEDS_HVCI"


def test_verdict_ineligible_server_2016() -> None:
    """SRV-2016-009: Windows Server 2016 (build 14393) → INELIGIBLE."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "SRV-2016-009")
    result = assess_intune_readiness(device)
    assert result.verdict == "INELIGIBLE"
    assert "14393" in result.rationale[0] or "Server" in result.rationale[0]


def test_verdict_ineligible_linux() -> None:
    """UBUNTU-APP-010: Ubuntu Linux → INELIGIBLE (non-Windows)."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "UBUNTU-APP-010")
    result = assess_intune_readiness(device)
    assert result.verdict == "INELIGIBLE"
    assert "Non-Windows" in result.rationale[0]


def test_verdict_ready_server_2019() -> None:
    """SRV-2019-011: Windows Server 2019 (build 17763), TPM 2.0, HVCI on → READY (hybrid co-mgmt)."""
    devices = _load_fixture()
    device = next(d for d in devices if d["name"] == "SRV-2019-011")
    result = assess_intune_readiness(device)
    assert result.verdict == "READY"


# ---------------------------------------------------------------------------
# All five verdicts present in fixture
# ---------------------------------------------------------------------------


def test_fixture_covers_all_five_verdicts() -> None:
    """Fixture must contain at least one device for each of the 5 verdicts."""
    devices = _load_fixture()
    results = assess_intune_readiness_batch(devices)
    verdicts = {r.verdict for r in results}
    expected = {"READY", "NEEDS_OS_UPGRADE", "NEEDS_TPM", "NEEDS_HVCI", "INELIGIBLE"}
    assert verdicts == expected, f"Missing verdicts: {expected - verdicts}"


# ---------------------------------------------------------------------------
# Precedence: INELIGIBLE > NEEDS_OS_UPGRADE > NEEDS_TPM > NEEDS_HVCI
# ---------------------------------------------------------------------------


def test_ineligible_blocks_tpm_and_hvci_gates() -> None:
    """An ineligible OS must return INELIGIBLE regardless of TPM/HVCI state."""
    result = assess_intune_readiness(
        {
            "name": "LINUX-BOX",
            "operatingSystem": "Ubuntu Linux 22.04",
            "operatingSystemVersion": "22.04",
            "tpmVersion": "",
            "hvciEnabled": False,
        }
    )
    assert result.verdict == "INELIGIBLE"


def test_os_upgrade_blocks_tpm_and_hvci_gates() -> None:
    """Old Win10 build must return NEEDS_OS_UPGRADE even when TPM missing and HVCI off."""
    result = assess_intune_readiness(
        {
            "name": "OLD-WIN10",
            "operatingSystem": "Windows 10",
            "operatingSystemVersion": "10.0.19041",  # 20H1 — below 22H2
            "tpmVersion": "1.2",
            "hvciEnabled": False,
        }
    )
    assert result.verdict == "NEEDS_OS_UPGRADE"


def test_tpm_gate_blocks_hvci_gate() -> None:
    """Win10 22H2 with TPM 1.2 and HVCI off must return NEEDS_TPM, not NEEDS_HVCI."""
    result = assess_intune_readiness(
        {
            "name": "WIN10-BAD-TPM",
            "operatingSystem": "Windows 10",
            "operatingSystemVersion": "10.0.19045",
            "tpmVersion": "1.2",
            "hvciEnabled": False,
        }
    )
    assert result.verdict == "NEEDS_TPM"


# ---------------------------------------------------------------------------
# Return type / dataclass integrity
# ---------------------------------------------------------------------------


def test_result_is_dataclass() -> None:
    result = assess_intune_readiness(
        {
            "name": "TEST-PC",
            "operatingSystem": "Windows 11",
            "operatingSystemVersion": "10.0.22631",
            "tpmVersion": "2.0",
            "hvciEnabled": True,
        }
    )
    assert isinstance(result, IntuneReadinessResult)
    assert result.computer_name == "TEST-PC"
    assert result.os_build == 22631
    assert result.tpm_version == "2.0"
    assert result.hvci_enabled is True


def test_result_rationale_is_list() -> None:
    result = assess_intune_readiness(
        {
            "name": "TEST-PC",
            "operatingSystem": "Windows 11",
            "operatingSystemVersion": "10.0.22631",
            "tpmVersion": "2.0",
            "hvciEnabled": True,
        }
    )
    assert isinstance(result.rationale, list)


# ---------------------------------------------------------------------------
# crosswalk_ad_to_intune
# ---------------------------------------------------------------------------


def test_crosswalk_maps_known_attributes() -> None:
    ad = {
        "name": "MY-PC",
        "operatingSystem": "Windows 11",
        "operatingSystemVersion": "10.0.22631",
        "tpmVersion": "2.0",
        "hvciEnabled": True,
        "extensionAttribute1": "ORG-IT-INF",
    }
    intune = crosswalk_ad_to_intune(ad)
    assert intune["deviceName"] == "MY-PC"
    assert intune["operatingSystem"] == "Windows 11"
    assert intune["osVersion"] == "10.0.22631"
    assert intune["tpmSpecificationVersion"] == "2.0"
    assert intune["hvciEnabled"] is True
    assert intune["extensionAttribute1"] == "ORG-IT-INF"


def test_crosswalk_unknown_attrs_get_ad_prefix() -> None:
    ad = {"name": "MY-PC", "customAttr": "value"}
    intune = crosswalk_ad_to_intune(ad)
    assert "ad_customAttr" in intune
    assert intune["ad_customAttr"] == "value"


def test_crosswalk_empty_input() -> None:
    assert crosswalk_ad_to_intune({}) == {}


def test_crosswalk_intune_attrs_populated_in_result() -> None:
    """assess_intune_readiness must populate intune_attrs via crosswalk."""
    result = assess_intune_readiness(
        {
            "name": "CROSSWALK-PC",
            "operatingSystem": "Windows 11",
            "operatingSystemVersion": "10.0.22631",
            "tpmVersion": "2.0",
            "hvciEnabled": True,
        }
    )
    assert "deviceName" in result.intune_attrs
    assert result.intune_attrs["deviceName"] == "CROSSWALK-PC"


# ---------------------------------------------------------------------------
# verdict_summary
# ---------------------------------------------------------------------------


def test_verdict_summary_counts() -> None:
    devices = _load_fixture()
    results = assess_intune_readiness_batch(devices)
    summary = verdict_summary(results)
    # At least one of each verdict must be present
    assert summary.get("READY", 0) >= 1
    assert summary.get("NEEDS_OS_UPGRADE", 0) >= 1
    assert summary.get("NEEDS_TPM", 0) >= 1
    assert summary.get("NEEDS_HVCI", 0) >= 1
    assert summary.get("INELIGIBLE", 0) >= 1


def test_verdict_summary_total_matches_input() -> None:
    devices = _load_fixture()
    results = assess_intune_readiness_batch(devices)
    summary = verdict_summary(results)
    assert sum(summary.values()) == len(devices)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_missing_os_name_returns_ineligible() -> None:
    """An empty OS name string cannot be classified → INELIGIBLE."""
    result = assess_intune_readiness({"name": "GHOST-PC"})
    assert result.verdict == "INELIGIBLE"


def test_windows_10_build_exactly_at_boundary() -> None:
    """Build 19045 is the minimum — must pass OS gate."""
    result = assess_intune_readiness(
        {
            "name": "BOUNDARY",
            "operatingSystem": "Windows 10",
            "operatingSystemVersion": "10.0.19045",
            "tpmVersion": "2.0",
            "hvciEnabled": True,
        }
    )
    assert result.verdict == "READY"


def test_windows_10_one_below_boundary() -> None:
    """Build 19044 (21H2) is one below — must fail OS gate."""
    result = assess_intune_readiness(
        {
            "name": "JUST-BELOW",
            "operatingSystem": "Windows 10",
            "operatingSystemVersion": "10.0.19044",
            "tpmVersion": "2.0",
            "hvciEnabled": True,
        }
    )
    assert result.verdict == "NEEDS_OS_UPGRADE"


def test_tpm_version_20_string_variants() -> None:
    for tpm_str in ("2.0", "2", "TPM2.0", "2.0.0"):
        result = assess_intune_readiness(
            {
                "name": "TPM-TEST",
                "operatingSystem": "Windows 10",
                "operatingSystemVersion": "10.0.19045",
                "tpmVersion": tpm_str,
                "hvciEnabled": True,
            }
        )
        assert result.verdict == "READY", f"Expected READY for tpmVersion={tpm_str!r}"


def test_tpm_version_12_string_variants() -> None:
    for tpm_str in ("1.2", "1", "1.0"):
        result = assess_intune_readiness(
            {
                "name": "TPM-TEST",
                "operatingSystem": "Windows 10",
                "operatingSystemVersion": "10.0.19045",
                "tpmVersion": tpm_str,
                "hvciEnabled": True,
            }
        )
        assert result.verdict == "NEEDS_TPM", f"Expected NEEDS_TPM for tpmVersion={tpm_str!r}"


def test_batch_empty_list() -> None:
    assert assess_intune_readiness_batch([]) == []


def test_computer_name_fallback_to_samaccountname() -> None:
    result = assess_intune_readiness(
        {
            "sAMAccountName": "FALLBACK-PC$",
            "operatingSystem": "Windows 11",
            "operatingSystemVersion": "10.0.22631",
            "tpmVersion": "2.0",
            "hvciEnabled": True,
        }
    )
    assert result.computer_name == "FALLBACK-PC$"


def test_computer_name_unknown_when_absent() -> None:
    result = assess_intune_readiness({})
    assert result.computer_name == "UNKNOWN"


# ---------------------------------------------------------------------------
# build_intune_plan — survey aggregation
# ---------------------------------------------------------------------------


def test_build_intune_plan_empty_survey() -> None:
    plan = build_intune_plan({})
    assert plan["total_computers"] == 0
    assert plan["enroll_ready_count"] == 0
    assert plan["enroll_blocked_count"] == 0
    assert plan["blocked_dns"] == []
    assert plan["readiness_pct"] == 0.0
    assert plan["verdict_counts"] == {}


def test_build_intune_plan_no_computers_key() -> None:
    plan = build_intune_plan({"users": [], "groups": []})
    assert plan["total_computers"] == 0
    assert plan["readiness_pct"] == 0.0


def test_build_intune_plan_all_ready() -> None:
    survey = {
        "computers": [
            {
                "dn": "CN=WS-001,OU=W,DC=x",
                "operating_system": "Windows 11 Enterprise",
                "operating_system_version": "10.0 (22631)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
            {
                "dn": "CN=WS-002,OU=W,DC=x",
                "operating_system": "Windows 10 Enterprise",
                "operating_system_version": "10.0 (19045)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
        ]
    }
    plan = build_intune_plan(survey)
    assert plan["total_computers"] == 2
    assert plan["enroll_ready_count"] == 2
    assert plan["enroll_blocked_count"] == 0
    assert plan["blocked_dns"] == []
    assert plan["readiness_pct"] == 100.0
    assert plan["verdict_counts"] == {"READY": 2}


def test_build_intune_plan_mixed_verdicts_records_blocked_dns() -> None:
    survey = {
        "computers": [
            {
                "dn": "CN=READY,DC=x",
                "operating_system": "Windows 11",
                "operating_system_version": "10.0 (22631)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
            {
                "dn": "CN=OLD-OS,DC=x",
                "operating_system": "Windows 10 Enterprise",
                "operating_system_version": "10.0 (19044)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
            {
                "dn": "CN=BAD-TPM,DC=x",
                "operating_system": "Windows 11",
                "operating_system_version": "10.0 (22631)",
                "tpm_version": "1.2",
                "hvci_enabled": True,
            },
            {
                "dn": "CN=LINUX-BOX,DC=x",
                "operating_system": "Ubuntu 22.04",
                "operating_system_version": "22.04",
            },
        ]
    }
    plan = build_intune_plan(survey)
    assert plan["total_computers"] == 4
    assert plan["enroll_ready_count"] == 1
    assert plan["enroll_blocked_count"] == 3
    assert sorted(plan["blocked_dns"]) == ["CN=BAD-TPM,DC=x", "CN=LINUX-BOX,DC=x", "CN=OLD-OS,DC=x"]
    assert plan["readiness_pct"] == 25.0
    assert plan["verdict_counts"] == {
        "READY": 1,
        "NEEDS_OS_UPGRADE": 1,
        "NEEDS_TPM": 1,
        "INELIGIBLE": 1,
    }


def test_build_intune_plan_accepts_camelcase_keys_natively() -> None:
    """LDAP-style camelCase keys must pass through the snake-case normalizer."""
    survey = {
        "computers": [
            {
                "dn": "CN=CAMEL,DC=x",
                "operatingSystem": "Windows 11",
                "operatingSystemVersion": "10.0.22631",
                "tpmVersion": "2.0",
                "hvciEnabled": True,
            }
        ]
    }
    plan = build_intune_plan(survey)
    assert plan["enroll_ready_count"] == 1
    assert plan["readiness_pct"] == 100.0


def test_build_intune_plan_skips_non_dict_records() -> None:
    survey = {
        "computers": [
            None,
            "not-a-dict",
            42,
            {
                "dn": "CN=OK,DC=x",
                "operatingSystem": "Windows 11",
                "operatingSystemVersion": "10.0.22631",
                "tpmVersion": "2.0",
                "hvciEnabled": True,
            },
        ]
    }
    plan = build_intune_plan(survey)
    assert plan["total_computers"] == 1
    assert plan["enroll_ready_count"] == 1


def test_build_intune_plan_blocked_dn_falls_back_to_distinguished_name() -> None:
    """Records that carry only the LDAP-form key (no normalized 'dn') still surface in blocked_dns."""
    survey = {
        "computers": [
            {
                "distinguishedName": "CN=ALT,DC=x",
                "operatingSystem": "Ubuntu",
                "operatingSystemVersion": "22.04",
            }
        ]
    }
    plan = build_intune_plan(survey)
    assert plan["enroll_blocked_count"] == 1
    assert plan["blocked_dns"] == ["CN=ALT,DC=x"]


def test_build_intune_plan_blocked_dn_omitted_when_no_dn_present() -> None:
    survey = {
        "computers": [
            {
                "operatingSystem": "Ubuntu",
                "operatingSystemVersion": "22.04",
            }
        ]
    }
    plan = build_intune_plan(survey)
    assert plan["enroll_blocked_count"] == 1
    assert plan["blocked_dns"] == []


def test_build_intune_plan_readiness_pct_rounds_to_one_decimal() -> None:
    """3 ready out of 7 = 42.857... → 42.9."""
    ready_record = {
        "operatingSystem": "Windows 11",
        "operatingSystemVersion": "10.0.22631",
        "tpmVersion": "2.0",
        "hvciEnabled": True,
    }
    blocked_record = {"operatingSystem": "Ubuntu", "operatingSystemVersion": "22.04"}
    survey = {
        "computers": [{**ready_record, "dn": f"CN=R{i},DC=x"} for i in range(3)]
        + [{**blocked_record, "dn": f"CN=B{i},DC=x"} for i in range(4)]
    }
    plan = build_intune_plan(survey)
    assert plan["total_computers"] == 7
    assert plan["enroll_ready_count"] == 3
    assert plan["readiness_pct"] == 42.9
