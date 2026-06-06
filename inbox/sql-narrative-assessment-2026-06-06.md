# SQL Server Narrative Bundle — External Assessment & Remediation Record

> **Status:** scratch / non-canon (per `inbox/README.md`). This is a traceable
> review record, not a governance artifact. Nothing here is SSOT.

**Date:** 2026-06-06
**Subject:** `docs/customer-documents/sql-server-narrative/` (Books 01–10),
rendered as `sqlservernarrativebundle_3.docx`.
**Trigger:** External four-dimension assessment (Technical Accuracy 8.5 /
Strategic Value 9.5 / Originality 9.0 / Publication Readiness 7.5) flagging
three "where a NIST/DoD review board would push back" gaps.

## Validity verdict

| # | Assessment critique | Verdict | Basis |
|---|---|---|---|
| 1 | "Must end" stated more absolutely than evidence supports; needs explicit linkage to FedRAMP / OMB M-22-09 / Zero Trust Strategy. | **Partially valid** — NTLM absolutism already softened by #834/#835; remaining kernel is that the zero-trust conclusion leaned on generic "FedRAMP-Moderate zero-trust requirements" and a mis-aimed `(ADR-008)` cite (ADR-008 governs Truth-Fabric anchor-binding, not Conditional Access / federal ZT). | Real mandate anchor exists in canon: `AC-17.yml` / `IA-2.yml` tie phishing-resistant MFA + Conditional Access to **OMB M-22-09 (Federal Zero Trust Strategy)**. |
| 2 | Conditional Access framed as a false binary; no treatment of compensating controls (PAM, PAWs, segmentation, bastion, JIT). | **Valid — highest value.** Narrative said the perimeter is "binary … covers all or none" and "none of these controls exist in the Windows model," conflating "CA can't see the token" with "no control constrains the connection." | Canon already supplies the rebuttal: `ADR-091 §4` governs surviving non-Entra logins as **documented, sunset-dated exceptions with a named compensating control**; CBA is the authorized interim posture (`ADR-068`). The fix reframes "false binary" → "binary steady state, compensating controls as a governed bridge." |
| 3 | Arc treated as inevitable; no formal comparison vs. gMSA / SP / cert-based / vault. | **Valid — moderate.** `ADR-002` / `ADR-091` assert the Managed Identity as destination but never compare alternatives. | Reasons are derivable and strong (gMSA re-anchors on the AD being retired; SP/vault reintroduces a stored bootstrap secret; CBA is the ADR-068 *interim* posture, not steady state). Added as exposition of the existing decision, not a new decision. |

## Remediation applied (this branch)

All three fixes are **additive prose + one citation correction** — no new
diagrams, no new canon, no new ADR decisions — and each *strengthens* both the
argument and provenance rather than weakening a claim.

- **Critique 2 → `Book_07_CPT_01.qmd`:** new section *"The Binary Perimeter Is
  Not a False Binary"* — concedes PAW/bastion, segmentation, JIT/PIM, PAM as
  real but non-equivalent (no identity-conditioned, continuous, per-connection
  evaluation), and ties them to the `ADR-091 §4` exception register + `ADR-068`
  CBA interim posture. Closing callout + intro updated. The `(ADR-008)` cite on
  the binary-perimeter claim corrected to `(ADR-091)` (binary-perimeter is
  ADR-091 doctrine).
- **Critique 3 → `Book_04_CPT_01.qmd`:** new section *"Why Arc and Not the
  Alternatives"* — gMSA (circular re-anchor on retiring AD), SP-with-secret /
  vault (stored bootstrap credential), CBA (interim only) vs. the credential-free
  Arc Managed Identity. Intro + closing callout updated.
- **Critique 1 → `Book_01_CPT_02.qmd`:** generic "FedRAMP-Moderate zero-trust
  requirements" replaced with the named mandate **OMB M-22-09 (Federal Zero
  Trust Strategy)** operationalized through **AC-17 / IA-2**, in the chapter
  intro, Driver Two opener, Driver Two close, and the Book-01 establishes
  callout.

## Not actioned (deliberately)

- No change to ADR-008's content or to its use elsewhere in the series; the
  fix *augments* citations with the M-22-09 / AC-17 / IA-2 anchor rather than
  asserting ADR-008 is wrong, since the program uses ADR-008 as its zero-trust
  ADR by convention.
- No canon edits, no `UIAO_NNN` allocation, no ADR — these are derived
  customer-facing narrative docs under `docs/`, so the changes flow as doc
  edits, not canon-change process.
