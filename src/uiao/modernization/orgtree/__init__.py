"""OrgTree canon + codebook loader.

Narrative canon lives in ``src/uiao/canon/UIAO_150_*.md`` through
``UIAO_176_*.md`` (registered in
``src/uiao/canon/document-registry.yaml``). The executable canon is the
six modules in this package — :mod:`~uiao.modernization.orgtree.codebook`
loads ``canon/data/orgpath/codebook.yaml`` and validates it against
``schemas/orgpath/codebook.schema.json``; the other five modules follow
the same shape for their respective YAML+schema pairs. Both surfaces
are exercised end-to-end by ``uiao orgtree validate ...``.
"""

from .admin_units import (
    AdminGroup,
    AdministrativeUnit,
    DelegationMatrix,
    DelegationMatrixValidationError,
    RoleAssignment,
    RoleTemplate,
    load_delegation_matrix,
)
from .codebook import (
    Codebook,
    CodebookEntry,
    CodebookValidationError,
    DeprecatedEntry,
    load_codebook,
)
from .device_planes import (
    ArmTagSpec,
    DevicePlane,
    DevicePlaneRegistry,
    DevicePlaneValidationError,
    SkipDisposition,
    load_device_plane_registry,
)
from .drift_engine_config import (
    DriftEngineConfig,
    DriftEngineConfigValidationError,
    DriftEngineDefaults,
    OpEntry,
    PhaseConfig,
    SeverityPolicy,
    load_drift_engine_config,
)
from .dynamic_groups import (
    DynamicGroupLibrary,
    DynamicGroupSpec,
    DynamicGroupValidationError,
    load_dynamic_group_library,
)
from .policy_targets import (
    ArcPolicyAssignment,
    IntuneAssignment,
    OrgPathSelector,
    PolicyDefinitionRef,
    PolicyTargetingCanon,
    PolicyTargetingValidationError,
    ProfileRef,
    load_policy_targeting_canon,
)

__all__ = [
    "AdminGroup",
    "AdministrativeUnit",
    "ArcPolicyAssignment",
    "ArmTagSpec",
    "Codebook",
    "CodebookEntry",
    "CodebookValidationError",
    "DelegationMatrix",
    "DelegationMatrixValidationError",
    "DeprecatedEntry",
    "DevicePlane",
    "DevicePlaneRegistry",
    "DevicePlaneValidationError",
    "DriftEngineConfig",
    "DriftEngineConfigValidationError",
    "DriftEngineDefaults",
    "DynamicGroupLibrary",
    "DynamicGroupSpec",
    "DynamicGroupValidationError",
    "IntuneAssignment",
    "OpEntry",
    "OrgPathSelector",
    "PhaseConfig",
    "PolicyDefinitionRef",
    "PolicyTargetingCanon",
    "PolicyTargetingValidationError",
    "ProfileRef",
    "RoleAssignment",
    "RoleTemplate",
    "SeverityPolicy",
    "SkipDisposition",
    "load_codebook",
    "load_delegation_matrix",
    "load_device_plane_registry",
    "load_drift_engine_config",
    "load_dynamic_group_library",
    "load_policy_targeting_canon",
]
