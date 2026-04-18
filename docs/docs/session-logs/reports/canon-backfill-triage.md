# Canon Backfill Triage — Batch 5.1.5

_Read-only analysis. No canon files were modified. Generated from a fresh `metadata_validator.py` run against `canon/` using the renamed `schemas/metadata-schema.json`._

## Headline numbers

- **Files scanned:** 24
- **BLOCKING:** 30
- **WARNING:** 0
- **INFO:** 0
- **Distinct offending files:** 24
- **Distinct failure patterns:** 2

## Schema contract

Required fields: _(none declared)_

## Exemplar frontmatter

_No passing canon file found — every canon `.md` under `canon/` is in the offender list. Stubs must be derived from the schema alone._

## Failure patterns (largest first)

### Pattern 1: 23 file(s)

Issues in this bucket:

- No valid YAML frontmatter found

<details><summary>Files</summary>

- `UIAO-SSOT.md`
- `UIAO_003_Adapter_Segmentation_Overview_v1.0.md`
- `specs\Compliance-Orchestrator.md`
- `specs\Platform-Overview.md`
- `specs\Platform-Services-Layer.md`
- `specs\UIAO-Spec-Test-Enforcement.md`
- `specs\UIAO-Test-Harness-CI-Enforcement.md`
- `specs\api-contract.md`
- `specs\cli.md`
- `specs\collector-interface.md`
- `specs\cql.md`
- `specs\data-lake.md`
- `specs\drift.md`
- `specs\enforcement-runtime.md`
- `specs\governance.md`
- `specs\graph-schema.md`
- `specs\ha.md`
- `specs\performance.md`
- `specs\policy.md`
- `specs\recovery.md`
- `specs\release.md`
- `specs\tenancy.md`
- `specs\zero-trust.md`

</details>

### Pattern 2: 1 file(s)

Issues in this bucket:

- Body contains potential boundary violation (GCC-High/DoD/Azure IaaS/PaaS reference)
- Invalid classification: 'UIAO Canon – Controlled'
- Invalid status: 'CANONICAL'
- Missing required field: boundary
- Missing required field: created_at
- Missing required field: title
- Missing required field: updated_at

<details><summary>Files</summary>

- `UIAO_002_SCuBA_Technical_Specification_v1.0.md`

</details>

## Decisions required before backfill

1. **Scope of `canon/`.** The single biggest pattern is driven by `canon/specs/` — are those files meant to be canon, or were they copied in from an earlier architecture dump? If not canon, move them (to `docs/` or out to `uiao-docs`) and shrink the validator's target. If canon, they all need frontmatter.

2. **Status enum semantics.** Any file flagged `Invalid status: 'CANONICAL'` or similar may just need `CANONICAL` added to the schema enum — or the file changed to use an existing value. Pick one: evolve the schema, or coerce the files.

3. **Encoding hygiene.** Mojibake sequences like `ΓÇô` in `classification` fields indicate a UTF-8 → cp1252 → UTF-8 round-trip somewhere upstream. Fix the source, not the symptom.

4. **Boundary violations in body text.** GCC-High references in a GCC-Moderate-only canon repo may be genuine policy statements (allowed) or accidental leaks (must be removed). These are per-file judgment calls.

5. **Branch protection ordering.** Do not flip `metadata-validator` to a required status check on `main` until BLOCKING count is zero. Alternative: enable as required + accept that `main` is red until backfill lands.

## Proposed next batches

- **5.1.6 — scope decision.** One-line: is `canon/specs/` canon? Answer drives everything else.
- **5.1.7 — mechanical backfill.** Apply the agreed frontmatter stub to every file in Pattern 1, one file → verify → batch-apply the rest.
- **5.1.8 — judgment backfill.** Walk Patterns 2..N by hand, one commit per file so diffs review cleanly.
- **5.2 — branch protection.** Only after BLOCKING is zero, or with explicit acceptance of a red main.

