# Command: /appendix
## Description
Manage documentation appendix lifecycle — audit integrity, rebuild index, sync state, and cross-repo alignment.
## Usage
```
/appendix [--mode <audit|rebuild|sync|cross-repo>] [--path <target>] [--core-path <path>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mode` | `audit` | Operation mode |
| `--path` | `appendices/` | Target appendix directory |
| `--core-path` | `../uiao-core/appendices/` | Path to uiao-core appendices for cross-repo mode |
## Modes
### audit (default)
Report-only integrity check: frontmatter, Copy sections, parent resolution, ID uniqueness.
### rebuild
Full audit + regenerate INDEX.md from directory contents, sorted by appendix_id ascending.
### sync
Compare existing INDEX.md against actual directory contents, report orphans and ghosts.
### cross-repo
Compare documentation appendices against uiao-core appendices for alignment.
## Agent
Delegates to `docs-appendix-manager`
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
