# FORMAT-CANON.md

**Authority Level**: This file OVERRIDES agent training defaults on all format decisions.
**Read Order**: Load this file AFTER PROJECT-CONTEXT.md and BEFORE generating any output.
**Last Updated**: 2026-03-26
**Owner**: whalermike

---

## Format Authority Chain (Disputes Resolve Top-Down)

1. `schemas/` JSON Schema files — ultimate arbiter for OSCAL field structure and types
2. This file (`FORMAT-CANON.md`) — governs all document, YAML, and Markdown format
3. `AGENTS.md` — governs code style and file placement
4. Agent training preference — **has zero weight**; never substitute defaults

---

## YAML Canon Rules (`data/atlas-appendices.yml` and all `.yaml` files)

- **Indentation**: 2 spaces. Never tabs.
- **Key naming**: `snake_case` only. Never `kebabCase`, `camelCase`, or `PascalCase` for YAML keys.
- **String quoting**: Double-quoted strings for all values containing special characters, UUIDs, URLs, or template variables. Plain scalars for simple alphanumeric values.
- **Lists**: Block sequence style (`- item`) at all levels. Never flow style (`[a, b, c]`) except for single-line coordinate pairs or enums explicitly marked `# flow-ok`.
- **Booleans**: `true` / `false` (lowercase). Never `yes`, `no`, `True`, `False`.
- **Nulls**: `null`. Never `~` or empty value.
- **Trailing newline**: Every `.yaml` file MUST end with a single newline character.
- **Blank lines**: One blank line between top-level keys. No trailing blank lines within blocks.
- **Comments**: Use `#` with a single space. Inline comments align to column 40 where practical.
- **DO NOT reformat** any YAML file you were not explicitly tasked to modify.

---

## OSCAL Artifact Rules (SSP, Component Definition, POA&M)

- **Schema version**: OSCAL 1.3.0. All artifacts must declare `oscal-version: 1.3.0`.
- **UUIDs**: Always freshly generated UUIDv4. Never reuse UUIDs across documents.
- **`prop:id` requirement**: Every `prop` element in back-matter and relevant-evidence links MUST include a `uuid` field with a valid UUIDv4. No exceptions.
- **POA&M ID format**: `POAM-UIAO-<8-char-hex>` (e.g., `POAM-UIAO-a3f1c920`).
- **POA&M status enum**: Only `Open`, `In-Progress`, `Closed`, `Risk-Accepted`, `False-Positive`, `Operational-Requirement`, `Vendor-Dependency`, `Not-Applicable`.
- **Back-matter resources**: Must be populated before any PR is marked review-ready.
- **Validation gate**: Run `make validate-oscal` before every PR. Never skip.
- **Evidence `prop:id` prefix**: All evidence props use prefix per `data/atlas-appendices.yml`. Do not invent new prefixes without updating canon.

---

## JSON Schema Rules (`schemas/` and all `.json` artifacts)

- **Indentation**: 2 spaces. Never tabs.
- **Key naming**: `camelCase` for all JSON Schema keywords and property names, consistent with OSCAL 1.3.0 conventions. Never `snake_case` in `.json` files (this is the one place snake_case does NOT apply — YAML canon uses snake_case, JSON schemas use camelCase; do not cross-contaminate).
- **String quoting**: Always double quotes. JSON does not permit single quotes.
- **Trailing commas**: Never. Trailing commas are invalid JSON and will break trestle validation.
- **Trailing newline**: Every `.json` file MUST end with a single newline character.
- **`$schema` declaration**: Every schema file in `schemas/` MUST declare `"$schema": "https://json-schema.org/draft/2020-12/schema"` as the first key.
- **`$id` declaration**: Every schema file MUST include a `"$id"` using the canonical repo URL pattern: `"https://github.com/WhalerMike/uiao-core/schemas/<filename>.json"`.
- **Required fields**: Always declare a `"required": [...]` array at each object level where mandatory fields exist. Never rely on `"default"` values to satisfy required semantics.
- **`additionalProperties`**: Set to `false` on all leaf-level objects to prevent silent field injection by agents. Use `true` only where explicitly documented with a comment in the accompanying `.yaml` definition.
- **`description` field**: Required on every top-level property and every `$defs` entry. One sentence, ending with a period. Agents must not omit descriptions to save tokens.
- **`enum` arrays**: List values in alphabetical order unless a canonical order is defined in `data/atlas-appendices.yml` (e.g., POA&M status enum follows FedRAMP document order, not alphabetical).
- **`$defs` placement**: All reusable type definitions go in a top-level `"$defs"` block. Never inline a complex type that is used more than once.
- **OSCAL schema cross-reference**: When a schema property maps to an OSCAL field, add `"x-oscal-ref": "<oscal-field-path>"` as an extension annotation so agents can trace schema fields back to the OSCAL 1.3.0 specification without guessing.
- **Validation gate**: Schema changes must pass `make validate-oscal` AND `python -m jsonschema --instance <artifact> <schema>` before PR submission.
- **DO NOT reformat** any `.json` file you were not explicitly tasked to modify. Even whitespace-only changes to schema files count as schema changes and require a full re-validation pass.

### JSON vs YAML Key Naming — The One Rule to Memorize

| File type | Key convention | Example |
|---|---|---|
| `data/*.yaml`, `canon/*.yaml` | `snake_case` | `control_id`, `prop_id` |
| `schemas/*.json`, OSCAL `.json` | `camelCase` | `controlId`, `propId` |
| Python variables | `snake_case` | PEP 8 |
| Mermaid node IDs | `UPPER_SNAKE_CASE` | `AUTH_BOUNDARY` |

This table is the single resolution point when an agent is unsure which convention applies.

---

## Markdown Document Rules (SSP narratives, READMEs, docs/)

- **Heading style**: ATX only (`##`, `###`). Never Setext (`===`, `---` underlines).
- **Heading levels**: H1 (`#`) reserved for document title only. Body sections start at H2 (`##`).
- **Heading text**: Title case for H1 and H2. Sentence case for H3 and below.
- **Line length**: Soft wrap at 100 characters for prose. Code blocks: no wrap limit.
- **Lists**: Use `-` bullets (not `*` or `+`). Ordered lists use `1.` `2.` `3.` (no reuse of `1.`).
- **Bold/Italic**: `**bold**` for key terms on first use or warnings. `*italic*` for document titles and light emphasis. Never nest bold inside italic.
- **Tables**: GFM pipe tables with header separator row. Left-align text columns, right-align numeric columns. No trailing pipes unless visually balanced.
- **Code blocks**: Fenced with triple backtick + explicit language tag (e.g., ` ```yaml `, ` ```python `). Never use indented code blocks.
- **Blank lines**: One blank line before and after every heading, list, table, and code block.
- **Trailing whitespace**: Never. Configure editor/pre-commit to strip.
- **Trailing newline**: Every `.md` file MUST end with a single newline.
- **DO NOT reformat** Markdown files you were not explicitly tasked to modify. Reformatting = noisy diffs = blocked PRs.

---

## Mermaid Diagram Rules (canon/diagrams.yaml → visuals/*.mermaid)

- **Source of truth**: `canon/diagrams.yaml`. Never hand-edit `.mermaid` output files.
- **Diagram type**: Use `flowchart LR` for pipelines, `flowchart TD` for hierarchies, `sequenceDiagram` for protocol flows. Do not use deprecated `graph` syntax.
- **Node IDs**: `UPPER_SNAKE_CASE`. Labels use normal sentence case in quotes.
- **Edge labels**: Short (≤4 words). No punctuation in edge labels.
- **Subgraphs**: Use for logical grouping (e.g., per security boundary). Title in quotes.
- **Six canonical diagrams**: `architecture_overview`, `authorization_boundary`, `data_flow`, `uiao_planes`, `generation_pipeline`, `zero_trust_journey`. Do not add new canonical diagrams without updating `PROJECT-CONTEXT.md` and this file.

---

## Python Code Format Rules (supplements AGENTS.md)

- **Formatter**: `ruff format` (Black-compatible). Line length: 100.
- **Linter**: `ruff check` with all rules in `pyproject.toml`. Zero warnings allowed in CI.
- **Import order**: stdlib → third-party → local. One blank line between groups.
- **Type hints**: Required on all public functions and class methods. Use `from __future__ import annotations`.
- **Docstrings**: Google style. Required on all public modules, classes, and functions.
- **f-strings**: Preferred over `.format()` and `%` formatting.
- **No bare `except:`**: Always catch specific exception types.

---

## File-Level Format Rules (All File Types)

- **Encoding**: UTF-8, no BOM.
- **Line endings**: LF (`\n`). Never CRLF. Enforced by `.gitattributes`.
- **Trailing newline**: Every text file ends with exactly one `\n`.
- **No binary files in `docs/` or `canon/`**: Only `.md`, `.yaml`, `.json`, `.j2`. PNGs belong in `assets/images/`.

---

## The "Don't Touch" Rule

If you were not explicitly tasked with modifying a file, **do not reformat it**.
This includes:
- Normalizing quote styles in YAML you're reading for context
- Reflowing paragraph text in Markdown during an unrelated fix
- Adjusting import order in Python files you only imported from
- "Fixing" trailing newlines in files that passed pre-commit before your change

Violations create noisy diffs, fail code review, and corrupt the diff history.
When in doubt: touch only what the task requires.

---

## Agent Checklist Before Any PR

- [ ] Read `PROJECT-CONTEXT.md` → `FORMAT-CANON.md` → `AGENTS.md` → `UIAO-MEMORY.md`
- [ ] YAML keys are `snake_case`, 2-space indent, double-quoted where required
- [ ] All OSCAL `prop` elements have `uuid` (UUIDv4)
- [ ] POA&M IDs use `POAM-UIAO-` prefix and valid status enum
- [ ] `make validate-oscal` passes
- [ ] No files reformatted beyond task scope
- [ ] Commit message references `UIAO-MEMORY.md` per convention
- [ ] Core principles in any doc reference `docs/00_CorePrinciples.md` (SSOT) — never duplicate inline
