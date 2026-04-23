---
document_id: UIAO_126
title: "UIAO Test Plans Program — Canonical Catalog"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-17"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Test Plans Program

Canonical catalog of test plans used across the UIAO substrate.
This document does not restate the individual plans; it registers
them, defines their scope, and defines the rules under which a new
test plan enters the catalog. It is the single document an auditor
or contributor consults to know **which** tests govern **what**.

---

## 1. Audience

Both internal and external.

- **Internal** — contributors who must produce, update, or run a
  plan as part of a canon change.
- **External** — agency operators and auditors who need to know
  which plans apply to their deployment and how results are
  reported.

---

## 2. Catalog

The catalog references canon artifacts by document ID. Adding a new
plan means adding a canon artifact and a registry entry — no plans
live only in this document.

| Plan | Doc ID | Scope | Applies to |
|---|---|---|---|
| Adapter Conformance Test Plan — Template | UIAO_121 | Per-adapter conformance contract | Every adapter, modernization and conformance |
| Adapter Integration & Test Plan — Canonical Template | UIAO_123 | End-to-end integration envelope | Every adapter + the overlay that ingests it |
| Substrate Smoke Tests | `tests/test_substrate_walker.py` | Walker resolves workspace root; DRIFT-SCHEMA / DRIFT-PROVENANCE emit on missing paths / registries | Every clone |
| Schema Validation Suite | `scripts/validate_schemas.py` | Every registry validates against its pinned JSON Schema | Every canon PR |
| Metadata Validator | `.github/workflows/metadata-validator.yml` (inline body) | Frontmatter contract on every doc under `src/uiao/canon/` | Every canon PR |
| CLI Coverage Tests | `tests/` per the canon-consumer rule at `src/uiao/rules/canon-consumer.md` | Happy-path + failure-mode per CLI subcommand | Every CLI PR |

---

## 3. Plan-Entry Rules

1. A new test plan is a canonical artifact. It goes under
   `src/uiao/canon/specs/` (if doctrinal) or is a runnable suite under
   `tests/` / `scripts/` (if executable). Either way it gets
   an entry in this catalog.
2. Every plan declares what it covers, what it does **not** cover,
   and what its pass / fail signal is. A plan whose pass signal is
   ambiguous is not a plan — it is an essay.
3. Pass signals must be machine-readable where the plan is
   executable (exit code, JSON report, JUnit). Human-readable
   reviews (e.g., doctrinal self-assessment) must list the
   reviewer and the date in the output.
4. When a plan is retired, it moves to status `Deprecated` in its
   frontmatter, stays in the registry with a supersession pointer,
   and this catalog adds the successor on the same row.

---

## 4. Execution

The executable plans run under CI on every PR that touches their
path filter. The doctrinal templates (UIAO_121, UIAO_123) are
applied per-adapter: a new adapter lands with a filled-out copy of
each, validated in the same PR.

- `pytest.yml` — runs `tests/` (substrate smoke + full suite)
- `schema-validation.yml` — runs `scripts/validate_schemas.py`
- `metadata-validator.yml` — runs the validator on canon frontmatter
- `substrate-drift.yml` — runs `uiao substrate drift` against the tree

All four are blocking.

---

## 5. Reporting

Executable plans emit structured output consumable by the dashboard
layer. Doctrinal plans emit a per-adapter filled template under
that adapter's directory, which the metadata validator then checks
for frontmatter compliance. This keeps test results inside the
provenance chain — no side-channel spreadsheets.

---

## 6. Maintenance

A plan that describes behavior the substrate no longer exhibits is
a DRIFT-PROVENANCE finding. A plan whose schema reference has moved
is a DRIFT-SCHEMA finding. Both are caught by the standard CI
gates; both are fixed in the same PR as the underlying behavior
change.

---

## 7. Cross-References

- UIAO_104 — UIAO Test Harness & CI Enforcement Layer
- UIAO_121 — Adapter Conformance Test Plan — Template
- UIAO_123 — Adapter Integration & Test Plan — Canonical Template
- UIAO_125 — Training Program
- UIAO_127 — Project Plans Program
- UIAO_128 — Education Program
