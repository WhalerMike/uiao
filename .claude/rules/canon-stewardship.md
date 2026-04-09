# Rule: Canon Stewardship

## Scope
Always active. Governs the lifecycle of canonical artifacts.

## Stewardship Principles

1. **Immutable History:** Once a canonical artifact is published to `main`, its version history is immutable. Corrections create new versions, not edits to history.

2. **Provenance Chain:** Every derived artifact must include a `provenance` block in its frontmatter:
   ```yaml
   provenance:
     source: canon/<document-id>.md
     version: <version>
     derived_at: <ISO-8601 timestamp>
     derived_by: <agent-or-human-id>
   ```

3. **Deprecation Protocol:** Artifacts are never deleted. Deprecated artifacts receive:
   - `status: DEPRECATED` in frontmatter
   - `superseded_by: <new-artifact-id>` pointer
   - Move to `canon/deprecated/` directory

4. **Review Gate:** Changes to canonical artifacts require:
   - All CI checks passing
   - Provenance validation
   - Owner sign-off (documented in PR)

5. **Artifact Naming:** Canonical documents follow the pattern:
   ```
   UIAO_<NNN>_<Short_Title>_v<Major>.<Minor>.md
   ```
   Where `<NNN>` is a zero-padded three-digit sequence number.

6. **Cross-Repository Sync:** When a canonical artifact in `uiao-core` is updated, all derived artifacts in `uiao-docs` must be flagged for review within the same PR cycle or the next scheduled sync.
