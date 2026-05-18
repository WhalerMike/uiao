"""
src/uiao/identity/
------------------
Canonical identity, group, RBAC, resource, and tag primitives per
UIAO_180.

These are the 15 functions the deterministic provisioner (UIAO_178)
calls to mutate Entra and Azure state. Each is idempotent and returns
a structured result with `outcome`, `delta`, and any `drift_records`
observed while reconciling.
"""

from uiao.identity.canonical_functions import (
    GroupMembershipResult,
    GroupResult,
    GroupSpec,
    IdentityResult,
    ManagedIdentitySpec,
    RbacAssignmentResult,
    ResourceGroupSpec,
    ResourceIdentityResult,
    ResourceResult,
    RoleAssignmentResult,
    TagReadResult,
    TagWriteResult,
    UserSpec,
    add_to_group,
    apply_tags,
    assign_rbac,
    assign_role,
    correct_tag_drift,
    create_group,
    create_managed_identity,
    create_resource_group,
    create_user,
    delete_user,
    detect_tag_drift,
    disable_user,
    read_tags,
    remove_from_group,
    remove_role,
)

__all__ = [
    "GroupMembershipResult",
    "GroupResult",
    "GroupSpec",
    "IdentityResult",
    "ManagedIdentitySpec",
    "RbacAssignmentResult",
    "ResourceGroupSpec",
    "ResourceIdentityResult",
    "ResourceResult",
    "RoleAssignmentResult",
    "TagReadResult",
    "TagWriteResult",
    "UserSpec",
    "add_to_group",
    "apply_tags",
    "assign_rbac",
    "assign_role",
    "correct_tag_drift",
    "create_group",
    "create_managed_identity",
    "create_resource_group",
    "create_user",
    "delete_user",
    "detect_tag_drift",
    "disable_user",
    "read_tags",
    "remove_from_group",
    "remove_role",
]
