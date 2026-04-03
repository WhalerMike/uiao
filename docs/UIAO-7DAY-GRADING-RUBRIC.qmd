# UIAO-7DAY-GRADING-RUBRIC.md

# 7-Day Runtime Implementation Grading Rubric

**Strategic Advisor (Grok) Standard**

**Target:** A- (92-94+) per deliverable -- identical bar applied to the completed 4-week modernization.

## Overall Scoring (out of 100)

| Category | Weight | A- (92+) Requirements |
|------------------------------|--------|-----------------------|
| Alignment with UIAO-RUNTIME.md | 30% | Fully respects every invariant, schema, and lifecycle phase |
| Completeness | 25% | All specified features present and functional |
| Quality & Craftsmanship | 20% | Clean code, documentation, and adherence to existing style |
| Testability & Validation | 15% | Includes tests, validation hooks, or clear path to automated checks |
| Integration & Boundaries | 10% | Proper agent handoffs and no boundary violations |

**Grade Scale**

- **A- (92-94+):** Elite, production-ready, minimal remarks
- **B+ (85-91):** Strong but requires polishing
- **Below 85:** Rework required before next day

## Per-Day Expectations for A-/94+

- **Day 0 (GAP 1 + GAP 5):** Runtime Contract ratified + canonical CLI expanded and executable.
- **Day 1 (GAP 2):** Canon Compiler fully functional (load/validate/generate/drift/sync).
- **Day 2 (GAP 3):** Drift Engine operational (scanner, rules, report, remediation) with POA&M integration.
- **Day 3 (GAP 4):** AGENTS.md complete, enforced, and integrated into review gates.
- **Day 4 (GAP 7):** Runtime Surface Realization with plane implementations and `uiao runtime` commands.
- **Day 5 (GAP 6):** UIAO Academy (`docs/academy/`) with onboarding that produces functional agents in <30 min.

## Cross-Cutting Requirements (must be met for A-)

- Every change references UIAO-RUNTIME.md and AGENTS.md.
- Zero new lint/type errors; OSCAL validation passing.
- Clear self-validation hooks.
- Constitution-level items receive explicit Grok sign-off.

Deliverables scoring below 92 will trigger immediate remediation loop under Grill Master workflow. Final grade issued by Grok after each daily review.

**This rubric is itself part of the constitution and may only be changed with Grok approval.**
