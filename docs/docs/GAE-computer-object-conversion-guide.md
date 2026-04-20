---
id: UIAO_GAE_CG
title: "Appendix GAE — Conversion Guide — AD Computer → Entra ID / Intune / Azure Arc"
category: Runbook
status: stub
canon_refs:
  - ADR-034
  - ADR-038
  - ADR-042
  - UIAO_GAE_AD_Computer_Object_Decomposition
pending_inputs:
  - "inbox/AD Computer Object Conversion Guide — Entra ID, Intune, and Azure Arc Governance.docx"
date: 2026-04-20
---

# Appendix GAE — Conversion Guide (STUB)

> **STATUS: STUB.** Content pending extraction from
> `inbox/AD Computer Object Conversion Guide — Entra ID, Intune,
> and Azure Arc Governance.docx` (46 KB, authored 2026-04-20).
> Run `make inbox-convert` to produce the pandoc sibling, then
> replace this stub with the converted markdown (keeping the
> frontmatter block above intact and adding `provenance`).

## Why this file exists

The session notes (`inbox/claude-session-AD-Group-and-OU-mapping-to-EntraID.md`)
flagged the computer-object dimension of the AD → Entra migration as
the single-largest governance gap after user-object work. Phase 4
(ADR-038) shipped the adapter contract and plane registry; this
document is its operator-facing companion.

- The **architectural model** of the decomposition lives at
  [`GAE-computer-object-decomposition.md`](./GAE-computer-object-decomposition.md).
- The **adapter contract** and plane registry live in
  [ADR-038](../../src/uiao/canon/adr/adr-038-device-plane-orgpath.md).
- The **integration decision** that adopts this guide as canonical
  operator input lives in
  [ADR-042](../../src/uiao/canon/adr/adr-042-ad-computer-conversion-guide-integration.md).
- The **step-by-step runbook content** (pre-flight checks, disposition
  selection, Arc onboarding, Intune enrollment, OrgPath write-back,
  verification) is what the pandoc-converted body of this file will
  contain.

## Expected structure (to be filled)

Once converted, this document is expected to contain at minimum:

1. **Pre-flight checks** — what to verify on the AD computer object
   before any conversion step (AD health, PKI posture, SPN inventory,
   KCD/GMSA dependencies).
2. **Disposition selection** — how to route each machine through the
   GAE.4 decision tree (implemented today in
   `src/uiao/adapters/modernization/active-directory/disposition.py`).
3. **Track 1 — Entra-joined clients** — Entra join, Intune enrollment,
   OrgPath write via Phase 4 adapter (`device-ext-create`).
4. **Track 2 — Arc-enrolled servers** — `Connect-AzConnectedMachine`
   onboarding, ARM tag write via Phase 4 adapter (`arc-tag-create`).
5. **Track 3 — Workload identity rebuild** — SPN/GMSA → Managed
   Identity transition; Phase 4 reserves `app-tag` plane (Phase 5+).
6. **Track 4 — Stay-on-AD** — DCs and dependency-roles remain, no
   OrgPath plane (per MOD_C registry `skip_dispositions`).
7. **Track 5 — Decommission** — EOL / stale, no migration path.
8. **Verification** — how to confirm OrgPath landed correctly on each
   plane; ties into Phase 6 drift-engine scan.

## Promotion checklist

- [ ] `pandoc` available locally (`winget install pandoc` / `brew install pandoc` / `apt install pandoc`).
- [ ] `make inbox-convert` has produced
      `inbox/AD Computer Object Conversion Guide — Entra ID, Intune, and Azure Arc Governance.md`.
- [ ] Content reviewed; any delta from the architectural model is
      reconciled into the guide, not into GAE or ADR-038.
- [ ] This stub has been replaced with the converted content +
      a `provenance:` block pointing at the source docx (filename,
      size, date, SHA-256).
- [ ] [ADR-042](../../src/uiao/canon/adr/adr-042-ad-computer-conversion-guide-integration.md)
      flipped from `draft` to `accepted`.
- [ ] `src/uiao/canon/document-registry.yaml` lists `UIAO_GAE_CG`.
- [ ] `src/uiao/adapters/modernization/active-directory/adapter-manifest.json`
      `uiao_doc_ref` references `UIAO_GAE_CG`.
