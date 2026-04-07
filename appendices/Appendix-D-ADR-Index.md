# Appendix D — ADR Index

## D.1 Purpose

This appendix is the canonical index of Architecture Decision Records (ADRs) governing the UIAO SCuBA integration. Each ADR documents a decision, its rationale, alternatives considered, and consequences.

ADR source files (machine-readable JSON) live in: `uiao-core/adr/`
ADR human-readable files live in: `uiao-docs/adr/`

---

## D.2 SCuBA Integration ADRs

| ADR ID | Title | Status | Date | Summary |
|---|---|---|---|---|
| ADR-SCuBA-001 | SCuBA Integration via UIAO Adapter | Accepted | 2026-04-07 | SCuBA runs via a UIAO adapter wrapper rather than standalone, enabling normalization, KSI mapping, and provenance. |
| ADR-SCuBA-002 | KSI Rules Stored as YAML in uiao-core | Accepted | 2026-04-07 | KSI rules are stored as individual YAML files in `uiao-core/ksi/rules/` for deterministic versioning and machine readability. |
| ADR-SCuBA-003 | Normalization Schema in JSON Schema Format | Accepted | 2026-04-07 | The UIAO normalized SCuBA schema is defined as a JSON Schema document to enable validation, tooling, and drift detection. |
| ADR-SCuBA-004 | Provenance Manifest per SCuBA Run | Accepted | 2026-04-07 | Every SCuBA pipeline run produces a SHA-256 hashed provenance manifest capturing lineage, environment, and artifact chain. |
| ADR-SCuBA-005 | Machine/Human Artifact Separation | Accepted | 2026-04-07 | Machine artifacts (schemas, scripts, KSI rules, provenance) are stored exclusively in uiao-core. Human artifacts (reports, appendices, runbooks) are stored exclusively in uiao-docs. No duplication. |
| ADR-SCuBA-006 | GitHub Actions for Automated SCuBA Execution | Accepted | 2026-04-07 | SCuBA pipeline runs are automated via GitHub Actions (weekly scheduled + manual dispatch) to ensure repeatable, documented execution. |

---

## D.3 ADR Template

All future SCuBA-related ADRs should follow this structure:

```
ADR ID:       ADR-SCuBA-###
Title:        <Decision Title>
Status:       Proposed | Accepted | Superseded | Rejected
Date:         YYYY-MM-DD
Version:      1.0

1. Context
   Describe the architectural or governance context.

2. Problem Statement
   Define the problem requiring a decision.

3. Decision
   State the decision in clear, normative language.

4. Rationale
   Explain why this decision was made.

5. Alternatives Considered
   List alternatives and why they were not chosen.

6. Consequences
   Positive and negative consequences.

7. Provenance
   Authors, reviewers, related ADRs, related KSI rules.
```

---

## D.4 Governance Rules for ADRs

- Every non-trivial change to the SCuBA pipeline requires an ADR
- ADRs are immutable once Accepted — supersede, do not edit
- ADR IDs are unique and sequential within the SCuBA namespace
- Machine-readable ADR JSON lives in `uiao-core/adr/`
- Human-readable ADR Markdown lives in `uiao-docs/adr/`

---

## D.5 Related Documents

- [Appendix B — UIAO SCuBA Pipeline](Appendix-B-UIAO-SCuBA-Pipeline.md)
- [Appendix C — KSI Mapping Tables](Appendix-C-KSI-Mapping-Tables.md)
- [SCuBA Pipeline Runbook](../docs/SCuBA-Pipeline-Runbook.md)
