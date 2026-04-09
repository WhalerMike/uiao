# Rule: Governance Enforcement

## Scope
Always active. Applies to all operations within uiao-core.

## Rules

1. **Canon Supremacy:** The `canon/` directory is the single source of truth. All artifacts outside `canon/` must trace provenance to a canonical document. If provenance cannot be established, flag the artifact as `ORPHAN` and block the commit.

2. 2. **Metadata Schema Compliance:** Every document with YAML frontmatter must validate against the canonical metadata schema defined in `schemas/metadata-schema.json`. Non-compliant documents fail CI.
  
   3. 3. **State Machine Determinism:** All workflow definitions must be acyclic and deterministic. Every state must have exactly one defined transition for each input. Ambiguous or cyclic transitions are CI-blocking errors.
     
      4. 4. **Artifact Classification:** Every file must be classified as one of:
         5.    - `CANONICAL`  Source of truth, lives in `canon/`
               -    - `DERIVED`  Generated from canonical source, includes provenance header
                    -    - `OPERATIONAL`  Playbooks, dashboards, tooling (must reference governing canon)
                         -    - `EPHEMERAL`  Scratch, draft, or temporary (must not appear in `main` branch)
                          
                              - 5. **Version Isolation:** No document may reference a previous version of itself or any artifact from a prior version epoch. Version references must point to current or future states only.
                               
                                6. 6. **GCC-Moderate Boundary:** All references to cloud services must be scoped to GCC-Moderate (M365 SaaS). Any reference to GCC-High, DoD, or Azure services is a CI-blocking error unless explicitly tagged with `boundary-exception: true` and a justification.
                                  
                                   7. 7. **Appendix Integrity:** Every appendix must have a unique ID, be registered in the appendix index (`appendices/INDEX.md`), and include a `Copy` section. Orphan or unindexed appendices are CI-blocking.
                                     
                                      8. 8. **Owner Accountability:** Every canonical artifact must have an `owner` field in its frontmatter. Ownerless artifacts are flagged for immediate assignment.
