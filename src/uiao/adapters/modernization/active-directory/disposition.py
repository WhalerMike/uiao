"""
impl/src/uiao/impl/adapters/modernization/active-directory/disposition.py
--------------------------------------------------------------------------
Computer Object Disposition Classifier

Canon reference: Appendix GAE (GAE.4 Disposition Decision Tree)
Crosswalk reference: src/uiao/canon/computer-object-crosswalk.yaml

Produces a disposition decision for each AD computer object:
  ENTRA-DEVICE              → Track 1 (Intune, Entra device join)
  ARC-SERVER                → Track 2 (Azure Arc enrollment)
  MANAGED-IDENTITY-CANDIDATE→ Track 3 (workload identity rebuild required)
  STAY-AD-DC                → Excluded (domain controllers)
  STAY-AD-DEPENDENCY        → Excluded until dependency resolved
  DECOMMISSION              → No migration path (EOL, orphaned)

Also classifies the OrgPath storage plane for each disposition:
  Entra device objects  → extensionAttribute1
  Arc server resources  → ARM resource tag: OrgPath
  Workload identities   → app tag or custom claim
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# EOL OS versions — no migration path, decommission required
# Updated per Microsoft lifecycle: https://learn.microsoft.com/lifecycle
_EOL_OS_PATTERNS = [
    r"Windows Server 2003",
    r"Windows Server 2008(?! R2)",
    r"Windows Server 2008 R2",
    r"Windows Server 2012(?! R2)",
    r"Windows Server 2012 R2",
    r"Windows XP",
    r"Windows Vista",
    r"Windows 7",
    r"Windows 8(?!\.1)",
]

# DC role indicators from OS or name patterns
_DC_NAME_PATTERNS = [r"^DC\d+", r"-DC\d+", r"DC\d+-", r"\.dc\."]
_DC_OS_PATTERNS = [r"Domain Controller", r"Windows Server.*Domain"]

# ADCS / ADFS / NPS / RADIUS host indicators
_DEPENDENCY_ROLES = [
    "Certificate Services",
    "ADCS",
    "Active Directory Certificate",
    "Federation Services",
    "ADFS",
    "Network Policy",
    "NPS",
    "RADIUS",
]
_DEPENDENCY_SPN_PATTERNS = [
    r"http/.*-ca",
    r"host/.*-ca",
    r"certsvc",
    r"adfssrv",
    r"rpc/.*nps",
]

# Client OS patterns → Entra device track
_CLIENT_OS_PATTERNS = [
    r"Windows 10",
    r"Windows 11",
    r"macOS",
    r"Mac OS X",
]

# Server OS patterns → ARC track
_SERVER_OS_PATTERNS = [
    r"Windows Server 2016",
    r"Windows Server 2019",
    r"Windows Server 2022",
    r"Windows Server 2025",
    r"Windows Server 2026",
    r"Ubuntu Server",
    r"Red Hat Enterprise Linux",
    r"CentOS",
    r"Rocky Linux",
]


@dataclass
class ComputerDisposition:
    """Disposition decision for one AD computer object."""

    computer_name: str
    distinguished_name: str
    os_version: str
    disposition: str  # ENTRA-DEVICE | ARC-SERVER | MANAGED-IDENTITY-CANDIDATE
    # STAY-AD-DC | STAY-AD-DEPENDENCY | DECOMMISSION
    migration_tracks: list[str] = field(default_factory=list)
    orgpath_plane: str = ""  # extensionAttribute1 | ARM-tag | app-tag | none
    spn_count: int = 0
    has_kcd: bool = False
    has_gmsa: bool = False
    adcs_dependent: bool = False
    is_dc: bool = False
    is_eol: bool = False
    blockers: list[str] = field(default_factory=list)
    notes: str = ""
    risk_factors: list[str] = field(default_factory=list)

    @property
    def is_retirement_blocker(self) -> bool:
        return self.disposition in (
            "STAY-AD-DC",
            "STAY-AD-DEPENDENCY",
            "MANAGED-IDENTITY-CANDIDATE",
        ) or bool(self.blockers)

    def as_dict(self) -> dict:
        return {**self.__dict__, "is_retirement_blocker": self.is_retirement_blocker}


def classify_computer_disposition(
    computer_name: str,
    distinguished_name: str,
    os_version: str,
    spns: list[str],
    kerberos_delegation: str,  # none | unconstrained | constrained
    gmsa_linked: bool,
    installed_roles: list[str],
    last_logon_days: int,
    is_enabled: bool,
) -> ComputerDisposition:
    """
    Classify a single AD computer object per Appendix GAE decision tree.

    Parameters mirror the fields collected by Invoke-ADSurvey.ps1
    and the ldap3 survey in survey.py.
    """
    disp = ComputerDisposition(
        computer_name=computer_name,
        distinguished_name=distinguished_name,
        os_version=os_version,
        disposition="",
        spn_count=len(spns),
        has_kcd=(kerberos_delegation != "none"),
        has_gmsa=gmsa_linked,
    )

    # ---- Step 1: EOL check — decommission only ----
    if _matches_any(os_version, _EOL_OS_PATTERNS):
        disp.disposition = "DECOMMISSION"
        disp.is_eol = True
        disp.orgpath_plane = "none"
        disp.notes = f"EOL OS: {os_version}. No migration path. Decommission required."
        disp.risk_factors.append("RF-C05")
        return disp

    # ---- Step 2: Stale / disabled ----
    if not is_enabled or last_logon_days > 180:
        disp.disposition = "DECOMMISSION"
        disp.notes = f"Disabled or stale (last logon {last_logon_days}d). Verify before decommission."
        return disp

    # ---- Step 3: DC detection ----
    name_is_dc = _matches_any(computer_name, _DC_NAME_PATTERNS)
    role_is_dc = any("Active Directory Domain Services" in r or "NTDS" in r for r in installed_roles)
    if name_is_dc or role_is_dc:
        disp.disposition = "STAY-AD-DC"
        disp.is_dc = True
        disp.orgpath_plane = "none"
        disp.notes = "Domain Controller. Do not migrate. Retire last."
        return disp

    # ---- Step 4: AD-dependent role detection ----
    dep_roles = [r for r in installed_roles if any(dep in r for dep in _DEPENDENCY_ROLES)]
    dep_spns = [s for s in spns if _matches_any(s.lower(), _DEPENDENCY_SPN_PATTERNS)]
    if dep_roles or dep_spns:
        disp.disposition = "STAY-AD-DEPENDENCY"
        disp.adcs_dependent = bool(dep_spns)
        disp.orgpath_plane = "ARM-tag"  # Arc-enrolled for visibility only
        disp.notes = (
            f"AD-dependent roles: {dep_roles or dep_spns}. "
            "Must remain AD-joined until dependency resolved (Track 3 prerequisite)."
        )
        disp.blockers.append("Dependency role requires AD — resolve before retirement")
        disp.risk_factors.append("RF-C03")
        if disp.adcs_dependent:
            disp.risk_factors.append("RF-C03")
        return disp

    # ---- Step 5: Client device (Entra device track) ----
    if _matches_any(os_version, _CLIENT_OS_PATTERNS):
        disp.disposition = "ENTRA-DEVICE"
        disp.migration_tracks = ["1"]
        disp.orgpath_plane = "extensionAttribute1"
        disp.notes = "Client device. Track 1: Entra join + Intune enrollment."
        if not disp.has_kcd and disp.spn_count == 0:
            return disp
        # Client with SPNs — also needs Track 3
        disp.migration_tracks.append("3")
        disp.blockers.append(f"{disp.spn_count} SPNs must be migrated to SP/MI")
        disp.risk_factors.append("RF-C02")
        return disp

    # ---- Step 6: Server classification ----
    if _matches_any(os_version, _SERVER_OS_PATTERNS):
        has_workload_identity_need = disp.spn_count > 0 or disp.has_kcd or disp.has_gmsa

        if has_workload_identity_need:
            disp.disposition = "MANAGED-IDENTITY-CANDIDATE"
            disp.migration_tracks = ["2", "3"]
            disp.orgpath_plane = "ARM-tag"
            disp.notes = (
                f"Server with workload identity needs: "
                f"SPNs={disp.spn_count}, KCD={disp.has_kcd}, GMSA={disp.has_gmsa}. "
                "Track 2 (Arc) + Track 3 (MI/SP rebuild). "
                "AD cannot retire until Track 3 complete."
            )
            if disp.spn_count > 0:
                disp.blockers.append(f"{disp.spn_count} SPNs require MI/SP mapping before AD retirement")
                disp.risk_factors.append("RF-C02")
            if disp.has_kcd:
                disp.blockers.append("Kerberos constrained delegation must be rebuilt as OAuth2 flow")
                disp.risk_factors.append("RF-C04")
            if disp.has_gmsa:
                disp.blockers.append("GMSA must be replaced by Managed Identity")
                disp.risk_factors.append("RF-C07")
        else:
            disp.disposition = "ARC-SERVER"
            disp.migration_tracks = ["2"]
            disp.orgpath_plane = "ARM-tag"
            disp.notes = "Server with no workload identity dependencies. Track 2: Arc enrollment + OrgPath ARM tag."
        return disp

    # ---- Fallback: unknown OS ----
    disp.disposition = "ARC-SERVER"
    disp.migration_tracks = ["2"]
    disp.orgpath_plane = "ARM-tag"
    disp.notes = f"Unknown OS '{os_version}' — defaulting to ARC-SERVER. Verify manually."
    disp.risk_factors.append("RF-C08")
    return disp


def _matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(p, value, re.IGNORECASE) for p in patterns)


# ------------------------------------------------------------------
# Batch classification from survey output
# ------------------------------------------------------------------


def classify_all_computers(
    computer_records: list[dict],
) -> tuple[list[ComputerDisposition], dict]:
    """
    Classify all computer objects from the survey output.

    Returns:
        dispositions: list of ComputerDisposition objects
        summary: dict with counts by disposition and retirement gates
    """
    dispositions: list[ComputerDisposition] = []

    for rec in computer_records:
        disp = classify_computer_disposition(
            computer_name=rec.get("name", ""),
            distinguished_name=rec.get("distinguishedName", ""),
            os_version=rec.get("operatingSystem", ""),
            spns=rec.get("spns", "").split("|") if rec.get("spns") else [],
            kerberos_delegation=rec.get("delegationType", "none"),
            gmsa_linked=rec.get("gmsaLinked", False),
            installed_roles=rec.get("installedRoles", []),
            last_logon_days=rec.get("lastLogonDays", 0),
            is_enabled=rec.get("enabled", True),
        )
        dispositions.append(disp)

    # Build summary
    counts: dict[str, int] = {}
    for d in dispositions:
        counts[d.disposition] = counts.get(d.disposition, 0) + 1

    blockers = [d for d in dispositions if d.is_retirement_blocker]
    unmitigated_spns = sum(d.spn_count for d in dispositions if d.disposition == "MANAGED-IDENTITY-CANDIDATE")

    summary = {
        "total_computers": len(dispositions),
        "by_disposition": counts,
        "retirement_blockers": len(blockers),
        "unmitigated_spn_count": unmitigated_spns,
        "gates": {
            "GAE-GATE-1": counts.get("ENTRA-DEVICE", 0),
            "GAE-GATE-2": counts.get("ARC-SERVER", 0),
            "GAE-GATE-3": counts.get("MANAGED-IDENTITY-CANDIDATE", 0),
            "GAE-GATE-4": counts.get("STAY-AD-DEPENDENCY", 0),
            "GAE-GATE-5": counts.get("STAY-AD-DC", 0),
        },
        "ad_retirement_ready": (
            counts.get("MANAGED-IDENTITY-CANDIDATE", 0) == 0 and counts.get("STAY-AD-DEPENDENCY", 0) == 0
        ),
    }
    return dispositions, summary
