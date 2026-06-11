"""LocPath location-registry loader — executable canon for physical-location addressing.

Loads an executable LocPath location registry (the per-node location
hierarchy authorized by ADR-102 §D6 and specified by UIAO_194) and
exposes a :class:`LocationRegistry` the drift engine, governance rules,
and future HR duty-station / E911 / network adapters consume.

Per ADR-102, LocPath is the OrgPath counterpart for physical place: a
canonical hierarchy ``/Country/Region/Site/Building/Floor/Space`` with
**Site as the minimum governance unit**. The shipped ``reference``
registry at ``src/uiao/canon/data/locpath/location-registry.yaml`` is the
executable form of the UIAO_194 worked example — agency registries are
loaded from their own paths with the same contract.

The loader:

* validates the registry envelope against
  ``src/uiao/schemas/locpath/location-registry.schema.json`` (v1.0.0);
* validates every node against
  ``src/uiao/schemas/locpath/location.schema.json`` (the UIAO_194
  normative node schema) — node-by-node, so errors stay addressable;
* validates integrity the JSON Schema cannot express:

  - a node's ``level`` matches its path depth
    (Country=1 … Space=6 segments);
  - ``locPath`` values are unique case-insensitively and stored in
    canonical casing; ``locPathId`` values are unique;
  - every node deeper than Country has its parent node in the registry;
  - ``locPathId`` parses as a UUID and ``lastUpdated`` as an ISO-8601
    timestamp (JSON Schema ``format`` is annotation-only by default);

* exposes the prefix-matching contract governance rules use
  (UIAO_194 §Path syntax): :meth:`LocationRegistry.node_for`,
  :meth:`LocationRegistry.nodes_under`, :meth:`LocationRegistry.sites`,
  and :meth:`LocationRegistry.ancestors_of` — all case-insensitive.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache, lru_cache
from importlib import resources
from pathlib import Path
from typing import Mapping
from uuid import UUID

import yaml

#: Hierarchy levels in canonical order (ADR-102 §D1 / UIAO_194 §Hierarchy levels).
LEVELS: tuple[str, ...] = ("Country", "Region", "Site", "Building", "Floor", "Space")

#: Path depth (number of segments) each level must have.
LEVEL_DEPTH: Mapping[str, int] = {level: i + 1 for i, level in enumerate(LEVELS)}

#: Packaged path of the canonical reference registry (UIAO_194 worked example).
CANONICAL_REGISTRY_RESOURCE = "data/locpath/location-registry.yaml"


class LocationRegistryValidationError(ValueError):
    """Raised when a location-registry YAML fails schema or integrity validation."""


@dataclass(frozen=True)
class LocationNode:
    """One validated LocPath location node (UIAO_194 §Node attribute catalog)."""

    loc_path_id: str
    loc_path: str
    display_name: str
    level: str
    status: str
    last_updated: str
    source_system: str
    owner: str | None = None
    source_record_id: str | None = None
    e911: Mapping[str, object] = field(default_factory=dict)
    network: Mapping[str, object] = field(default_factory=dict)
    boundaries: Mapping[str, object] = field(default_factory=dict)

    @property
    def depth(self) -> int:
        """Number of path segments (Country=1 … Space=6)."""
        return self.loc_path.count("/")

    @property
    def parent_path(self) -> str | None:
        """The containing node's path, or ``None`` for Country nodes."""
        if self.depth <= 1:
            return None
        return self.loc_path.rsplit("/", 1)[0]


@dataclass(frozen=True)
class LocationRegistry:
    """A validated LocPath location registry (envelope + nodes)."""

    registry_id: str
    schema_version: str
    status: str
    display_name: str
    updated: str
    nodes: tuple[LocationNode, ...]
    description: str | None = None

    def node_for(self, loc_path: str) -> LocationNode | None:
        """The node at exactly ``loc_path`` (case-insensitive), if registered."""
        needle = loc_path.lower()
        for node in self.nodes:
            if node.loc_path.lower() == needle:
                return node
        return None

    def nodes_under(self, prefix: str) -> tuple[LocationNode, ...]:
        """The node at ``prefix`` plus every descendant, in declaration order.

        This is the prefix-matching contract governance rules use:
        ``/USA/MD/ANNAPOLIS-HQ`` covers the Site and everything under it.
        """
        needle = prefix.rstrip("/").lower()
        return tuple(
            node
            for node in self.nodes
            if node.loc_path.lower() == needle or node.loc_path.lower().startswith(needle + "/")
        )

    def sites(self) -> tuple[LocationNode, ...]:
        """All Site-level nodes — the minimum governance unit (ADR-102 §D1)."""
        return tuple(node for node in self.nodes if node.level == "Site")

    def ancestors_of(self, loc_path: str) -> tuple[LocationNode, ...]:
        """Registered ancestors of ``loc_path``, outermost (Country) first."""
        segments = loc_path.strip("/").split("/")
        ancestors: list[LocationNode] = []
        for end in range(1, len(segments)):
            ancestor = self.node_for("/" + "/".join(segments[:end]))
            if ancestor is not None:
                ancestors.append(ancestor)
        return tuple(ancestors)


# ---------------------------------------------------------------------------
# Loading + validation
# ---------------------------------------------------------------------------


@lru_cache(maxsize=2)
def _load_schema(name: str) -> dict[str, object]:
    schema_text = resources.files("uiao.schemas").joinpath(f"locpath/{name}").read_text(encoding="utf-8")
    loaded = json.loads(schema_text)
    if not isinstance(loaded, dict):
        raise LocationRegistryValidationError(f"{name} must be a JSON object")
    return loaded


def _validate_against_schema(doc: Mapping[str, object], schema_name: str, source: str) -> None:
    import jsonschema

    validator = jsonschema.Draft202012Validator(_load_schema(schema_name))
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        details = "; ".join(f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors[:5])
        raise LocationRegistryValidationError(f"{source}: schema validation failed — {details}")


def _node_from_dict(doc: Mapping[str, object], source: str) -> LocationNode:
    return LocationNode(
        loc_path_id=str(doc["locPathId"]),
        loc_path=str(doc["locPath"]),
        display_name=str(doc["displayName"]),
        level=str(doc["level"]),
        status=str(doc["status"]),
        last_updated=str(doc["lastUpdated"]),
        source_system=str(doc["sourceSystem"]),
        owner=doc.get("owner"),  # type: ignore[arg-type]
        source_record_id=doc.get("sourceRecordId"),  # type: ignore[arg-type]
        e911=doc.get("e911", {}),  # type: ignore[arg-type]
        network=doc.get("network", {}),  # type: ignore[arg-type]
        boundaries=doc.get("boundaries", {}),  # type: ignore[arg-type]
    )


def _check_integrity(registry: LocationRegistry, source: str) -> None:
    """Enforce the UIAO_194 invariants JSON Schema cannot express."""
    seen_paths: dict[str, str] = {}
    seen_ids: set[str] = set()
    for node in registry.nodes:
        expected_depth = LEVEL_DEPTH.get(node.level)
        if expected_depth is None:
            raise LocationRegistryValidationError(f"{source}: node '{node.loc_path}' has unknown level '{node.level}'")
        if node.depth != expected_depth:
            raise LocationRegistryValidationError(
                f"{source}: node '{node.loc_path}' declares level '{node.level}' "
                f"(depth {expected_depth}) but has {node.depth} segment(s)"
            )
        key = node.loc_path.lower()
        if key in seen_paths:
            raise LocationRegistryValidationError(
                f"{source}: locPath '{node.loc_path}' collides with '{seen_paths[key]}' "
                "(comparison is case-insensitive per UIAO_194 §Path syntax)"
            )
        seen_paths[key] = node.loc_path
        if node.loc_path_id in seen_ids:
            raise LocationRegistryValidationError(f"{source}: duplicate locPathId '{node.loc_path_id}'")
        seen_ids.add(node.loc_path_id)
        try:
            UUID(node.loc_path_id)
        except ValueError as exc:
            raise LocationRegistryValidationError(
                f"{source}: node '{node.loc_path}' locPathId is not a UUID: {exc}"
            ) from exc
        try:
            datetime.fromisoformat(node.last_updated.replace("Z", "+00:00"))
        except ValueError as exc:
            raise LocationRegistryValidationError(
                f"{source}: node '{node.loc_path}' lastUpdated is not ISO-8601: {exc}"
            ) from exc

    for node in registry.nodes:
        parent = node.parent_path
        if parent is not None and parent.lower() not in seen_paths:
            raise LocationRegistryValidationError(
                f"{source}: node '{node.loc_path}' has no registered parent '{parent}'"
            )


def _registry_from_doc(doc: Mapping[str, object], source: str) -> LocationRegistry:
    _validate_against_schema(doc, "location-registry.schema.json", source)
    nodes_raw = doc["nodes"]
    if not isinstance(nodes_raw, list):
        raise LocationRegistryValidationError(f"{source}: 'nodes' must be a list")
    nodes: list[LocationNode] = []
    for i, entry in enumerate(nodes_raw):
        if not isinstance(entry, Mapping):
            raise LocationRegistryValidationError(f"{source}: nodes[{i}] must be a mapping; got {entry!r}")
        _validate_against_schema(entry, "location.schema.json", f"{source}: nodes[{i}]")
        nodes.append(_node_from_dict(entry, source))
    registry = LocationRegistry(
        registry_id=str(doc["registry_id"]),
        schema_version=str(doc["schema_version"]),
        status=str(doc["status"]),
        display_name=str(doc["display_name"]),
        updated=str(doc["updated"]),
        nodes=tuple(nodes),
        description=doc.get("description"),  # type: ignore[arg-type]
    )
    _check_integrity(registry, source)
    return registry


def load_location_registry_from_path(path: Path | str) -> LocationRegistry:
    """Load and validate a location registry from an explicit filesystem path."""
    source = str(path)
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise LocationRegistryValidationError(f"{source}: registry YAML must be a mapping at the top level")
    return _registry_from_doc(doc, source)


@cache
def load_location_registry() -> LocationRegistry:
    """Load the canonical reference registry from packaged canon."""
    source = f"uiao.canon:{CANONICAL_REGISTRY_RESOURCE}"
    text = resources.files("uiao.canon").joinpath(CANONICAL_REGISTRY_RESOURCE).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    if not isinstance(doc, Mapping):
        raise LocationRegistryValidationError(f"{source}: registry YAML must be a mapping at the top level")
    return _registry_from_doc(doc, source)
