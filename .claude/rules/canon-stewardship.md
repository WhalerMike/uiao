# Rule: Canon Stewardship (Documentation Layer)
## Scope
Always active. Governs the lifecycle of derived documentation artifacts.
## Stewardship Principles
1. **Derived Authority:** This repository does not define canon. All canonical authority resides in `uiao-core`. Documentation here must trace provenance to `uiao-core` artifacts.
2. **Provenance Chain:** Every document must include a `provenance` block in its frontmatter:
```yaml
provenance:
source: uiao-core/canon/<document-id>.md
version: <version>
derived_at: <ISO-8601 timestamp>
derived_by: <agent-or-human-id>
```
3. **Deprecation Protocol:** Documents are never deleted. Deprecated documents receive:
- `status: DEPRECATED` in frontmatter
- `superseded_by: <new-document-id>` pointer
- Move to appropriate `deprecated/` subdirectory
4. **Article Publication Gate:** Articles require:
- All CI checks passing
- Provenance validation against `uiao-core`
- Formatting validation against Article 1 template
- Owner sign-off documented in PR
5. **Cross-Repository Awareness:** When `uiao-core` canon changes:
- All derived documents referencing that canon must be flagged for review
- Drift detection runs automatically on next CI pass
- Stale provenance references become WARNING-level findings
6. **Copy Section Preservation:** Every appendix must retain its Copy section through all edits, migrations, and version updates. Removal of a Copy section is a BLOCKING violation.
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
