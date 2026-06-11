"""LocPath — executable canon for physical-location addressing (ADR-102 / UIAO_194)."""

from uiao.modernization.locpath.registry import (
    CANONICAL_REGISTRY_RESOURCE,
    LEVEL_DEPTH,
    LEVELS,
    LocationNode,
    LocationRegistry,
    LocationRegistryValidationError,
    load_location_registry,
    load_location_registry_from_path,
)

__all__ = [
    "CANONICAL_REGISTRY_RESOURCE",
    "LEVEL_DEPTH",
    "LEVELS",
    "LocationNode",
    "LocationRegistry",
    "LocationRegistryValidationError",
    "load_location_registry",
    "load_location_registry_from_path",
]
