# Skill: Metadata Validation (Documentation Layer)
## Purpose
Validate YAML frontmatter across all documentation artifacts against the docs metadata schema.
## When to Use
- Before any commit to `articles/`, `guides/`, or `appendices/`
- During PR review
- As part of the `/validate` or `/publish` command pipeline
## Schema Requirements
Every documentation artifact must include the following frontmatter fields:
```yaml
---
document_id: "UIAO_<NNN>" # Required — unique artifact identifier
title: "<Document Title>" # Required — human-readable title
version: "<Major>.<Minor>" # Required — semantic version
status: "Current | Draft | Deprecated | Needs Replacing | Needs Creating"
classification: "DERIVED | OPERATIONAL" # Note: no CANONICAL in docs repo
owner: "<owner-id>" # Required — accountable individual
created_at: "<ISO-8601>" # Required — creation timestamp
updated_at: "<ISO-8601>" # Required — last modification timestamp
boundary: "GCC-Moderate" # Required — cloud boundary scope
provenance: # Required — ALWAYS required in docs repo
source: "uiao-core/canon/<source-path>"
version: "<source-version>"
derived_at: "<ISO-8601>"
derived_by: "<agent-or-human-id>"
article_series: "<series-name>" # Required for articles
article_number: <N> # Required for articles
author_pseudonym: "Michal Doroszewski" # Required for articles
tags: [] # Optional — classification tags
nhp: false # Optional — No-Hallucination Protocol flag
boundary-exception: false # Optional — boundary exception flag
---
```
## Validation Rules
1. All `Required` fields must be present and non-empty
2. `document_id` must match pattern `UIAO_\d{3}`
3. `version` must match pattern `\d+\.\d+`
4. `status` must be one of the enumerated values
5. `classification` must be `DERIVED` or `OPERATIONAL` (never `CANONICAL`)
6. `boundary` must be `GCC-Moderate` unless `boundary-exception: true`
7. `provenance` block is ALWAYS required (this is a derived repository)
8. `provenance.source` must reference a path in `uiao-core`
9. Articles must include `article_series`, `article_number`, and `author_pseudonym`
10. `author_pseudonym` must be `Michal Doroszewski` for the M365 series
## Execution
```bash
python tools/metadata_validator.py --path <target> --schema schemas/docs-metadata-schema.json
```
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
