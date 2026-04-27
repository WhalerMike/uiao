"""
active_directory/survey.py
--------------------------
UIAO Modernization Adapter: Active Directory Forest Archaeological Survey

Canon reference: Appendix F (Migration Runbook), Phases 1–2.
Adapter class:   modernization
Mission class:   identity
UIAO doc ref:    UIAO_AD_001

Purpose
-------
Reads an on-premises AD forest via LDAP (ldap3) or a PowerShell subprocess
fallback and produces:
  - OU intent classification report
  - Sites and Services topology delta
  - GPO archaeology inventory
  - Service account risk registry
  - Computer object survey
  - Identity collision detection (multi-forest)

All findings are returned as DriftFinding objects matching the repo-wide
substrate walker taxonomy so they can be consumed by the drift engine and
CLI surface without special casing.

IMPORTANT: This module is READ-ONLY against AD by default.
OrgPath write-back lives in orgpath.py::write_orgpath_to_ad().

Drift classes emitted
---------------------
DRIFT-IDENTITY   : user or device object has no resolvable OrgPath
DRIFT-SCHEMA     : OU path encoding makes canonical OrgPath impossible
DRIFT-PROVENANCE : identity exists in AD but has no HR record (unresolvable)
DRIFT-SEMANTIC   : geographic OU path encodes 2003 topology, not org structure
"""

from __future__ import annotations

import datetime
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------
# userAccountControl bit constants (MS-ADTS 2.2.18)
# ------------------------------------------------------------------
UAC_ACCOUNTDISABLE: int = 0x0002
UAC_LOCKOUT: int = 0x0010
UAC_PASSWD_NOTREQD: int = 0x0020
UAC_DONT_EXPIRE_PASSWORD: int = 0x10000
UAC_SMARTCARD_REQUIRED: int = 0x40000
UAC_PASSWORD_EXPIRED: int = 0x800000

# Default window for stale-account detection (days)
_DEFAULT_STALE_DAYS: int = 90


# ------------------------------------------------------------------
# Shared DriftFinding — mirrors impl/src/uiao/impl/substrate/walker.py
# so findings can be merged into a single substrate report.
# ------------------------------------------------------------------
@dataclass
class DriftFinding:
    drift_class: str  # DRIFT-SCHEMA | DRIFT-SEMANTIC | DRIFT-PROVENANCE | DRIFT-IDENTITY
    severity: str  # P1 | P2 | P3 | P4
    path: str  # canonical path or object DN
    detail: str  # human-readable description
    error_code: str = ""  # GOV-MIG-NNN or GOV-DRF-NNN
    object_type: str = ""  # User | Computer | OU | GPO | ServiceAccount | Site
    source_forest: str = ""  # forest FQDN for multi-forest disambiguation
    suggested_orgpath: str = ""  # best-effort OrgPath candidate; empty = unresolvable

    def to_drift_state(self, provenance=None):  # type: ignore[no-untyped-def]
        """Bridge to DriftState for governance engine consumption."""
        import datetime

        from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

        prov = provenance or ProvenanceRecord(
            source="ad-survey-adapter",
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            version="0.1.0",
        )
        actual = {"path": self.path, "object_type": self.object_type, "detail": self.detail}
        h = canonical_hash(actual)
        risk = "unauthorized" if self.severity == "P1" else "risky"
        return DriftState(
            id=f"{self.drift_class.lower()}:{self.path}",
            resource_id=self.path,
            policy_ref=self.error_code or "ad-survey",
            expected_hash=h,
            actual_hash=h,
            drift_detected=True,
            classification=risk,  # type: ignore[arg-type]  # duck-typed: risk is narrowed to "benign"/"risky"/"unauthorized" upstream
            delta={"detail": [self.detail]},
            provenance=prov,
            drift_class=self.drift_class,  # type: ignore[arg-type]  # duck-typed: caller passes canonical DRIFT-* constant
        )


@dataclass
class ADSurveyReport:
    """Aggregated output of the full forest archaeological survey."""

    forest_root: str
    domain_count: int = 0
    # OU classification
    ou_total: int = 0
    ou_functional: int = 0
    ou_geographic_active: int = 0
    ou_geographic_orphan: int = 0
    ou_technical: int = 0
    ou_delegation_artifact: int = 0
    # Users
    user_total: int = 0
    user_hr_resolvable: int = 0
    user_orgpath_derived: int = 0
    user_unresolvable: int = 0
    # Computers
    computer_total: int = 0
    computer_stale: int = 0
    # Service accounts
    sa_total: int = 0
    sa_with_spn: int = 0
    sa_adcs_dependent: int = 0
    sa_orphaned: int = 0
    # GPOs
    gpo_total: int = 0
    gpo_geographic_only: int = 0
    gpo_no_live_intent: int = 0
    # Sites
    site_total: int = 0
    site_stale: int = 0
    # Findings
    findings: list[DriftFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    @property
    def blockers(self) -> list[DriftFinding]:
        return [f for f in self.findings if f.severity == "P1"]

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "findings"}
        d["findings"] = [f.__dict__ for f in self.findings]
        d["ok"] = self.ok
        d["blocker_count"] = len(self.blockers)
        return d


# ------------------------------------------------------------------
# Enrichment dataclasses (WS-A1 Phase 1)
# ------------------------------------------------------------------


@dataclass
class AccountFlags:
    """Decoded userAccountControl flags for a user or service account."""

    disabled: bool
    locked_out: bool
    password_not_required: bool
    password_never_expires: bool
    smartcard_required: bool
    password_expired: bool
    raw_value: int


@dataclass
class UserEnrichment:
    """Per-user enrichment produced by enrich_user()."""

    distinguished_name: str
    sam_account_name: str
    account_flags: AccountFlags
    is_stale: bool
    stale_days: int  # days since last logon; -1 = never logged in
    manager_chain: list[str]  # ordered list of manager DNs (immediate first)
    manager_chain_cycle: bool  # True if a cycle was detected before reaching root
    group_memberships: list[str]  # flat list of all group DNs (recursive)
    group_memberships_cycle: bool  # True if a cycle was detected during group expansion
    orphaned_sids: list[str]  # SIDs in memberOf that resolve to nothing
    candidate_orgpath: Optional[str]  # OU-derived suggestion (not authoritative)


# ------------------------------------------------------------------
# Deliverable 2: userAccountControl decoding
# ------------------------------------------------------------------


def decode_account_flags(uac: int) -> AccountFlags:
    """
    Decode a raw userAccountControl integer into named flag fields.

    Uses module-level UAC_* constants so callers never reference magic numbers.
    """
    return AccountFlags(
        disabled=bool(uac & UAC_ACCOUNTDISABLE),
        locked_out=bool(uac & UAC_LOCKOUT),
        password_not_required=bool(uac & UAC_PASSWD_NOTREQD),
        password_never_expires=bool(uac & UAC_DONT_EXPIRE_PASSWORD),
        smartcard_required=bool(uac & UAC_SMARTCARD_REQUIRED),
        password_expired=bool(uac & UAC_PASSWORD_EXPIRED),
        raw_value=uac,
    )


def is_stale_account(last_logon_timestamp: Optional[int], stale_days: int = _DEFAULT_STALE_DAYS) -> tuple[bool, int]:
    """
    Determine whether an account is stale based on lastLogonTimestamp.

    lastLogonTimestamp is a Windows FILETIME (100-nanosecond intervals since
    1601-01-01). Returns (is_stale, days_since_logon).

    A value of 0 or None means the account has never logged in — treated as
    stale with sentinel days=-1.
    """
    if not last_logon_timestamp:
        return True, -1  # never logged in

    # Convert Windows FILETIME to Unix timestamp.
    # Windows epoch: 1601-01-01; Unix epoch: 1970-01-01 (difference = 11644473600 s)
    _EPOCH_DIFF_S: int = 11_644_473_600
    seconds = last_logon_timestamp // 10_000_000 - _EPOCH_DIFF_S
    logon_dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    delta_days = (now - logon_dt).days
    return delta_days > stale_days, delta_days


# ------------------------------------------------------------------
# Deliverable 1: Nested group resolution with cycle detection
# ------------------------------------------------------------------


def resolve_group_members(
    group_dn: str,
    all_objects: dict[str, dict],  # DN → raw AD object dict with "members" list
    visited: Optional[set[str]] = None,
) -> tuple[list[str], bool]:
    """
    Recursively expand group membership for *group_dn*.

    Parameters
    ----------
    group_dn    : DN of the group to expand.
    all_objects : flat index of DN → object dict; each object may have a
                  ``"members"`` key containing a list of member DNs.
    visited     : set of DNs already on the current traversal stack (cycle guard).

    Returns
    -------
    (members, cycle_detected)
        members        — deduplicated flat list of all member DNs.
        cycle_detected — True if a cycle was detected during expansion.
    """
    if visited is None:
        visited = set()

    if group_dn in visited:
        return [], True  # cycle — stop here

    visited = visited | {group_dn}  # copy; don't mutate caller's set

    obj = all_objects.get(group_dn)
    if obj is None:
        return [], False

    direct_members: list[str] = obj.get("members", [])
    all_members: list[str] = []
    cycle_detected = False

    for member_dn in direct_members:
        if member_dn in all_members:
            continue
        all_members.append(member_dn)
        # If the member is itself a group, recurse
        member_obj = all_objects.get(member_dn)
        if member_obj and member_obj.get("object_class") == "group":
            nested, nested_cycle = resolve_group_members(member_dn, all_objects, visited)
            if nested_cycle:
                cycle_detected = True
            for dn in nested:
                if dn not in all_members:
                    all_members.append(dn)

    return all_members, cycle_detected


# ------------------------------------------------------------------
# Deliverable 3: Orphaned SID detection
# ------------------------------------------------------------------


def detect_orphaned_sids(
    member_dns: list[str],
    all_objects: dict[str, dict],
) -> list[str]:
    """
    Identify member entries that look like unresolvable SIDs.

    An orphaned SID is a group member DN whose CN begins with the SID format
    "S-1-5-21-..." (foreign security principal) and does not appear as a key
    in ``all_objects`` — meaning the referenced object no longer exists in the
    surveyed forest.

    Returns a list of orphaned SID strings.
    """
    orphans: list[str] = []
    for member in member_dns:
        sid_match = re.search(r"CN=(S-1-5-21-[\d-]+)", member, re.IGNORECASE)
        if sid_match:
            sid = sid_match.group(1)
            if member not in all_objects:
                orphans.append(sid)
    return orphans


# ------------------------------------------------------------------
# Deliverable 4: Manager chain resolution
# ------------------------------------------------------------------


def resolve_manager_chain(
    user_dn: str,
    all_objects: dict[str, dict],
    visited: Optional[set[str]] = None,
) -> tuple[list[str], bool]:
    """
    Walk the manager chain from *user_dn* up to the root or a cycle.

    Parameters
    ----------
    user_dn     : DN of the user whose manager chain we are resolving.
    all_objects : flat index of DN → object dict; each object may have a
                  ``"manager"`` key containing a single manager DN string.
    visited     : set of DNs already on the current chain (cycle guard).

    Returns
    -------
    (chain, cycle_detected)
        chain          — ordered list of manager DNs (immediate manager first).
        cycle_detected — True if the chain looped back to a previously seen DN.
    """
    if visited is None:
        visited = set()

    obj = all_objects.get(user_dn)
    if obj is None:
        return [], False

    manager_dn: Optional[str] = obj.get("manager")
    if not manager_dn:
        return [], False

    if manager_dn in visited:
        return [manager_dn], True  # cycle

    chain, cycle = resolve_manager_chain(manager_dn, all_objects, visited | {user_dn})
    return [manager_dn, *chain], cycle


# ------------------------------------------------------------------
# Deliverable 5: OU-derived candidate OrgPath per user
# (wraps derive_orgpath_from_dn, which is defined later in this module;
# Python resolves names at call time so forward reference is safe)
# ------------------------------------------------------------------


def derive_candidate_orgpath(dn: str, codebook: set[str]) -> Optional[str]:
    """
    Return a candidate OrgPath derived from the OU components of *dn*.

    This is a *suggestion only*. The authoritative OrgPath projection lives
    in ``orgpath.py`` (WS-A4). This function is a thin wrapper so the
    enrichment pipeline can call it without knowing the codebook lookup
    internals.
    """
    return derive_orgpath_from_dn(dn, codebook)


# ------------------------------------------------------------------
# Master enrichment entry point
# ------------------------------------------------------------------


def enrich_user(
    user_dn: str,
    user_obj: dict,
    all_objects: dict[str, dict],
    codebook: set[str],
    stale_days: int = _DEFAULT_STALE_DAYS,
) -> UserEnrichment:
    """
    Produce a :class:`UserEnrichment` record for a single AD user object.

    Parameters
    ----------
    user_dn     : Distinguished name of the user.
    user_obj    : Raw attribute dict for the user (from LDAP or synthetic survey
                  fixture). Expected keys (all optional): ``userAccountControl``
                  (int), ``lastLogonTimestamp`` (int), ``manager`` (str DN),
                  ``memberOf`` (list[str] of group DNs).
    all_objects : Flat DN → attribute dict index for the entire surveyed forest
                  (users, groups, computers). Used for recursive resolution.
    codebook    : Set of known OrgPath codes for candidate validation.
    stale_days  : Inactivity window in days (default 90).

    Returns
    -------
    UserEnrichment with all 5 deliverable fields populated.
    """
    uac = user_obj.get("userAccountControl", 0)
    flags = decode_account_flags(uac)

    last_logon = user_obj.get("lastLogonTimestamp")
    stale, stale_delta = is_stale_account(last_logon, stale_days)

    manager_chain, mgr_cycle = resolve_manager_chain(user_dn, all_objects)

    # Expand all group memberships recursively
    member_of: list[str] = user_obj.get("memberOf", [])
    all_groups: list[str] = []
    group_cycle_detected = False
    for grp_dn in member_of:
        if grp_dn not in all_groups:
            all_groups.append(grp_dn)
        grp_obj = all_objects.get(grp_dn)
        if grp_obj and grp_obj.get("object_class") == "group":
            nested, nested_cycle = resolve_group_members(grp_dn, all_objects)
            if nested_cycle:
                group_cycle_detected = True
            for dn in nested:
                if dn not in all_groups:
                    all_groups.append(dn)

    # Detect orphaned SIDs across all memberships
    orphaned = detect_orphaned_sids(all_groups, all_objects)

    candidate = derive_candidate_orgpath(user_dn, codebook)

    return UserEnrichment(
        distinguished_name=user_dn,
        sam_account_name=user_obj.get("sAMAccountName", ""),
        account_flags=flags,
        is_stale=stale,
        stale_days=stale_delta,
        manager_chain=manager_chain,
        manager_chain_cycle=mgr_cycle,
        group_memberships=all_groups,
        group_memberships_cycle=group_cycle_detected,
        orphaned_sids=orphaned,
        candidate_orgpath=candidate,
    )


def emit_enrichment_findings(
    enrichment: UserEnrichment,
    report: ADSurveyReport,
    source_forest: str,
) -> None:
    """
    Translate a :class:`UserEnrichment` record into DriftFinding entries and
    append them to *report*.

    Keeping finding emission separate from enrichment computation allows both
    to be tested independently.
    """
    dn = enrichment.distinguished_name

    # Disabled account
    if enrichment.account_flags.disabled:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-IDENTITY",
                severity="P2",
                path=dn,
                detail=f"User '{dn}' is disabled (UAC ACCOUNTDISABLE bit set). "
                "Verify intent before migration — disabled accounts may indicate "
                "terminated users that should be excluded.",
                error_code="GOV-MIG-010",
                object_type="User",
                source_forest=source_forest,
            )
        )

    # Locked-out account
    if enrichment.account_flags.locked_out:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-IDENTITY",
                severity="P3",
                path=dn,
                detail=f"User '{dn}' is locked out (UAC LOCKOUT bit set). "
                "Account may be under attack or forgotten — review before migration.",
                error_code="GOV-MIG-010",
                object_type="User",
                source_forest=source_forest,
            )
        )

    # Stale account
    if enrichment.is_stale:
        days_str = (
            "never logged in" if enrichment.stale_days == -1 else f"{enrichment.stale_days} days since last logon"
        )
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-IDENTITY",
                severity="P2",
                path=dn,
                detail=f"User '{dn}' is stale ({days_str}). "
                "Account exceeds inactivity threshold; confirm active status before migration.",
                error_code="GOV-MIG-011",
                object_type="User",
                source_forest=source_forest,
            )
        )

    # Cyclic manager chain
    if enrichment.manager_chain_cycle:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-SCHEMA",
                severity="P2",
                path=dn,
                detail=f"User '{dn}' has a cyclic manager chain: {enrichment.manager_chain}. "
                "Manager attribute loop detected; requires manual correction before OrgPath derivation.",
                error_code="GOV-MIG-012",
                object_type="User",
                source_forest=source_forest,
            )
        )

    # Cyclic group membership
    if enrichment.group_memberships_cycle:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-SCHEMA",
                severity="P2",
                path=dn,
                detail=f"User '{dn}' belongs to groups with a cyclic membership chain. "
                "Cycle detected during nested group expansion; full membership cannot be determined. "
                "Investigate group nesting in AD before migration.",
                error_code="GOV-MIG-014",
                object_type="User",
                source_forest=source_forest,
            )
        )

    # Orphaned SIDs in group memberships
    for sid in enrichment.orphaned_sids:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P2",
                path=dn,
                detail=f"User '{dn}' is a member of a group containing orphaned SID '{sid}'. "
                "The SID does not resolve to any object in the surveyed forest; "
                "likely a deleted cross-forest trust principal.",
                error_code="GOV-MIG-013",
                object_type="User",
                source_forest=source_forest,
            )
        )


# ------------------------------------------------------------------
# OU Intent Classification
# ------------------------------------------------------------------

# Geographic keywords that signal a 2003-era topology OU
_GEO_TOKENS = {
    "east",
    "west",
    "north",
    "south",
    "central",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "emea",
    "apac",
    "latam",
    "amer",
    "us",
    "uk",
    "ca",
    "au",
    # Common US city/state abbreviations seen in legacy forests
    "dc",
    "va",
    "md",
    "ny",
    "nj",
    "tx",
    "il",
    "fl",
    "ga",
    "baltimore",
    "chicago",
    "dallas",
    "boston",
    "atlanta",
    "seattle",
    "denver",
    "phoenix",
    "miami",
    "detroit",
    "region",
    "regional",
    "site",
    "office",
    "branch",
    "location",
}

# Functional keywords that signal an org-structure OU
_FUNC_TOKENS = {
    "finance",
    "hr",
    "humanresources",
    "it",
    "infosec",
    "security",
    "operations",
    "ops",
    "legal",
    "compliance",
    "engineering",
    "dev",
    "development",
    "infrastructure",
    "networking",
    "helpdesk",
    "marketing",
    "sales",
    "procurement",
    "facilities",
    "audit",
    "payroll",
    "benefits",
    "recruiting",
    "training",
}


def classify_ou_intent(ou_name: str, has_active_gpo: bool, has_delegation_owner: bool) -> str:
    """
    Classify an OU by its governance intent.

    Returns one of:
      functional           — encodes org structure → map to OrgPath directly
      geographic-active    — geographic but still drives real delegation
      geographic-orphan    — geographic, owner gone, no active GPOs
      technical            — service accounts, computers-by-type, admin containers
      delegation-artifact  — created to scope a role, no longer needed
    """
    name_lower = ou_name.lower().replace("-", "").replace("_", "").replace(" ", "")
    tokens = set(re.findall(r"[a-z]+", name_lower))

    is_geo = bool(tokens & _GEO_TOKENS)
    is_func = bool(tokens & _FUNC_TOKENS)

    # Technical containers by common naming patterns
    technical_patterns = [
        r"^service.?accounts?$",
        r"^admin.?accounts?$",
        r"^workstations?$",
        r"^servers?$",
        r"^computers?$",
        r"^disabled",
        r"^quarantine",
        r"^staging",
        r"^resources?$",
        r"^groups?$",
        r"^distribution",
    ]
    is_technical = any(re.search(p, name_lower) for p in technical_patterns)

    if is_technical:
        return "technical"
    if is_func and not is_geo:
        return "functional"
    if is_func and is_geo:
        # Mixed — classify by what drives the delegation
        return "functional" if has_active_gpo else "geographic-active"
    if is_geo and has_active_gpo and has_delegation_owner:
        return "geographic-active"
    if is_geo and (not has_active_gpo or not has_delegation_owner):
        return "geographic-orphan"
    if not has_active_gpo and has_delegation_owner:
        return "delegation-artifact"
    # Default: geographic-orphan (safest — requires human review)
    return "geographic-orphan"


# ------------------------------------------------------------------
# OrgPath candidate derivation from OU DN
# ------------------------------------------------------------------

# Segment normalization: map common long-form names to 2-6 char codes
_NAME_TO_CODE: dict[str, str] = {
    "finance": "FIN",
    "humanresources": "HR",
    "information technology": "IT",
    "informationtechnology": "IT",
    "security": "SEC",
    "infosec": "SEC",
    "infrastructure": "INF",
    "development": "DEV",
    "operations": "OPS",
    "legal": "LEG",
    "compliance": "COM",
    "marketing": "MKT",
    "engineering": "ENG",
    "networking": "NET",
    "helpdesk": "HELP",
    "training": "TRN",
    "recruiting": "REC",
    "benefits": "BEN",
    "audit": "AUD",
    "payroll": "PAY",
    "facilities": "FAC",
    "procurement": "PROC",
    "logistics": "LOG",
    "accountspayable": "AP",
    "accountsreceivable": "AR",
    "budget": "BUD",
    "litigation": "LIT",
}

_ORGPATH_SEGMENT_RE = re.compile(r"^[A-Z]{2,6}$")


def _normalize_segment(raw: str) -> Optional[str]:
    """
    Convert a raw OU name segment to an OrgPath segment code.
    Returns None if the segment cannot be normalized (geographic, technical, etc.).
    """
    normalized = raw.lower().replace("-", "").replace("_", "").replace(" ", "")
    if normalized in _NAME_TO_CODE:
        return _NAME_TO_CODE[normalized]
    # If it's already 2–6 uppercase: use as-is
    if _ORGPATH_SEGMENT_RE.match(raw.upper()) and len(raw) <= 6:
        return raw.upper()
    return None


def derive_orgpath_from_dn(distinguished_name: str, codebook: set[str]) -> Optional[str]:
    """
    Attempt to derive a canonical OrgPath from an AD distinguished name.

    Strategy:
      1. Parse OU components from DN (right-to-left = top-to-bottom in hierarchy).
      2. Skip domain components (DC=), skip geographic segments.
      3. Normalize functional segments to code form.
      4. Assemble candidate OrgPath.
      5. Validate against codebook; return closest ancestor if exact not found.

    Returns None if no functional OrgPath can be derived (geographic-only path).
    """
    # Extract OU components, preserve order (DC-stripped, OU-only)
    parts = re.findall(r"OU=([^,]+)", distinguished_name, re.IGNORECASE)
    # AD DNs are leaf-to-root; reverse so we go root → leaf
    parts = list(reversed(parts))

    segments = []
    for part in parts:
        code = _normalize_segment(part)
        if code is None:
            # Geographic or unrecognizable — stop here; don't include deeper nodes
            break
        segments.append(code)

    if not segments:
        return None

    # Build candidate from most-specific to least until we hit codebook
    for depth in range(len(segments), 0, -1):
        candidate = "ORG-" + "-".join(segments[:depth])
        if candidate in codebook:
            return candidate

    # Nothing in codebook — return the deepest valid-format candidate
    # for governance review queue
    candidate = "ORG-" + "-".join(segments)
    if re.match(r"^ORG(-[A-Z]{2,6}){1,4}$", candidate):
        return candidate  # Valid format but not yet in codebook → queue for registration

    return None


# ------------------------------------------------------------------
# Service Account Risk Classification
# ------------------------------------------------------------------


@dataclass
class ServiceAccountRisk:
    sam_account_name: str
    distinguished_name: str
    spns: list[str]
    last_password_change_days: int
    last_logon_days: int
    kerberos_delegation: str  # none | unconstrained | constrained | resource-based
    adcs_dependent: bool  # has SPN matching HTTP/LDAP/certsrv pattern
    risk_level: str = "unknown"  # low | medium | high | critical
    notes: str = ""

    def classify_risk(self) -> None:
        score = 0
        notes = []

        if self.kerberos_delegation == "unconstrained":
            score += 40
            notes.append("unconstrained Kerberos delegation — highest risk pattern")
        elif self.kerberos_delegation == "constrained":
            score += 15
            notes.append("constrained delegation — verify post-migration")

        if self.adcs_dependent:
            score += 30
            notes.append("ADCS-dependent SPN — will break silently when AD retires")

        if self.last_password_change_days > 365:
            score += 15
            notes.append(f"password unchanged {self.last_password_change_days}d — likely undocumented")

        if self.last_logon_days > 90:
            score += 10
            notes.append(f"no logon in {self.last_logon_days}d — possibly orphaned")
        elif self.last_logon_days < 0:
            score += 20
            notes.append("never logged in — may be zombie account")

        if len(self.spns) > 10:
            score += 5
            notes.append(f"{len(self.spns)} SPNs — review for accumulation")

        if score >= 60:
            self.risk_level = "critical"
        elif score >= 35:
            self.risk_level = "high"
        elif score >= 15:
            self.risk_level = "medium"
        else:
            self.risk_level = "low"

        self.notes = "; ".join(notes) if notes else "no risk indicators"


def classify_sa_adcs_dependency(spns: list[str]) -> bool:
    """
    Heuristic: does this service account's SPN list suggest ADCS dependency?
    Patterns that indicate ADCS-chained authentication:
      - HTTP/certsrv
      - HOST/CASERVER
      - RPCSS on a machine known as CA
      - LDAP on a DC (used by ADCS for template lookup)
    """
    adcs_patterns = [
        r"http/certsrv",
        r"http/pki\.",
        r"host/ca\d*",
        r"host/.*-ca",
        r"certsvc",
        r"certificateservices",
    ]
    spn_str = " ".join(spns).lower()
    return any(re.search(p, spn_str) for p in adcs_patterns)


# ------------------------------------------------------------------
# Forest Survey Entry Point
# ------------------------------------------------------------------


def run_discovery(
    ldap_server: str,
    base_dn: str,
    username: str,
    password: str,
    hr_export_path: Optional[Path] = None,
    codebook_path: Optional[Path] = None,
    dry_run: bool = True,
) -> ADSurveyReport:
    """
    Phase F.1: Discovery + Phase F.2: OrgPath Mapping.

    This is the primary entry point for the AD adapter. It:
      1. Connects to AD via ldap3 (or PowerShell fallback if ldap3 unavailable).
      2. Enumerates OUs, users, computers, GPOs, service accounts, sites.
      3. Classifies each OU by intent.
      4. Attempts OrgPath derivation for each user.
      5. Cross-references against HR export if provided.
      6. Emits DriftFinding objects for all unresolvable or problematic objects.

    Parameters
    ----------
    ldap_server      : LDAP server hostname or IP
    base_dn          : Forest root DN, e.g. DC=corp,DC=contoso,DC=com
    username         : Bind account (read-only service account recommended)
    password         : Bind account password
    hr_export_path   : Optional CSV path — columns: employeeId, orgPath
                       If provided, HR is authoritative over OU derivation.
    codebook_path    : Optional JSON path — OrgPathCodebook (Appendix H schema).
                       If omitted, OrgPath format validation only (no codebook check).
    dry_run          : If True, no writes to AD. Always True in survey mode.

    Returns
    -------
    ADSurveyReport with findings list ready for drift engine ingestion.
    """
    report = ADSurveyReport(forest_root=base_dn)

    # Load codebook if provided
    codebook: set[str] = set()
    if codebook_path and codebook_path.exists():
        raw = json.loads(codebook_path.read_text())
        codebook = {e["code"] for e in raw.get("entries", []) if e.get("status") == "active"}

    # Load HR export if provided: employeeId → orgPath
    hr_map: dict[str, str] = {}
    if hr_export_path and hr_export_path.exists():
        import csv

        with hr_export_path.open(newline="") as fh:
            for row in csv.DictReader(fh):
                eid = row.get("employeeId", "").strip()
                op = row.get("orgPath", "").strip()
                if eid and op:
                    hr_map[eid] = op

    # Attempt ldap3 survey; fall back to PowerShell. The actual ldap3
    # imports live inside _run_ldap_survey; a missing module surfaces
    # as ImportError from that call.
    try:
        _run_ldap_survey(report, ldap_server, base_dn, username, password, codebook, hr_map)
    except ImportError:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P2",
                path="impl/adapters/active-directory/survey.py",
                detail="ldap3 not installed; falling back to PowerShell subprocess. "
                "Install ldap3 for faster, cross-platform survey.",
                error_code="",
                object_type="adapter",
            )
        )
        _run_powershell_survey(report, ldap_server, base_dn, username, password, codebook, hr_map)

    return report


def _emit_ou_finding(
    report: ADSurveyReport,
    ou_dn: str,
    intent: str,
    source_forest: str,
) -> None:
    """Emit a DriftFinding for an OU that cannot yield a clean OrgPath."""
    if intent == "geographic-orphan":
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-SEMANTIC",
                severity="P2",
                path=ou_dn,
                detail=(
                    f"OU '{ou_dn}' classified as geographic-orphan: "
                    "encodes 2003 datacenter topology, not organizational structure. "
                    "Users here require HR-sourced OrgPath assignment. "
                    "Canonical code: GOV-MIG-003."
                ),
                error_code="GOV-MIG-003",
                object_type="OU",
                source_forest=source_forest,
            )
        )
    elif intent == "delegation-artifact":
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P3",
                path=ou_dn,
                detail=(
                    f"OU '{ou_dn}' classified as delegation-artifact: "
                    "created to scope an admin role, no active GPOs, delegation owner may be gone. "
                    "Candidate for retirement rather than migration."
                ),
                error_code="GOV-MIG-003",
                object_type="OU",
                source_forest=source_forest,
            )
        )


def _emit_user_finding(
    report: ADSurveyReport,
    user_dn: str,
    employee_id: str,
    ou_intent: str,
    derived_orgpath: Optional[str],
    in_hr: bool,
    source_forest: str,
) -> None:
    """Emit a DriftFinding for a user that cannot be cleanly OrgPath-assigned."""
    if not in_hr and ou_intent in ("geographic-orphan", "delegation-artifact"):
        report.user_unresolvable += 1
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-IDENTITY",
                severity="P1",
                path=user_dn,
                detail=(
                    f"User '{user_dn}' (employeeId={employee_id or 'MISSING'}) "
                    "is not in HR export AND resides in a geographic-orphan OU. "
                    "OrgPath cannot be deterministically assigned. "
                    "Manual governance review required before migration can proceed. "
                    "Canonical code: GOV-DRF-003."
                ),
                error_code="GOV-DRF-003",
                object_type="User",
                source_forest=source_forest,
                suggested_orgpath=derived_orgpath or "",
            )
        )
    elif not in_hr and derived_orgpath:
        report.user_orgpath_derived += 1
        # Soft finding — OrgPath was derived from OU but HR didn't confirm
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P2",
                path=user_dn,
                detail=(
                    f"User '{user_dn}' OrgPath derived from OU (candidate: {derived_orgpath}) "
                    "but not confirmed by HR export. Treat as provisional until HR sync validates."
                ),
                error_code="GOV-MIG-002",
                object_type="User",
                source_forest=source_forest,
                suggested_orgpath=derived_orgpath,
            )
        )
    elif not derived_orgpath and not in_hr:
        report.user_unresolvable += 1
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-IDENTITY",
                severity="P1",
                path=user_dn,
                detail=(
                    f"User '{user_dn}' has no OrgPath derivable from OU path and no HR record. "
                    "Cannot migrate without manual classification. GOV-MIG-003."
                ),
                error_code="GOV-MIG-003",
                object_type="User",
                source_forest=source_forest,
            )
        )


def _run_ldap_survey(
    report: ADSurveyReport,
    server_addr: str,
    base_dn: str,
    username: str,
    password: str,
    codebook: set[str],
    hr_map: dict[str, str],
) -> None:
    """
    Live LDAP survey using ldap3.
    Populates report in-place.
    """
    from ldap3 import ALL, SUBTREE, Connection, Server  # type: ignore

    srv = Server(server_addr, get_info=ALL)
    conn = Connection(srv, user=username, password=password, auto_bind=True)

    # --- OU enumeration ---
    conn.search(
        base_dn,
        "(objectClass=organizationalUnit)",
        search_scope=SUBTREE,
        attributes=["distinguishedName", "name", "gPLink", "managedBy"],
    )
    ou_results = list(conn.entries)
    report.ou_total = len(ou_results)

    ou_intent_map: dict[str, str] = {}
    for ou in ou_results:
        dn = str(ou.distinguishedName)
        name = str(ou.name)
        has_gpo = bool(ou.gPLink.value if hasattr(ou.gPLink, "value") else None)
        has_owner = bool(ou.managedBy.value if hasattr(ou.managedBy, "value") else None)
        intent = classify_ou_intent(name, has_gpo, has_owner)
        ou_intent_map[dn] = intent

        # Tally
        if intent == "functional":
            report.ou_functional += 1
        elif intent == "geographic-active":
            report.ou_geographic_active += 1
        elif intent == "geographic-orphan":
            report.ou_geographic_orphan += 1
        elif intent == "technical":
            report.ou_technical += 1
        elif intent == "delegation-artifact":
            report.ou_delegation_artifact += 1

        _emit_ou_finding(report, dn, intent, base_dn)

    # --- User enumeration ---
    conn.search(
        base_dn,
        "(&(objectClass=user)(objectCategory=person))",
        search_scope=SUBTREE,
        attributes=[
            "distinguishedName",
            "sAMAccountName",
            "employeeID",
            "department",
            "manager",
            "userAccountControl",
            "lastLogonTimestamp",
            "extensionAttribute1",
        ],
    )
    report.user_total = len(conn.entries)

    for user in conn.entries:
        dn = str(user.distinguishedName)
        emp_id = str(user.employeeID.value) if user.employeeID else ""
        in_hr = emp_id in hr_map

        # Determine parent OU DN
        ou_dn = ",".join(dn.split(",")[1:])
        ou_intent = ou_intent_map.get(ou_dn, "geographic-orphan")

        # OrgPath resolution priority: HR → OU derivation
        if in_hr:
            report.user_hr_resolvable += 1
        else:
            derived = derive_orgpath_from_dn(dn, codebook)
            _emit_user_finding(report, dn, emp_id, ou_intent, derived, in_hr, base_dn)

    # --- Service account enumeration ---
    # Service accounts: enabled accounts in technical OUs or with SPNs
    conn.search(
        base_dn,
        "(&(objectClass=user)(servicePrincipalName=*))",
        search_scope=SUBTREE,
        attributes=[
            "distinguishedName",
            "sAMAccountName",
            "servicePrincipalName",
            "pwdLastSet",
            "lastLogonTimestamp",
            "userAccountControl",
            "msDS-AllowedToDelegateTo",
        ],
    )
    report.sa_total = len(conn.entries)

    for sa in conn.entries:
        dn = str(sa.distinguishedName)
        spns = list(sa.servicePrincipalName) if sa.servicePrincipalName else []
        report.sa_with_spn += 1
        adcs = classify_sa_adcs_dependency(spns)
        if adcs:
            report.sa_adcs_dependent += 1
            report.findings.append(
                DriftFinding(
                    drift_class="DRIFT-AUTHZ",
                    severity="P1",
                    path=dn,
                    detail=(
                        f"Service account '{sa.sAMAccountName}' has ADCS-dependent SPN pattern. "
                        "Will break silently when AD retires. "
                        "Must be resolved before migration. See pki-adapter for certificate chain analysis."
                    ),
                    error_code="GOV-MIG-005",
                    object_type="ServiceAccount",
                    source_forest=base_dn,
                )
            )

    # --- Sites and Services ---
    sites_dn = f"CN=Sites,CN=Configuration,{base_dn}"
    conn.search(
        sites_dn,
        "(objectClass=site)",
        search_scope=SUBTREE,
        attributes=["name", "whenCreated", "siteObjectBL"],
    )
    report.site_total = len(conn.entries)
    for site in conn.entries:
        # Sites with no subnet associations are almost certainly stale
        if not site.siteObjectBL:
            report.site_stale += 1
            report.findings.append(
                DriftFinding(
                    drift_class="DRIFT-SCHEMA",
                    severity="P2",
                    path=f"CN={site.name},{sites_dn}",
                    detail=(
                        f"Site '{site.name}' has no subnet associations. "
                        "Created circa 2003 topology; likely stale. "
                        "Validate against current DC placement before cleanup."
                    ),
                    error_code="",
                    object_type="Site",
                    source_forest=base_dn,
                )
            )

    conn.unbind()


def _run_powershell_survey(
    report: ADSurveyReport,
    server_addr: str,
    base_dn: str,
    username: str,
    password: str,
    codebook: set[str],
    hr_map: dict[str, str],
) -> None:
    """
    PowerShell-subprocess fallback for environments where ldap3 is unavailable
    or where the caller is running on a domain-joined Windows machine.

    Delegates to Invoke-ADSurvey.ps1 and parses JSON output.
    """
    ps_script = (
        Path(__file__).parent.parent.parent.parent.parent.parent / "scripts" / "ad-survey" / "Invoke-ADSurvey.ps1"
    )

    if not ps_script.exists():
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P1",
                path=str(ps_script),
                detail=(
                    "PowerShell survey script not found and ldap3 is not installed. "
                    "Cannot complete AD survey. Install ldap3 or ensure "
                    "scripts/ad-survey/Invoke-ADSurvey.ps1 exists."
                ),
                error_code="GOV-MIG-001",
                object_type="adapter",
            )
        )
        return

    cmd = [
        "pwsh",
        "-NonInteractive",
        "-File",
        str(ps_script),
        "-Server",
        server_addr,
        "-BaseDN",
        base_dn,
        "-OutputJson",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            report.findings.append(
                DriftFinding(
                    drift_class="DRIFT-PROVENANCE",
                    severity="P1",
                    path=str(ps_script),
                    detail=f"PowerShell survey failed: {result.stderr[:500]}",
                    error_code="GOV-MIG-001",
                    object_type="adapter",
                )
            )
            return
        raw = json.loads(result.stdout)
        _merge_ps_output(report, raw, codebook, hr_map, base_dn)
    except subprocess.TimeoutExpired:
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P1",
                path=str(ps_script),
                detail="PowerShell survey timed out after 300 seconds. Forest may be too large; use ldap3 with pagination.",
                error_code="GOV-MIG-001",
                object_type="adapter",
            )
        )


def _merge_ps_output(
    report: ADSurveyReport,
    raw: dict,
    codebook: set[str],
    hr_map: dict[str, str],
    source_forest: str,
) -> None:
    """Parse structured JSON from Invoke-ADSurvey.ps1 and populate report."""
    for ou in raw.get("ous", []):
        intent = classify_ou_intent(
            ou["name"],
            bool(ou.get("hasGpo")),
            bool(ou.get("hasDelegationOwner")),
        )
        ou_dn = ou["distinguishedName"]
        report.ou_total += 1
        _emit_ou_finding(report, ou_dn, intent, source_forest)

    for user in raw.get("users", []):
        dn = user["distinguishedName"]
        emp_id = user.get("employeeId", "")
        in_hr = emp_id in hr_map
        ou_dn = ",".join(dn.split(",")[1:])
        ou_intent = classify_ou_intent(ou_dn.split(",")[0].replace("OU=", ""), False, False)
        derived = derive_orgpath_from_dn(dn, codebook)
        report.user_total += 1
        if in_hr:
            report.user_hr_resolvable += 1
        else:
            _emit_user_finding(report, dn, emp_id, ou_intent, derived, in_hr, source_forest)
