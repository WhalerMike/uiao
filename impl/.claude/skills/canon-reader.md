# Skill: canon-reader

> Resolve and read canonical governance artifacts from `uiao-core` through
> the `--canon-path` boundary.

## Purpose

Provide a single, well-documented way for agents and commands to access
canon without reaching into sibling checkouts directly.

## Interface

```python
from uiao.impl.canon import load_document, load_registry

doc = load_document("UIAO_001", canon_path=canon_path)
registry = load_registry("document-registry", canon_path=canon_path)
```

## Rules

1. **Never hard-code paths.** All reads take `canon_path` (a `pathlib.Path`)
   resolved from the CLI's `--canon-path` argument.
2. **Validate on read.** Every document is validated against its schema
   (`tools/schema/canon_schema.json`) before being returned.
3. **Cache per-invocation only.** Do not persist canon between CLI runs.
4. **Surface version.** Callers always see `doc.version`; they can decide
   whether to proceed.

## Typical failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError` | Wrong `--canon-path` | Verify path points to `uiao-core` checkout root |
| `ValidationError` | Canon drift — schema updated, document not | Update doc in `uiao-core` first |
| Stale version returned | Caller cached across invocations | Remove the cache |

## Related

- Rule: [`.claude/rules/canon-consumer.md`](../rules/canon-consumer.md)
- Canon schemas: `uiao-core/tools/schema/canon_schema.json`

<!-- NEW (Proposed) -->
