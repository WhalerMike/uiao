"""LocPath — executable canon for physical-location addressing (ADR-102 / UIAO_194)."""

from uiao.modernization.locpath.hr_assign import (
    CANONICAL_MAP_RESOURCE,
    DutyStationMap,
    DutyStationMapping,
    DutyStationMapValidationError,
    LocPathAssignment,
    LocPathAssignmentPlan,
    assign_locpaths,
    load_duty_station_map,
    load_duty_station_map_from_path,
)
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
    "CANONICAL_MAP_RESOURCE",
    "CANONICAL_REGISTRY_RESOURCE",
    "DutyStationMap",
    "DutyStationMapping",
    "DutyStationMapValidationError",
    "LEVEL_DEPTH",
    "LEVELS",
    "LocPathAssignment",
    "LocPathAssignmentPlan",
    "LocationNode",
    "LocationRegistry",
    "LocationRegistryValidationError",
    "assign_locpaths",
    "load_duty_station_map",
    "load_duty_station_map_from_path",
    "load_location_registry",
    "load_location_registry_from_path",
]
