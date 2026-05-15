---
title: "CHARTER-001-APPENDICES — Preprocessing Report"
status: draft
intent: "Architect-facing summary of preprocessing decisions on AtoBZ_clean.md before ingestion as CHARTER-001-APPENDICES. Produced by Charter Restoration Plan PR-A2a; ingestion gated on architect signoff in PR-A2b."
authored_at: "2026-05-15"
source_audit: "inbox/drafts/charter-restoration-plan.md §AtoBZ Audit Findings (2026-05-05)"
machine_report: "inbox/drafts/CHARTER-001-APPENDICES-preprocessing-report.json"
preprocessor: "scripts/charter-preprocessor/atobz_preprocess.py"
---

# CHARTER-001-APPENDICES — Preprocessing Report

This report documents every decision the preprocessor made converting
the OneDrive source `AtoBZ_clean.md` into the candidate canon file
`inbox/drafts/CHARTER-001-APPENDICES-cleaned.md`. **Architect signoff
on this report is the gate to PR-A2b** (which will move the cleaned
file into `src/uiao/canon/charter/CHARTER-001-APPENDICES.md`, register
it in `charter-registry.yaml`, and remove the `pending` annotation
on that entry).

## Executive summary

| Metric | Source | Cleaned | Change |
|---|---|---|---|
| Lines | 35,669 | 17,832 | **−50.0%** |
| Characters | 908,949 | 455,646 | **−49.9%** |
| Unique appendix codes | 52 | 52 | none |
| Total H1 `# Appendix X` occurrences | 106 | 52 | −54 (dedup) |
| Non-breaking hyphens (U+2011) | 1,895 in cleaned-pre-normalization | 0 | normalized |
| Invented-acronym annotations | n/a | 3 | flagged for confirmation |
| Source-side truncation | yes (line 35,669) | documented in cleaned tail | no recovery attempted |

**Audit reconciliation:** The 2026-05-05 audit estimated ~17,500 lines after
dedup. Actual: 17,832. The audit was within 2% of actual.

## Dedup decisions (54 total)

The preprocessor's rule: **for each appendix code, keep the FIRST H1
occurrence; drop all subsequent occurrences AND their content (lines
between the dropped H1 and the next H1).** Identical-after-normalization
content is dropped without further review; non-identical content is
flagged here.

### Identical-content dedups (52)

52 of 54 dedup decisions involve duplicate occurrences whose content
matches the first occurrence after whitespace and non-breaking-hyphen
normalization (SHA-256 hash equivalence). These are mechanical
pandoc-concatenation duplicates — the same prose emitted twice. Dropped
without architect review.

Full dedup decision list (with line ranges and content hashes) is in
`inbox/drafts/CHARTER-001-APPENDICES-preprocessing-report.json` under
`dedup_decisions[]`.

### Non-identical dedups requiring architect review (2)

> **Both cases below are non-identical because the *dropped* version
> is shorter than the *kept* version — i.e., the dropped version was a
> stub or truncated copy. Recommended action: confirm dedup as proposed.**

#### Appendix Z — Automation Architecture

| Version | Source lines | Line count | Char count | SHA-256 (norm) |
|---|---|---|---|---|
| **KEPT (1st occurrence)** | 2–287 | 286 | 8,349 | `8e6b1ee54851` |
| DROPPED (3rd occurrence) | 16,350–16,360 | 11 | 288 | `6b2f90401921` |

The 3rd occurrence (line 16,350) is only 11 lines — it is a heading
plus a few lines of placeholder text, not actual content. The kept
version (line 2) carries the full 286-line content. Note: the 2nd
occurrence (line 8,176) was identical-after-normalization and is
already counted in the 52 mechanical dedups above.

**Question for architect:** OK to confirm dedup as proposed?

#### Appendix AL — Session Binding Architecture

| Version | Source lines | Line count | Char count | SHA-256 (norm) |
|---|---|---|---|---|
| **KEPT (1st occurrence)** | 16,361–16,751 | 391 | 9,286 | `1b15d64165ac` |
| DROPPED (4th occurrence) | 35,663–35,669 | 7 | 187 | `168c47741a83` |

The 4th occurrence at line 35,663 IS the truncated tail of the source
file — it is the `## 1. Introducti` cliffhanger named in the audit.
The kept first occurrence carries full content. (The 2nd occurrence at
line 26,012 was identical to the 1st; it's in the 52 mechanical
dedups.)

**Question for architect:** OK to confirm dedup as proposed?

## Reordering (1 change)

The source had **Appendix Z at line 2** — out of alphabetical order,
appearing before Appendix A. The preprocessor moves all appendices
into alphabetical sequence (A–Z, then AA–AZ). Z now appears in its
correct position between Y and AA.

This was a structural fix, not a content change — the Z segment's text
is unchanged. Source-line provenance is preserved in the JSON report's
`dedup_decisions[].kept.line_start` field for any architect who wants
to trace a section back to its source location.

## Non-breaking hyphen normalization (1,895 occurrences)

Every U+2011 (non-breaking hyphen) was replaced with U+002D (ASCII
hyphen). This is a mechanical change that does not affect rendered
output but normalizes character encoding for downstream tooling
(grep, jq, schema validators) that does not handle Unicode hyphen
variants identically.

## Invented-acronym annotations (3 terms)

The 2026-05-05 audit flagged 4 invented terms for architect
confirmation. The preprocessor scanned the source and found:

| Audit-named term | Found? | Occurrences in cleaned file | Annotation count |
|---|---|---|---|
| `UAI` | ✅ Yes | 1 (after dedup) | 1 |
| `UCI-X` | ❌ **NOT FOUND** | 0 | — |
| `UIAO Autonomous Operations Fabric` | ✅ Yes | 1 (after dedup) | 1 |
| `UIAO Assurance and Governance Fabric` | ✅ Yes | 1 (after dedup) | 1 |

**Audit correction:** `UCI-X` was named in the 2026-05-05 audit (line
7607) but is not present anywhere in the source file. Either the audit
was wrong, the term was renamed before the audit, or the term was
removed in a later source revision. **Recommended action:** drop
`UCI-X` from the invented-acronym worry list.

For each present term, the preprocessor wrapped the occurrence with
HTML comments:

```html
<!-- ARCHITECT-CONFIRM: term 'UAI' is Copilot-derived per CHARTER-001-APPENDICES audit; confirm canonical or replace -->UAI<!-- /ARCHITECT-CONFIRM -->
```

These render as plain text but are visible to PR review tooling and
greppable for follow-up. PR-A2b should resolve them: either drop the
markers (term confirmed canonical) or replace each with V3/V4U-consistent
terminology.

**Architect questions:**

1. **`UAI`** — what does this acronym stand for in context? Recommend
   confirming canonical or replacing with a defined term.
2. **`UIAO Autonomous Operations Fabric`** — is this distinct from
   the existing UIAO Governance OS terminology, or a synonym?
3. **`UIAO Assurance and Governance Fabric`** — same question. Both
   "Fabric" terms feel like layered concepts that may overlap with
   established UIAO_169 (Governance OS State Machine) and UIAO_174
   (Governance Telemetry Model).

## Source-side truncation (no recovery attempted)

The source file ends mid-word at line 35,669 with the partial
heading `## 1. Introducti`. This is the 4th occurrence of Appendix AL
in the source (already addressed in the dedup section above). The
**first** occurrence of Appendix AL is complete; **no canon content
is lost** from the cleaned file.

The preprocessor appended a callout note at the end of the cleaned
file documenting the source truncation for transparency.

**Recovery option (not pursued in this preprocessing pass):** The
audit suggested checking OneDrive `UIAO-V1/` for the predecessor source
files that `AtoBZ_clean.md` was concatenated from. If those exist and
contain the full untruncated content, a future PR could recover it.
**Architect question:** is recovery desired? If yes, name the candidate
predecessor source(s); if no, the truncation note in the cleaned file
is the final answer.

## Editorial pass scope

Per ADR-070 §"Editorial pass on ingestion is light by design":

| Permitted | Applied? |
|---|---|
| Pandoc-escape removal | n/a (source has no pandoc backslash escapes) |
| List-bullet de-escape | n/a |
| Table-row contiguity restoration | n/a (source tables are well-formed) |
| Non-breaking-hyphen normalization | ✅ 1,895 normalized |
| Removal of metadata that duplicates frontmatter | n/a |
| Dedup of mechanical pandoc-concatenation duplicates | ✅ 52 mechanical + 2 reviewed |
| Reordering of out-of-sequence appendices | ✅ Z moved into alphabetical position |
| Source-truncation documentation | ✅ Footer callout appended |
| Invented-acronym flagging | ✅ 3 terms marked with ARCHITECT-CONFIRM comments |

| **Not permitted without separate ADR** | Applied? |
|---|---|
| Prose rewrites | ❌ none |
| Section reorderings beyond alphabetical | ❌ none |
| Content additions beyond ARCHITECT-CONFIRM markers and truncation note | ❌ none |
| Content deletions beyond the dedup rule | ❌ none |

## Tooling

- **Preprocessor:** `scripts/charter-preprocessor/atobz_preprocess.py`
  — stdlib only (no python-docx / lxml dependency). Re-runnable for
  source revisions.
- **Source (gitignored):** `inbox/_audit-input/AtoBZ-source.md`
  — copy of the OneDrive original; do not commit.
- **Cleaned candidate:** `inbox/drafts/CHARTER-001-APPENDICES-cleaned.md`
  — moves to `src/uiao/canon/charter/CHARTER-001-APPENDICES.md` in PR-A2b.
- **Machine report:** `inbox/drafts/CHARTER-001-APPENDICES-preprocessing-report.json`
  — full per-decision detail for diff/audit.

## Architect signoff checklist (required to unblock PR-A2b)

- [ ] Confirm dedup of Appendix Z (3rd occurrence at line 16,350)
- [ ] Confirm dedup of Appendix AL (4th occurrence at line 35,663 — the truncated tail)
- [ ] Confirm reordering of Appendix Z into alphabetical position
- [ ] Decide on `UAI` acronym: confirm canonical (and define) or replace
- [ ] Decide on `UIAO Autonomous Operations Fabric`: confirm canonical or replace
- [ ] Decide on `UIAO Assurance and Governance Fabric`: confirm canonical or replace
- [ ] Acknowledge `UCI-X` is not present (drop from worry list)
- [ ] Decide on truncation recovery: pursue or accept the footer note
- [ ] Sanity-pass the cleaned file (~17,800 lines) — spot-check 3–5 random appendices

When all boxes are checked, PR-A2b can:
1. Resolve every `<!-- ARCHITECT-CONFIRM: ... -->` marker per decisions above.
2. Strip the markers (replace with confirmed text).
3. Move the file to `src/uiao/canon/charter/CHARTER-001-APPENDICES.md`.
4. Add proper frontmatter (`document_id: CHARTER-001-APPENDICES`, `tier: foundational`, etc.).
5. Update `charter-registry.yaml` to move CHARTER-001-APPENDICES from `pending_ingestion[]` into `charter_documents[]`.
6. Remove this report and the cleaned draft from `inbox/drafts/`.
