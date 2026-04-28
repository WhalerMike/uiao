# GITHUB IMPORT GUIDE — GAE Package
# AD Computer Object Decomposition (A, B, C, D)
# Repository: WhalerMike/uiao | Branch: main
# ============================================================

## FILE PLACEMENT

diagrams/
  computer-object-decomposition.mermaid     [NEW — A: Decomposition diagram]
  device-disposition-by-type.mermaid        [NEW — A: By-type diagram]

src/uiao/canon/
  adr/
    adr-031-three-plane-device-model.md     [NEW — PR 1, governance gate]
  computer-object-crosswalk.yaml            [NEW — C: Crosswalk, machine-readable]

docs/docs/
  GAE-computer-object-decomposition.md      [NEW — B: Appendix GAE]
  GAD-modernization-impact-model.md         [NEW — D: Appendix GAD]

src/uiao/adapters/modernization/active_directory/
  disposition.py                            [NEW — extends survey.py]

## PR SEQUENCE

# PR 1 — Canon first (governance gate)
# [UIAO-CORE] add: ADR-031 — three-plane device model
# [UIAO-CORE] add: computer-object-crosswalk.yaml
src/uiao/canon/adr/adr-034-three-plane-device-model.md
src/uiao/canon/computer-object-crosswalk.yaml

# PR 2 — Implementation
# [UIAO-IMPL] add: computer disposition classifier
src/uiao/adapters/modernization/active_directory/disposition.py

# Also update survey.py to call classify_all_computers() and
# include disposition in ADSurveyReport output.

# PR 3 — Documentation
# [UIAO-DOCS] add: Appendix GAE and GAD
docs/docs/GAE-computer-object-decomposition.md
docs/docs/GAD-modernization-impact-model.md
diagrams/computer-object-decomposition.mermaid
diagrams/device-disposition-by-type.mermaid

## UPDATES TO EXISTING FILES

# Appendix C (src/uiao/canon/adr — or docs/appendices/C-attribute-mapping.md)
# Add section: Device Attribute Mapping by Plane
# Four new rows:
#   Entra device     | extensionAttribute1  | String | OrgPath value
#   Intune scope     | Inherited from Entra | —      | Scope tag derived from OrgPath
#   Arc ARM resource | OrgPath (ARM tag)    | String | OrgPath value
#   Workload identity| App tag / claim      | String | OrgPath value

# Appendix T (identity risk scoring)
# Add RF-C01 through RF-C08 from GAD.4
# These are computer-object-specific risk factors

# Appendix F (migration runbook)
# Add reference to three-track extension (GAF — next artifact)
# Add computer disposition as Phase 0 prerequisite

## NEXT ARTIFACT: APPENDIX GAF
# Three-Track Computer Migration Runbook
# Covers Track 1 (Intune), Track 2 (Arc), Track 3 (Workload Identity)
# Each track: prerequisites, steps, validation, gate criteria
# To be authored after ADR-031 merges.

## VALIDATION BEFORE MERGE
# Run: uiao substrate walk (confirm zero P1 findings)
# Run: python -m pytest impl/ (disposition classifier unit tests needed)
# Verify: computer-object-crosswalk.yaml validates against schema

## COMMIT MESSAGES
# [UIAO-CORE] add: ADR-031 — three-plane device model and OrgPath plane-aware arch
# [UIAO-CORE] add: computer-object-crosswalk YAML — machine-readable AD function mapping
# [UIAO-IMPL] add: disposition classifier — computer object migration track assignment
# [UIAO-DOCS] add: Appendix GAE — AD computer object decomposition
# [UIAO-DOCS] add: Appendix GAD — modernization impact model
# [UIAO-DOCS] add: DIAG-GAE-001 DIAG-GAE-002 — computer decomposition diagrams
