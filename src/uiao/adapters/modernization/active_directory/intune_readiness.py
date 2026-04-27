"""
active_directory/intune_readiness.py
-------------------------------------
UIAO Modernization Adapter: AD Computer → Intune Readiness Assessment

Canon reference: computer-object-crosswalk.yaml (XW-002, XW-003, XW-004,
                  XW-009, XW-010, XW-011), Appendix GAE, ADR-038
Adapter class:   modernization
Mission class:   identity
UIAO doc ref:    UIAO_AD_003

Phase 1, Workstream A2 — v0.6.0 OrgTree Readiness

Purpose
-------
For each AD computer object produces an Intune readiness verdict:

  READY            — device meets all Intune enrollment pre-reqs
  NEEDS_OS_UPGRADE — OS build is too old (Win10 < 22H2 / Server < 2019)
  NEEDS_TPM        — TPM not present or version < 2.0
  NEEDS_HVCI       — HVCI / Memory Integrity not enabled
  INELIGIBLE       — Non-Windows, Windows Server < 2019, or structurally
                     excluded (DC, ADCS role). Servers >= 2019 are
                     eligible for hybrid co-management.

Decision precedence (most-blocking wins):
  INELIGIBLE > NEEDS_OS_UPGRADE > NEEDS_TPM > NEEDS_HVCI > READY

Also exposes crosswalk_ad_to_intune() which maps raw AD computer attributes
to the Intune device attribute namespace via the canonical crosswalk YAML.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

# ------------------------------------------------------------------
# OS build-number constants
# ------------------------------------------------------------------
WIN10_MIN_BUILD: int = 19045  # Windows 10 22H2 — minimum supported by Intune
WIN11_MIN_BUILD: int = 22000  # Windows 11 21H2 — any Win11 build accepted
WINSERVER_MIN_BUILD: int = 17763  # Windows Server 2019 — minimum for hybrid co-mgmt

# ------------------------------------------------------------------
# Verdict type
# ------------------------------------------------------------------
IntuneVerdict = Literal[
    "READY",
    "NEEDS_OS_UPGRADE",
    "NEEDS_TPM",
    "NEEDS_HVCI",
    "INELIGIBLE",
]


@dataclass
class IntuneReadinessResult:
    """
    Per-computer Intune readiness result.

    Fields
    ------
    computer_name   : sAMAccountName or hostname
    verdict         : Most-blocking gate that failed, or READY
    rationale       : List of all failing gate descriptions (ordered by precedence)
    os_name         : Raw OS name from AD (operatingSystem attribute)
    os_build        : Parsed numeric OS build (0 if unparseable)
    tpm_version     : Raw tpmVersion string from AD
    hvci_enabled    : Whether HVCI/Memory Integrity is reported enabled
    intune_attrs    : Crosswalked Intune device attribute dict
    """

    computer_name: str
    verdict: IntuneVerdict
    rationale: list[str] = field(default_factory=list)
    os_name: str = ""
    os_build: int = 0
    tpm_version: str = ""
    hvci_enabled: bool = False
    intune_attrs: dict[str, object] = field(default_factory=dict)


# ------------------------------------------------------------------
# AD attribute → Intune attribute crosswalk
# (mirrors computer-object-crosswalk.yaml XW-002, XW-003, XW-004,
#  XW-009, XW-010, XW-011; extended with device-level attributes
#  required for Intune enrollment pre-flight assessment)
# ------------------------------------------------------------------

#: Mapping from AD computer attribute name → Intune device attribute name.
#: This is the programmatic form of the XW-INI-* crosswalk entries added
#: to computer-object-crosswalk.yaml.
_AD_TO_INTUNE_ATTR_MAP: dict[str, str] = {
    # Core identity
    "name": "deviceName",
    "sAMAccountName": "deviceName",
    "distinguishedName": "adDistinguishedName",
    "objectGUID": "adObjectGuid",
    "objectSid": "adObjectSid",
    # OS / build
    "operatingSystem": "operatingSystem",
    "operatingSystemVersion": "osVersion",
    "operatingSystemServicePack": "osServicePack",
    # Hardware / compliance pre-req attributes
    "tpmVersion": "tpmSpecificationVersion",
    "hvciEnabled": "hvciEnabled",
    # Organizational placement (OrgPath plane per ADR-038)
    "extensionAttribute1": "extensionAttribute1",
    # Last activity
    "lastLogonTimestamp": "lastSyncDateTime",
    # Account state
    "userAccountControl": "adAccountControl",
    # Enrollment metadata
    "managedBy": "adManagedBy",
    "description": "notes",
}


def crosswalk_ad_to_intune(ad_computer: Mapping[str, object]) -> dict[str, object]:
    """
    Map an AD computer attribute dict to the Intune device attribute namespace.

    Only keys present in the input dict are included in the output; no
    synthetic defaults are injected. Unknown AD attributes are passed through
    under their original key with an ``ad_`` prefix so callers can inspect
    unmapped attributes without losing data.

    Parameters
    ----------
    ad_computer:
        Dict of raw AD computer attributes, e.g. as returned by ldap3 or the
        AD survey adapter.  Keys should match standard LDAP attribute names.

    Returns
    -------
    Dict using Intune device attribute names where a mapping exists.
    """
    result: dict[str, object] = {}
    for ad_key, value in ad_computer.items():
        intune_key = _AD_TO_INTUNE_ATTR_MAP.get(ad_key)
        if intune_key is not None:
            result[intune_key] = value
        else:
            # Preserve unmapped attributes with ad_ prefix for auditability
            result[f"ad_{ad_key}"] = value
    return result


# ------------------------------------------------------------------
# OS classification helpers
# ------------------------------------------------------------------


def _parse_os_build(os_version: str) -> int:
    """
    Extract the build number from an AD operatingSystemVersion string.

    AD stores OS version as ``"major.minor.build[.revision]"``.
    Examples:
      "10.0.19045"   → 19045   (Windows 10 22H2)
      "10.0.22631"   → 22631   (Windows 11 23H2)
      "10.0.17763"   → 17763   (Server 2019)
      "10.0.14393"   → 14393   (Server 2016)
      "22.04"        → 0       (Linux — no valid Windows build)

    Returns 0 if the string cannot be parsed into a meaningful build number.
    """
    if not os_version:
        return 0
    parts = os_version.strip().split(".")
    if len(parts) >= 3:
        try:
            return int(parts[2])
        except ValueError:
            return 0
    return 0


def _classify_os(os_name: str, os_build: int) -> tuple[str, str]:
    """
    Classify operating system type and Intune eligibility tier.

    Returns
    -------
    (os_type, eligibility) where:
      os_type     : "win10" | "win11" | "winserver_modern" | "winserver_legacy"
                    | "non_windows"
      eligibility : "ok" | "needs_upgrade" | "ineligible"
    """
    os_lower = os_name.lower()

    # Non-Windows fast path
    if not any(token in os_lower for token in ("windows", "microsoft")):
        return ("non_windows", "ineligible")

    is_server = "server" in os_lower

    if is_server:
        # Windows Server 2019+ → ok for hybrid co-mgmt; older → ineligible
        if os_build >= WINSERVER_MIN_BUILD:
            return ("winserver_modern", "ok")
        return ("winserver_legacy", "ineligible")

    # Client Windows
    if os_build >= WIN11_MIN_BUILD:
        return ("win11", "ok")

    if os_build >= WIN10_MIN_BUILD:
        return ("win10", "ok")

    # Windows 10 but build below 22H2 — or Windows 8/7/Vista (build < WIN10_MIN_BUILD)
    if "windows 10" in os_lower:
        return ("win10", "needs_upgrade")

    # Older client Windows (7, 8, Vista) — ineligible
    return ("non_windows", "ineligible")


# ------------------------------------------------------------------
# TPM gate
# ------------------------------------------------------------------


def _tpm_ok(tpm_version: str) -> bool:
    """
    Return True iff the TPM version string indicates TPM >= 2.0.

    Accepts versions like "2.0", "2", "TPM2.0".
    Returns False for "1.2", "1", empty string, or unparseable values.
    """
    if not tpm_version:
        return False
    # Normalize: strip non-numeric prefix/suffix and compare
    import re

    match = re.search(r"(\d+(?:\.\d+)?)", tpm_version)
    if not match:
        return False
    try:
        version_float = float(match.group(1))
    except ValueError:
        return False
    return version_float >= 2.0


# ------------------------------------------------------------------
# Primary verdict function
# ------------------------------------------------------------------


def assess_intune_readiness(ad_computer: Mapping[str, object]) -> IntuneReadinessResult:
    """
    Compute the Intune readiness verdict for a single AD computer object.

    Decision precedence (most-blocking wins):
      INELIGIBLE > NEEDS_OS_UPGRADE > NEEDS_TPM > NEEDS_HVCI > READY

    Parameters
    ----------
    ad_computer:
        Dict of AD computer attributes. Expected keys (all optional; missing
        keys are treated as absent/unknown):
          name / sAMAccountName   : computer name
          operatingSystem         : OS name string
          operatingSystemVersion  : version string, e.g. "10.0.19045"
          tpmVersion              : TPM version string, e.g. "2.0"
          hvciEnabled             : bool — whether HVCI is enabled

    Returns
    -------
    IntuneReadinessResult with verdict + rationale.
    """
    # Resolve computer name
    computer_name = str(ad_computer.get("name") or ad_computer.get("sAMAccountName") or "UNKNOWN")

    os_name = str(ad_computer.get("operatingSystem") or "")
    os_version_str = str(ad_computer.get("operatingSystemVersion") or "")

    # Phase 1.5 fix #4: distinguish absent keys from explicit bad values.
    # When tpmVersion / hvciEnabled are absent we emit an attribute_not_collected
    # finding but do NOT downgrade the verdict — only explicit bad values trigger
    # NEEDS_TPM / NEEDS_HVCI.
    _tpm_present = "tpmVersion" in ad_computer and ad_computer["tpmVersion"] is not None
    _hvci_present = "hvciEnabled" in ad_computer and ad_computer["hvciEnabled"] is not None
    tpm_version = str(ad_computer["tpmVersion"]) if _tpm_present else ""
    hvci_enabled = bool(ad_computer["hvciEnabled"]) if _hvci_present else False

    os_build = _parse_os_build(os_version_str)
    os_type, eligibility = _classify_os(os_name, os_build)

    # Crosswalk for the intune_attrs field
    intune_attrs = crosswalk_ad_to_intune(ad_computer)

    # Collect all failing gates (ordered by precedence so rationale is clear)
    rationale: list[str] = []
    verdict: IntuneVerdict = "READY"

    # Gate 1 — OS eligibility (INELIGIBLE or NEEDS_OS_UPGRADE)
    if eligibility == "ineligible":
        if os_type == "non_windows":
            rationale.append(
                f"Non-Windows OS '{os_name}' is not supported by Intune MDM enrollment; "
                "route to Arc or a third-party MDM."
            )
        elif os_type == "winserver_legacy":
            rationale.append(
                f"Windows Server build {os_build} is below the Server 2019 minimum "
                f"(build {WINSERVER_MIN_BUILD}) for Intune hybrid co-management; "
                "decommission or migrate OS before enrollment."
            )
        else:
            rationale.append(f"OS '{os_name}' (build {os_build}) is not eligible for Intune enrollment.")
        verdict = "INELIGIBLE"
        # INELIGIBLE blocks all further gate evaluation
        return IntuneReadinessResult(
            computer_name=computer_name,
            verdict=verdict,
            rationale=rationale,
            os_name=os_name,
            os_build=os_build,
            tpm_version=tpm_version,
            hvci_enabled=hvci_enabled,
            intune_attrs=intune_attrs,
        )

    if eligibility == "needs_upgrade":
        rationale.append(
            f"Windows 10 build {os_build} is below the minimum supported build "
            f"({WIN10_MIN_BUILD} / 22H2). Upgrade to Windows 10 22H2 or Windows 11 "
            "before Intune enrollment."
        )
        verdict = "NEEDS_OS_UPGRADE"
        # OS upgrade blocks TPM/HVCI gates — return immediately
        return IntuneReadinessResult(
            computer_name=computer_name,
            verdict=verdict,
            rationale=rationale,
            os_name=os_name,
            os_build=os_build,
            tpm_version=tpm_version,
            hvci_enabled=hvci_enabled,
            intune_attrs=intune_attrs,
        )

    # Gate 2 — TPM (only evaluated if OS gate passed)
    if _tpm_present:
        # Attribute was collected — evaluate it.
        if not _tpm_ok(tpm_version):
            rationale.append(
                f"TPM version '{tpm_version}' does not meet the TPM 2.0 requirement for "
                "Intune enrollment and Windows Hello for Business. Replace hardware or "
                "enable firmware TPM (fTPM) in UEFI."
            )
            verdict = "NEEDS_TPM"
            # TPM gate blocks HVCI gate — return immediately
            return IntuneReadinessResult(
                computer_name=computer_name,
                verdict=verdict,
                rationale=rationale,
                os_name=os_name,
                os_build=os_build,
                tpm_version=tpm_version,
                hvci_enabled=hvci_enabled,
                intune_attrs=intune_attrs,
            )
    else:
        # Attribute not present in the survey record — note it but don't fail.
        rationale.append(
            "attribute_not_collected: tpmVersion absent from survey record. "
            "TPM readiness cannot be assessed; collect the attribute before enrollment."
        )

    # Gate 3 — HVCI (only evaluated if OS + TPM gates passed)
    if _hvci_present:
        # Attribute was collected — evaluate it.
        if not hvci_enabled:
            rationale.append(
                "HVCI (Memory Integrity / Hypervisor-Protected Code Integrity) is not enabled. "
                "Enable via Intune Device Security baseline, Windows Security Center, or "
                "UEFI firmware settings before enrollment where required by policy."
            )
            verdict = "NEEDS_HVCI"
    else:
        # Attribute not present in the survey record — note it but don't fail.
        rationale.append(
            "attribute_not_collected: hvciEnabled absent from survey record. "
            "HVCI readiness cannot be assessed; collect the attribute before enrollment."
        )

    return IntuneReadinessResult(
        computer_name=computer_name,
        verdict=verdict,
        rationale=rationale,
        os_name=os_name,
        os_build=os_build,
        tpm_version=tpm_version,
        hvci_enabled=hvci_enabled,
        intune_attrs=intune_attrs,
    )


# ------------------------------------------------------------------
# Batch assessment
# ------------------------------------------------------------------


def assess_intune_readiness_batch(
    ad_computers: Sequence[Mapping[str, object]],
) -> list[IntuneReadinessResult]:
    """
    Assess Intune readiness for a list of AD computer objects.

    Parameters
    ----------
    ad_computers:
        List of AD computer attribute dicts (same schema as
        assess_intune_readiness()).

    Returns
    -------
    List of IntuneReadinessResult, one per input computer, in input order.
    """
    return [assess_intune_readiness(c) for c in ad_computers]


def verdict_summary(results: list[IntuneReadinessResult]) -> dict[str, int]:
    """
    Aggregate verdict counts across a batch result list.

    Returns a dict mapping each verdict string to its count. Verdicts with
    zero occurrences are not included.
    """
    counts: dict[str, int] = {}
    for r in results:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1
    return counts
