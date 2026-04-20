"""OrgTree canon + codebook loader.

Narrative canon lives in MOD_A..MOD_Z markdown files in this directory; the
executable canon is :mod:`uiao.modernization.orgtree.codebook`, which loads
``canon/data/orgpath/codebook.yaml`` and validates it against
``schemas/orgpath/codebook.schema.json``.
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
from .dynamic_groups import (
    DynamicGroupLibrary,
    DynamicGroupSpec,
    DynamicGroupValidationError,
    load_dynamic_group_library,
)

__all__ = [
    "AdminGroup",
    "AdministrativeUnit",
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
    "DynamicGroupLibrary",
    "DynamicGroupSpec",
    "DynamicGroupValidationError",
    "RoleAssignment",
    "RoleTemplate",
    "SkipDisposition",
    "load_codebook",
    "load_delegation_matrix",
    "load_device_plane_registry",
    "load_dynamic_group_library",
]
