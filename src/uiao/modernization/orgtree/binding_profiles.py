"""OrgPath binding-profile loader — vendor-neutral facet storage contracts.

Loads the executable binding profiles at
``src/uiao/canon/data/orgpath/binding-profiles/<profile>.yaml`` (the
per-target storage contracts authorized by ADR-098 and specified by
UIAO_193) and exposes a :class:`BindingProfile` object the assess /
write-back adapters and the enforcement projection consume.

Per ADR-098, the codebook (UIAO_151) defines *what* a facet means; a
binding profile defines *where* that facet lives on one target platform —
an attribute name, a tag key/category, a label key, or a custom-attribute
id — plus the endpoint-resolution seam and the deterministic overflow
rule for slot-poor planes. The Microsoft ``onPremisesExtensionAttribute``
slot table fixed by ADR-078 is the ``microsoft-entra`` reference profile.

The loader:

* validates each YAML against
  ``src/uiao/schemas/orgpath/binding-profile.schema.json`` (v1.0.0);
* validates integrity the JSON Schema cannot express:

  - every bound facet exists in the codebook (UIAO_151);
  - ``plane`` is declared on every binding when the profile spans
    multiple planes, and every binding's plane is one the profile declares;
  - each facet binds at most once per plane, and each ``(plane, locator)``
    pair is unique;
  - a ``priority`` overflow ordering only names facets bound on its plane;
  - a ``composite-secondary`` overflow locator does not collide with any
    facet binding's locator;

* exposes per-profile helpers (``bindings_for_plane``, ``locator_for``,
  ``facets_for_plane``) and registry-level lookup
  (:func:`load_binding_profile`, :func:`load_all_binding_profiles`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache, lru_cache
from importlib import resources
from pathlib import Path
from typing import Mapping

import yaml

from uiao.modernization.orgtree.codebook import Codebook, load_codebook

#: The profile ids shipped as executable canon (UIAO_193 first-class targets).
CANONICAL_PROFILE_IDS: tuple[str, ...] = (
    "microsoft-entra",
    "aws",
    "gcp",
    "okta",
    "ldap",
    "vmware",
)


class BindingProfileValidationError(ValueError):
    """Raised when a binding-profile YAML fails schema or integrity validation."""


@dataclass(frozen=True)
class FacetBinding:
    """Where one facet lives on one plane of a target platform."""

    facet: str
    plane: str
    locator: str
    locator_kind: str
    writable: bool
    notes: str | None = None


@dataclass(frozen=True)
class OverflowRule:
    """Deterministic handling for planes that cannot store all bound facets."""

    rule: str
    plane: str | None = None
    ordering: tuple[str, ...] = ()
    composite_locator: str | None = None


@dataclass(frozen=True)
class BindingProfile:
    """A validated per-target OrgPath storage contract (UIAO_193)."""

    profile_id: str
    display_name: str
    status: str
    boundary: str
    planes: tuple[str, ...]
    endpoint_resolution: str
    bindings: tuple[FacetBinding, ...]
    overflow: OverflowRule | None = None
    constraints: Mapping[str, object] = field(default_factory=dict)
    notes: str | None = None

    def bindings_for_plane(self, plane: str) -> tuple[FacetBinding, ...]:
        """All bindings on one plane, in declaration order."""
        return tuple(b for b in self.bindings if b.plane == plane)

    def facets_for_plane(self, plane: str) -> tuple[str, ...]:
        """Facet names bound on one plane, in declaration order."""
        return tuple(b.facet for b in self.bindings_for_plane(plane))

    def locator_for(self, facet: str, plane: str) -> str | None:
        """The native storage key for ``facet`` on ``plane``, if bound."""
        for b in self.bindings:
            if b.facet == facet and b.plane == plane:
                return b.locator
        return None


# ---------------------------------------------------------------------------
# Loading + validation
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, object]:
    schema_text = (
        resources.files("uiao.schemas").joinpath("orgpath/binding-profile.schema.json").read_text(encoding="utf-8")
    )
    loaded = json.loads(schema_text)
    if not isinstance(loaded, dict):
        raise BindingProfileValidationError("binding-profile.schema.json must be a JSON object")
    return loaded


def _validate_against_schema(doc: Mapping[str, object], source: str) -> None:
    import jsonschema

    validator = jsonschema.Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        details = "; ".join(f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors[:5])
        raise BindingProfileValidationError(f"{source}: schema validation failed — {details}")


def _check_integrity(profile: BindingProfile, codebook: Codebook, source: str) -> None:
    """Enforce the UIAO_193 invariants JSON Schema cannot express."""
    known_facets = set(codebook.facets)
    seen_facet_plane: set[tuple[str, str]] = set()
    seen_plane_locator: set[tuple[str, str]] = set()
    for b in profile.bindings:
        if b.facet not in known_facets:
            raise BindingProfileValidationError(
                f"{source}: binding for unknown facet '{b.facet}' — not in codebook (UIAO_151)"
            )
        if b.plane not in profile.planes:
            raise BindingProfileValidationError(
                f"{source}: facet '{b.facet}' bound on plane '{b.plane}' which the profile does not declare"
            )
        if (b.facet, b.plane) in seen_facet_plane:
            raise BindingProfileValidationError(
                f"{source}: facet '{b.facet}' bound more than once on plane '{b.plane}'"
            )
        seen_facet_plane.add((b.facet, b.plane))
        if (b.plane, b.locator) in seen_plane_locator:
            raise BindingProfileValidationError(
                f"{source}: locator '{b.locator}' used by more than one facet on plane '{b.plane}'"
            )
        seen_plane_locator.add((b.plane, b.locator))

    if profile.overflow is not None:
        ov = profile.overflow
        ov_plane = ov.plane or (profile.planes[0] if len(profile.planes) == 1 else None)
        if ov_plane is None:
            raise BindingProfileValidationError(
                f"{source}: overflow rule on a multi-plane profile must declare its plane"
            )
        plane_facets = set(profile.facets_for_plane(ov_plane))
        if ov.rule == "priority":
            unknown = [f for f in ov.ordering if f not in plane_facets]
            if unknown:
                raise BindingProfileValidationError(
                    f"{source}: overflow ordering names facets not bound on plane '{ov_plane}': {unknown}"
                )
        if ov.rule == "composite-secondary" and ov.composite_locator is not None:
            plane_locators = {b.locator for b in profile.bindings_for_plane(ov_plane)}
            if ov.composite_locator in plane_locators:
                raise BindingProfileValidationError(
                    f"{source}: composite_locator '{ov.composite_locator}' collides with a facet binding on plane '{ov_plane}'"
                )


def _profile_from_dict(doc: Mapping[str, object], source: str) -> BindingProfile:
    planes_raw = doc["planes"]
    bindings_raw = doc["facet_bindings"]
    if not isinstance(planes_raw, list) or not isinstance(bindings_raw, list):
        raise BindingProfileValidationError(f"{source}: 'planes' and 'facet_bindings' must be lists")
    planes = tuple(str(p) for p in planes_raw)
    multi_plane = len(planes) > 1
    bindings: list[FacetBinding] = []
    for entry in bindings_raw:
        if not isinstance(entry, Mapping):
            raise BindingProfileValidationError(f"{source}: each facet binding must be a mapping; got {entry!r}")
        plane = entry.get("plane")
        if plane is None:
            if multi_plane:
                raise BindingProfileValidationError(
                    f"{source}: facet '{entry['facet']}' omits 'plane' but the profile declares multiple planes"
                )
            plane = planes[0]
        bindings.append(
            FacetBinding(
                facet=str(entry["facet"]),
                plane=str(plane),
                locator=str(entry["locator"]),
                locator_kind=str(entry["locator_kind"]),
                writable=bool(entry["writable"]),
                notes=entry.get("notes"),
            )
        )
    overflow = None
    ov = doc.get("overflow")
    if isinstance(ov, Mapping):
        overflow = OverflowRule(
            rule=str(ov["rule"]),
            plane=ov.get("plane"),  # type: ignore[arg-type]
            ordering=tuple(ov.get("ordering", ())),  # type: ignore[arg-type]
            composite_locator=ov.get("composite_locator"),  # type: ignore[arg-type]
        )
    return BindingProfile(
        profile_id=str(doc["profile_id"]),
        display_name=str(doc["display_name"]),
        status=str(doc["status"]),
        boundary=str(doc["boundary"]),
        planes=planes,
        endpoint_resolution=str(doc["endpoint_resolution"]),
        bindings=tuple(bindings),
        overflow=overflow,
        constraints=doc.get("constraints", {}),  # type: ignore[arg-type]
        notes=doc.get("notes"),  # type: ignore[arg-type]
    )


def load_binding_profile_from_path(path: Path | str, codebook: Codebook | None = None) -> BindingProfile:
    """Load and validate one binding profile from an explicit filesystem path."""
    source = str(path)
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise BindingProfileValidationError(f"{source}: profile YAML must be a mapping at the top level")
    _validate_against_schema(doc, source)
    profile = _profile_from_dict(doc, source)
    _check_integrity(profile, codebook or load_codebook(), source)
    return profile


@cache
def load_binding_profile(profile_id: str) -> BindingProfile:
    """Load one canonical binding profile from packaged canon by id."""
    if profile_id not in CANONICAL_PROFILE_IDS:
        raise BindingProfileValidationError(
            f"unknown binding profile '{profile_id}' (canonical: {', '.join(CANONICAL_PROFILE_IDS)})"
        )
    text = (
        resources.files("uiao.canon")
        .joinpath(f"data/orgpath/binding-profiles/{profile_id}.yaml")
        .read_text(encoding="utf-8")
    )
    doc = yaml.safe_load(text)
    source = f"uiao.canon:data/orgpath/binding-profiles/{profile_id}.yaml"
    if not isinstance(doc, Mapping):
        raise BindingProfileValidationError(f"{source}: profile YAML must be a mapping at the top level")
    _validate_against_schema(doc, source)
    profile = _profile_from_dict(doc, source)
    if profile.profile_id != profile_id:
        raise BindingProfileValidationError(
            f"{source}: profile_id '{profile.profile_id}' does not match filename '{profile_id}'"
        )
    _check_integrity(profile, load_codebook(), source)
    return profile


def load_all_binding_profiles() -> dict[str, BindingProfile]:
    """Load every canonical binding profile, keyed by profile id."""
    return {pid: load_binding_profile(pid) for pid in CANONICAL_PROFILE_IDS}
