# CLAUDE.md — UIAO-Docs Repository
> Canonical control surface for Claude Code integration with the UIAO-Docs documentation repository.
> This file is the root-level configuration. All subagents, skills, rules, and commands
> are defined under `.claude/`.
## Repository Identity
- **Name:** uiao-docs
- **Purpose:** Documentation layer — derived articles, guides, playbooks, and published materials for the UIAO modernization ecosystem. All content traces provenance to canonical artifacts in `uiao-core`.
- **Canon Authority:** This repository is a DERIVED consumer of `uiao-core` canon. It does NOT define canonical governance artifacts.
- **Cloud Boundary:** GCC-Moderate (Microsoft 365 SaaS only). No GCC-High, DoD, or Azure services unless explicitly noted.
- **Exception:** Amazon Connect Contact Center operates in Commercial Cloud.
## Operating Principles
1. **Provenance Required:** Every document must trace to a canonical source in `uiao-core`. Orphan documents are CI-blocking.
2. **No-Hallucination Protocol:** Available on demand. When invoked, only user-provided text is source of truth.
3. **Version Isolation:** No references to any previous version in any context prior to the current version.
4. **Article Series Standards:** Articles follow the canonical structure: story, comic, technical section, disclaimer, author bio. Authored under pseudonym Michal Doroszewski.
5. **Copy Section Mandate:** Every appendix retains its Copy section. No exceptions.
6. **Drift Prevention:** Cross-repo drift between `uiao-docs` and `uiao-core` is detected and flagged via CI.
## Directory Convention
```
uiao-docs/
├── CLAUDE.md # This file — root config
├── .claude/ # Claude Code control center
│ ├── rules/ # Governance rules (always-on)
│ ├── agents/ # Subagent persona definitions
│ ├── skills/ # Reusable skill modules
│ └── commands/ # Slash-command definitions
├── .github/workflows/ # CI enforcement pipelines
├── tools/ # Python enforcement scripts
├── schemas/ # JSON schemas (dashboard, metadata)
├── articles/ # Published article series
├── guides/ # Implementation and operations guides
├── appendices/ # Documentation appendices (with Copy sections)
└── dashboard/exports/ # Dashboard metric exports
```
## Commit Convention
All commits touching documentation artifacts must follow:
```
[UIAO-DOCS] <verb>: <artifact-id> — <short description>
```
Verbs: `CREATE`, `UPDATE`, `FIX`, `PUBLISH`, `MIGRATE`, `DEPRECATE`
## CI Gates
Every PR must pass:
- `metadata-validator` — Schema compliance for all YAML/JSON frontmatter
- `drift-scan` — Detect cross-repo drift against `uiao-core` canon
- `appendix-sync` — Verify appendix index integrity and Copy sections
- `dashboard-export` — Validate dashboard schema and export readiness
## Agent Activation
| Command | Agent | Purpose |
|---|---|---|
| `/validate` | `docs-governance-agent` | Run metadata validation suite |
| `/drift` | `docs-drift-detector` | Scan for cross-repo canon drift |
| `/appendix` | `docs-appendix-manager` | Index and sync documentation appendices |
| `/dashboard` | `docs-dashboard-exporter` | Export documentation health dashboard |
| `/publish` | `docs-publisher` | Validate and prepare articles for publication |
## Cross-Repository Sync
This repository maintains a sync relationship with `uiao-core`:
- Canon changes in `uiao-core` trigger drift detection here
- Provenance references must point to current `uiao-core` artifacts
- Scheduled weekly sync checks verify alignment
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
