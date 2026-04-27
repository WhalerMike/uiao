"""
active_directory/arc_readiness.py
----------------------------------
UIAO Modernization Adapter: Azure Arc Readiness Assessment for AD Servers

Canon reference:  computer-object-crosswalk.yaml (XW-009, XW-010), ADR-038
Adapter class:    modernization
Mission class:    identity
UIAO doc ref:     UIAO_AD_003

Purpose
-------
Given a collection of AD computer records, determines whether each server is
eligible for Azure Arc enrollment and emits a per-server readiness verdict.

Scope
-----
ONLY server-class machines are assessed.  Client OS records (Windows 10/11,
macOS, etc.) are returned with verdict NOT_SERVER and skipped from rollup
counts.  Domain Controllers and EOL servers that cannot run the Arc agent are
marked INELIGIBLE.

Verdict precedence (highest to lowest):
  INELIGIBLE          > NEEDS_OS_UPGRADE > NEEDS_NETWORK_EGRESS > READY

    READY                 — OS is supported, no blocking factors detected
    NEEDS_OS_UPGRADE      — OS is technically Arc-capable (Windows Server 2012/
                            2012 R2 with Extended Security Updates) but should
                            be flagged for OS upgrade review before full rollout
    NEEDS_NETWORK_EGRESS  — OS is fine, but record carries
                            network_egress_validated=false (or is absent and
                            strict_network_mode=True)
    INELIGIBLE            — OS is not supported by Arc (EOL/unknown), or the
                            record is a Domain Controller
    NOT_SERVER            — Not a server OS; out of scope for this module

Microsoft Learn reference for Arc network requirements (NOT exhaustive — always
verify against the current Microsoft documentation):
  https://learn.microsoft.com/azure/azure-arc/servers/network-requirements
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


def _normalize_os_string(s: str) -> str:
    """Lowercase and strip non-alphanumeric chars for fuzzy distro matching."""
    return re.sub(r"[^a-z0-9]", "", s.lower())

# ---------------------------------------------------------------------------
# Verdict type
# ---------------------------------------------------------------------------

ArcVerdict = Literal[
    "READY",
    "NEEDS_OS_UPGRADE",
    "NEEDS_NETWORK_EGRESS",
    "INELIGIBLE",
    "NOT_SERVER",
]

# ---------------------------------------------------------------------------
# Outbound endpoint requirement matrix
#
# Source: https://learn.microsoft.com/azure/azure-arc/servers/network-requirements
# NOTE: This list is NOT exhaustive. Always verify against the current
# Microsoft Learn page for up-to-date endpoints and port requirements.
# ---------------------------------------------------------------------------
ARC_EGRESS_ENDPOINTS: dict[str, list[str]] = {
    # Core Arc agent communication
    "arc_agent_core": [
        "*.his.arc.azure.com",
        "gbl.his.arc.azure.com",
        "*.guestconfiguration.azure.com",
    ],
    # Azure management plane
    "azure_management": [
        "management.azure.com",
    ],
    # Azure Active Directory / authentication
    "authentication": [
        "login.windows.net",
        "login.microsoftonline.com",
    ],
    # OBO (on-behalf-of) proxy for region-specific Arc communication
    # Replace <region> with the target Azure region (e.g. eastus)
    "arc_obo_proxy": [
        "<region>.obo.arc.azure.com",
    ],
    # Extended Security Updates delivery + Hybrid Runbook Worker
    "esu_and_hybrid_runbook": [
        "*.servicebus.windows.net",
    ],
    # Arc agent download / update
    "agent_download": [
        "download.microsoft.com",
    ],
}

# ---------------------------------------------------------------------------
# OS gate: server detection patterns
# ---------------------------------------------------------------------------

# Windows Server OS prefix — case-insensitive match against operatingSystem field
_WINDOWS_SERVER_PREFIX = "Windows Server"

# Linux server distro tokens recognised as server-class (after normalization).
# Normalization: lowercase + strip non-alphanumeric chars.
# Source: https://learn.microsoft.com/azure/azure-arc/servers/prerequisites
# NOTE: Arc support matrix evolves; verify version requirements per distro.
# Handles real-world variants such as:
#   "Red Hat Enterprise Linux 8.9" / "RHEL 8.9" / "Red Hat Enterprise Linux Server release 8.9 (Ootpa)"
#   "Ubuntu Server 22.04" / "Ubuntu 22.04 LTS Server" / "ubuntu-server-22.04"
_LINUX_SERVER_TOKENS: list[str] = [
    "redhatenterprise",  # matches "Red Hat Enterprise Linux *"
    "rhel",              # matches "RHEL *"
    "centos",
    "ubuntuserver",      # matches "Ubuntu Server *" and "ubuntu-server-*"
    "suselinuxenterprise",  # matches "SUSE Linux Enterprise Server *"
    "sles",              # matches "SLES *"
    "oraclelinux",
    "rockylinux",
    "almalinux",
    "debian",
]

# Windows Server versions with only ESU support (arc-capable, but flag for upgrade)
# Arc supports 2012/2012 R2 *with* Extended Security Updates.
# Ref: https://learn.microsoft.com/azure/azure-arc/servers/prerequisites
_WINDOWS_NEEDS_UPGRADE_PATTERNS: list[str] = [
    r"Windows Server 2012(?!\s*R2)\b",  # 2012 (not 2012 R2 — matched below)
    r"Windows Server 2012 R2",
]

# Windows Server versions that are fully supported by Arc (subject to network)
_WINDOWS_SUPPORTED_PATTERNS: list[str] = [
    r"Windows Server 2016",
    r"Windows Server 2019",
    r"Windows Server 2022",
    r"Windows Server 2025",
]

# EOL Windows Server versions (no Arc support path)
_WINDOWS_EOL_PATTERNS: list[str] = [
    r"Windows Server 2003",
    r"Windows Server 2008(?!\s*R2)\b",
    r"Windows Server 2008 R2",
]

# Domain Controller role / name indicators — Arc is not used for DCs
_DC_ROLE_TOKENS: list[str] = [
    "Active Directory Domain Services",
    "NTDS",
    "Domain Controller",
]
_DC_NAME_RE = re.compile(r"(^DC\d+|[-.]DC\d+|DC\d+[-.])", re.IGNORECASE)


def _matches_any(value: str, patterns: list[str]) -> bool:
    """Return True if *value* matches any compiled regex in *patterns*."""
    return any(re.search(p, value, re.IGNORECASE) for p in patterns)


def _is_linux_server_os(os_version: str) -> bool:
    """Return True if *os_version* identifies a Linux server-class OS.

    Uses normalized matching (lowercase + strip non-alphanumeric) so that
    real-world variants like "Red Hat Enterprise Linux Server release 8.9 (Ootpa)",
    "RHEL 8.9", "ubuntu-server-22.04", and "Ubuntu 22.04 LTS Server" all match.

    Ubuntu is treated specially: the word "server" may appear after the version
    number (e.g. "Ubuntu 22.04 LTS Server"), so we check for both "ubuntu" and
    "server" anywhere in the normalized form rather than requiring them adjacent.
    """
    normalized = _normalize_os_string(os_version)
    # Special case: "Ubuntu * Server" variants where "server" trails the version
    if "ubuntu" in normalized and "server" in normalized:
        return True
    return any(token in normalized for token in _LINUX_SERVER_TOKENS)


def _is_server_os(os_version: str) -> bool:
    """Return True if *os_version* identifies a server-class OS."""
    if os_version.startswith(_WINDOWS_SERVER_PREFIX):
        return True
    return _is_linux_server_os(os_version)


def _is_domain_controller(
    computer_name: str,
    installed_roles: list[str],
) -> bool:
    """Heuristic: return True if the record appears to be a Domain Controller."""
    if _DC_NAME_RE.search(computer_name):
        return True
    return any(token in role for role in installed_roles for token in _DC_ROLE_TOKENS)


# ---------------------------------------------------------------------------
# Per-server readiness result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ArcReadinessResult:
    """Readiness verdict for one AD server computer record."""

    computer_name: str
    distinguished_name: str
    operating_system: str
    verdict: ArcVerdict
    notes: str = ""
    # Populated when verdict is NEEDS_OS_UPGRADE or INELIGIBLE
    os_gate_reason: str = ""
    # True when network egress has been confirmed; None means unknown
    network_egress_validated: bool | None = None

    def as_dict(self) -> dict:
        return {**self.__dict__}


# ---------------------------------------------------------------------------
# Core assessment logic
# ---------------------------------------------------------------------------


def assess_server_arc_readiness(
    computer_name: str,
    distinguished_name: str,
    operating_system: str,
    installed_roles: list[str] | None = None,
    network_egress_validated: bool | None = None,
    strict_network_mode: bool = False,
) -> ArcReadinessResult:
    """
    Assess Azure Arc readiness for a single computer record.

    Parameters
    ----------
    computer_name            : sAMAccountName or hostname
    distinguished_name       : Full AD DN
    operating_system         : Value of the AD ``operatingSystem`` attribute
    installed_roles          : List of role strings from the AD survey (optional)
    network_egress_validated : True/False if egress has been confirmed;
                               None if unknown
    strict_network_mode      : When True, treat unknown network_egress_validated
                               (None) as False, downgrading verdict to
                               NEEDS_NETWORK_EGRESS

    Returns
    -------
    ArcReadinessResult with verdict and explanatory notes.
    """
    roles: list[str] = installed_roles or []

    result = ArcReadinessResult(
        computer_name=computer_name,
        distinguished_name=distinguished_name,
        operating_system=operating_system,
        verdict="INELIGIBLE",  # safe default; overwritten below
        network_egress_validated=network_egress_validated,
    )

    # ------------------------------------------------------------------
    # Gate 0: server detection
    # ------------------------------------------------------------------
    if not _is_server_os(operating_system):
        result.verdict = "NOT_SERVER"
        result.notes = (
            f"'{operating_system}' is not a server OS.  This record is out of scope for Arc readiness assessment."
        )
        return result

    # ------------------------------------------------------------------
    # Gate 1: Domain Controller exclusion (INELIGIBLE)
    # ------------------------------------------------------------------
    if _is_domain_controller(computer_name, roles):
        result.verdict = "INELIGIBLE"
        result.os_gate_reason = "Domain Controller"
        result.notes = (
            "Domain Controllers are not enrolled in Azure Arc.  "
            "Per crosswalk XW-009 servers remain AD-joined during migration."
        )
        return result

    # ------------------------------------------------------------------
    # Gate 2: OS eligibility
    # ------------------------------------------------------------------
    # 2a. EOL — no Arc support path
    if _matches_any(operating_system, _WINDOWS_EOL_PATTERNS):
        result.verdict = "INELIGIBLE"
        result.os_gate_reason = f"EOL Windows Server OS: {operating_system}"
        result.notes = (
            f"'{operating_system}' has no Azure Arc support path.  "
            "Decommission or upgrade before any Arc enrollment attempt."
        )
        return result

    # 2b. Windows Server 2012 / 2012 R2 — supported only with ESU; flag for upgrade
    if _matches_any(operating_system, _WINDOWS_NEEDS_UPGRADE_PATTERNS):
        # Still eligible with ESU, but flagged — NEEDS_OS_UPGRADE takes precedence
        # over network issues per the stated verdict precedence.
        result.verdict = "NEEDS_OS_UPGRADE"
        result.os_gate_reason = f"ESU-only support: {operating_system}"
        result.notes = (
            f"'{operating_system}' is Arc-capable only under Extended Security "
            "Updates (ESU).  Flag for OS upgrade review before production enrollment.  "
            "Ref: https://learn.microsoft.com/azure/azure-arc/servers/prerequisites"
        )
        return result

    # 2c. Supported Windows Server versions
    if operating_system.startswith(_WINDOWS_SERVER_PREFIX):
        if not _matches_any(operating_system, _WINDOWS_SUPPORTED_PATTERNS):
            # Unknown / future Windows Server version — treat as INELIGIBLE
            result.verdict = "INELIGIBLE"
            result.os_gate_reason = f"Unrecognised Windows Server version: {operating_system}"
            result.notes = (
                f"'{operating_system}' is not in the known-supported Arc OS list.  "
                "Verify against https://learn.microsoft.com/azure/azure-arc/servers/prerequisites"
            )
            return result

    # 2d. Linux — coarse pass: if it matches a known server distro, treat as
    #     READY (subject to network gate).  A future pass can add per-distro
    #     version gating once the version roster is captured in the AD survey.
    #     Ref: https://learn.microsoft.com/azure/azure-arc/servers/prerequisites

    # ------------------------------------------------------------------
    # Gate 3: Network egress gate
    # ------------------------------------------------------------------
    egress_ok: bool | None = network_egress_validated
    if egress_ok is False or (egress_ok is None and strict_network_mode):
        result.verdict = "NEEDS_NETWORK_EGRESS"
        result.notes = (
            "OS is Arc-eligible, but outbound network egress to Azure Arc endpoints "
            "has not been validated (network_egress_validated=false or unknown in "
            "strict mode).  Verify connectivity to endpoints in ARC_EGRESS_ENDPOINTS.  "
            "Ref: https://learn.microsoft.com/azure/azure-arc/servers/network-requirements"
        )
        return result

    # ------------------------------------------------------------------
    # All gates passed — READY
    # ------------------------------------------------------------------
    result.verdict = "READY"
    result.notes = f"'{operating_system}' is a supported Arc OS and no blocking factors detected."
    return result


# ---------------------------------------------------------------------------
# Batch assessment
# ---------------------------------------------------------------------------


@dataclass
class ArcReadinessSummary:
    """Aggregated Arc readiness summary for a fleet of computer records."""

    total_records: int = 0
    total_servers: int = 0  # non-NOT_SERVER records
    ready: int = 0
    needs_os_upgrade: int = 0
    needs_network_egress: int = 0
    ineligible: int = 0
    not_server: int = 0
    results: list[ArcReadinessResult] = field(default_factory=list)

    @property
    def arc_enrollable(self) -> int:
        """Records that can be enrolled today (READY verdict)."""
        return self.ready

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "results"}
        d["arc_enrollable"] = self.arc_enrollable
        d["results"] = [r.as_dict() for r in self.results]
        return d


def assess_fleet_arc_readiness(
    computer_records: list[dict],
    strict_network_mode: bool = False,
) -> ArcReadinessSummary:
    """
    Assess Azure Arc readiness for a list of AD computer records.

    Each record dict should carry (at minimum):
      name              : str  — computer name / sAMAccountName
      distinguishedName : str  — full AD DN
      operatingSystem   : str  — AD operatingSystem attribute value
      installedRoles    : list[str] (optional) — roles from AD survey
      network_egress_validated : bool | None (optional)

    Parameters
    ----------
    computer_records    : List of computer record dicts (AD survey output format)
    strict_network_mode : Treat absent network_egress_validated as unvalidated

    Returns
    -------
    ArcReadinessSummary with per-record results and aggregate counts.
    """
    summary = ArcReadinessSummary(total_records=len(computer_records))

    for rec in computer_records:
        result = assess_server_arc_readiness(
            computer_name=rec.get("name", ""),
            distinguished_name=rec.get("distinguishedName", ""),
            operating_system=rec.get("operatingSystem", ""),
            installed_roles=rec.get("installedRoles", []),
            network_egress_validated=rec.get("network_egress_validated"),
            strict_network_mode=strict_network_mode,
        )
        summary.results.append(result)

        if result.verdict == "NOT_SERVER":
            summary.not_server += 1
        else:
            summary.total_servers += 1
            if result.verdict == "READY":
                summary.ready += 1
            elif result.verdict == "NEEDS_OS_UPGRADE":
                summary.needs_os_upgrade += 1
            elif result.verdict == "NEEDS_NETWORK_EGRESS":
                summary.needs_network_egress += 1
            elif result.verdict == "INELIGIBLE":
                summary.ineligible += 1

    return summary
