"""OrgPath codebook loader — Model C (15-facet multi-attribute).

Loads ``src/uiao/canon/data/orgpath/codebook.yaml`` (the executable canon
bound to UIAO_151 by ADR-035, restructured to Model C by ADR-078) and
exposes a :class:`Codebook` object the drift engine and the OrgPath
adapters consume.

Per ADR-078, OrgPath identity is decomposed into facets, each carried by
one ``onPremisesExtensionAttribute`` slot:

* slots 1-10 are the canonical facets (region, department, division,
  role, cost_center, classification, hire_date, term_date,
  clearance_level, account_type);
* slots 11-14 are reserved for tenant-specific extension;
* slot 15 carries the derived canonical OrgPath — the inheritance
  layer of the Hybrid-C+Path model (ADR-127), composed from the
  governance-layer hierarchy facets with a trailing delimiter always
  present. The optional top-level ``hybrid`` block declares the
  composition (``derived_from`` order, delimiter, segment labels).

The loader:

* validates the YAML structure against
  ``src/uiao/schemas/orgpath/codebook.schema.json`` (v2.0.0);
* validates that each facet binds a unique extensionAttribute slot (the
  Model C invariant the JSON Schema cannot express);
* validates that every deprecated ``replaced_by`` resolves to an active
  value in the same facet's enumeration;
* exposes per-facet helpers (``is_active``, ``is_deprecated``,
  ``replacement_for``, ``is_valid_value``) and codebook-level lookup
  (``facet``, ``facet_by_attribute``, ``facets``) so the drift engine
  can emit per-facet drift findings without re-parsing the YAML.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, Mapping

import yaml

# Canonical regex for any extensionAttribute slot name accepted by the schema.
_EXTENSION_ATTRIBUTE_RE = re.compile(r"^extensionAttribute([1-9]|1[0-5])$")


class CodebookValidationError(ValueError):
    """Raised when the codebook YAML fails schema or integrity validation."""


@dataclass(frozen=True)
class FacetValue:
    """A single enumerated value for one facet."""

    value: str
    description: str


@dataclass(frozen=True)
class DeprecatedFacetValue:
    """A facet value that has been retired in favour of a successor."""

    value: str
    replaced_by: str
    deprecated_at: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Facet:
    """One semantic facet of OrgPath, bound to a single extensionAttribute slot.

    A facet has one of three kinds:

    * ``enumerated`` — values are constrained to a closed list (``enumeration``).
    * ``typed`` — values are constrained only by ``value_type`` and optional
      ``value_pattern`` (e.g., ISO 8601 date). ``enumeration`` is empty.
    * ``reserved`` — no semantics declared yet; the slot is unused. Both
      ``enumeration`` and ``value_pattern`` are absent.
    """

    name: str
    attribute: str
    description: str
    kind: str
    enumeration: Mapping[str, FacetValue] = field(default_factory=dict)
    deprecated: Mapping[str, DeprecatedFacetValue] = field(default_factory=dict)
    value_type: str | None = None
    value_pattern: str | None = None
    allow_empty: bool = False
    # Whether this facet is stamped onto a directory extensionAttribute slot.
    # ``False`` keeps the facet's semantics (HR-SSOT / reporting / lifecycle)
    # without consuming one of the scarce 15 directory slots — the projection
    # subset that controls "attributes written per object" (ADR-121). Defaults
    # ``True`` so existing in-memory codebooks are unaffected.
    projected: bool = True

    # ------------------------------------------------------------------
    # Convenience accessors used by the drift engine and adapters
    # ------------------------------------------------------------------
    def is_active(self, value: str) -> bool:
        """True when ``value`` is a current (non-deprecated) value of this facet.

        For enumerated facets, checks membership in ``enumeration``.
        For typed facets, checks ``value_pattern`` (and ``allow_empty``).
        For reserved facets, always False (no value can be active yet).
        """
        if self.kind == "enumerated":
            return value in self.enumeration
        if self.kind == "typed":
            if value == "" and self.allow_empty:
                return True
            if self.value_pattern is None:
                return True
            return bool(re.match(self.value_pattern, value))
        # reserved
        return False

    def is_deprecated(self, value: str) -> bool:
        """True when ``value`` is a deprecated value of this facet."""
        return value in self.deprecated

    def replacement_for(self, value: str) -> str | None:
        """Successor value for a deprecated ``value``, or None."""
        entry = self.deprecated.get(value)
        return entry.replaced_by if entry else None

    def is_valid_value(self, value: str) -> bool:
        """True when ``value`` is acceptable for this facet (active or deprecated).

        Used by the drift engine to distinguish *unknown* values
        (DRIFT-SEMANTIC) from *deprecated* values (also DRIFT-SEMANTIC
        but with a known replacement path).
        """
        return self.is_active(value) or self.is_deprecated(value)


@dataclass(frozen=True)
class Codebook:
    """In-memory view of the Model C OrgPath codebook.

    The Model A composite-string API (``is_active(code)``,
    ``parent_of(code)``, ``regex``, ``codes``) is **gone** per ADR-078;
    use ``codebook.facet("region").is_active("NCR")`` instead.
    """

    schema_version: str
    document_id: str
    parent_canon: str
    model: str
    adoption_tier_min: int
    facets: Mapping[str, Facet]
    # Hybrid-C+Path declaration (ADR-127): governance layer on slots
    # 1-14, derived OrgPath (inheritance layer) on slot 15. ``None`` for
    # in-memory codebooks that predate the hybrid model.
    hybrid: Mapping | None = None

    def facet(self, name: str) -> Facet:
        """Return the facet by name, raising KeyError if unknown.

        Use ``facet_by_attribute`` to look up by extensionAttribute slot.
        """
        try:
            return self.facets[name]
        except KeyError as exc:
            raise KeyError(f"OrgPath facet '{name}' is not declared in the codebook") from exc

    def facet_by_attribute(self, attribute: str) -> Facet | None:
        """Return the facet bound to ``attribute`` (e.g., 'extensionAttribute1')."""
        for f in self.facets.values():
            if f.attribute == attribute:
                return f
        return None

    def has_facet(self, name: str) -> bool:
        return name in self.facets

    def derived_path_facet_name(self) -> str | None:
        """Name of the ADR-127 derived-OrgPath facet, or None.

        The inheritance layer of the Hybrid-C+Path model is recomputed
        from governance facets by the writers — it is never sourced from
        HR / survey data, so surveys and backfill planners exclude it.
        """
        if not self.hybrid:
            return None
        layer = self.hybrid.get("inheritance_layer") or {}
        return layer.get("facet")

    def projected_facets(self) -> Mapping[str, Facet]:
        """Facets stamped onto a directory slot (``projected`` and not reserved).

        This is the subset that determines how many extensionAttributes are
        written per object. Non-projected facets keep their semantics but are
        not pushed to the directory (ADR-121).
        """
        return {n: f for n, f in self.facets.items() if f.projected and f.kind != "reserved"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_DEFAULT_CODEBOOK_RESOURCE = ("uiao.canon.data.orgpath", "codebook.yaml")
_DEFAULT_SCHEMA_RESOURCE = ("uiao.schemas.orgpath", "codebook.schema.json")


def _read_default_codebook() -> str:
    package, name = _DEFAULT_CODEBOOK_RESOURCE
    return resources.files(package).joinpath(name).read_text(encoding="utf-8")


def _read_default_schema() -> Dict:
    package, name = _DEFAULT_SCHEMA_RESOURCE
    return json.loads(  # type: ignore[no-any-return]
        resources.files(package).joinpath(name).read_text(encoding="utf-8")
    )


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise CodebookValidationError("jsonschema is required to validate the OrgPath codebook") from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path)
        raise CodebookValidationError(f"OrgPath codebook schema validation failed: {exc.message} at {path}") from exc


def _validate_integrity(document: Dict) -> None:
    """Enforce invariants not expressible in JSON Schema."""
    facets = document["facets"]

    # Slot uniqueness — no two facets may bind to the same
    # extensionAttribute slot.
    slots_seen: Dict[str, str] = {}
    for facet_name, facet_doc in facets.items():
        attribute = facet_doc["attribute"]
        if not _EXTENSION_ATTRIBUTE_RE.match(attribute):
            raise CodebookValidationError(
                f"Facet '{facet_name}' binds to '{attribute}', which is not a valid extensionAttribute slot (1-15)."
            )
        if attribute in slots_seen:
            raise CodebookValidationError(
                f"Facets '{facet_name}' and '{slots_seen[attribute]}' both bind "
                f"to '{attribute}'. Each extensionAttribute slot must be "
                "claimed by at most one facet."
            )
        slots_seen[attribute] = facet_name

    # Hybrid-C+Path (ADR-127): the inheritance layer must reference a
    # declared facet, bind the same slot as that facet, and derive from
    # declared, projected, non-reserved facets.
    hybrid_doc = document.get("hybrid")
    if hybrid_doc:
        layer = hybrid_doc["inheritance_layer"]
        path_facet_name = layer["facet"]
        if path_facet_name not in facets:
            raise CodebookValidationError(
                f"hybrid.inheritance_layer.facet '{path_facet_name}' is not declared in 'facets'."
            )
        path_facet_doc = facets[path_facet_name]
        if path_facet_doc["attribute"] != layer["attribute"]:
            raise CodebookValidationError(
                f"hybrid.inheritance_layer.attribute '{layer['attribute']}' does not match "
                f"facet '{path_facet_name}' binding '{path_facet_doc['attribute']}'."
            )
        for source_name in layer["derived_from"]:
            if source_name not in facets:
                raise CodebookValidationError(
                    f"hybrid.inheritance_layer.derived_from names '{source_name}', which is not declared in 'facets'."
                )
            source_doc = facets[source_name]
            if source_doc.get("kind") == "reserved" or not source_doc.get("projected", True):
                raise CodebookValidationError(
                    f"hybrid.inheritance_layer.derived_from names '{source_name}', which is "
                    "reserved or not projected — the derived OrgPath can only compose "
                    "facets that are actually stamped to a directory slot."
                )

    # Deprecated.replaced_by must resolve to an active enumeration value
    # in the same facet.
    deprecated_doc = document.get("deprecated") or {}
    for facet_name, dep_list in deprecated_doc.items():
        if facet_name not in facets:
            raise CodebookValidationError(
                f"Deprecated values declared for facet '{facet_name}' but the facet itself is not declared in 'facets'."
            )
        facet_doc = facets[facet_name]
        if facet_doc.get("kind") != "enumerated":
            raise CodebookValidationError(
                f"Deprecated values declared for non-enumerated facet "
                f"'{facet_name}'. Only enumerated facets support deprecation."
            )
        active_values = {v["value"] for v in facet_doc.get("enumeration", [])}
        for dep in dep_list or []:
            if dep["replaced_by"] not in active_values:
                raise CodebookValidationError(
                    f"Deprecated value '{dep['value']}' in facet '{facet_name}' "
                    f"is replaced_by '{dep['replaced_by']}', which is not an "
                    "active enumeration value in that facet."
                )


def _build_facet(name: str, facet_doc: Dict, deprecated_doc: Dict) -> Facet:
    enumeration_list = facet_doc.get("enumeration", []) or []
    enumeration = {
        item["value"]: FacetValue(value=item["value"], description=item["description"]) for item in enumeration_list
    }
    dep_list = (deprecated_doc.get(name) or []) if facet_doc.get("kind") == "enumerated" else []
    deprecated = {
        d["value"]: DeprecatedFacetValue(
            value=d["value"],
            replaced_by=d["replaced_by"],
            deprecated_at=d.get("deprecated_at"),
            reason=d.get("reason"),
        )
        for d in dep_list
    }
    return Facet(
        name=name,
        attribute=facet_doc["attribute"],
        description=facet_doc["description"],
        kind=facet_doc["kind"],
        enumeration=enumeration,
        deprecated=deprecated,
        value_type=facet_doc.get("value_type"),
        value_pattern=facet_doc.get("value_pattern"),
        allow_empty=bool(facet_doc.get("allow_empty", False)),
        projected=bool(facet_doc.get("projected", True)),
    )


def _build(document: Dict) -> Codebook:
    deprecated_doc = document.get("deprecated") or {}
    facets = {name: _build_facet(name, facet_doc, deprecated_doc) for name, facet_doc in document["facets"].items()}
    return Codebook(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        model=document["model"],
        adoption_tier_min=int(document.get("adoption_tier_min", 3)),
        facets=facets,
        hybrid=document.get("hybrid"),
    )


def load_codebook(path: Path | None = None) -> Codebook:
    """Load and validate the OrgPath codebook.

    Parameters
    ----------
    path:
        Optional override pointing at an alternate YAML file (typically
        used in tests). When omitted, the canonical codebook shipped
        inside the ``uiao.canon`` package is loaded via
        ``importlib.resources``.
    """
    raw_text = _read_default_codebook() if path is None else Path(path).read_text(encoding="utf-8")
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise CodebookValidationError("Codebook must be a YAML mapping at the top level")
    _validate_schema(document)
    _validate_integrity(document)
    return _build(document)


@lru_cache(maxsize=1)
def default_codebook() -> Codebook:
    """Return the cached canonical codebook (no path override)."""
    return load_codebook()
