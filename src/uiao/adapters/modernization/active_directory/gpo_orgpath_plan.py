"""GPO → OrgPath migration planner — Phase 3 (the differentiated join).

Phase 1 says *what a GPO configures* and how portable each setting is;
Phase 2 replaces the portability heuristic with Microsoft's authoritative
MDM verdict. Neither answers the question a migration team actually has:
**"where does this land in my Intune estate, and who does it target?"**

This module produces that answer — the part Microsoft's Group Policy
Analytics does *not* give you. For each GPO it joins:

* the GPO's **scope** (its OU links) → OU **intent** (functional /
  geographic / technical / delegation-artifact, via the AD survey's
  :func:`classify_ou_intent`) → a recommended **OrgPath dynamic-group
  target**, and
* each **portability bucket** → the concrete **Intune mechanism** that
  carries it (Settings Catalog profile, platform script, Account
  Protection, Folder-Redirection-via-OneDrive, …).

The result is a per-GPO, facet-scoped Intune migration plan. Pure and
offline — it consumes a :class:`GpoReport` (optionally Phase-2-enriched)
and emits a :class:`GpoMigrationPlan`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from uiao.adapters.modernization.active_directory.gpo_analytics import GpoReport
from uiao.adapters.modernization.active_directory.survey import classify_ou_intent

# portability_class → (intune_mechanism, action verb) for the remediation rollup.
_REMEDIATION: dict[str, tuple[str, str]] = {
    "csp-mappable": ("Intune Settings Catalog profile", "port"),
    "partial": ("Intune Settings Catalog / Account Protection (per-setting review)", "port-with-review"),
    "needs-platform-script": ("Intune platform script / Proactive Remediation", "reimplement"),
    "needs-different-mechanism": ("Intune feature equivalent (e.g. OneDrive KFM, certificate profile)", "replace"),
    "no-csp": ("no Intune equivalent", "retire-or-replace"),
    "deprecated": ("deprecated technology", "drop"),
    "review-required": ("unclassified — needs manual review", "review"),
}

# OU intent → (recommendation, whether a facet-scoped group is appropriate).
_INTENT_RECOMMENDATION: dict[str, tuple[str, bool]] = {
    "functional": ("OU encodes org structure — map to an OrgPath facet and target a dynamic group", True),
    "technical": ("Technical container — target by device-type facet", True),
    "geographic-active": ("Geographic OU still driving delegation — review before encoding as a facet", False),
    "geographic-orphan": ("Geographic orphan — do NOT encode as a facet; retire the link", False),
    "delegation-artifact": ("Delegation artifact — retire; no Intune target", False),
}


@dataclass(frozen=True)
class ScopeTarget:
    """One GPO link resolved to an OU intent + recommended OrgPath target."""

    som_name: str
    som_path: str
    scope_level: str  # "domain" | "ou"
    ou_name: str
    intent: str
    recommended_group: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "som_name": self.som_name,
            "som_path": self.som_path,
            "scope_level": self.scope_level,
            "ou_name": self.ou_name,
            "intent": self.intent,
            "recommended_group": self.recommended_group,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class SettingRemediation:
    """One portability bucket mapped to its Intune carrier mechanism."""

    portability_class: str
    count: int
    intune_mechanism: str
    action: str

    def to_dict(self) -> dict:
        return {
            "portability_class": self.portability_class,
            "count": self.count,
            "intune_mechanism": self.intune_mechanism,
            "action": self.action,
        }


@dataclass(frozen=True)
class GpoMigrationPlan:
    """A per-GPO, facet-scoped Intune migration plan."""

    gpo_guid: str
    gpo_name: str
    total_settings: int
    headline_difficulty: str
    scope_targets: tuple[ScopeTarget, ...]
    remediations: tuple[SettingRemediation, ...]

    def to_dict(self) -> dict:
        return {
            "gpo_guid": self.gpo_guid,
            "gpo_name": self.gpo_name,
            "total_settings": self.total_settings,
            "headline_difficulty": self.headline_difficulty,
            "scope_targets": [t.to_dict() for t in self.scope_targets],
            "remediations": [r.to_dict() for r in self.remediations],
        }


def _sanitize_group_token(name: str) -> str:
    """Turn an OU name into a group-name token (alnum + hyphens)."""
    token = re.sub(r"[^0-9A-Za-z]+", "-", name).strip("-")
    return token or "Unscoped"


def _resolve_ou(som_path: str, som_name: str) -> tuple[str, str]:
    """Return ``(scope_level, ou_name)`` for a GPMC SOM path.

    GPMC paths read ``domain.fqdn/OU1/OU2``; a path with no ``/`` is a
    domain-level link. The OU name is the deepest path segment.
    """
    segments = [seg for seg in som_path.split("/") if seg]
    if len(segments) <= 1:
        return ("domain", "")
    return ("ou", segments[-1] or som_name)


def _scope_target(
    som_name: str,
    som_path: str,
    *,
    has_delegation_owner: bool,
) -> ScopeTarget:
    scope_level, ou_name = _resolve_ou(som_path, som_name)
    if scope_level == "domain":
        return ScopeTarget(
            som_name=som_name,
            som_path=som_path,
            scope_level="domain",
            ou_name="",
            intent="domain-root",
            recommended_group="",
            recommendation="Domain-linked GPO — target all managed devices or split by facet; not OU-scoped.",
        )
    intent = classify_ou_intent(ou_name, has_active_gpo=True, has_delegation_owner=has_delegation_owner)
    recommendation, facet_appropriate = _INTENT_RECOMMENDATION.get(
        intent, ("Unclassified OU intent — manual review", False)
    )
    group = f"OrgTree-{_sanitize_group_token(ou_name)}-Devices" if facet_appropriate else ""
    return ScopeTarget(
        som_name=som_name,
        som_path=som_path,
        scope_level="ou",
        ou_name=ou_name,
        intent=intent,
        recommended_group=group,
        recommendation=recommendation,
    )


def build_migration_plan(report: GpoReport, *, has_delegation_owner: bool = True) -> GpoMigrationPlan:
    """Build a facet-scoped Intune migration plan for one GPO.

    Only **enabled** links contribute scope targets (a disabled link does
    not apply the GPO). ``has_delegation_owner`` feeds the OU-intent
    classifier; callers that have run the AD survey can pass the observed
    ``managedBy`` presence, otherwise the conservative default (``True``)
    keeps an owned-OU classification.
    """
    scope_targets = tuple(
        _scope_target(link.som_name, link.som_path, has_delegation_owner=has_delegation_owner)
        for link in report.links
        if link.enabled
    )

    counts = report.counts_by_portability()
    remediations = tuple(
        SettingRemediation(
            portability_class=cls,
            count=counts[cls],
            intune_mechanism=_REMEDIATION.get(cls, ("unknown", "review"))[0],
            action=_REMEDIATION.get(cls, ("unknown", "review"))[1],
        )
        # Stable, difficulty-ordered output (hardest first).
        for cls in sorted(counts, key=lambda c: -_difficulty(c))
    )

    return GpoMigrationPlan(
        gpo_guid=report.guid,
        gpo_name=report.name,
        total_settings=report.setting_count,
        headline_difficulty=report.hardest_portability,
        scope_targets=scope_targets,
        remediations=remediations,
    )


def build_plans(reports: Iterable[GpoReport], *, has_delegation_owner: bool = True) -> list[GpoMigrationPlan]:
    """Build migration plans for many GPOs."""
    return [build_migration_plan(r, has_delegation_owner=has_delegation_owner) for r in reports]


_DIFFICULTY = {
    "review-required": 6,
    "no-csp": 5,
    "deprecated": 4,
    "needs-different-mechanism": 3,
    "needs-platform-script": 2,
    "partial": 1,
    "csp-mappable": 0,
}


def _difficulty(cls: str) -> int:
    return _DIFFICULTY.get(cls, 0)


__all__ = [
    "GpoMigrationPlan",
    "ScopeTarget",
    "SettingRemediation",
    "build_migration_plan",
    "build_plans",
]
