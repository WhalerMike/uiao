"""GPO settings-level analyzer — Phase 1 (settings inventory + portability triage).

Parses Group Policy Object backups (``Backup-GPO`` output, i.e. the
``gpreport.xml`` settings report Microsoft's own Group Policy Analytics
ingests) into a structured, schema-validatable inventory of every
configured setting, classified by **setting class** (admin-template /
security / preference / script / folder-redirection / …) and a coarse,
**type-based portability heuristic**.

Scope discipline (see the GPO-analyzer ADR):

* This module **owns the parse** — turning ``gpreport.xml`` into typed
  records — and a *coarse, indicative* portability class derived purely
  from the setting type. It is deterministic and fully offline
  (fixture-testable); it makes no network calls.
* It does **not** rebuild Microsoft's GPO→CSP crosswalk. The
  authoritative per-setting ``isMdmSupported`` verdict comes from
  Intune Group Policy Analytics over Graph in Phase 2
  (``uiao.adapters.intune_gpo_analytics``), which *overrides* the
  heuristic ``portability_class`` here on a per-setting basis.
* The OrgPath join (link a GPO's scope → OU intent → facet → policy
  target) is Phase 3.

The ``portability_class`` emitted here is therefore explicitly labelled
*indicative* — a triage signal for "how hard will this GPO be to move",
not an authoritative migration verdict.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# XML Schema instance namespace — the home of the ``xsi:type`` attribute
# that names each Group Policy client-side extension's settings type.
_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"

# A GUID with the canonical brace form Microsoft writes in gpreport.xml.
_GUID_BRACED_LEN = 38  # len("{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}")

# Extension xsi:type local-name (lowercased) → (setting_class, portability_class).
# The portability_class is a COARSE, indicative triage signal keyed off the
# setting *type*, not an authoritative MDM-support verdict (that is Phase 2).
_EXTENSION_CLASSIFICATION: dict[str, tuple[str, str]] = {
    "registrysettings": ("admin-template", "csp-mappable"),
    "scripts": ("script", "needs-platform-script"),
    "securitysettings": ("security", "partial"),
    "auditsettings": ("security-audit", "partial"),
    "advancedauditconfiguration": ("security-audit", "partial"),
    "folderredirectionsettings": ("folder-redirection", "needs-different-mechanism"),
    "softwareinstallationsettings": ("software-install", "no-csp"),
    "publickeysettings": ("certificate", "needs-different-mechanism"),
    "internetexplorersettings": ("ie-maintenance", "deprecated"),
    "lan": ("network-wired", "csp-mappable"),
    "wlan": ("network-wifi", "csp-mappable"),
}

# Group Policy Preferences share a namespace; any extension whose settings
# namespace carries this marker is a preference regardless of local type
# name (this also disambiguates GPP "RegistrySettings" from the
# admin-template "RegistrySettings", which collide on local name).
_PREFERENCES_NS_MARKER = "preferences"

# Portability class assigned when no classification rule matches; surfaced
# as a finding so coverage gaps are explicit rather than silently dropped.
_UNKNOWN_CLASS = ("unknown", "review-required")

# The full set of portability classes this analyzer can emit (mirrors the
# JSON Schema enum — keep the two in lockstep).
PORTABILITY_CLASSES: frozenset[str] = frozenset(
    {
        "csp-mappable",
        "partial",
        "needs-platform-script",
        "needs-different-mechanism",
        "no-csp",
        "deprecated",
        "review-required",
    }
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GpoFinding:
    """One analyzer finding (unknown extension type, empty GPO, etc.)."""

    code: str  # GOV-GPO-NNN
    severity: str  # P1 | P2 | P3 | P4
    detail: str
    gpo_guid: str = ""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "detail": self.detail,
            "gpo_guid": self.gpo_guid,
        }


@dataclass(frozen=True)
class GpoLink:
    """A single Scope-of-Management link the GPO is attached to.

    Drives the Phase-3 OrgPath join: ``som_path`` resolves to an OU whose
    intent (functional / geographic / …) maps to an OrgPath facet target.
    """

    som_name: str
    som_path: str
    enabled: bool
    enforced: bool

    def to_dict(self) -> dict:
        return {
            "som_name": self.som_name,
            "som_path": self.som_path,
            "enabled": self.enabled,
            "enforced": self.enforced,
        }


@dataclass(frozen=True)
class GpoSetting:
    """One configured setting (or setting entry) within a GPO half."""

    scope: str  # "Computer" | "User"
    setting_class: str  # admin-template | security | preference | script | …
    extension_type: str  # raw xsi:type local name as authored
    setting_name: str
    portability_class: str  # COARSE heuristic until Phase 2 overrides per-setting
    state: str = ""  # Enabled | Disabled | "" (not applicable)
    category: str = ""  # ADMX category path when present
    # Phase-2 enrichment (Intune Group Policy Analytics over Graph). Default
    # ``verdict_source == "heuristic"`` means only the type-based triage has
    # run; ``"intune-gpa"`` means ``portability_class`` carries Microsoft's
    # authoritative ``isMdmSupported`` verdict for this setting.
    mdm_supported: bool | None = None
    mdm_uri: str = ""
    verdict_source: str = "heuristic"

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "setting_class": self.setting_class,
            "extension_type": self.extension_type,
            "setting_name": self.setting_name,
            "portability_class": self.portability_class,
            "state": self.state,
            "category": self.category,
            "mdm_supported": self.mdm_supported,
            "mdm_uri": self.mdm_uri,
            "verdict_source": self.verdict_source,
        }


# Portability classes ranked worst → best for "headline difficulty" rollup.
_PORTABILITY_DIFFICULTY: dict[str, int] = {
    "review-required": 6,
    "no-csp": 5,
    "deprecated": 4,
    "needs-different-mechanism": 3,
    "needs-platform-script": 2,
    "partial": 1,
    "csp-mappable": 0,
}


@dataclass(frozen=True)
class GpoReport:
    """The parsed inventory of a single GPO's ``gpreport.xml``."""

    guid: str
    name: str
    computer_enabled: bool
    user_enabled: bool
    created_time: str
    modified_time: str
    wmi_filter: str
    links: tuple[GpoLink, ...]
    settings: tuple[GpoSetting, ...]
    findings: tuple[GpoFinding, ...] = ()

    @property
    def setting_count(self) -> int:
        return len(self.settings)

    def counts_by_class(self) -> dict[str, int]:
        """Setting counts keyed by ``setting_class``."""
        out: dict[str, int] = {}
        for s in self.settings:
            out[s.setting_class] = out.get(s.setting_class, 0) + 1
        return out

    def counts_by_portability(self) -> dict[str, int]:
        """Setting counts keyed by the indicative ``portability_class``."""
        out: dict[str, int] = {}
        for s in self.settings:
            out[s.portability_class] = out.get(s.portability_class, 0) + 1
        return out

    @property
    def hardest_portability(self) -> str:
        """The most difficult portability class present (headline triage)."""
        if not self.settings:
            return "csp-mappable"
        return max(
            (s.portability_class for s in self.settings),
            key=lambda c: _PORTABILITY_DIFFICULTY.get(c, 0),
        )

    def to_dict(self) -> dict:
        return {
            "guid": self.guid,
            "name": self.name,
            "computer_enabled": self.computer_enabled,
            "user_enabled": self.user_enabled,
            "created_time": self.created_time,
            "modified_time": self.modified_time,
            "wmi_filter": self.wmi_filter,
            "links": [link.to_dict() for link in self.links],
            "settings": [s.to_dict() for s in self.settings],
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                "setting_count": self.setting_count,
                "counts_by_class": self.counts_by_class(),
                "counts_by_portability": self.counts_by_portability(),
                "hardest_portability": self.hardest_portability,
            },
        }


@dataclass(frozen=True)
class GpoAnalysis:
    """An inventory across many GPOs (one ``Backup-GPO`` tree)."""

    version: str
    reports: tuple[GpoReport, ...] = ()
    findings: tuple[GpoFinding, ...] = field(default_factory=tuple)

    @property
    def gpo_count(self) -> int:
        return len(self.reports)

    @property
    def total_settings(self) -> int:
        return sum(r.setting_count for r in self.reports)

    def rollup_by_portability(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.reports:
            for cls, n in r.counts_by_portability().items():
                out[cls] = out.get(cls, 0) + n
        return out

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "gpo_count": self.gpo_count,
            "total_settings": self.total_settings,
            "rollup_by_portability": self.rollup_by_portability(),
            "reports": [r.to_dict() for r in self.reports],
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# XML helpers (namespace-tolerant — gpreport.xml is heavily namespaced)
# ---------------------------------------------------------------------------


def _local(tag: str) -> str:
    """Strip an ElementTree ``{namespace}Local`` tag down to ``Local``."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _ns(tag: str) -> str:
    """Return the namespace URI of an ElementTree tag (empty when none)."""
    if tag.startswith("{"):
        return tag[1 : tag.index("}")]
    return ""


def _child(elem: ET.Element, local_name: str) -> ET.Element | None:
    """First direct child of ``elem`` whose local tag == ``local_name``."""
    for c in elem:
        if _local(c.tag) == local_name:
            return c
    return None


def _child_text(elem: ET.Element, local_name: str, default: str = "") -> str:
    c = _child(elem, local_name)
    if c is None or c.text is None:
        return default
    return c.text.strip()


def _children(elem: ET.Element, local_name: str) -> list[ET.Element]:
    return [c for c in elem if _local(c.tag) == local_name]


def _bool_text(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_extension(type_local: str, settings_ns: str) -> tuple[str, str]:
    """Map an extension to ``(setting_class, portability_class)``.

    ``type_local`` is the ``xsi:type`` local name (e.g. ``RegistrySettings``);
    ``settings_ns`` is the namespace URI of the extension's settings (used to
    disambiguate Group Policy Preferences from like-named policy extensions).
    Unknown extensions fall through to ``("unknown", "review-required")``.
    """
    if _PREFERENCES_NS_MARKER in settings_ns.lower():
        return ("preference", "needs-platform-script")
    return _EXTENSION_CLASSIFICATION.get(type_local.lower(), _UNKNOWN_CLASS)


# ---------------------------------------------------------------------------
# Parsing — single gpreport.xml
# ---------------------------------------------------------------------------


def _extract_guid(root: ET.Element) -> str:
    """Return the braced GPO GUID from the (doubly-nested) Identifier block."""
    for elem in root.iter():
        if _local(elem.tag) == "Identifier" and elem.text:
            text = elem.text.strip()
            if len(text) == _GUID_BRACED_LEN and text.startswith("{"):
                return text
    return ""


def _extension_type_local(ext: ET.Element) -> str:
    """The ``xsi:type`` local name of an ``<Extension>`` (after any prefix)."""
    raw = ext.get(_XSI_TYPE, "")
    return raw.rsplit(":", 1)[-1] if raw else ""


def _settings_namespace(ext: ET.Element) -> str:
    """Infer the extension's settings namespace from its first child tag."""
    for child in ext:
        return _ns(child.tag)
    return ""


def _setting_name(entry: ET.Element) -> str:
    """Best-effort human name for one setting entry under an extension."""
    name = _child_text(entry, "Name")
    if name:
        return name
    for attr in ("name", "Name"):
        if entry.get(attr):
            return entry.get(attr, "")
    return _local(entry.tag)


def _parse_half(root: ET.Element, half_local: str, scope: str) -> tuple[list[GpoSetting], list[GpoFinding], bool]:
    """Parse one ``<Computer>`` / ``<User>`` half into settings + findings.

    Returns ``(settings, findings, enabled)``.
    """
    half = _child(root, half_local)
    if half is None:
        return ([], [], False)

    enabled = _bool_text(_child_text(half, "Enabled", "false"))
    settings: list[GpoSetting] = []
    findings: list[GpoFinding] = []

    ext_data = _child(half, "ExtensionData")
    if ext_data is None:
        return (settings, findings, enabled)

    for ext in _children(ext_data, "Extension"):
        type_local = _extension_type_local(ext)
        settings_ns = _settings_namespace(ext)
        setting_class, portability = classify_extension(type_local, settings_ns)
        if setting_class == "unknown":
            findings.append(
                GpoFinding(
                    code="GOV-GPO-001",
                    severity="P3",
                    detail=(
                        f"Unclassified GPO extension '{type_local or '(no xsi:type)'}' "
                        f"in {scope} scope — portability marked review-required."
                    ),
                )
            )
        # Each direct child of the extension is one setting entry. ``Name`` /
        # ``Blocked`` bookkeeping elements carry no settings payload.
        for entry in ext:
            if _local(entry.tag) in ("Name", "Blocked"):
                continue
            settings.append(
                GpoSetting(
                    scope=scope,
                    setting_class=setting_class,
                    extension_type=type_local,
                    setting_name=_setting_name(entry),
                    portability_class=portability,
                    state=_child_text(entry, "State"),
                    category=_child_text(entry, "Category"),
                )
            )
    return (settings, findings, enabled)


def _parse_links(root: ET.Element) -> list[GpoLink]:
    links: list[GpoLink] = []
    for link in _children(root, "LinksTo"):
        links.append(
            GpoLink(
                som_name=_child_text(link, "SOMName"),
                som_path=_child_text(link, "SOMPath"),
                enabled=_bool_text(_child_text(link, "Enabled", "false")),
                enforced=_bool_text(_child_text(link, "NoOverride", "false")),
            )
        )
    return links


def parse_gpo_report(xml_text: str) -> GpoReport:
    """Parse one ``gpreport.xml`` document into a :class:`GpoReport`.

    Pure and offline. Raises :class:`xml.etree.ElementTree.ParseError` on
    malformed XML (callers that walk a tree catch this per-file).
    """
    root = ET.fromstring(xml_text)

    comp_settings, comp_findings, comp_enabled = _parse_half(root, "Computer", "Computer")
    user_settings, user_findings, user_enabled = _parse_half(root, "User", "User")

    guid = _extract_guid(root)
    name = _child_text(root, "Name")
    settings = tuple(comp_settings + user_settings)
    findings = [GpoFinding(f.code, f.severity, f.detail, guid) for f in (comp_findings + user_findings)]

    if not settings:
        findings.append(
            GpoFinding(
                code="GOV-GPO-002",
                severity="P4",
                detail=f"GPO '{name or guid}' has no configured settings (empty / tombstone candidate).",
                gpo_guid=guid,
            )
        )

    return GpoReport(
        guid=guid,
        name=name,
        computer_enabled=comp_enabled,
        user_enabled=user_enabled,
        created_time=_child_text(root, "CreatedTime"),
        modified_time=_child_text(root, "ModifiedTime"),
        wmi_filter=_child_text(root, "FilterName"),
        links=tuple(_parse_links(root)),
        settings=settings,
        findings=tuple(findings),
    )


def parse_gpo_report_file(path: Path | str) -> GpoReport:
    """Parse a single ``gpreport.xml`` from disk."""
    return parse_gpo_report(Path(path).read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------------------
# Parsing — a Backup-GPO tree (or a flat directory of gpreport.xml files)
# ---------------------------------------------------------------------------

ANALYSIS_VERSION = "1.0.0"


def _discover_reports(root_dir: Path) -> list[Path]:
    """Find every ``gpreport.xml`` under ``root_dir`` (recursive, sorted)."""
    return sorted(root_dir.rglob("gpreport.xml"))


def analyze_backup(root_dir: Path | str, *, extra_files: Iterable[Path] | None = None) -> GpoAnalysis:
    """Analyze a ``Backup-GPO`` tree into a :class:`GpoAnalysis`.

    Walks ``root_dir`` for ``gpreport.xml`` files (the per-GPO settings
    report Microsoft's Group Policy Analytics also consumes). A malformed
    or unreadable report does not abort the run — it is recorded as a
    ``GOV-GPO-003`` finding so one bad backup never blackholes the rest.
    """
    root = Path(root_dir)
    paths = _discover_reports(root)
    if extra_files is not None:
        paths = sorted({*paths, *(Path(p) for p in extra_files)})

    reports: list[GpoReport] = []
    findings: list[GpoFinding] = []
    for path in paths:
        try:
            reports.append(parse_gpo_report_file(path))
        except (ET.ParseError, OSError, ValueError) as exc:
            findings.append(
                GpoFinding(
                    code="GOV-GPO-003",
                    severity="P2",
                    detail=f"Failed to parse GPO report '{path}': {exc}",
                )
            )

    if not reports and not findings:
        findings.append(
            GpoFinding(
                code="GOV-GPO-004",
                severity="P2",
                detail=f"No gpreport.xml files found under '{root}'.",
            )
        )

    return GpoAnalysis(version=ANALYSIS_VERSION, reports=tuple(reports), findings=tuple(findings))


__all__ = [
    "ANALYSIS_VERSION",
    "PORTABILITY_CLASSES",
    "GpoAnalysis",
    "GpoFinding",
    "GpoLink",
    "GpoReport",
    "GpoSetting",
    "analyze_backup",
    "classify_extension",
    "parse_gpo_report",
    "parse_gpo_report_file",
]
