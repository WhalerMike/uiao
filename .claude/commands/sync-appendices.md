# Command: /appendix
## Description
Manage appendix lifecycle — audit integrity, rebuild index, and sync state.
## Usage
```
/appendix [--mode <audit|rebuild|sync>] [--path <target>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mode` | `audit` | Operation mode: audit (report only), rebuild (regenerate index), sync (compare index vs directory) |
| `--path` | `appendices/` | Target appendix directory |
## Behavior
### Audit Mode (default)
1. Walk appendices directory, parse each appendix frontmatter
2. Verify required fields: appendix_id, title, parent_document, status, owner
3. Verify Copy section presence in every appendix
4. Check parent_document resolves to existing canon
5. Check appendix_id uniqueness
6. Generate integrity report
### Rebuild Mode
1. Perform full audit
2. Generate new INDEX.md from directory contents
3. Sort by appendix_id ascending
4. Write INDEX.md to appendices/INDEX.md
5. Report changes vs previous index
### Sync Mode
1. Load existing INDEX.md
2. Walk directory for actual appendix files
3. Compute diff: orphans (in directory, not in index) and ghosts (in index, not in directory)
4. Report sync status
## Agent
Delegates to `appendix-manager`
## Example
```
/appendix --mode rebuild
```
Output:
```
Appendix Index Rebuild — 2026-04-09T07:00:00
Appendices found: 24
Index entries before: 22
Index entries after: 24
Changes:
+ APP-023 (new appendix added)
+ APP-024 (new appendix added)
Copy Section Audit:
With Copy: 24/24 ✅
INDEX.md written successfully.
```