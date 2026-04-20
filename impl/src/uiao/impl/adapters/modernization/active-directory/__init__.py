"""
active_directory/__init__.py
----------------------------
UIAO Modernization Adapter: Active Directory

Registers this adapter with the UIAO substrate and exposes the
CLI surface: `uiao ad survey` and `uiao ad assign`.

Adapter registration
--------------------
  adapter_id:    active-directory-survey-v1
  class:         modernization
  mission_class: identity
  canon_ref:     Appendix F (Migration Runbook), Appendix C (Attribute Mapping)
"""

from .survey import ADSurveyReport, DriftFinding, run_discovery
from .orgpath import (
    OrgPathAssignmentReport,
    UserOrgPathAssignment,
    build_ou_mapping,
    resolve_user_assignments,
    write_orgpath_to_ad,
    export_ou_mapping,
    export_assignment_report,
)

__all__ = [
    "ADSurveyReport",
    "DriftFinding",
    "OrgPathAssignmentReport",
    "UserOrgPathAssignment",
    "run_discovery",
    "build_ou_mapping",
    "resolve_user_assignments",
    "write_orgpath_to_ad",
    "export_ou_mapping",
    "export_assignment_report",
]

# Adapter manifest — consumed by modernization-registry.yaml validation
ADAPTER_ID = "active-directory-survey-v1"
ADAPTER_CLASS = "modernization"
MISSION_CLASS = "identity"
