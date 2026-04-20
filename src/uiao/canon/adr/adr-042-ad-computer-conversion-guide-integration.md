---
id: ADR-042
title: "AD Computer Conversion Guide — Canonical Input to Phase 4 Device Planes"
status: draft
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
  - device-management-steward
supersedes: []
extends:
  - ADR-034
  - ADR-038
canon_refs:
  - MOD_C_Attribute_Mapping_Table
  - UIAO_GAE_AD_Computer_Object_Decomposition
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
pending_inputs:
  - "inbox/AD Computer Object Conversion Guide — Entra ID, Intune, and Azure Arc Governance.docx"
---

# ADR-042: AD Computer Conversion Guide — Canonical Input to Phase 4 Device Planes

## Status

**DRAFT — extends ADR-038 without superseding it.**

ADR-038 (Phase 4, device-plane OrgPath) shipped the *write-side*
plumbing: the plane registry, the dual-transport adapter, the
disposition ↔ plane mapping, and the phantom-OrgPath governance rule.
It did not cite the operator-level **AD Computer Object Conversion
Guide** (`inbox/AD Computer Object Conversion Guide — Entra ID,
Intune, and Azure Arc Governance.docx`, 46 KB, 2026-04-20) because
that document had not yet been extracted from the inbox when ADR-038
was written.

This ADR records the decision to adopt that guide as a **canonical
operator input** to Phase 4. It is a narrative supplement, not a
replacement. No code changes required on ADR-038's adapter or canon.

## Context

The session notes (`inbox/claude-session-AD-Group-and-OU-mapping-to-EntraID.md`)
flagged the device-object dimension of OrgPath as the governance gap
most likely to silently fail after AD retirement. ADR-038 closed the
gap *structurally* — a plane registry + a write adapter. The gap that
remained, and that this ADR closes, is **operational**: how does a
human operator actually drive the conversion of a given computer
object from AD-joined to its destination plane, in the correct
sequence, with the correct pre-flight checks?

`docs/docs/GAE-computer-object-decomposition.md` (UIAO_GAE) is the
*architectural* model for this decomposition. ADR-038 is the
*adapter contract*. The AD Computer Conversion Guide is the
*step-by-step runbook* that binds the two. None of the three is
redundant; all three are necessary for Phase 4 to be executable by
a non-author operator.

The guide was authored in `.docx` and blocked by `inbox/.gitignore`
from reaching `origin/main`. The companion `make inbox-convert`
target (introduced in the same PR as this ADR) provides the pandoc
bridge that will produce the Markdown sibling an operator can
consume via Quarto.

## Decision

1. **Adopt the AD Computer Conversion Guide as a canonical Phase 4
   operator input.** Its Markdown sibling ships under
   `docs/docs/GAE-computer-object-conversion-guide.md` (stub created
   alongside this ADR; content populated once pandoc has run).
2. **Do not re-home ADR-038's decisions.** The adapter contract, the
   op vocabulary, and the phantom-OrgPath governance rule remain
   exactly as ADR-038 specifies. This ADR is additive.
3. **Tie the guide into the `uiao_doc_ref` block of
   `adapters/modernization/active-directory/adapter-manifest.json`**
   by adding the guide's document id (UIAO_GAE_CG, reserved here)
   once the markdown lands. The manifest's `phase_map` stays
   the F1/F2/F3 user-plane shape; the device-plane workflow gets its
   own section in the guide.
4. **Drift-engine configuration (MOD_M) stays unchanged.** Phase 6's
   op → drift_class → severity map already covers every op Phase 4
   can emit; the guide is operator documentation, not a new rule
   set.

## Consequences

**Positive**

- Phase 4 becomes executable end-to-end by an operator who has never
  read ADR-038. The adapter, the model, and the runbook finally
  cite each other.
- Future auditors can trace every device-plane decision (GAE →
  ADR-038 → ADR-042 → operator runbook) through a single chain of
  canon.
- The inbox → canon promotion path is exercised once, via pandoc, so
  subsequent docx authoring lands in canon with zero ad-hoc copying.

**Negative / deferred**

- Until pandoc produces the markdown, the guide is a dangling
  reference. The ADR remains `draft` and
  `docs/docs/GAE-computer-object-conversion-guide.md` stays a stub.
  Promotion to `accepted` is conditional on content extraction.
- If the guide specifies a pre-enrollment step (e.g., Azure Arc
  onboarding via `Connect-AzConnectedMachine` before the adapter's
  `arc-tag-create` op can run), ADR-038 will need a forward link
  here — not a rewrite, but a cross-reference.
- The guide may introduce terminology that diverges from the GAE
  model (e.g., "Track 1/2/3" vs GAE's plane names). Any divergence
  gets reconciled in the markdown sibling, not in this ADR.

## Alternatives considered

- **Roll the guide's content into a revised ADR-038.** Rejected. The
  original ADR-038 is already merged; amending it in-place would
  conflate operator documentation with adapter-contract decisions.
  Keeping the two ADRs distinct preserves reviewability.
- **Treat the guide as narrative only, skip the ADR.** Rejected.
  Without an ADR that formally adopts the guide, future canon edits
  have no anchor for the "why does this document exist?" question,
  and the `adapter-manifest.json` cross-reference has nothing to
  cite.
- **Host the guide in `docs/narrative/`.** Rejected. Narrative is for
  explainer content aimed at principals; the conversion guide is a
  runbook — operational, step-keyed, operator-facing. `docs/docs/`
  is the correct home.

## Promotion checklist

Before this ADR can move from `draft` to `accepted`:

- [ ] `make inbox-convert` has produced
      `inbox/AD Computer Object Conversion Guide — Entra ID,
      Intune, and Azure Arc Governance.md`.
- [ ] The markdown sibling has been reviewed and moved to
      `docs/docs/GAE-computer-object-conversion-guide.md`
      (replacing the stub).
- [ ] Any implementation deltas surfaced by the guide have been
      captured as follow-up items (e.g., if the guide specifies
      pre-enrollment steps Phase 4 doesn't cover, open an issue
      for Phase 4.5).
- [ ] `adapters/modernization/active-directory/adapter-manifest.json`
      has been updated with the new `uiao_doc_ref` entry.
- [ ] `src/uiao/canon/document-registry.yaml` lists UIAO_GAE_CG.

## Related work

- ADR-034 — Three-plane device model (architectural context).
- ADR-038 — Phase 4 device-plane OrgPath provisioning (the adapter
  contract this ADR complements).
- GAE — AD Computer Object Decomposition (the structural model).
- Pending PR that runs `make inbox-convert` + populates the stub.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 2026-04-20 | Drafted as scaffolding for pandoc-converted guide | Automation |
