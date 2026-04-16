# `.claude/` — Claude Code Control Surface for uiao-impl

> This directory configures Claude Code for the `uiao-impl` repository.
> Root-level orientation is in [`../CLAUDE.md`](../CLAUDE.md); quick-start
> context is in [`../PROJECT-CONTEXT.md`](../PROJECT-CONTEXT.md).

## Layout

```
.claude/
├── README.md         # This file
├── rules/            # Always-on governance rules (loaded automatically)
├── agents/           # Subagent persona definitions (activated by slash command)
├── skills/           # Reusable skill modules
└── commands/         # Slash-command definitions
```

## Conventions

- **Rules** are always-on. Keep them short and declarative. One concern per file.
- **Agents** are personas invoked by slash commands. They should have a single
  clear purpose, reference the rules they depend on, and define their success
  criteria.
- **Skills** are reusable capability modules. They do not own personas; they
  expose capabilities that agents or direct invocations can use.
- **Commands** are the slash-command surface. Each command maps to an agent
  or a scripted action.

## Activation

Claude Code loads `rules/` automatically on session start. Agents, skills, and
commands are activated on demand — either by slash-command invocation or by
explicit `Skill` tool calls.

## Alignment with sibling repos

This directory mirrors the structure used by `uiao-core/.claude/` and
`uiao-docs/.claude/`. Cross-repo consistency is enforced by convention, not by
CI (yet).

<!-- NEW (Proposed) -->
