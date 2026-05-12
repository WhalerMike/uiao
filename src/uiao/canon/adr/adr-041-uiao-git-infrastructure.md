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
  - "inbox/UIAO Git Infrastructure — Architecture Decision Record.docx (absent — content synthesized from platform-server-build.qmd v1.2)"
  - "inbox/UIAO Git Server — Windows Server 2025 with IIS Implementation Guide.docx (absent — content synthesized from platform-server-build.qmd v1.2)"
  - "inbox/Git on Windows Server 2025 with IIS — Step-by-Step Implementation Guide.docx (absent — content synthesized from platform-server-build.qmd v1.2)"
---

# ADR-041: UIAO Git Infrastructure — Self-Hosted Git on Windows Server 2025 + IIS

## Status

**DRAFT — populated from canonical implementation guide; awaiting governance review.**

Sections below were originally skeleton placeholders expecting pandoc
extraction from three `.docx` sources in `inbox/`. Those sources are
absent from the repository as of this revision. Until they are
restored, the authoritative narrative is the operational implementation
guide at `docs/customer-documents/platform/platform-server-build.qmd`
(version 1.2, merged via PR #439, Phases 0–14 inlined). Every Decision
clause below maps to a numbered phase in that guide; every Consequence
follows from operational properties asserted there.

Flip `status:` to `proposed` after governance review, then to
`accepted` once the customer-document portal points operators at this
ADR as the binding source.

## Context

UIAO governance requires that every canonical artifact — OrgPath
codebook entries, dynamic-group rules, delegation matrices,
transformation plans, policy libraries, adapter manifests, drift
reports — live as a versioned file with attributable, signed commits.
The cloud boundary for the program is **GCC-Moderate (Microsoft 365
SaaS only)**, with two named Commercial exceptions encoded in
`src/uiao/canon/substrate-manifest.yaml` (Amazon Connect, SailPoint
NERM). Public-internet-only Git hosting (GitHub.com SaaS, Bitbucket
Cloud, GitLab.com) is permitted as an **upstream mirror** for canon
ingest but **not** as the customer-side substrate authority — the
authoritative instance must sit inside the customer's GCC-Moderate
boundary so that every commit, every webhook, and every audit log
remains under the same authorization plane that governs the rest of
the substrate.

That constraint defines the scope of this ADR: choose the host
platform, web front-end, authentication model, storage layout,
identity model, and DR posture for the **on-premises canonical Git
service** that every UIAO deployment runs as its substrate authority.

The choice is forced by three boundary properties:

1. **Tier-0 classification.** The Git service holds the canon — every
   plan, every authorization, every drift signal traces back to a
   commit on it. CIS Level-2, AppLocker, WDAC, Defender for Servers
   Plan 2, and Intune compliance scoping all apply. The host is
   governed identically to a domain controller from a security-baseline
   perspective.
2. **Single source of truth.** Two hosts cannot both be authoritative;
   they would diverge. Replication exists for disaster recovery, not
   active-active load-sharing. Horizontal scale, where required, is
   handled at the target-surface layer (Entra, Intune, Arc) — not by
   fanning out the substrate authority. This is the architectural
   claim asserted by `docs/customer-documents/modernization/client-server-to-hybrid-cloud/01-platform-foundation.qmd:19-26`.
3. **Operator skillset.** The federal customer base already runs
   Active Directory, ADCS, IIS, and Windows Server at scale, with
   AppLocker / WDAC tooling and PowerShell as the lingua franca. A
   Windows-native Git service inherits that operator competence
   directly; a Linux alternative imposes a new operator stack on a
   substrate that the rest of UIAO assumes is Windows-administered.

Where Git sits in the substrate manifest: it is **not** a substrate
module peer to `src/uiao/`, `tests/`, `docs/`, etc. It is a
**satellite service** that hosts the consolidated monorepo and that
the substrate manifest references as the canonical Git URL. The
substrate walker (`uiao substrate walk`) treats it as the
authority-of-record for canon content; the modernization adapters
read and write through it only via signed commits validated by the
server-side hook chain.

## Decision

Authoritative for the implementation: every clause below is enforced
operationally in `docs/customer-documents/platform/platform-server-build.qmd`
Phases 0–14.

- **Host platform.** Single Windows Server 2025 host, Desktop
  Experience, build 26100+. Hardware floor 4 vCPU / 16 GB RAM /
  500 GB on the `D:` data volume. Domain-joined to the legacy AD
  forest and Entra-registered. Hostname `UIAO-GIT01` (or per the
  customer's OrgPath naming convention). One host, not a cluster —
  the substrate is governed, not horizontally scaled.
- **Web front-end.** Microsoft IIS 10+ on the same host, terminating
  HTTPS on `:443`. URL Rewrite 2.1 + Application Request Routing 3.0
  forward all traffic to Gitea on `127.0.0.1:3000`. IIS is the only
  process bound to the public interface; Gitea is not reachable from
  outside the loopback. HSTS, X-Content-Type-Options, X-Frame-Options
  DENY are set at the IIS layer. Build-guide Phases 2, 5.
- **Git service.** Gitea (Windows AMD64 binary, pinned to a 1.21.x LTS
  release in the release manifest at
  `src/uiao/canon/release-manifests/platform-server-v1.2.yaml`).
  Service is registered to a Group-Managed Service Account
  (`corp\svc-uiao-gitea$`). Repositories live under `D:\GitRepos\`
  with NTFS ACLs granting the gMSA `M`odify rights. Git LFS server is
  enabled (`LFS_START_SERVER = true`). Build-guide Phase 4.
- **Authentication.** Dual-source-config inside Gitea, both
  registered via `/api/v1/admin/sources`:
  - **AD LDAPS** (`:636`) against the forest, scoped to the
    OrgPath-governed Users OU, with a least-privilege bind account.
    Maps internal operators to native Gitea identities. Build-guide
    Phase 6.
  - **Entra OIDC** via an app registration in the tenant, redirecting
    to `https://git.uiao.corp/user/oauth2/EntraID/callback` and
    emitting the `groups` claim so dynamic-group membership becomes
    native Gitea team membership without manual reconciliation.
    Build-guide Phase 7.
  Anonymous access is disabled. Self-registration is disabled
  (`DISABLE_REGISTRATION = true`). Sign-in is required to view any
  repo (`REQUIRE_SIGNIN_VIEW = true`).
- **Authorization.** Three Gitea teams on the `uiao` org mapped 1:1
  to OrgTree dynamic groups per UIAO_152 §Pattern 1:
  `OrgTree-IT-INF-PLATFORM-CanonStewards` (Owner),
  `-Contributors` (Write), `OrgTree-IT-INF-Users` (Read). HR-feed
  joiner/mover/leaver events arrive as Gitea permission changes
  within the Entra group-recalculation window (typically < 15 min).
  Build-guide Phase 14.3.
- **Server-side hooks.** Pre-receive, update, and post-receive hooks
  are required on every repo, signed with the enterprise code-signing
  certificate, and live alongside the bare repos in
  `D:\GitRepos\<repo>.git\hooks\`. Enforcement rules: `main` push
  requires CanonStewards membership; no FOUO/For Official Use Only
  markings; canon-file frontmatter validates against the schema;
  filenames match `^UIAO_\d{3}_[\w]+_v\d+\.\d+\.md$`; unsigned `.ps1`
  files are rejected. Build-guide Phase 9.
- **Storage layout.** `D:\Gitea\` for the Gitea binary, `app.ini`,
  data, logs; `D:\GitRepos\` for bare repos (the
  `[repository] ROOT` value); `D:\Gitea\data\lfs\` for LFS chunks.
  Postgres on a separate host (`pg01.corp.contoso.com:5432`,
  database `uiao_gitea`) holds Gitea's relational state. Secrets
  (DB password, internal token, JWT secret) sourced from
  `Microsoft.PowerShell.SecretManagement` / `SecretStore` under the
  gMSA. Build-guide Phases 4.b, 4.d.
- **Identity model.** Gitea runs as the gMSA `svc-uiao-gitea$`. The
  IIS reverse-proxy app pool runs as the built-in
  `ApplicationPoolIdentity`. Operators authenticate as themselves via
  LDAPS or OIDC; service-to-service calls authenticate via signed
  short-lived Gitea API tokens stored in the platform secret vault.
- **Upstream mirror.** A pull-mirror of the canonical GitHub
  repository (`https://github.com/WhalerMike/uiao.git`) is configured
  via the Gitea migrate API with a 15-minute interval. GitHub is the
  source of canon ingest; the on-prem Gitea is the source of canon
  authority. Build-guide Phase 8.
- **Backup / DR.** Nightly `Backup-UIAOGitea` PowerShell function
  quiesces Gitea, runs `gitea dump`, archives `D:\GitRepos\`,
  uploads both to a customer-tenant Azure Blob container under the
  managed identity assigned to the Arc resource, and applies a
  30-day retention policy. RPO target 24 h; RTO target 4 h via cold
  restore into a passive replica. Build-guide Phase 12.
- **Hardening.** CIS Level-2 GPO baseline applied via LGPO; AppLocker
  policy restricts script execution to publisher `CN=UIAO Canon
  Signing`; WDAC enforces UMCI for the same publisher; Defender for
  Servers Plan 2 active; Azure Monitor Agent forwards audit logs to
  the Log Analytics workspace; firewall is domain-profile only with
  deny-by-default outbound except the §0.5 egress allowlist.
  Build-guide Phases 1, 13.
- **Boundary.** GCC-Moderate for all M365 SaaS interactions (Entra,
  Intune, Graph). IaaS resources (Azure Arc, Azure Blob, Log
  Analytics) sit in the commercial-FedRAMP exception scope per
  ADR-059's pattern — recorded explicitly in the boundary frontmatter
  of every artifact this ADR governs. No public-internet inbound to
  the canonical instance.

## Consequences

### Positive

- **Canon stays inside the boundary.** No SaaS dependency for the
  substrate authority. Every commit, every webhook, every server-side
  hook execution sits inside the customer's audit plane.
- **Single audit surface.** One host, one patch cadence, one Intune
  compliance policy, one Arc enrollment, one OrgPath tag. The
  drift-detection engine (UIAO_163) sees a single object to evaluate,
  not a fleet.
- **AD-joined operator SSO is free.** The same Kerberos ticket that
  authorizes a forest read authorizes a Git push. No additional
  identity bridge.
- **Deterministic TLS + request logging.** IIS produces W3C-extended
  logs with the authenticated principal on every request, which feeds
  CA-7 telemetry directly.
- **OrgTree-native team mapping.** Entra group claims arrive as Gitea
  team membership; HR-feed mover events propagate to repo permissions
  in < 15 min without operator intervention.
- **Bounded supply chain.** Every binary in the build (PowerShell,
  Git, Gitea, the four IIS extension MSIs, Visual C++ runtime,
  Azure Arc agent) is pinned by version + SHA-256 in the release
  manifest, sourced from documented GitHub-Releases or Microsoft-CDN
  URLs, and consumable from an internal mirror in proxy-restricted
  environments.

### Negative / mitigations

- **Single-host failure domain.** Mitigated by the documented Phase
  12 backup + manual failover playbook; a hot-standby replica is a
  follow-up ADR if the 4-hour RTO is insufficient for a given
  customer.
- **Windows-only operator story.** Linux contributors authenticate
  via Entra OIDC + Git HTTPS with a Gitea PAT, not Kerberos. The
  source-config in Phase 7 covers this.
- **Gitea LTS dependence.** Tied to the Gitea project's release
  cadence. Mitigated by pinning to LTS in the release manifest and
  validating each upgrade against the canon-validation test suite
  before promotion. Forking Gitea is explicitly out of scope.
- **Two-domain identity surface.** The host is simultaneously
  AD-joined (legacy) and Entra-registered (modern). Until the AD
  forest is retired (a separate, long-horizon program), the platform
  server straddles both authorities. Mitigated by the read-only AD
  side per `01-platform-foundation.qmd:104-108`.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Option A — IIS + `git-http-backend.exe` (CGI) without Gitea** | No web UI, no native LFS, no built-in OIDC, no team/group semantics, hand-rolled hook chain. Auth-integration and operational-complexity costs documented as Option A in `platform-server-build.qmd` Appendix A. Retained as a lab/reference build at `docs/customer-documents/platform/git-server-implementation.qmd`. |
| **GitHub Enterprise Server (on-prem appliance)** | Fits the boundary, but introduces a non-Windows operator stack (Linux appliance, GHES upgrade ladder) and a vendor licensing dependency that the rest of the substrate does not have. Cost/skillset asymmetry vs. the Windows-native Gitea pattern. |
| **Bitbucket Data Center / GitLab self-managed** | Both viable, both Linux-first. Same operator-stack objection as GHES, plus heavier infrastructure footprint (Bitbucket needs a clustered DB; GitLab needs Redis, Sidekiq, NGINX, Puma, …). Overkill for a substrate-authority workload sized at one host. |
| **Azure DevOps Services (SaaS)** | Excluded by boundary — same reason GitHub SaaS cannot serve as the substrate authority. ADO Server (on-prem) is retired post-2020 and not a future-proof choice. |
| **Plain bare repos over SSH** | No URL-based access-control granularity, no audit log of read operations, no LFS unless bolted on, no OIDC. Acceptable for an emergency offline mirror; not acceptable as the substrate authority. |
| **Gogs (Gitea predecessor)** | Maintenance and security cadence inferior to Gitea; Gitea forked Gogs precisely to address this. No reason to choose the upstream over the fork. |

## Implementation

Authoritative implementation reference:

- **Customer-document portal:**
  `docs/customer-documents/platform/platform-server-build.qmd`
  (Phases 0–14, including Phase 0 Prerequisites, Phase 0.5 Egress
  Allowlist, and Appendix A Option-A/B reconciliation).
- **Reference Option A (rejected, retained for lab use):**
  `docs/customer-documents/platform/git-server-implementation.qmd`.
  Carries an Option-A banner pointing back to this ADR.
- **Release manifest:**
  `src/uiao/canon/release-manifests/platform-server-v1.2.yaml`
  pins every binary, URL, and SHA-256 the build depends on.
- **Conformance adapter:** `uiao-git-server` (entry already present
  in `src/uiao/canon/adapter-registry.yaml:399`, status `reserved`).
  Promote to `active` once the adapter Python module ships under
  `src/uiao/adapters/`.

The earlier draft of this ADR referenced two `docs/docs/ops/git-server/...`
files as the implementation home; that path is superseded by the
customer-document portal location above.

## Governance classification

- **Substrate module?** No — Git is a satellite service that hosts
  the consolidated monorepo, not a peer of `src/uiao/`, `tests/`,
  or `docs/`. No edit to `src/uiao/canon/substrate-manifest.yaml`
  is required by this ADR.
- **Conformance adapter?** Yes — `uiao-git-server` is registered as
  `reserved` in `adapter-registry.yaml`. The adapter will produce
  `git-server-health.json`, `git-tls-inventory.json`, and
  `git-repo-inventory.json` as evidence outputs.
- **Modernization adapter?** No — provisioning is handled by the
  PowerShell runbook in the build guide and (eventually) by
  Azure-Arc-projected Guest Configuration. No change-making adapter
  needed.
- **Document registry entry?** This ADR is the registry anchor;
  no new `UIAO_NNN` allocation required. The customer-facing build
  guide carries its own `doc-id: UIAO_SBG_001`.

## Related work

- **ADR-028** — monorepo consolidation (defines what this Git host
  serves: the single `WhalerMike/uiao` repository).
- **ADR-032** — single-package consolidation (same).
- **ADR-059** — IaaS commercial-FedRAMP exception pattern that this
  ADR's Azure Arc / Blob / Log Analytics dependencies inherit.
- **Pending: ADR-042** — AD Computer Conversion Guide integration
  (orthogonal scope; different source document).
- **Pending follow-up ADR** — hot-standby replication if a customer
  requires sub-4-hour RTO.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 2026-04-20 | Skeleton created, pending docx extraction | Automation |
| 0.2 | 2026-05-12 | Sections populated from `platform-server-build.qmd` v1.2 (PR #439); docx sources noted as absent; status remains `draft` pending governance review | Claude Code via `claude/assess-server-github-integration-bKTO3` |
