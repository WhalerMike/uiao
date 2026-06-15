"""LocPath — executable canon for physical-location addressing (ADR-102 / UIAO_194)."""

from uiao.modernization.locpath.drift import (
    DRIFT_LOCATION_ASSIGNMENT,
    DRIFT_LOCATION_BOUNDARY,
    DRIFT_LOCATION_POLICY,
    ObservedSiteState,
    detect_location_policy_drift,
)
from uiao.modernization.locpath.e911_compliance import (
    DRIFT_E911_COMPLETENESS,
    detect_e911_completeness_gaps,
)
from uiao.modernization.locpath.entra_exposure import (
    LocPathAdminUnitSpec,
    LocPathExposureError,
    LocPathGroupSpec,
    plan_locpath_admin_units,
    plan_locpath_site_groups,
)
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
from uiao.modernization.locpath.mover import (
    LocationMoverPlan,
    MoverEvent,
    plan_location_moves,
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
    "DRIFT_E911_COMPLETENESS",
    "DRIFT_LOCATION_ASSIGNMENT",
    "DRIFT_LOCATION_BOUNDARY",
    "DRIFT_LOCATION_POLICY",
    "DutyStationMap",
    "DutyStationMapping",
    "DutyStationMapValidationError",
    "LEVEL_DEPTH",
    "LEVELS",
    "LocPathAdminUnitSpec",
    "LocPathAssignment",
    "LocPathAssignmentPlan",
    "LocPathExposureError",
    "LocPathGroupSpec",
    "LocationMoverPlan",
    "LocationNode",
    "LocationRegistry",
    "LocationRegistryValidationError",
    "MoverEvent",
    "ObservedSiteState",
    "assign_locpaths",
    "detect_e911_completeness_gaps",
    "detect_location_policy_drift",
    "load_duty_station_map",
    "load_duty_station_map_from_path",
    "load_location_registry",
    "load_location_registry_from_path",
    "plan_location_moves",
    "plan_locpath_admin_units",
    "plan_locpath_site_groups",
]
