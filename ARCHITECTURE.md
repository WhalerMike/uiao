# UIAO Customer Documentation Platform — Architecture

> **Status:** NEW (Proposed) — pending sign-off
> **Canonical location (proposed):** `uiao-core/ARCHITECTURE.md`
> **Scope:** End-to-end architecture for the UIAO Customer Documentation platform spanning the federal pair — `uiao-core` (canonical authority) and `uiao-docs` (derived publication surface).
> **Out of scope:** `uiao-gos` — a separate commercial product with its own companion architecture document (`uiao-gos/ARCHITECTURE.md`). No canon, tooling, secrets, or workflows are shared between the federal pair and `uiao-gos`.
> **Authoring convention:** Per UIAO No-Hallucination Protocol, proposed artifacts are marked `NEW (Proposed)`, unknowns are marked `UNSURE`, and gaps are marked `MISSING`.

---

## 1. Purpose

Define the canonical architecture, governance contracts, compliance posture, and operational mechanics of the Customer Documentation platform for the federal-government offering. This document is the single source of truth for how `uiao-core` and `uiao-docs` coordinate to produce FedRAMP-Moderate-appropriate customer-facing documentation, and for how on-prem production in Azure Government is reached from GitHub-based development.

This document **does not** cover `uiao-gos`. See `uiao-gos/ARCHITECTURE.md` for the commercial product's governance model.

## 2. Repository topology

| Repo | Role | Authority | Compliance Posture | Contents |
|---|---|---|---|---|
| `WhalerMike/uiao-core` | Canonical governance | Authoritative | FedRAMP Moderate | State machines, enforcement rules, canon manifests, playbooks, appendices |
| `WhalerMike/uiao-docs` | Derived publication | Consumer of canon | FedRAMP Moderate | Articles, guides, customer-documents tree, rendered Quarto site |
| `WhalerMike/uiao-gos` | **Out of scope** | Commercial product | Commercial — no federal controls | See `uiao-gos/ARCHITECTURE.md` |

### 2.1 Compliance posture (federal pair)

The `uiao-core` + `uiao-docs` pair is designed to be offered free of charge to U.S. Government agencies under FedRAMP-Moderate-compatible constraints:

- **FedRAMP Moderate** — system categorization
- **NIST SP 800-53 Rev 5** — control baseline, moderate impact tailoring
- **CISA BOD 25-01** — emergency directive compliance for covered assets
- **CISA SCuBA** — Microsoft 365 Secure Configuration Baselines enforced
- **Cloud boundary** — GCC-Moderate (Microsoft 365 SaaS only)
- **Microsoft GCC-Moderate inheritances** — telemetry, location data, and dashboard restrictions inherited from the GCC-Moderate tenant boundary
- **Exception** — Amazon Connect Contact Center operates in Commercial Cloud per existing UIAO exception

### 2.2 Firewall between federal and commercial

`uiao-gos` is explicitly firewalled from the federal pair:

- **No canon sync** in either direction
- **No shared secrets** — each repo has its own `GEMINI_API_KEY` and PAT tokens
- **No cross-referenced artifacts** — the federal pair must not reference `uiao-gos` content, and vice versa
- **No shared workflows** — CI/CD pipelines are independent
- **No shared branding language** — the federal offering uses federal-specific terminology; `uiao-gos` uses commercial-neutral terminology

Violation of the firewall is CI-blocking via the `firewall-check` workflow (see §9).

## 3. Canon registry mechanism

Every piece of canon that `uiao-docs` must mirror is declared in a machine-readable manifest in `uiao-core`. Nothing downstream ever hardcodes an adapter name or domain identifier — all structure is derived from the registry.

### 3.1 Registry files

```
uiao-core/canon/
├── adapter-registry.yaml         # canonical list of every adapter
├── modernization-registry.yaml   # canonical list of every modernization domain
└── registry-schema.json          # JSON Schema for both manifests (validation)
```

### 3.2 Adapter registry schema (NEW, Proposed)

Two adapter classes are supported. `modernization` adapters are migration/change workers. `conformance` adapters are read-only assessment/continuous-monitoring workers (see §16). Both live in the same registry and share a common identity/provenance shape; additional fields are class-specific.

```yaml
schema-version: 1.1
adapters:
  # Modernization class — migration/change workers
  - id: entra-id
    class: modernization          # modernization | conformance
    display-name: Microsoft Entra ID
    status: active                # active | proposed | deprecated
    cloud-boundary: gcc-moderate
    canonical-source: canon/adapters/entra-id.md
    docs-required:
      - adapter-technical-specifications
      - adapter-validation-suites
    added: 2026-01-15

  # Conformance class — assessment / ISCM workers (see §16)
  - id: scubagear
    class: conformance
    display-name: CISA ScubaGear (M365 SCuBA baseline)
    status: proposed
    cloud-boundary: gcc-moderate
    vendor: cisa
    license: CC0                  # UNSURE — verify LICENSE in cisagov/ScubaGear
    runtime: powershell
    scope: [entra, exchange, sharepoint, teams, power-platform, defender-o365]
    policy-engine: opa-rego
    outputs: [report-html, findings-json, poam-csv]
    triggers:
      - schedule: monthly         # FedRAMP ConMon cadence
      - event: post-migration     # repository_dispatch after modernization adapter completes
    evidence-class: iscm-automated
    canonical-source: canon/adapters/scubagear.md
    added: 2026-04-14
```

### 3.3 Modernization registry schema (NEW, Proposed)

```yaml
schema-version: 1.0
domains:
  - id: identity
    display-name: Identity Modernization
    status: active
    canonical-source: canon/modernization/identity.md
    docs-required:
      - modernization-technical-specifications
      - modernization-validation-suites
    added: 2026-01-15
```

### 3.4 Seeded entries — modernization class (from existing scaffold)

Adapter registry: `entra-id`, `m365`, `service-now`, `palo-alto`, `scuba`.
Modernization registry: `identity`, `telemetry`, `sdwan`, `sase`, `zero-trust`, `cloud`.

**Naming clarification (UNSURE, requires owner decision):** The seeded `scuba` adapter represents the SCuBA *baseline configuration as a target state* (a landing-zone target). The NEW `scubagear` conformance adapter in §3.5 represents the CISA *assessment tool* that verifies conformance to that baseline. These are adjacent but distinct. If retained, the `scuba` modernization adapter documents the target configuration; `scubagear` documents the automated verification of it.

### 3.5 Seeded entries — conformance class (NEW, Proposed)

Four conformance adapter slots are proposed to establish ISCM coverage. Only `scubagear` is scheduled for v1 implementation; the other three are slots reserved for adapters the program will need to satisfy broader NIST SP 800-137 capability coverage (see §15 ISCM capability matrix and §16.5 adapter roadmap).

| Adapter ID | Class | Status | Scope | ISCM Capability Coverage | Phase |
|---|---|---|---|---|---|
| `scubagear` | conformance | proposed (v1) | M365 control plane | Config Mgmt, IAM | Phase 1 |
| `vuln-scan` | conformance | slot-reserved | RHEL/Rocky/Alma hosts (Phase 3+) | Vuln Mgmt, Patch Mgmt | Phase 3 |
| `stig-compliance` | conformance | slot-reserved | OS + Apache httpd | Config Mgmt (host-level) | Phase 2–3 |
| `patch-state` | conformance | slot-reserved | OS + M365 tenant | Patch Mgmt, Software Assurance | Phase 2 |

Additional slots (malware detection, network monitoring, asset inventory, license mgmt) remain unplanned — see §15 ISCM capability matrix for the gap set.

## 4. Cross-repo sync — three-layer defense in depth

### 4.1 Layer 1 — Real-time push (`repository_dispatch`)

On merge to `uiao-core` main branch that modifies either registry manifest, workflow `canon-sync-dispatch.yml` fires a `repository_dispatch` event of type `canon-updated` to `uiao-docs` with the diff payload. `uiao-docs` workflow `canon-sync-receive.yml` consumes the event, runs `tools/sync_canon.py`, and opens a labeled PR (`canon-sync`) with scaffolded additions and drift annotations.

**Propagation SLO:** under 5 minutes from canon merge to pending `uiao-docs` PR.

### 4.2 Layer 2 — Scheduled drift scan

Nightly workflow `drift-scan-nightly.yml` in `uiao-docs` fetches both registry manifests via GitHub API (no submodule required), compares against the on-disk `customer-documents/` tree, and reports:

- **Additive drift** — registry entry without corresponding docs folder
- **Orphan drift** — docs folder without registry entry
- **Status mismatch** — registry `status` ≠ doc YAML frontmatter `status`

Report posts as commit status and opens a tracking issue if non-zero.

### 4.3 Layer 3 — PR-gate drift check

CI check `drift-scan` runs on every PR to `uiao-docs`. Executes `sync_canon.py --check-only` and fails the build if the PR leaves `uiao-docs` out of sync with the current `uiao-core` canon. This is the enforcement gate that makes drift unmergeable.

## 5. Customer documentation tree

### 5.1 Top-level layout

```
uiao-docs/docs/customer-documents/
├── index.qmd                         # Master Document (landing page)
├── MASTER-IMAGE-PROMPTS.md           # generated aggregator
├── MASTER-IMAGE-INDEX.md             # generated catalog with thumbnails
├── .image-manifest.json              # machine-readable prompt→file map
├── _tools/                           # generation scripts
├── _assets/                          # shared styles + theme overrides
├── adapter-technical-specifications/
├── adapter-validation-suites/
├── modernization-technical-specifications/
├── modernization-validation-suites/
├── executive-governance-series/
├── executive-briefs/
├── architecture-series/
├── case-studies/
└── whitepapers/
```

### 5.2 Per-document layout (leaf pattern)

Every document folder carries the triad `qmd + IMAGE-PROMPTS.md + images/`:

```
<document>/
├── <document>.qmd        # content with {{IMAGE:N}} placeholders + provenance frontmatter
├── IMAGE-PROMPTS.md      # prompts for this doc (schema §7.2)
└── images/
    ├── .gitkeep
    ├── image-01-<slug>.png      # NanoBanana raw output
    ├── image-01-<slug>.webp     # web-optimized
    └── image-01-<slug>.thumb.webp  # thumbnail for Front Door index
```

### 5.3 YAML frontmatter convention

Every `.qmd` carries:

```yaml
---
artifact-id: <family>-<slug>
version: 0.1.0
status: draft                    # draft | review | locked
provenance: uiao-core/canon/<source>.md
cloud-boundary: gcc-moderate
images:
  regeneration-policy: auto-on-hash-change
  freeze-on-status: locked
---
```

## 6. Versioning and release-lock policy

| Status | Images regenerate on prompt-hash change? | Canon sync can modify? | Version bump required to change? |
|---|---|---|---|
| `draft` | Yes | Yes | No |
| `review` | Yes | Yes | No |
| `locked` | **No** | **No** | **Yes** |

**Lock semantics:** When a doc flips to `status: locked`, (a) CI refuses to regenerate its images, (b) canon sync refuses to modify its frontmatter or structure, and (c) any subsequent content change requires a `version` bump and a corresponding git tag. The LFS-committed image bytes become the canonical frozen record.

**Drift-scan enforcement:** A `locked` document with uncommitted prompt changes or stale image hashes produces a CI failure.

## 7. Image generation pipeline

### 7.1 Model and SDK

- **Primary model:** Gemini NanoBanana via `google-genai` SDK (`pip install google-genai`)
- **Default model string:** `gemini-3.1-flash-image-preview` — **UNSURE**, verify against current Gemini image-gen GA string at build time
- **API key source:** `GEMINI_API_KEY` environment variable (read from GitHub Actions secret in CI; from `.env` locally via `python-dotenv`)
- **Never** a literal in source code. Prior key leaked in uploaded template has been flagged for revocation.

### 7.2 `IMAGE-PROMPTS.md` schema (NEW — extends existing pattern)

```markdown
# Image Prompts — <Document Title>

**Doc-ID:** <artifact-id>
**Style guide:** Federal government whitepaper — muted navy/gray/white, no stock photos, no people unless abstracted.

---

## Image 1: <Title>

**Placement:** <where in the document>

**Alt-text:** <Section 508-compliant alt text, 1-2 sentences>

**Prompt:**
<full prompt text, multiline>

---
```

Two fields added to the existing pattern (`Doc-ID`, `Alt-text`). `Doc-ID` enables aggregation provenance. `Alt-text` satisfies Section 508 federal accessibility requirements — mandatory for federal customer deliverables.

### 7.3 `MASTER-IMAGE-PROMPTS.md` (generated)

Aggregator walks every `IMAGE-PROMPTS.md` under `customer-documents/`, emits a single master file at `customer-documents/MASTER-IMAGE-PROMPTS.md` grouped by document, with back-links to source. Regenerated by `tools/aggregate_prompts.py` on every merge to main via `master-prompts-sync.yml` workflow. Hand-editing is CI-blocked.

### 7.4 Prompt-hash caching

`.image_hashes.json` (one per document's `images/` folder) stores `{image-N: sha256-prefix}` keyed on prompt text. The generation script skips any image whose current prompt hash matches the cache — guarantees deterministic regeneration only when a prompt genuinely changed. This cache file is committed (not gitignored) so hash identity is reproducible across clones.

### 7.5 Output formats

Three variants per image, committed via Git LFS:

| Format | Purpose | Source | Size target |
|---|---|---|---|
| PNG | Source of truth from NanoBanana, never edited | Gemini API | ~500KB–2MB |
| WebP | Served on Front Door | Pillow conversion | ~30% of PNG |
| Thumbnail WebP | Master index, search cards | Pillow, max 400px | <50KB |

## 8. Storage strategy — Architecture C (Git LFS)

**Decision:** Generated images are committed to `uiao-docs/main` via Git LFS. Rationale:

- Self-contained repo (clone works offline, no external blob dependency)
- Clean audit trail per governance requirements (every image revision is a git object — satisfies NIST 800-53 AU-2, AU-3)
- LFS pointers keep main clone fast (~tens of KB per image pointer vs. MB for binary)
- Tagged release freezes exact bytes by content hash (supports immutable-evidence principle)

### 8.1 `.gitattributes` routing

```
customer-documents/**/*.png  filter=lfs diff=lfs merge=lfs -text
customer-documents/**/*.webp filter=lfs diff=lfs merge=lfs -text
```

### 8.2 LFS quota posture

- GitHub Team includes 1 GB LFS storage + 1 GB/month bandwidth (same baseline as Pro)
- Projected load: ~49 docs × ~6 images × 3 variants ≈ 900 files, estimated 1–2 GB total at maturity
- **Escalation:** $5/month 50 GB data pack when `lfs_budget_check.py` reports >80% of current ceiling
- `tools/lfs_budget_check.py` runs on every PR, posts usage to commit status

## 9. CI/CD workflows

| Workflow | Repo | Trigger | Purpose |
|---|---|---|---|
| `canon-sync-dispatch.yml` | uiao-core | merge to main touching `canon/*-registry.yaml` | Fire `repository_dispatch` to uiao-docs |
| `canon-sync-receive.yml` | uiao-docs | `repository_dispatch: canon-updated` | Run `sync_canon.py`, open PR |
| `drift-scan-nightly.yml` | uiao-docs | schedule (daily) | Compare tree vs. manifests, report drift |
| `drift-scan-pr.yml` | uiao-docs | PR | Block merge on drift |
| `image-regeneration.yml` | uiao-docs | PR touching `IMAGE-PROMPTS.md` | Regenerate changed images, commit back to PR branch |
| `master-prompts-sync.yml` | uiao-docs | merge to main | Rebuild `MASTER-IMAGE-PROMPTS.md` |
| `quarto-build.yml` | uiao-docs | merge to main, release tag | Render site, publish to GitHub Pages |
| `lfs-budget-check.yml` | uiao-docs | PR, weekly schedule | Report LFS quota consumption |
| `firewall-check.yml` | uiao-core, uiao-docs | PR | Block any PR that references `uiao-gos` content or identifiers |
| `conformance-run.yml` | uiao-core | `repository_dispatch: modernization-completed`, manual | Execute named conformance adapter (e.g. ScubaGear) against target tenant; commit findings to `evidence/conformance/<adapter>/<run-id>/` |
| `conmon-scheduled.yml` | uiao-core | schedule (monthly, 1st at 0200 UTC) | Fan-out all `class: conformance, status: active` adapters; aggregate outputs |
| `conmon-aggregate.yml` | uiao-core | after `conformance-run.yml` or `conmon-scheduled.yml` | Roll findings into POA&M CSV + dashboard JSON; open tracking issues on regressions |

Secrets required in `uiao-docs` Actions: `GEMINI_API_KEY`. Secrets required in `uiao-core` Actions: `CANON_DISPATCH_TOKEN` (fine-grained PAT with contents:write and metadata:read scope on `uiao-docs`) for cross-repo `repository_dispatch`; `SCUBAGEAR_TENANT_APP_ID` + `SCUBAGEAR_TENANT_APP_SECRET` (service principal with read-only Graph scopes) for `conformance-run.yml`. See §16.6 for secret handling and §16.8 for runner strategy.

## 10. GitHub plan posture — revised for FedRAMP context

| Dimension | Decision |
|---|---|
| Current tier | GitHub Pro ($48/yr) |
| **Recommended tier** | **GitHub Team (~$4/user/month) — UNSURE on exact 2026 pricing** |
| Rationale | Audit log API at org level, required reviews, protected-branch enforcement — primitives FedRAMP auditors expect for NIST 800-53 AU and CM controls. Pro lacks these. |
| Copilot decision | Deferred. Copilot Business ($19/user/month, UNSURE on 2026 pricing) if adopted — has content exclusions, no-training-on-your-data, IP indemnity. **Copilot Individual is inappropriate** for federal source material. |
| Actions budget | Team quota sufficient for projected workload (50–200 min/month) |
| LFS budget | 1 GB included; add 50 GB data pack ($5/mo) when budget-check alerts |
| Upgrade to Enterprise | Only if SAML SSO, SCIM provisioning, or IP allow-lists become compliance requirements |

**Federal authorization caveat (UNSURE):** GitHub's current FedRAMP authorization status as of April 2026 has not been verified by the author of this document. Historically GitHub Enterprise Cloud held FedRAMP Tailored LI-SaaS (Low); Moderate authorization was being pursued. **Verify at `marketplace.fedramp.gov`** before formally positioning GitHub as the authorization boundary for federal customer workloads. See §13 Item 7.

**Long-term posture:** GitHub is the **development** surface. Production authorization for federal customers inherits from **Azure Government** (see §12) — not from GitHub. This is why the on-prem migration is not optional; it is the compliance path.

## 11. Rendering stack — Quarto-canonical

**Decision:** Quarto is the single rendering stack for customer documentation.

| Output | Path | Notes |
|---|---|---|
| HTML (Front Door site) | Published to GitHub Pages (dev) → Azure Gov static site (prod) | Pagefind client-side search; card-grid landing page |
| PDF | Per-document or per-family | Custom LaTeX template, cover page, federal branding |
| DOCX | Customer contract deliverables | Style-mapped to agency template |
| PPTX | **Authored separately** via Cowork `pptx` skill | Quarto's pptx output is not presentation-quality |

### 11.1 Diagram tracks (three, by content type)

| Track | Use for | Toolchain |
|---|---|---|
| Mermaid | Simple flows <10 nodes, sequence diagrams, state machines, gantt | `.mmd` source → SVG at build |
| Gemini NanoBanana | Conceptual / hero illustrations | Image generation pipeline §7 |
| Draw.io (diagrams.net) | Architecturally precise diagrams (six-plane, boundary impact, drift engine, evidence chain) | `.drawio` XML source in git → SVG export |

**Phased adoption:** Start with Mermaid + Gemini to collect signal. Adopt draw.io for specific architectural diagrams when Mermaid layout quality proves insufficient. All three tracks render cleanly to HTML and PDF via Quarto.

### 11.2 Mermaid scaling — known limitations

Mermaid's dagre/ELK auto-layout engines produce poor layouts above ~15 nodes, cannot manually override edge routing, and rasterize inconsistently across PDF output. These are **structural** limitations, not definition-quality issues. Mitigation: keep Mermaid diagrams simple; move to draw.io or Gemini when structural precision matters.

## 12. On-prem production migration roadmap — Azure Government

### Phase 0 — GitHub-only (current, weeks 0–2)
All authoring, CI, and publication in GitHub. Quarto renders via `quarto-build.yml` to GitHub Pages. Images in LFS. Source of truth: `github.com/WhalerMike/uiao-docs`. GitHub Team tier for audit primitives.

### Phase 1 — Azure Government read mirror (weeks 3–4)
**Target region:** US Gov Virginia or US Gov Arizona (pick for latency to primary customer set).
**Base image:** Azure Government Marketplace → **Rocky Linux 9** or **RHEL 9** hardened image.
**Setup:** Bare mirror clone of `uiao-docs` via `git clone --mirror`. Periodic `git fetch --all --prune` via systemd timer, plus GitHub webhook for immediate post-push sync. `git lfs fetch --all` pulls LFS objects. Read-only; GitHub remains the write surface.
**Network:** Private VNet with restricted egress to `github.com` only; no inbound from internet yet.

### Phase 2 — Azure Government site serving (weeks 5–6)
**Apache httpd** on the same (or sibling) hardened Linux VM, FIPS 140-3 mode, SELinux enforcing, STIG-compliant vhost config per DISA Apache HTTP Server 2.4 STIG.
**Authorization:** Azure Government inherits FedRAMP High from the platform; the VM-level ATO is composed via the selected Linux base + Apache httpd + your own application controls.
**TLS:** Federal PKI certificate via agency-issued CA or DoD CA depending on customer. Azure Government Certificate Authority integration available.
**Static Quarto output:** Built via GitHub Actions, rsynced over SSH to Azure Government VM on every release tag. Nginx documented as alternative.
**Nginx alternative:** Documented for completeness; same STIG compatibility via DISA Nginx STIG (UNSURE — verify publication state).

### Phase 3 — Flip the canonical direction (weeks 8–12)
**Canonical Git host:** Gitea or GitLab CE installed on Azure Government VM. Configure GitHub as push mirror (reverse of Phase 1). This satisfies the federal compliance pattern where a third-party SaaS cannot be authoritative for the federal ATO boundary.
**Access:** Developer access via Azure Government B2B guest or agency-issued identities; no direct internet exposure.
**Decision trigger:** Flip before first federal customer ATO submission.

### Phase 4 — Full air-gap (conditional, later)
Customer-specific. Azure Government tenant seeded from one-time export to customer's isolated tenant. Developers VPN in via agency-approved path. No inbound/outbound internet dependency at the customer boundary.

### Key architectural observation
For a static Quarto site, the production server does not need Git running at all — it only needs the rendered HTML/CSS/JS/images. Git on prod is only useful if (a) the Azure Gov box also serves as a Git server for developers, or (b) audit requires a Git log independent of GitHub. Phase 3 addresses case (b).

**Follow-on document:** `uiao-docs/customer-documents/runbook/on-prem-migration.qmd` — full commands, systemd unit files, Apache vhost configs, DISA STIG hardening checklist, Azure Government tenant setup procedure, air-gap validation procedure. To be authored after Phase 0 (GitHub build) is stable.

## 13. Open decisions

| # | Decision | Owner | Resolution needed by |
|---|---|---|---|
| 1 | ~~`uiao-gos` role~~ **RESOLVED** — Out of scope (commercial, separate architecture doc) | — | — |
| 2 | ~~Specific draw.io adoption trigger~~ | Michael | Before architecture-series authoring |
| 3 | LFS data pack purchase trigger threshold | Michael | When budget-check first alerts (~800 MB) |
| 4 | Customer-specific branding overrides (LaTeX/CSS per agency) | Michael | When first customer deliverable is scoped |
| 5 | Air-gap requirement — deferred to actual customer request | — | Phase 4 trigger |
| 6 | Copilot Business adoption | Michael | Deferred — revisit at team size growth or production code landing |
| 7 | **Verify GitHub FedRAMP authorization state (2026)** — check FedRAMP Marketplace | Michael | Before positioning GitHub as authorization boundary |
| 8 | ~~Azure Gov vs AWS GovCloud~~ **RESOLVED** — Azure Government | — | — |
| 9 | Specific Azure Gov region (Virginia vs Arizona vs DoD) | Michael | Before Phase 1 execution |
| 10 | Gitea vs GitLab CE for Phase 3 on-prem canonical | Michael | Before Phase 3 execution |
| 11 | ScubaGear license text confirmation (LICENSE file in cisagov/ScubaGear) | Michael | Before v1 implementation of `adapter.scubagear` |
| 12 | Disposition of the seeded `scuba` modernization adapter vs new `scubagear` conformance adapter (keep both, rename, or merge — see §3.4 note) | Michael | Before Phase 1 execution |
| 13 | Self-hosted Windows runners in Azure Government: resource group, VM SKU, hardening baseline, secret-broker pattern | Michael | Before Phase 3 execution |
| 14 | Conformance adapter slot expansion beyond v1 (vuln-scan, stig-compliance, patch-state) — sequencing and tool selection (e.g. Tenable vs OpenSCAP) | Michael | Before Phase 2 execution |

## 14. Change log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-14 | 0.1.0 | Initial draft (NEW, Proposed) — captures scaffold, canon registry, cross-repo sync, image pipeline, LFS, Quarto, versioning, CI workflows, on-prem migration roadmap | Claude (Cowork) |
| 2026-04-14 | 0.2.0 | FedRAMP posture integration: explicit compliance mapping (§15), firewall with `uiao-gos` (§2.2), Team tier recommendation (§10), Azure Government as on-prem target (§12), federal PKI/TLS, STIG references, resolved decisions tracked in §13 | Claude (Cowork) |
| 2026-04-14 | 0.3.0 | Continuous monitoring program: Conformance Adapter class introduced (§3.2, §3.5); three new workflows (§9); NIST SP 800-137 ISCM capability matrix added (§15); new §16 Continuous Monitoring Program; four open decisions added (§13 items 11–14); pointer to standalone `CONMON.md` for full operational detail | Claude (Cowork) |
| 2026-04-14 | 0.4.0 | Source verification pass. Two authority PDFs placed at `compliance/reference/nist-sp-800-137/` and `compliance/reference/fedramp-conmon-playbook/` with provenance READMEs and SHA-256 checksums. §15.2 corrected to canonical 11 security automation domains (added Incident Management; corrected IAM placement). §16.2 lifecycle citations added verbatim from 800-137 §§3.1–3.6. §16.3 cadence table rebuilt against Playbook v1.0 (2025-11-17) with control citations (CA-5, CM-8, RA-5, SI-2, CM-3, CM-4, CA-2). §16.9 updated with verified/UNSURE split and five newly-surfaced requirements from verified Playbook read | Claude (Cowork) |

## 15. Federal compliance mapping

The architectural choices in this document map to NIST SP 800-53 Rev 5 control families as follows. This section is advisory — formal control mapping belongs in the SSP, not here — but provides the auditor-facing rationale for each choice.

| Control Family | Architectural Choice | Rationale |
|---|---|---|
| **AC** — Access Control | GitHub Team protected branches + required reviews; Azure Gov identity-based access in Phase 1+ | Enforces least-privilege and separation of duties |
| **AU** — Audit and Accountability | GitHub org audit log (Team tier); git commit history with LFS content hashes; draft/review/locked lifecycle | Every document and image change is attributable and timestamped |
| **CM** — Configuration Management | Canon registry (§3); three-layer sync (§4); `drift-scan` CI gate; semantic versioning with git tags | Baseline managed as code; deviations detected and blocked |
| **CP** — Contingency Planning | Mirror to Azure Gov (Phase 1); air-gap option (Phase 4); LFS content-addressable storage | Supports recovery and continuity requirements |
| **IA** — Identification and Authentication | GitHub + Azure Gov identity; federal PKI for TLS (Phase 2) | Authorized user identification at all tiers |
| **RA** — Risk Assessment | Release-lock policy (§6); firewall-check workflow (§9) | Frozen locked content prevents unauthorized changes; firewall prevents scope creep |
| **SA** — System and Services Acquisition | Open-source toolchain (Quarto, Apache, Rocky/RHEL); OSS licensing tracked per dependency | Supply-chain transparency |
| **SC** — System and Communications Protection | FIPS 140-3 mode on Apache (Phase 2); TLS via federal PKI; Azure Gov boundary | Cryptographic protections consistent with federal requirements |
| **SI** — System and Information Integrity | Prompt-hash caching (§7.4); LFS content-addressability; CI-enforced drift-scan | Integrity of generated content is detectable and verifiable |

**Section 508 Accessibility:** `Alt-text` field required in every `IMAGE-PROMPTS.md` entry (§7.2) ensures alt-text exists for every customer-facing image at authoring time, not retrofitted.

### 15.2 NIST SP 800-137 security automation domain coverage (VERIFIED against source 2026-04-14)

NIST SP 800-137 Appendix D, §D.1 (September 2011), page D-3, enumerates **eleven security automation domains** that support continuous monitoring. This matrix declares which domains the planned conformance adapter set will satisfy versus the remaining gap. Terminology aligned to source document.

**Source:** NIST Special Publication 800-137, Appendix D, Figure D-1 — *Security Automation Domains*. Local copy: `compliance/reference/nist-sp-800-137/NIST.SP.800-137.pdf`.

| # | 800-137 Domain | Planned Adapter | Status | Notes |
|---|---|---|---|---|
| 1 | Vulnerability Management | `vuln-scan` (slot) | Phase 3 | Tool selection open — Tenable/Qualys/OpenSCAP (§13-14) |
| 2 | Patch Management | `patch-state` (slot) | Phase 2 | OS + M365 tenant patch drift |
| 3 | Event Management | inheritance-candidate | gap | Azure Gov-native (Sentinel) candidate; prefer inheritance over custom adapter |
| 4 | Incident Management | inheritance-candidate | gap | Tied to FedRAMP ConMon Playbook §6 Incident Communications; agency-level process |
| 5 | Malware Detection | inheritance-candidate | gap | Defender for Endpoint coverage likely in M365 ATO inheritance |
| 6 | Asset Management | inheritance-candidate | gap | Intune/Entra device inventory candidate; ties to CM-8 inventory requirement |
| 7 | Configuration Management | `scubagear` (M365) + `stig-compliance` (host OS) | v1 + Phase 2–3 | ScubaGear covers M365 control plane; OpenSCAP/STIG covers Linux base |
| 8 | Network Management | inheritance-candidate | gap | Azure Gov NSG/firewall telemetry candidate |
| 9 | License Management | unplanned | gap | Low priority for v1 |
| 10 | Information Management | partial | partial | Canon registry (§3) provides partial evidence; formal data-flow inventory unplanned |
| 11 | Software Assurance | partial | partial | SBOM generation candidate in `quarto-build.yml`; not yet implemented |

**Note on IAM:** ScubaGear assertions against Entra ID configuration satisfy IAM-class controls, but 800-137 treats IAM as a subset of *Configuration Management* (Domain 7) rather than a separate domain. The earlier draft incorrectly separated these.

**Coverage posture:** v1 claims automated coverage of one 800-137 domain (Configuration Management for the M365 control plane, via ScubaGear). Host-level Configuration Management arrives with Phase 2–3. Domains 1–2 are adapter-owned (Phase 2–3). Domains 3–6 and 8 are planned to inherit from the Azure Government / M365 GCC-Moderate ATO boundaries rather than be re-implemented as custom adapters. Domains 9–11 are partial or unplanned for v1.

---

## 16. Continuous Monitoring Program

> **Full operational detail** — runbook cadence, adapter schemas, evidence schema, workflow yaml, SCR playbook — lives in standalone `CONMON.md`. This section is the strategic summary and cross-references.

### 16.1 Purpose

Establish and operate an Information Security Continuous Monitoring (ISCM) program for the `uiao-core` + `uiao-docs` federal pair, satisfying FedRAMP Continuous Monitoring Playbook cadence and NIST SP 800-137 ISCM lifecycle requirements. The program is anchored on the Conformance Adapter class (§3.5) and produces structured evidence suitable for SSP inheritance and auditor review.

### 16.2 NIST SP 800-137 lifecycle mapping (VERIFIED against source 2026-04-14)

**Source:** NIST Special Publication 800-137, Chapter 3 — *The Process*, §§3.1–3.6 (September 2011). Local copy: `compliance/reference/nist-sp-800-137/NIST.SP.800-137.pdf`.

| 800-137 Step (verbatim from §3) | UIAO responsibility | Primary artifact |
|---|---|---|
| §3.1 Define ISCM Strategy | `canon/conmon/strategy.md` (NEW) | Strategy doc, reviewed annually |
| §3.2 Establish an ISCM Program | Canon registry Conformance class (§3.5) | `adapter-registry.yaml` (class: conformance) |
| §3.3 Implement an ISCM Program | `conformance-run.yml`, `conmon-scheduled.yml` | Scheduled adapter executions |
| §3.4 Analyze Data and Report Findings | `conmon-aggregate.yml` + `tools/conmon_aggregate.py` (NEW) | Dashboard JSON + POA&M CSV |
| §3.5 Respond to Findings | POA&M workflow in `uiao-docs` | POA&M item lifecycle |
| §3.6 Review and Update the Monitoring Program and Strategy | Canon versioning; annual review of `conmon/strategy.md` | Version bump + change-log entry |

### 16.3 FedRAMP ConMon deliverable cadence (VERIFIED against source 2026-04-14)

**Source:** *FedRAMP Continuous Monitoring Playbook*, Version 1.0, November 17, 2025. Local copy: `compliance/reference/fedramp-conmon-playbook/FedRAMP_Continuous_Monitoring_Playbook.pdf`. Applies to Rev 5 Agency Authorization and legacy JAB path. Playbook consolidates ten predecessor FedRAMP documents (Strategy Guide v3.2, Vulnerability Scanning Requirements v3.0, Annual Assessment Guidance v3.0, Significant Change Policies v1.0, Incident Communications Procedures v5.0, and others).

FedRAMP ConMon is anchored on three process areas: **(i) Operational Visibility, (ii) Change Control, (iii) Incident Response** (Playbook §2).

| Deliverable | Cadence | Source Adapter(s) | Output format | 800-53 Control |
|---|---|---|---|---|
| POA&M | Monthly | `conmon-aggregate.yml` | FedRAMP POA&M Template (version-current — see UNSURE #5) | CA-5 |
| System inventory | Monthly | `patch-state` + asset inventory source | FedRAMP Integrated Inventory Workbook | CM-8 |
| Configuration baseline compliance (M365) | Monthly | `scubagear` | JSON + POA&M rows | CM family |
| Vulnerability scan | Monthly (authenticated, Mod/High) | `vuln-scan` (Phase 3) | Machine-readable: XML, CSV, or JSON | RA-5 |
| Raw vulnerability scan files | Monthly (per agency agreement) | `vuln-scan` (Phase 3) | Native scanner format | RA-5 |
| Patch state | Monthly | `patch-state` (Phase 2) | JSON delta report | SI-2 |
| STIG compliance | Quarterly (recommended) | `stig-compliance` (Phase 2–3) | OpenSCAP ARF (UNSURE #7) | CM family |
| Annual assessment | Yearly | FedRAMP-recognized 3PAO (external) | SAR + SRTM + RET + POA&M | CA-2 |
| Significant Change Request | As-needed | pre/post `conformance-run.yml` (§16.7) | Playbook §5 SCR package | CM-3, CM-4 |

**Key verified requirements (Playbook §3):**

- Authenticated scanning required for Moderate and High systems — `RA-5(5)`.
- Machine-readable output in XML, CSV, or JSON required; greatest-information format preferred.
- CVE reference numbers required from NIST NVD for any vulnerability listed there.
- CVSSv3 base score required as original risk rating; CVSSv2 acceptable fallback.
- CSPs with multiple federal agency customers must implement **collaborative ConMon** (Playbook §7).

### 16.4 Conformance Adapter class (schema reference)

Defined in §3.2 with full schema. Key class-specific fields: `vendor`, `license`, `runtime`, `scope`, `policy-engine`, `outputs`, `triggers`, `evidence-class`. All conformance adapters are read-only — they do not change tenant state. Any adapter that writes must declare `class: modernization`.

### 16.5 Conformance adapter roadmap

| Phase | Adapter | Scope | Dependency |
|---|---|---|---|
| Phase 1 (v1) | `scubagear` | M365 control plane | GitHub-hosted `windows-latest` runner; service principal credential |
| Phase 2 | `patch-state` | OS + M365 tenant | Azure Gov subscription; device inventory source |
| Phase 2–3 | `stig-compliance` | RHEL/Rocky + Apache httpd | Azure Gov VMs in scope; OpenSCAP availability |
| Phase 3 | `vuln-scan` | RHEL/Rocky + Apache httpd | Azure Gov VMs in scope; scanner licensing |
| Post-Phase-3 | event/asset/network (inheritance-first) | Azure Gov platform | Azure Gov ATO inheritance confirmed |

### 16.6 Aggregation, POA&M feed, and secret handling

`conmon-aggregate.yml` reads every `evidence/conformance/<adapter>/<run-id>/findings.json`, groups by control-family and severity, writes two artifacts: (1) `dashboard/conmon-dashboard.json` for site rendering, (2) `poam/poam-<YYYY-MM>.csv` for FedRAMP POA&M submission. Regressions (new findings relative to prior run) automatically open GitHub issues labeled `conmon/regression` with adapter + control context.

**Secrets** for Conformance Adapters live in GitHub Actions secrets scoped to `uiao-core` only. Naming pattern: `<ADAPTER>_<TENANT>_<PURPOSE>` (e.g. `SCUBAGEAR_TENANT_APP_ID`). Rotation via the `canon-steward` subagent on a 90-day cadence (UNSURE — confirm federal rotation requirement). Never committed; never passed to `uiao-docs` or `uiao-gos`.

### 16.7 Significant Change Request (SCR) evidence pattern

Any proposed significant change (e.g. major Entra ID tenant reconfiguration, new SCuBA baseline revision) follows the pre/post pattern:

1. Pre-change: `conformance-run.yml` manual dispatch with label `scr-pre/<scr-id>` — snapshots current state.
2. Change executes (outside ConMon scope).
3. Post-change: `conformance-run.yml` manual dispatch with label `scr-post/<scr-id>` — snapshots new state.
4. `tools/conmon_diff.py` (NEW) produces a diff report between pre and post findings.
5. Diff report attaches to the SCR package submitted to the agency AO (UNSURE — confirm SCR submission process per agency).

### 16.8 Runner strategy — dual-track

| Phase | Runner | Rationale | Constraints |
|---|---|---|---|
| Phase 1 (now → Azure Gov cutover) | GitHub-hosted `windows-latest` | Zero infrastructure; fast start; ScubaGear PowerShell runtime available | Actions run on GitHub's commercial infrastructure — not inside the federal ATO boundary. This is acceptable for dev/assessment but not for production evidence of record (UNSURE — confirm agency acceptance). |
| Phase 2 | GitHub-hosted for code; self-hosted for sensitive evidence runs | Bridge phase — move the tenant-touching conformance runs to self-hosted while everything else stays GitHub-hosted | Requires Azure Gov Windows VM(s); hardened baseline; secret broker |
| Phase 3+ | Self-hosted Windows runners in Azure Government | All tenant-touching conformance execution happens inside the federal boundary | DISA STIG Windows Server baseline; managed identity for M365 auth where supported; runner registration token via Azure Key Vault |

Specific Azure Gov self-hosted runner design (resource group, VM SKU, hardening baseline, key vault integration, scale-set vs standalone) is deferred to §13 Decision 13 — tracked as open.

### 16.9 UNSURE markers and verification status (updated 2026-04-14)

Source documents for FedRAMP ConMon and NIST 800-137 are now local at `compliance/reference/`. Verification status below reflects document reads on 2026-04-14.

**Verified against source (no longer UNSURE):**

| # | Claim | Verification |
|---|---|---|
| ✓ | NIST SP 800-137 six-step lifecycle | Verified verbatim against §3, §§3.1–3.6 |
| ✓ | NIST SP 800-137 eleven security automation domains | Verified verbatim against Appendix D, §D.1, page D-3 — list includes Incident Management (originally missed) |
| ✓ | FedRAMP ConMon deliverable cadences (monthly POA&M, monthly inventory, annual 3PAO) | Verified against FedRAMP ConMon Playbook v1.0 (2025-11-17), §§2, 3, 4 |
| ✓ | FedRAMP ConMon three process areas (Operational Visibility, Change Control, Incident Response) | Verified against Playbook §2 |
| ✓ | Machine-readable vuln-scan format requirement (XML/CSV/JSON) | Verified against Playbook §3 |
| ✓ | ScubaGear runtime = PowerShell | Verified by user context (corroboration pending repo read) |

**Still UNSURE — require verification:**

| # | Claim | Source of gap |
|---|---|---|
| 1 | ScubaGear LICENSE text | Cannot reach cisagov/ScubaGear repo (github.com egress blocked) |
| 2 | ScubaGear current product scope and baseline set | Same — repo unreachable |
| 3 | ScubaGear PS 5.1 vs PS 7 requirement; Graph SDK version pin | Same — repo unreachable |
| 4 | FedRAMP POA&M Template column schema (version-current) | Playbook notes templates "periodically updated" — POA&M Template is distributed separately |
| 5 | DISA STIG + OpenSCAP ARF format assumption for `stig-compliance` adapter output | Separate authority (DISA) document not yet on hand |
| 6 | Federal secret rotation cadence (90-day assumption) | Not covered by the two PDFs retrieved |
| 7 | Agency-specific SCR submission process beyond Playbook §5 | Agency-dependent — each agency AO may have custom process |
| 8 | Azure Gov ATO inheritance scope for event/asset/network/malware/incident | Requires Azure Government FedRAMP package review |

**Newly-introduced, from verified source read (should be tracked):**

| # | Claim | Implication |
|---|---|---|
| N1 | Playbook mandates collaborative ConMon for CSPs with multiple agency customers (§7) | Architecture should plan for this pattern when second federal agency is onboarded |
| N2 | Playbook requires authenticated scanning for Moderate/High systems (RA-5(5)) | `vuln-scan` adapter must be built with authenticated-scan support |
| N3 | Playbook requires CVSSv3 base score as original risk rating, NVD CVE lookups | `conmon-aggregate.yml` must enrich findings with NVD CVE data |
| N4 | Playbook repository options: USDA Connect.gov (LI-SaaS/Low/Moderate) or CSP-owned (High) | Affects where POA&M deliverables ultimately land — not a GitHub artifact |
| N5 | 3PAO-authored documentation requires chain-of-custody integrity guarantees | Affects how annual assessment deliverables are handled in CI |

---

**Next actions upon sign-off:**
1. Commit this file to `uiao-core/ARCHITECTURE.md`
2. Commit companion `uiao-gos/ARCHITECTURE.md` to `uiao-gos` repo
3. Add pointer paragraphs to `uiao-core/README.md`, `uiao-docs/README.md`, and `uiao-gos/README.md`
4. Commit companion `uiao-core/CONMON.md` (standalone operational detail)
5. Proceed with build steps 0a–7 per todo list
