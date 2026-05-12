# 02 — Proposed ADR-058 Draft (Inbox)

> **Status:** Draft for maintainer review. Promoted to canon as
> `src/uiao/canon/adr/adr-065-hrit-productization-mission.md` (Accepted
> 2026-05-11) — renumbered from ADR-058 to ADR-065 to resolve slot
> collision with `adr-058-microsoft-purview-conformance-adapter-coverage.md`
> (accepted 2026-05-07). Spec slot moved similarly: UIAO_143 →
> **UIAO_144** (UIAO_143 is now SCIM Core Schema per PR #342).
>
> This inbox file retains the original ADR-058 / UIAO_143 numbering for
> historical traceability. The canonical ratified ADR is ADR-065; the
> canonical operational spec is UIAO_144.
>
> Original draft text follows verbatim below.

---

```
---
adr: ADR-058
title: "HRIT Single-ATO Productization as v0.6.0 Mission Theme"
status: Proposed
date: 2026-05-06
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-051  # SAML Trust Anchor
  - ADR-052  # PIV / USAccess Adapter
  - ADR-053  # OPM Azure APIM Adapter
  - ADR-054  # Single-ATO Reciprocity Model — runtime contract this ADR ratifies
  - ADR-055  # KYC / Customer Identity (sibling theme)
  - ADR-056  # Login.gov Federation (sibling, not blocking)
canon_refs:
  - UIAO_112  # Multi-Tenant Isolation
  - UIAO_113  # Evidence Graph (v1.2 amendment in scope)
  - UIAO_140  # Single-ATO Reciprocity Model
  - UIAO_143  # HRIT Productization Operational Spec — new spec introduced by this ADR
  - Spec2-D6.1  # Federal HRIT Integration Runbook
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4 PWS §5.1.1 #5"
  - "Solicitation Q&A #43, #44, #47, #48"
  - "Clause 1752.239-74"
---
```

*(Historical inbox draft text continues; see the canonical ratified ADR
at `src/uiao/canon/adr/adr-065-hrit-productization-mission.md` for the
authoritative content with updated numbering.)*

## See also

- `src/uiao/canon/adr/adr-065-hrit-productization-mission.md` (canonical, accepted)
- `src/uiao/canon/specs/hrit-productization.md` (UIAO_144, draft)
- `inbox/v0.6.0-hrit-productization/00-theme-rationale.md`
- `inbox/v0.6.0-hrit-productization/01-state-of-tree.md`
- `inbox/v0.6.0-hrit-productization/03-batch-plan.md`
