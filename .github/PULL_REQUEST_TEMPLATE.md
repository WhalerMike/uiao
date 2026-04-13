# PR Title
<!-- Use: [UIAO_xxx] Short descriptive title -->

## Summary

- **Document(s) changed**: UIAO_xxx, UIAO_yyy
- **Type**: Draft update / New document / ADR / Minor edit / Deprecation
- **Short description**: One or two sentences describing the change.

## Motivation

Why is this change needed? Reference issues, ADRs, or incidents.

## Affected Appendices and Artifacts

- Appendix: A | B | C | D | E
- ADRs referenced: ADR-000, ADR-NNN
- Cross-references updated: list files

## Checklist Before Requesting Review

- [ ] I used the canonical document template and frontmatter.
- [ ] `uiao_id` present and follows pattern `UIAO_<AppendixLetter>_<Number>` (e.g., `UIAO_A_01`).
- [ ] `status` set to one of: `Current`, `Draft`, `Needs Replacing`, `Needs Creating`, `Deprecated`.
- [ ] `owner` field present in frontmatter.
- [ ] Links validated locally; no broken internal links.
- [ ] If this change affects other documents, cross-references updated.
- [ ] If this change requires an architectural decision, ADR created or referenced.

## Reviewer Guidance

- **Primary reviewer**: @owner-team
- **Focus areas**: correctness of governance rules, cross-fabric impacts, ADR implications, naming and status.
- **Testing**: confirm CI frontmatter validation passes.

## Post Merge Actions

- [ ] Confirm dashboard metadata updated.
- [ ] Notify appendix owners if cross-fabric impact exists.
- [ ] If deprecating a document, add archive entry.

---

**Quick Checklist (copy into PR body if needed)**

- [ ] Canon template used
- [ ] `uiao_id` valid
- [ ] `status` set
- [ ] `owner` present
- [ ] CI validation passes

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
