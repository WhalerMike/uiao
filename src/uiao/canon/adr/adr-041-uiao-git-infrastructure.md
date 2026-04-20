---
id: ADR-041
title: "UIAO Git Infrastructure — Self-Hosted Git on Windows Server 2025 + IIS"
status: draft
date: 2026-04-20
deciders:
  - governance-steward
  - platform-engineer
  - security-steward
supersedes: []
related_adrs:
  - ADR-028
  - ADR-032
canon_refs:
  - UIAO_200_Substrate_Manifest
pending_inputs:
  - "inbox/UIAO Git Infrastructure — Architecture Decision Record.docx"
  - "inbox/UIAO Git Server — Windows Server 2025 with IIS Implementation Guide.docx"
  - "inbox/Git on Windows Server 2025 with IIS — Step-by-Step Implementation Guide.docx"
---

# ADR-041: UIAO Git Infrastructure — Self-Hosted Git on Windows Server 2025 + IIS

## Status

**DRAFT — content pending pandoc extraction.**

This ADR is a structural skeleton matching the Author's docx ADR
(`inbox/UIAO Git Infrastructure — Architecture Decision Record.docx`,
34 KB, 2026-04-20). Every section below reserves the shape the
final document needs to hold. The ✳ markers flag content that must
be populated from the docx sources listed in `pending_inputs`
before this ADR can be promoted from `draft` to `accepted`.

Run `make inbox-convert` to produce the pandoc `.md` siblings, then
open a follow-up PR that fills in the ✳ sections and flips `status`
to `proposed` for governance review.

## Context

**✳ Source of truth — the architecture narrative from the docx ADR.**

This section should capture:

1. Why UIAO needs self-hosted Git infrastructure (the boundary
   constraint that makes GitHub SaaS insufficient — GCC-Moderate,
   air-gapped, or customer-owned source-control substrate).
2. Why Windows Server 2025 + IIS was selected as the host platform
   (likely: existing Windows operator skillset, AD-joined host for
   Kerberos auth, IIS URL Rewrite for the smart-HTTP backend).
3. Where Git sits in the UIAO substrate manifest — is it a new
   substrate module peer to `core/`/`docs/`, or a satellite service
   referenced by both?

Provenance: the pandoc-converted narrative from the docx ADR lands
at `inbox/UIAO Git Infrastructure — Architecture Decision Record.md`.
Quote the relevant passages into this section with a provenance
footnote, don't copy-paste the whole file.

## Decision

**✳ Populate from docx ADR §Decision.**

Expected decision axes (from filename hints):

- **Host platform**: Windows Server 2025.
- **Web front-end**: IIS with `git http-backend.exe` via CGI /
  `ApplicationRequestRouting`.
- **Authentication**: likely Active Directory Kerberos for internal
  operators; an OAuth bridge for cross-boundary federation is a TBD.
- **Storage**: NTFS-backed bare repositories under a governed path
  (probably `D:\git\` or similar; the impl guide will specify).
- **Identity model**: AD-joined service account for the IIS app pool;
  per-repo ACLs layered via NTFS + Git pre-receive hooks.
- **Backup / DR**: volume shadow copy + off-host replication (method
  TBD from impl guide §DR).
- **Boundary**: GCC-Moderate. No public internet exposure for the
  canonical instance.

## Consequences

**✳ Populate from docx ADR §Consequences.**

Expected positives:

- Canonical source control sits inside the tenant's compliance
  boundary; no SaaS dependency for code substrate.
- AD-joined auth means operator SSO is free.
- IIS gives deterministic TLS + request logging (CA-7 telemetry).

Expected negatives / mitigations:

- Single-host failure domain — needs DR playbook (from impl guide).
- Windows-only operator story — any Linux contributor needs Git
  over HTTPS with PAT, not Kerberos. Plan for mixed-client auth.
- Hot-standby replication may need a separate ADR if the trade-off
  between cost and RTO lands somewhere contentious.

## Alternatives considered

**✳ Populate from docx ADR §Alternatives.**

Likely alternatives the docx ADR rejects:

- Bitbucket Data Center, GitLab self-managed, Gitea, Gogs — all
  viable but carry separate operator skillsets.
- GitHub Enterprise Server — fits the boundary requirement but
  moves operator skillset outside the Windows estate.
- Azure DevOps Services — SaaS, excluded by boundary.
- Plain bare repos over SSH — rejected for lack of URL-based
  access-control granularity IIS + hooks provide.

## Implementation

**✳ Pointer section** — detailed steps live in:

- `docs/docs/ops/git-server/iis-installation.md` (to be produced
  from the Windows-Server-2025 step-by-step guide).
- `docs/docs/ops/git-server/uiao-configuration.md` (to be produced
  from the UIAO-specific impl guide).

Neither target file exists yet; both are follow-ups to this ADR.

## Governance classification

- **Substrate module?** TBD. If Git becomes a first-class substrate
  module, update `src/uiao/canon/substrate-manifest.yaml` with a
  new `git` entry (role: authority | consumer — depends on the
  decision in §Context).
- **Conformance adapter?** Yes — a health-check / evidence-producer
  adapter is planned. See ``uiao-git-server`` entry in
  `src/uiao/canon/adapter-registry.yaml` (registered as `reserved`
  alongside this ADR; promotes to `active` when the impl guide lands).
- **Modernization adapter?** Unlikely — the Git service itself
  doesn't need a change-making adapter if IaC (Terraform / DSC)
  handles provisioning.

## Related work

- ADR-028 — monorepo consolidation (what this Git host will serve).
- ADR-032 — single-package consolidation (same).
- Pending: ADR-042 for the AD Computer Conversion Guide integration
  (orthogonal — different source document, different scope).

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 2026-04-20 | Skeleton created, pending docx extraction | Automation |
