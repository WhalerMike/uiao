---
title: Session Logs — Convention
doc-type: governance-readme
status: ACTIVE
owner: Michael Stratton
date: 2026-04-14
tags: [session-logs, provenance, audit-trail, claude]
---

# Session Logs

## Purpose

This directory captures **running transcripts of working sessions** between Michael (owner) and AI copilots (Claude, agents). Session logs are the narrative counterpart to ADRs: ADRs record *what was decided*, session logs record *the conversation that led there, the tool calls made, and the files touched along the way*.

They exist so that six months from now, an auditor, a new contributor, or future-Michael can reconstruct the full reasoning trail behind any change — not just the final commit message.

## File Format

Each session produces two files with the same basename:

| File | Authority | Purpose |
|---|---|---|
| `YYYY-MM-DD-<topic>.md` | **Source of truth** | Markdown transcript, append-only, clean `git diff` per turn |
| `YYYY-MM-DD-<topic>.docx` | **Derived** | Regenerated from the `.md` after each append via pandoc; for human reading, sharing, or printing |

The `.docx` is always a mirror of the `.md` — never edit the `.docx` directly. If the `.docx` drifts from the `.md`, regenerate it:

```bash
pandoc YYYY-MM-DD-<topic>.md -o YYYY-MM-DD-<topic>.docx
```

## Naming Convention

```
YYYY-MM-DD-<kebab-case-topic>.md
YYYY-MM-DD-<kebab-case-topic>.docx
```

- Date: UTC date when the session *started*. Long-running topics keep the original start date even if they span multiple calendar days.
- Topic: 3–6 kebab-case words describing the thread of work (e.g., `customer-docs-platform`, `conmon-scubagear-integration`, `adapter-registry-bootstrap`).
- Rotate to a new file when the working thread genuinely changes topic, not when the day changes.

## Structure of Each Log

Every log file has the same shape:

```markdown
---
title: <Session title>
date: <start date>
session-id: <optional — jsonl filename from Claude Code if applicable>
topic: <kebab-case topic>
participants:
  - Michael Stratton (owner)
  - Claude (claude-opus-4-6)
status: IN-PROGRESS | COMPLETE
related-adrs: [ADR-NNN, ...]
related-commits: [<repo>@<sha>, ...]
---

# <Session title>

## Context

<1–3 paragraphs: what prompted this session, what was already in flight>

## Turn 1 — <ISO timestamp> — <actor>

<verbatim or lightly-edited message>

**Actions:**
- <tool called>
- <file created/modified>
- <decision made>

---

## Turn 2 — <ISO timestamp> — <actor>

...
```

## Append Cadence

Claude appends to the active session log after every substantive turn (a turn that involves tool calls, file changes, or a key decision). Conversational back-and-forth without tool use may be batched to keep noise down.

After each append, Claude regenerates the `.docx` mirror with:

```bash
pandoc <file>.md -o <file>.docx
```

Commit cadence is the owner's choice. Suggested pattern:

```powershell
Set-Location 'C:\Users\whale\uiao-docs'
git add docs/session-logs/
git commit -m "[UIAO-DOCS] LOG: append <topic> session journal"
git push
```

## Retention

Session logs are **permanent artifacts**. Do not delete them. If a log contains sensitive information that must be removed, the remediation is to redact the specific content in place and add a dated editorial note, not to delete the file. This preserves audit continuity.

## Relationship to ADRs

| Concern | Belongs in ADR | Belongs in Session Log |
|---|---|---|
| One crisp decision and its rationale | Yes | No (reference the ADR instead) |
| Immutable record of a choice | Yes | No |
| Raw chat transcript | No | Yes |
| Tool-call trace and file-touch history | No | Yes |
| Timeline of how thinking evolved | No | Yes |

If a session produces an important decision, that decision gets its own ADR in `docs/adr/` and the session log links to it in `related-adrs`. The session log is the *working tape*; the ADR is the *signed-off ruling*.

## Provenance

This convention was established 2026-04-14 during the customer-documentation-platform bootstrap, in response to the owner's request to preserve the full chat transcript alongside governance artifacts.

Related: `docs/adr/adr-025-continuous-monitoring-program.md` (first ADR that embedded a full session log inline — superseded by this convention going forward).
