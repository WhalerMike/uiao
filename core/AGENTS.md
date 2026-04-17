# AGENTS.md — UIAO-Core Module
> Canonical control surface for IDE agent integration with the UIAO core module.
> This file is the module-level configuration. Any tool-specific subagents,
> skills, rules, and commands live under per-tool integration directories
> (e.g., `.claude/` for Claude Code).
>
> **Naming note:** filename is `AGENTS.md` — the emerging tool-neutral convention. A thin `CLAUDE.md` stub at the same path points here for tools looking specifically for `CLAUDE.md`.
## Repository Identity
- **Name:** uiao-core
- **Purpose:** Core governance framework — canonical artifacts, state machines, enforcement rules, and operational playbooks for the UIAO modernization ecosystem.
- **Canon Authority:** This repository is the single source of truth for UIAO governance canon.
- **Cloud Boundary:** GCC-Moderate (Microsoft 365 SaaS only). No GCC-High, DoD, or Azure services unless explicitly noted.
- **Exception:** Amazon Connect Contact Center operates in Commercial Cloud.
## Operating Principles
1. **No-Hallucination Protocol:** When invoked, use only provided text as source of truth. Mark gaps as `MISSING`, uncertainties as `UNSURE`, and invented content as `NEW (Proposed)`.
2. **Provenance First:** Every artifact must trace to a canonical source. No orphan artifacts.
3. **Deterministic Workflows:** All state machines are acyclic and deterministic. No ambiguous transitions.
4. **Drift Prevention:** Metadata drift is detected, flagged, and remediated via CI enforcement.
5. **Version Isolation:** No references to any previous version in any context prior to the current version.
## Directory Convention
```
uiao-core/
├── CLAUDE.md # This file — root config
├── .claude/ # Claude Code control center
│ ├── rules/ # Governance rules (always-on)
│ ├── agents/ # Subagent persona definitions
│ ├── skills/ # Reusable skill modules
│ └── commands/ # Slash-command definitions
├── .github/workflows/ # CI enforcement pipelines
├── tools/ # Python enforcement scripts
├── schemas/ # JSON schemas (dashboard, metadata)
├── canon/ # Canonical governance documents
├── playbooks/ # Operational playbooks
└── appendices/ # Meta-appendix artifacts
```
## Commit Convention
All commits touching governance artifacts must follow:
```
[UIAO-CORE] <verb>: <artifact-id> — <short description>
```
Verbs: `CREATE`, `UPDATE`, `FIX`, `ENFORCE`, `MIGRATE`, `DEPRECATE`
## CI Gates
Every PR must pass:
- `metadata-validator` — Schema compliance for all YAML/JSON frontmatter
- `drift-scan` — Detect metadata drift between canon and working artifacts
- `appendix-sync` — Verify appendix index integrity
- `dashboard-export` — Validate dashboard schema and export readiness
## Agent Activation
Claude Code loads `.claude/rules/` automatically. Agents are activated via slash commands:
| Command | Agent | Purpose |
|---|---|---|
| `/validate` | `governance-agent` | Run metadata validation suite |
| `/drift` | `drift-detector` | Scan for canon drift |
| `/appendix` | `appendix-manager` | Index and sync appendices |
| `/dashboard` | `dashboard-exporter` | Export governance dashboard |
| `/canon` | `canon-steward` | Full canon integrity check |