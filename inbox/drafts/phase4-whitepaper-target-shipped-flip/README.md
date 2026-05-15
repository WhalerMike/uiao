---
title: "Phase 4 — Whitepaper TARGET → SHIPPED flip + AGENTS.md alignment"
status: DRAFT
date: 2026-05-15
owner: Michael Stratton
depends_on: Phase 3 PR-3a ACCEPTED (canonical DriftFinding + RemediationRouter live)
related_strategy: "Whitepaper TARGET → SHIPPED plan (governance-os whitepaper §3)"
---

# Phase 4 — Whitepaper TARGET → SHIPPED Flip

The smallest phase. No ADR, no engineering, no Python. Phase 4 is the
documentation catching up to canon — two whitepaper rows flip from
**TARGET** to **SHIPPED**, the §8 "What this is not" bullet that says
"runtime drift is design-only" is retired, the §10 closing paragraph
loses its forward-looking sentence about runtime targets, and
AGENTS.md's substrate-walker description grows to reflect the
five-class emission surface.

## Why this is a separate phase

Phase 3 PR-3a (canonical DriftFinding + router) is the last load-bearing
engineering change. Once it lands, the substrate is structurally
complete — both whitepaper TARGET rows are factually SHIPPED. Phase 4
is just the marketing/canon-truth alignment, but it deserves a
separate PR for three reasons:

1. **Reviewability.** A "flip TARGET → SHIPPED" PR is a single
   reviewable claim — does the engineering actually back the new
   status? Mixing it into PR-3a forces reviewers to verify both the
   engineering AND the claim in one pass.
2. **Reversibility.** If post-merge testing or assessor feedback
   surfaces a gap, Phase 4 can be reverted independently without
   reverting the engineering.
3. **Audit trail.** A standalone "Phase 4 flip" commit is a clean
   timeline marker — "as of this date, the Governance OS substrate
   declares runtime drift + continuous capture SHIPPED." That matters
   for the next ATO package's compliance narrative.

## What's in this folder

| File | Purpose | Target |
|---|---|---|
| [whitepaper.diff.md](whitepaper.diff.md) | Three section diffs: §3 substrate-stack table (TARGET → SHIPPED), §8 "What this is not" (retire the runtime-drift bullet), §10 "Conclusion" (drop the forward-looking sentence) | [`docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd`](../../../docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd) |
| [agents-md.diff.md](agents-md.diff.md) | Substrate-walker description update + new public-surface rows for telemetry sink, validators, router, drift_finding, provenance + consent + identity-resolver models | [`AGENTS.md`](../../../AGENTS.md) |

No ADR draft. Phase 4 doesn't make architectural decisions — every
load-bearing call was made in ADR-070 / ADR-071 / ADR-072 / ADR-073.

## What Phase 4 does NOT do

- **No image regeneration.** The substrate-stack diagram
  (`uiao-governance-os-whitepaper-image-02-uiao-substrate-stack-diagram-pos.png`)
  shows a "Drift Engine" sidebar that already spans all three layers;
  it does not visually distinguish TARGET from SHIPPED, so it does not
  need regeneration. The §3 table is the source of truth for status.
- **No SSP / POA&M / KSI / Component Definition narrative changes.**
  Those carry their own provenance; Phase 4 doesn't touch them.
- **No new whitepaper sections.** The §3 substrate-stack table is the
  only structural addition since the whitepaper landed; Phase 4 just
  fills its TARGET rows in.
- **No press release or external announcement.** Phase 4 is a
  documentation merge, not a marketing event. Agencies see the flip
  on the next ATO package regeneration; no separate announcement is
  necessary.

## Promotion plan

Phase 4 is one PR. Promotion order is mechanical:

1. Apply the whitepaper.diff.md changes to
   `docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd`.
2. Apply the agents-md.diff.md changes to `AGENTS.md`.
3. Run `quarto render docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd` locally to confirm the table renders.
4. PR title: `docs(whitepaper): flip runtime drift + continuous capture from TARGET to SHIPPED`
5. Commit message body cites ADR-070 through ADR-073 as the engineering chain.

## Exit criteria

Phase 4 is complete when:

1. The §3 substrate-stack table in `uiao-governance-os-whitepaper.qmd`
   shows **SHIPPED** on every row.
2. §8 "What this is not" no longer asserts that runtime drift is
   TARGET / DESIGN-ONLY (the framing is honest — the *fix* handler's
   adapter coverage is still partial, which is what §8 now reflects).
3. §10 "Conclusion" no longer carries the "what is target state
   extends the same model" sentence.
4. AGENTS.md substrate-walker description lists the full five-class
   emission surface across walker + sink subkinds.
5. AGENTS.md public-surface table includes rows for the new modules
   introduced in Phases 0–3.

## Status after Phase 4

The whitepaper TARGET → SHIPPED plan from this conversation series
closes. The Governance OS substrate's structural floor + runtime
extension are both shipped. Remaining items live in future ADRs:

- **Phase 5 (cleanup)** — Unify the OrgTree engine's `DriftFinding`
  with the canonical class introduced in Phase 3. Separate ADR.
- **`fix` handler adapter coverage** — Each adapter family registers
  its own apply() functions over time; one PR per adapter per drift
  class. Not a phase; ongoing.
- **POA&M dedup** — Follow-on cleanup ADR; not Phase 4 scope.
- **Federated provenance verification** — Cross-agency envelope
  verification across the federal substrate. Mentioned in ADR-070 as
  a future ADR; not in scope here.

## Cross-references

- [`inbox/drafts/phase0-runtime-provenance-envelope/`](../phase0-runtime-provenance-envelope/) — typed envelope
- [`inbox/drafts/phase1-emit-hook-and-evidence-capture/`](../phase1-emit-hook-and-evidence-capture/) — emit hook + event log
- [`inbox/drafts/phase2-runtime-drift-validators/`](../phase2-runtime-drift-validators/) — runtime validators
- [`inbox/drafts/phase3-remediation-contract-and-router/`](../phase3-remediation-contract-and-router/) — remediation contract + router + OSCAL
- [`docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd`](../../../docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd) — flip target
- [`AGENTS.md`](../../../AGENTS.md) — flip target
