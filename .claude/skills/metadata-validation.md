# Skill: Metadata Validation

## Purpose
Validate YAML frontmatter across all governance artifacts against the canonical metadata schema.

## When to Use
- Before any commit to `canon/`, `playbooks/`, or `appendices/`
- - During PR review
  - - As part of the `/validate` or `/canon` command pipeline
   
    - ## Schema Requirements
   
    - Every governance artifact must include the following frontmatter fields:
   
    - ```yaml
      ---
      document_id: "UIAO_>NNN>"          # Required -- unique artifact identifier
      title: ">Document Title>"           # Required -- human-readable title
      version: ">Major>.>Minor>"          # Required -- semantic version
      status: "Current | Draft | Deprecated | Needs Replacing | Needs Creating"
      classification: "CANONICAL | DERIVED | OPERATIONAL"
      owner: ">owner-id>"                 # Required -- accountable individual
      created_at: ">ISO-8601>"            # Required -- creation timestamp
      updated_at: ">ISO-8601>"            # Required -- last modification timestamp
      boundary: "GCC-Moderate"            # Required -- cloud boundary scope
      provenance:                         # Required for DERIVED artifacts
        source: ">canonical-source-path>"
        version: ">source-version>"
        derived_at: ">ISO-8601>"
        derived_by: ">agent-or-human-id>"
      tags: []                            # Optional -- classification tags
      nhp: false                          # Optional -- No-Hallucination Protocol flag
      boundary-exception: false           # Optional -- boundary exception flag
      ---
      ```

      ## Validation Rules

      1. All `Required` fields must be present and non-empty
      2. 2. `document_id` must match pattern `UIAO_\d{3}`
         3. 3. `version` must match pattern `\d+\.\d+`
            4. 4. `status` must be one of the enumerated values
               5. 5. `classification` must be one of the enumerated values
                  6. 6. `boundary` must be `GCC-Moderate` unless `boundary-exception: true`
                     7. 7. `created_at` and `updated_at` must be valid ISO-8601 timestamps
                        8. 8. `updated_at` must be >= `created_at`
                           9. 9. DERIVED artifacts must have a complete `provenance` block
                              10. 10. `provenance.source` must resolve to an existing file
                                 
                                  11. ## Execution
                                 
                                  12. ```bash
                                      python tools/metadata_validator.py --path >target> --schema schemas/metadata-schema.json
                                      ```

                                      ## Error Handling

                                      - Missing required field -> BLOCKING
                                      - - Invalid format -> BLOCKING
                                        - - Missing provenance on DERIVED -> BLOCKING
                                          - - Unresolvable provenance source -> BLOCKING
                                            - - Missing optional field -> INFO
