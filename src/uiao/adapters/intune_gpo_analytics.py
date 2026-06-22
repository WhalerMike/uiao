"""Intune Group Policy Analytics adapter — Phase 2 (authoritative MDM verdict).

Phase 1 (``uiao.adapters.modernization.active_directory.gpo_analytics``)
*owns the parse* of ``gpreport.xml`` and assigns each setting a coarse,
type-based ``portability_class``. This module supplies the **authoritative**
per-setting verdict by *consuming* Microsoft's own GPO→MDM crosswalk via the
Intune **Group Policy Analytics** Graph surface — rather than rebuilding that
(large, perishable) crosswalk ourselves.

Flow against a live tenant::

    transport = GraphTransport.from_environment(cloud="gcc-high")
    adapter = IntuneGpoAnalyticsAdapter(transport)
    report_id = adapter.create_migration_report(gpo_xml, ou_dn="OU=Finance,DC=corp,DC=contoso,DC=com")
    mappings = adapter.fetch_setting_mappings(report_id)
    enriched = apply_mdm_verdicts(phase1_report, mappings)   # pure, offline

The Graph-calling methods take the injected
``Transport = Callable[[str, str, dict | None], dict]`` seam every Entra
adapter uses, so they are exercised offline with a recorder/fake; the
:func:`apply_mdm_verdicts` join is pure and needs no transport at all.

Graph permission: ``DeviceManagementConfiguration.ReadWrite.All`` (the
migration-report create action writes a transient analysis object).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from typing import Callable, Iterable

from uiao.adapters.modernization.active_directory.gpo_analytics import GpoReport, GpoSetting

Transport = Callable[[str, str, dict | None], dict]

_GPA_BASE = "/deviceManagement/groupPolicyMigrationReports"


@dataclass(frozen=True)
class SettingMapping:
    """One Intune Group Policy Analytics ``groupPolicySettingMapping`` row."""

    setting_name: str
    is_mdm_supported: bool
    mdm_setting_uri: str = ""
    setting_category: str = ""
    setting_type: str = ""
    mdm_minimum_os_version: str = ""

    @classmethod
    def from_graph(cls, row: dict) -> SettingMapping:
        return cls(
            setting_name=str(row.get("settingName", "")),
            is_mdm_supported=bool(row.get("isMdmSupported", False)),
            mdm_setting_uri=str(row.get("mdmSettingUri", "") or ""),
            setting_category=str(row.get("settingCategory", "") or ""),
            setting_type=str(row.get("settingType", "") or ""),
            mdm_minimum_os_version=str(row.get("mdmMinimumOSVersion", "") or ""),
        )


@dataclass(frozen=True)
class MdmSupportSummary:
    """Aggregate MDM-support rollup over a set of setting mappings."""

    total: int
    supported: int

    @property
    def unsupported(self) -> int:
        return self.total - self.supported

    @property
    def support_pct(self) -> float:
        return round(100.0 * self.supported / self.total, 1) if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "supported": self.supported,
            "unsupported": self.unsupported,
            "support_pct": self.support_pct,
        }


def summarize_mappings(mappings: Iterable[SettingMapping]) -> MdmSupportSummary:
    items = list(mappings)
    return MdmSupportSummary(total=len(items), supported=sum(1 for m in items if m.is_mdm_supported))


class IntuneGpoAnalyticsAdapter:
    """Drives the Intune Group Policy Analytics Graph surface (read-mostly)."""

    ADAPTER_ID = "intune-gpo-analytics"

    def __init__(self, transport: Transport, *, page_cap: int = 50) -> None:
        self._transport = transport
        # Defensive bound on nextLink following so a pathological tenant
        # response can never spin this into an unbounded loop.
        self._page_cap = page_cap

    def create_migration_report(self, gpo_xml: str, *, ou_dn: str = "") -> str:
        """Upload one ``gpreport.xml`` and return the migration report id.

        Wraps ``POST {base}/createMigrationReport``. Graph base64-encodes the
        report content; ``ou_dn`` records which scope the GPO was linked to
        (carried through to the Phase-3 OrgPath join).
        """
        content_b64 = base64.b64encode(gpo_xml.encode("utf-8")).decode("ascii")
        body = {
            "groupPolicyObjectFile": {
                "ouDistinguishedName": ou_dn,
                "content": content_b64,
            }
        }
        resp = self._transport("POST", f"{_GPA_BASE}/createMigrationReport", body)
        # The action returns either the created report object or its id string
        # under "value"; tolerate both shapes.
        report_id = resp.get("id") or resp.get("value") or ""
        return str(report_id)

    def fetch_setting_mappings(self, report_id: str) -> list[SettingMapping]:
        """Return every ``groupPolicySettingMapping`` for a migration report.

        Follows ``@odata.nextLink`` pagination (bounded by ``page_cap``).
        """
        path: str | None = f"{_GPA_BASE}/{report_id}/groupPolicySettingMappings"
        mappings: list[SettingMapping] = []
        pages = 0
        while path and pages < self._page_cap:
            resp = self._transport("GET", path, None)
            for row in resp.get("value", []):
                mappings.append(SettingMapping.from_graph(row))
            next_link = resp.get("@odata.nextLink")
            path = str(next_link) if next_link else None
            pages += 1
        return mappings

    def analyze(self, gpo_xml: str, *, ou_dn: str = "") -> list[SettingMapping]:
        """Convenience: create a report and return its setting mappings."""
        report_id = self.create_migration_report(gpo_xml, ou_dn=ou_dn)
        return self.fetch_setting_mappings(report_id)


# ---------------------------------------------------------------------------
# The join — pure, offline (no transport)
# ---------------------------------------------------------------------------


def _normalize(name: str) -> str:
    return " ".join(name.split()).casefold()


def apply_mdm_verdicts(report: GpoReport, mappings: Iterable[SettingMapping]) -> GpoReport:
    """Override each setting's heuristic verdict with Microsoft's authoritative one.

    Matches Phase-1 settings to Intune Group Policy Analytics mappings on
    (whitespace-normalised, case-folded) setting name. A matched setting's
    ``portability_class`` becomes ``csp-mappable`` when ``isMdmSupported`` and
    ``no-csp`` otherwise, ``verdict_source`` flips to ``intune-gpa``, and the
    MDM setting URI is attached. Unmatched settings keep their heuristic
    verdict untouched. Pure: returns a new :class:`GpoReport`.
    """
    index: dict[str, SettingMapping] = {}
    for m in mappings:
        if m.setting_name:
            index.setdefault(_normalize(m.setting_name), m)

    enriched: list[GpoSetting] = []
    for s in report.settings:
        mapping = index.get(_normalize(s.setting_name))
        if mapping is None:
            enriched.append(s)
            continue
        enriched.append(
            replace(
                s,
                portability_class="csp-mappable" if mapping.is_mdm_supported else "no-csp",
                mdm_supported=mapping.is_mdm_supported,
                mdm_uri=mapping.mdm_setting_uri,
                verdict_source="intune-gpa",
            )
        )
    return replace(report, settings=tuple(enriched))


__all__ = [
    "IntuneGpoAnalyticsAdapter",
    "MdmSupportSummary",
    "SettingMapping",
    "apply_mdm_verdicts",
    "summarize_mappings",
]
