---
name: Remediation PR - Metadata
about: Fix metadata drift items detected by automated scan
---

# Remediation PR -- Metadata

**Target file:** <!-- file_path -->
**Issue:** <!-- #issue_number -->
**Type:** <!-- e.g., invalid-id, adr-missing-affects -->

## Summary

- **Change:** Brief description of the metadata fix
- **UIAO ID:** <!-- uiao_id -->
- **Owner:** <!-- owner -->
- **Status:** <!-- status -->

## Changes

- Update frontmatter:
  - `uiao.id`: <!-- new_uiao_id -->
  - `uiao.status`: <!-- status -->
  - `uiao.owner`: <!-- owner -->
  - `uiao.tags`: <!-- tags -->
  - `uiao.lastUpdated`: <!-- date -->
  - `uiao.commit`: will be populated by CI on merge
- Add status badge at top of document (if missing)
- Add accessible diagram metadata (`title` and `desc`) if applicable

## Rationale

Explain why this metadata change is required and reference the automated report or governance rule.

## Branch naming

Use pattern: `remediation/metadata/<YYYYMMDD>-<UIAO_ID>-<short>`

Examples:
- `remediation/metadata/2026-04-07-UIAO_A_05-fix-id`
- `remediation/metadata/2026-04-07-ADR-034-add-affects`

## Commit message format

`<type>(metadata): <short description> [<UIAO_ID>]`

Examples:
- `fix(metadata): set uiao.id to UIAO_A_05 and add status badge [UIAO_A_05]`
- `chore(metadata): add affects list to ADR-034 [ADR-034]`

## Checklist

- [ ] Used canonical UIAO frontmatter template
- [ ] `uiao.id` follows `UIAO_<AppendixLetter>_<Number>`
- [ ] `uiao.status` is one of: `Current`, `Draft`, `Needs Replacing`, `Needs Creating`, `Deprecated`
- [ ] `uiao.owner` is a team or role
- [ ] `uiao.tags` present and relevant
- [ ] Status badge present in top 8 lines
- [ ] Diagrams include `title` and `desc` if applicable
- [ ] Local validation passed: `node scripts/validate_uiao_metadata.js`
- [ ] CI validation passes

## Reviewer guidance

- Confirm frontmatter fields are correct and consistent with the metadata contract
- Confirm no duplicate IDs exist
- Confirm ADR cross references if applicable

## Post-merge actions

- Verify `docs/_data/corpus-index.json` updated
- Confirm governance dashboard reflects the change
- Close linked issue when remediation is verified
