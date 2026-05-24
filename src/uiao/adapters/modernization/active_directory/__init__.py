"""
active_directory/__init__.py
----------------------------
UIAO Modernization Adapter: Active Directory

Registers this adapter with the UIAO substrate and exposes the
CLI surface: `uiao ad survey` and `uiao ad assign`.

Per ADR-078, the Model A composite-string orgpath helper module
(``orgpath.py`` — OrgPathAssignmentReport / build_ou_mapping /
resolve_user_assignments / write_orgpath_to_ad / etc.) was retired
in the same PR. The Model C facet-aware OrgPath assignment workflow
will return with the Phase 5 consumer rebuild.

Adapter registration
--------------------
  adapter_id:    active-directory-survey-v1
  class:         modernization
  mission_class: identity
  canon_ref:     Appendix F (Migration Runbook), Appendix C (Attribute Mapping)
"""

from .survey import ADSurveyReport, DriftFinding, run_discovery

__all__ = [
    "ADSurveyReport",
    "DriftFinding",
    "run_discovery",
]

# Adapter manifest — consumed by modernization-registry.yaml validation
ADAPTER_ID = "active-directory-survey-v1"
ADAPTER_CLASS = "modernization"
MISSION_CLASS = "identity"
