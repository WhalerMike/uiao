"""AD-attribute → OrgPath-facet mapping (the READ/ASSESS → DERIVE bridge).

Defines how source Active Directory attributes (``department``, ``title``,
office, ``employeeType``, SPNs, group membership, …) are translated into
OrgPath facet values (``region``, ``department``, ``role``, … per the
Codebook UIAO_151). This is the piece that was missing between the AD survey
(``adapters.modernization.active_directory.survey``) and the Entra/ARM write
adapters: the survey reads AD and the adapters write facet values, but nothing
*derived* the facet values from AD. This module does.

A mapping is a list of :class:`FacetRule`, one per facet. Each rule names the
source AD attribute (or a pure derivation), a transform, and a value-alias
table that maps raw AD values onto the facet's codebook enum (e.g.
``"Information Technology" → "IT"``). :func:`default_mapping` ships a sensible
default; :meth:`OrgPathMapping.from_yaml` loads a tenant override so operators
can tune the aliases without a code change.

The mapping is deliberately **not** canon data — it is operator/tenant
configuration. The default lives in code; tenant YAML is read from any path.
``ad_facet_mapping.example.yaml`` (shipped beside this module) documents the
schema for operators to copy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

# Transform verbs a rule may use to turn a raw AD value into a facet candidate.
TRANSFORMS = frozenset({"alias", "passthrough", "date", "derive_account_type"})
# How an "alias" transform matches a raw value against the alias table.
MATCH_MODES = frozenset({"exact", "substring"})


class MappingError(ValueError):
    """Raised when a mapping document is structurally invalid."""


@dataclass(frozen=True)
class FacetRule:
    """How one OrgPath facet is derived from an AD object.

    Attributes
    ----------
    facet
        Codebook facet name (e.g. ``"department"``).
    source
        AD attribute key read from the object record (e.g. ``"department"``).
        ``None`` for pure derivations (``transform="derive_account_type"``).
    transform
        ``alias`` (map raw via ``aliases``), ``passthrough`` (use raw as-is),
        ``date`` (normalise to ``YYYY-MM-DD``), or ``derive_account_type``
        (compute from SPNs / privileged-group membership).
    aliases
        Lowercased raw AD value → codebook value. Used by the ``alias`` transform.
    match
        ``exact`` (raw must equal an alias key, case-insensitively) or
        ``substring`` (first alias key contained in the raw value wins —
        useful for free-text ``title`` fields).
    default
        Codebook value used when the source is absent or unmapped. ``None``
        means "leave the facet unset and emit a finding".
    """

    facet: str
    source: str | None = None
    transform: str = "alias"
    aliases: Mapping[str, str] = field(default_factory=dict)
    match: str = "exact"
    default: str | None = None

    def __post_init__(self) -> None:
        if self.transform not in TRANSFORMS:
            raise MappingError(
                f"facet '{self.facet}': unknown transform '{self.transform}' (one of {sorted(TRANSFORMS)})"
            )
        if self.match not in MATCH_MODES:
            raise MappingError(
                f"facet '{self.facet}': unknown match mode '{self.match}' (one of {sorted(MATCH_MODES)})"
            )


@dataclass(frozen=True)
class OrgPathMapping:
    """An ordered set of per-facet rules."""

    rules: tuple[FacetRule, ...]

    def rule_for(self, facet: str) -> FacetRule | None:
        return next((r for r in self.rules if r.facet == facet), None)

    @classmethod
    def from_dict(cls, doc: Mapping[str, object]) -> OrgPathMapping:
        """Build a mapping from a parsed YAML/JSON document.

        Expected shape::

            facets:
              - facet: department
                source: department
                transform: alias
                match: exact
                default: null
                aliases: { "information technology": IT, hr: HR }
        """
        raw_facets = doc.get("facets")
        if not isinstance(raw_facets, list) or not raw_facets:
            raise MappingError("mapping must contain a non-empty 'facets' list")
        rules: list[FacetRule] = []
        for entry in raw_facets:
            if not isinstance(entry, Mapping) or "facet" not in entry:
                raise MappingError(f"each facet rule must be a mapping with a 'facet' key; got {entry!r}")
            aliases_raw = entry.get("aliases", {}) or {}
            if not isinstance(aliases_raw, Mapping):
                raise MappingError(f"facet '{entry['facet']}': 'aliases' must be a mapping")
            rules.append(
                FacetRule(
                    facet=str(entry["facet"]),
                    source=entry.get("source"),  # type: ignore[arg-type]
                    transform=str(entry.get("transform", "alias")),
                    aliases={str(k).lower(): str(v) for k, v in aliases_raw.items()},
                    match=str(entry.get("match", "exact")),
                    default=entry.get("default"),  # type: ignore[arg-type]
                )
            )
        return cls(rules=tuple(rules))

    @classmethod
    def from_yaml(cls, path: Path | str) -> OrgPathMapping:
        """Load a tenant mapping override from a YAML file."""
        import yaml

        text = Path(path).read_text(encoding="utf-8")
        doc = yaml.safe_load(text)
        if not isinstance(doc, Mapping):
            raise MappingError("mapping YAML must be a mapping at the top level")
        return cls.from_dict(doc)


# ---------------------------------------------------------------------------
# Default mapping — sensible AD→facet derivation grounded in UIAO_151 enums
# ---------------------------------------------------------------------------


def default_mapping() -> OrgPathMapping:
    """The shipped default AD→facet mapping.

    Tenants override per-facet aliases via :meth:`OrgPathMapping.from_yaml`;
    these defaults make the assigner useful out of the box for a typical AD.
    """
    return OrgPathMapping(
        rules=(
            FacetRule(
                facet="region",
                source="physicalDeliveryOfficeName",
                transform="alias",
                match="substring",
                aliases={
                    "washington": "NCR",
                    "dc": "NCR",
                    "arlington": "NCR",
                    "reston": "EASTUS",
                    "new york": "EASTUS",
                    "boston": "EASTUS",
                    "atlanta": "EASTUS",
                    "chicago": "CENTRAL",
                    "dallas": "CENTRAL",
                    "denver": "CENTRAL",
                    "seattle": "WESTUS",
                    "san francisco": "WESTUS",
                    "los angeles": "WESTUS",
                    "london": "EMEA",
                    "frankfurt": "EMEA",
                    "singapore": "APAC",
                    "tokyo": "APAC",
                    "sydney": "APAC",
                    "são paulo": "LATAM",
                    "mexico city": "LATAM",
                },
            ),
            FacetRule(
                facet="department",
                source="department",
                transform="alias",
                match="exact",
                aliases={
                    "information technology": "IT",
                    "it": "IT",
                    "human resources": "HR",
                    "hr": "HR",
                    "finance": "Finance",
                    "accounting": "Finance",
                    "legal": "Legal",
                    "compliance": "Legal",
                    "engineering": "Engineering",
                    "operations": "Operations",
                    "ops": "Operations",
                    "sales": "Sales",
                    "marketing": "Sales",
                    "executive": "Executive",
                    "leadership": "Executive",
                },
            ),
            FacetRule(
                facet="division",
                source="division",
                transform="alias",
                match="exact",
                aliases={
                    "cybersecurity": "CyberOps",
                    "cyber": "CyberOps",
                    "security operations": "CyberOps",
                    "infrastructure": "InfraOps",
                    "infra": "InfraOps",
                    "application development": "AppDev",
                    "appdev": "AppDev",
                    "grc": "GRC",
                    "governance": "GRC",
                    "service desk": "Service",
                    "support": "Service",
                    "data": "Data",
                    "analytics": "Data",
                    "cloud": "Cloud",
                    "identity": "Identity",
                },
            ),
            FacetRule(
                facet="role",
                source="title",
                transform="alias",
                match="substring",
                default="Analyst",
                aliases={
                    "ciso": "CISO",
                    "chief information security": "CISO",
                    "cio": "CIO",
                    "chief information officer": "CIO",
                    "cto": "CTO",
                    "chief technology": "CTO",
                    "vice president": "VP",
                    "vp": "VP",
                    "director": "Director",
                    "manager": "Manager",
                    "architect": "Architect",
                    "engineer": "Engineer",
                    "developer": "Engineer",
                    "analyst": "Analyst",
                },
            ),
            FacetRule(facet="cost_center", source="extensionAttribute5", transform="passthrough"),
            FacetRule(
                facet="classification",
                source="employeeType",
                transform="alias",
                match="exact",
                default="Employee",
                aliases={
                    "employee": "Employee",
                    "full-time": "Employee",
                    "fulltime": "Employee",
                    "part-time": "PartTime",
                    "parttime": "PartTime",
                    "contractor": "Contractor",
                    "vendor": "Contractor",
                    "intern": "Intern",
                    "volunteer": "Volunteer",
                    "executive": "Executive",
                },
            ),
            FacetRule(facet="hire_date", source="whenCreated", transform="date"),
            FacetRule(facet="term_date", source="accountExpires", transform="date", default=""),
            FacetRule(
                facet="clearance_level",
                source="clearanceLevel",
                transform="alias",
                match="exact",
                default="None",
                aliases={
                    "none": "None",
                    "public trust": "PublicTrust",
                    "publictrust": "PublicTrust",
                    "secret": "Secret",
                    "top secret": "TopSecret",
                    "topsecret": "TopSecret",
                    "ts/sci": "TS_SCI",
                    "ts_sci": "TS_SCI",
                },
            ),
            FacetRule(facet="account_type", transform="derive_account_type", default="Standard"),
        )
    )
