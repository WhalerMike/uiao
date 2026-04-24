# Image Prompts — Client-Server to Hybrid-Cloud Transformation (Series)

> Companion catalog for the 11-chapter series. One entry per `![...]`
> placeholder in the `.qmd` files. Generated images land in `./images/`
> with the exact filename referenced by the chapter (e.g.
> `04-orgpath-fanout.png`).
>
> **Visual language for the series.** All figures should share a
> consistent UIAO aesthetic:
>
> - **Palette:** neutral slate + federal navy accents; avoid
>   Microsoft-branded reds/greens that would read as vendor marketing.
> - **Typography:** clean sans-serif for labels; monospace for
>   attribute values, path fragments, and code tokens.
> - **Style:** diagrammatic / technical illustration — not photographic,
>   not isometric-3D, not marketing-flat. Similar in spirit to
>   high-quality engineering architecture diagrams (AWS / Azure
>   reference-architecture style, but neutral).
> - **Backgrounds:** white or very light slate; no gradients.
> - **Aspect ratio:** landscape 3:2 (e.g. 1440×960) unless otherwise
>   noted. Embedded at 720px wide in the `.qmd` files.
> - **No human figures.** This is infrastructure documentation, not
>   lifestyle imagery.
>
> **Canon-compliance.** Every diagram must respect UIAO canon:
> GCC-Moderate boundary visible where relevant; OrgPath format
> `ORG-XXX-YYY`; MOD_* and DM_* identifiers spelled exactly per canon;
> no tenant-specific GUIDs or UPNs.

---

## 00-ad-hidden-governance-surface

**Chapter:** [00 — The Problem Nobody Talks About](00-introduction.qmd)

**Caption:** *Figure 0.1 — Active Directory as the implicit governance
substrate for eleven categories of infrastructure object.*

**Prompt:**

> A central labeled block "Active Directory Domain Services" in federal
> navy, with eleven curved arrows radiating outward to eleven labeled
> leaves arranged in a circle. The eleven leaves are: Users, Computers,
> Service Accounts, Security Groups, Group Policy Objects, DNS / DHCP,
> PKI / Certificate Services, RADIUS / NPS, LDAP, SPNs / App
> Registrations, Trust Relationships. Each leaf is a small rounded
> rectangle with a one-line sub-label in gray showing what AD was doing
> for that category (e.g. "Identity lifecycle", "Domain join",
> "Kerberos delegation"). The whole figure sits on a neutral white
> background. Clean diagrammatic style, no icons, typography-driven.

**Size:** 1440×960 (3:2 landscape). Embed 720px.

---

## 01-platform-server-five-roles

**Chapter:** [01 — The UIAO Platform Server](01-platform-foundation.qmd)

**Caption:** *Figure 1.1 — UIAO Platform Server: five roles on one
Windows Server 2025 host.*

**Prompt:**

> A single large rounded-rectangle host labeled "UIAO-GIT01 · Windows
> Server 2025 · Tier-0". Inside the host, five horizontally arranged
> panels, each a distinct role:
> (1) "Canonical Source of Truth" with a Gitea mark and a small Git
> commit-graph icon;
> (2) "HTTPS Reverse Proxy + Client-Cert Terminator" with an IIS
> label and a lock-with-certificate icon;
> (3) "Legacy-to-Modern Auth Bridge" with two small adjacent badges,
> one reading "AD Kerberos (read-only)" and one reading "Entra OIDC
> (read-write)";
> (4) "Transformation Engine Host" showing three stacked pills —
> PowerShell, Python, API Integrators;
> (5) "Adapter Dispatcher" showing labels "DM_010..080", "MOD_I".
> External connectors extend from each panel to the appropriate
> target (AD Forest, Entra ID, Intune, Azure Arc, Infoblox, etc.),
> shown as small outline boxes around the perimeter. Federal navy
> accents; neutral slate host body.

**Size:** 1440×960 (3:2).

---

## 02-assessment-ingestion-pipeline

**Chapter:** [02 — Analyzing the Client/Server Estate](02-legacy-ingestion.qmd)

**Caption:** *Figure 2.1 — Eleven ingestion streams feed a single
provenance-bound artifact set in Gitea.*

**Prompt:**

> A left-to-right pipeline diagram. Left: a labeled cylinder "Client /
> Server AD Forest" (Tier B access badge shown). Middle: eleven
> parallel horizontal lanes, each a rounded-rectangle stream labeled
> in order top-to-bottom: Forest + Domain topology, OU hierarchy,
> Users, Computers, Service Accounts + SPNs, Groups, GPOs, DNS Zones,
> DHCP Scopes, ADCS / PKI, LDAP Bindings + Kerberos SPN Map. Each
> lane passes through two small process boxes — "PowerShell
> (UIAOADAssessment)" then "Python (uiao.assess.graph)". Right: a
> labeled folder tree rendering the `assessments/<run-id>/` layout
> with `provenance.yaml` at the top. A small lock icon labeled
> "signed" overlays the folder. Neutral palette, no colored
> categories — the streams are visually uniform.

**Size:** 1440×960 (3:2).

---

## 03-analyze-plan-deliver

**Chapter:** [03 — Analysis → Plan → Delivery](03-transformation-pipeline.qmd)

**Caption:** *Figure 3.1 — Analyze → Plan → Deliver pipeline with
Two-Brain authorization handoff.*

**Prompt:**

> A three-stage horizontal pipeline. Each stage is a large rounded
> rectangle:
> Stage 1 "Analyze" (labeled brain: "Copilot · governance") shows
> four sub-outputs: current-state graph, target-state graph, diff,
> risk score.
> Stage 2 "Plan" (same brain) shows a YAML action-list preview
> (3–4 sample actions visible with `type: create-administrative-unit`,
> `type: assign-role-scoped`) and a MOD_J validation stamp.
> Stage 3 "Deliver" (labeled brain: "Execution Substrate · execution")
> shows vendor-API call icons (Graph, ARM, Infoblox WAPI) and an
> evidence packet on the right.
> A bold vertical dashed line between Stage 2 and Stage 3 labeled
> "Two-Brain handoff · authorized plan only". Small signed-commit
> icons between stages. Federal navy for governance brain; slate
> for execution brain.

**Size:** 1440×960 (3:2).

---

## 04-orgpath-fanout

**Chapter:** [04 — Identity: x.500 → Flat Entra ID + OrgPath](04-identity-transformation.qmd)

**Caption:** *Figure 4.1 — A single OrgPath attribute drives five
downstream governance outcomes.*

**Prompt:**

> A user object (small head-and-shoulders outline is acceptable) in
> the center, captioned with a monospace tag
> `extensionAttribute1 = ORG-FIN-AP-EAST`. Five labeled arrows radiate
> outward to five downstream effects:
> (1) "Dynamic Group Membership" → `OrgTree-FIN-AP-Users` with a group
> icon;
> (2) "Administrative Unit Scope" → `AU-ORG-FIN-AP` with a scope icon;
> (3) "Conditional Access Targeting" → a CA policy badge;
> (4) "Group-Based License Assignment" → a license SKU badge;
> (5) "Drift Detection (MOD_M)" → a green check / red X comparator
> icon.
> Each downstream effect is a small rounded panel. Below the figure,
> a one-line footer: "One attribute. Five governance outcomes. Zero
> admin-portal clicks." Federal navy accents on the attribute tag;
> neutral slate everywhere else.

**Size:** 1440×960 (3:2).

---

## 05-gpo-retirement-map

**Chapter:** [05 — Policy: GPO → Intune + Conditional Access](05-policy-transformation.qmd)

**Caption:** *Figure 5.1 — GPO categories mapped to their modern
target surfaces.*

**Prompt:**

> A two-column mapping diagram. Left column: six stacked legacy GPO
> category boxes, each a pale slate rectangle — "Device Configuration",
> "Security Baselines", "Software Deployment", "Access Control",
> "Server Configuration", "Browser / Mailbox Config". Right column:
> six corresponding modern target boxes — "Intune Configuration
> Profiles", "Intune Security Baselines + Entra Auth Methods",
> "Intune Win32 Apps + Autopilot", "Conditional Access + Entra
> Session Controls", "Azure Arc Guest Configuration + Azure Policy",
> "Intune Settings Catalog + Office 365 Policies". One horizontal
> arrow per row, labeled with the mapping rule (e.g. "regenerate,
> not copy"). A dashed border around the right column labeled
> "OrgPath-scoped targeting — every profile targets OrgTree dynamic
> groups". Federal navy on the target column, slate on the legacy.

**Size:** 1440×960 (3:2).

---

## 06-hybrid-dns-topology

**Chapter:** [06 — Services: DNS, DHCP, IPAM in Hybrid Cloud](06-network-services.qmd)

**Caption:** *Figure 6.1 — Hybrid resolution topology: on-prem
namespace, Private Resolver, Private DNS zone, and IPAM as single
source of truth.*

**Prompt:**

> A three-column topology diagram.
> Left column "On-prem namespace": three sample records —
> `UIAO-GIT01.corp`, `fileserver.corp`, `printer.corp` — each a small
> host icon.
> Middle column "Hybrid path": a large rounded rectangle labeled
> "Azure DNS Private Resolver" with two clearly-labeled endpoints,
> "inbound endpoint" (arrow from left) and "outbound endpoint"
> (arrow from right). Below it, a Private DNS Zone box
> "uiao.internal (authoritative)".
> Right column "Cloud namespace": a record
> `privatelink.blob.core.windows.net` with an Azure storage icon.
> Below the entire figure, a single horizontal band labeled
> "IPAM (DM_010) · single source of truth" with arrows going up into
> both Private DNS Zone and conceptual DHCP-scope records. Federal
> navy accents on the resolver and Private DNS; slate elsewhere.

**Size:** 1440×960 (3:2).

---

## 07-device-state-transitions

**Chapter:** [07 — Compute: Domain-Joined → Entra + Intune + Arc](07-compute-objects.qmd)

**Caption:** *Figure 7.1 — Device state transitions from Domain-Joined
to target Entra-Joined (or Arc-connected for servers).*

**Prompt:**

> A state-transition diagram with five labeled states shown as rounded
> rectangles:
> "Domain-Joined (legacy)" on the far left,
> "Azure AD Registered" at top,
> "Entra Hybrid Joined (transition, not destination)" — rendered with
> a dashed border and a small warning glyph to signal its transitional
> nature,
> "Entra Joined (target for user PCs)" on the far right with a solid
> checkmark,
> "Arc-connected server (target for servers)" below, offset.
> Labeled directed arrows between states show the three migration
> patterns: "greenfield via Autopilot" (direct to Entra Joined),
> "reset-and-re-enroll" (Domain-Joined → Entra Joined), and
> "hybrid-then-cloud" (Domain-Joined → Hybrid → Entra Joined). A
> dotted branch from any state into the Arc-connected server shows
> the server migration path. Neutral slate with federal navy on the
> target states.

**Size:** 1440×960 (3:2).

---

## 08-morning-login-flow

**Chapter:** [08 — Access Plane](08-access-plane.qmd)

**Caption:** *Figure 8.1 — Morning login: seven-step Zero-Trust
access flow from device boot to privileged elevation.*

**Prompt:**

> A vertical sequence diagram with seven numbered steps, each a
> rounded-rectangle action panel with a short title and a one-line
> actor label:
> 1. "Device boot" — Intune compliance check, BitLocker unlock;
> 2. "Sign-in" — CAC + PIN, Entra CBA validates certificate chain,
> CAE-aware token issued;
> 3. "Conditional Access evaluation" — CA-100 baseline, four signals
> ticked (compliant device, CBA MFA, location, risk);
> 4. "Application access" — M365 apps, Platform SSO satisfies
> subsequent auths, CAE live;
> 5. "VPN-replacement" — SASE ZTNA reverse-proxy to on-prem app;
> 6. "Privileged elevation" — PIM request, FIDO2 re-challenge,
> CyberArk session recording, MOD_X telemetry;
> 7. "End of day" — token expires, CAE revokes on reconnect.
> On the right side, a narrow vertical rail labeled "OrgPath-scoped ·
> provenance-bound · drift-monitored" running the full height.
> Federal navy for the rail; slate for the steps.

**Size:** 1440×960 (3:2).

---

## 09-program-gantt

**Chapter:** [09 — Migration Roadmap](09-migration-roadmap.qmd)

**Caption:** *Figure 9.1 — 52-week modernization program with seven
phases, five parallel workstreams, and six named gates.*

**Prompt:**

> A Gantt-style program timeline spanning 52 weeks on the horizontal
> axis. Along the top, seven labeled phase bands spanning the weeks:
> Phase 0 Pre-flight (wk 1–4), Phase 1 Foundation (5–8), Phase 2
> Pilot Division (9–16), Phase 3 General Rollout (17–36), Phase 4
> Legacy Retirement (37–44), Phase 5 AD DS Retirement (45–48), Phase
> 6 Steady State (49+).
> Below, five horizontal workstream lanes stacked vertically:
> Identity, Policy, Services, Compute, Access. Each lane has pale
> colored bars showing activity intensity per phase (not gantt
> dependencies — more like a heat-band showing when that workstream
> is active).
> Six vertical gate markers with thick lines and labels G0–G5 at
> weeks 4, 8, 16, 36, 44, 48. Each gate has a small tooltip showing
> its name (e.g. "G2 · Pilot Clean").
> Neutral white background, federal navy on gate markers, slate on
> lane bars.

**Size:** 1920×1080 (16:9 — wider than other figures because of the
timeline). Embed 720px.

---

## 10-instruments-vs-orchestra

**Chapter:** [10 — Leadership Takeaway](10-executive-summary.qmd)

**Caption:** *Figure 10.1 — Microsoft provides the instruments. UIAO
provides the orchestra.*

**Prompt:**

> A stylized orchestra-stage illustration (diagrammatic, not
> photographic). Eight instruments arranged in classical orchestra
> seating, each labeled with a Microsoft-native tool:
> Entra ID (first violin), Intune (second violin), Azure Arc (cello),
> Conditional Access (viola), Azure PIM (double bass), ScubaGear
> (oboe), Azure Private Resolver (clarinet), Entra CBA (French horn).
> At the front center, a conductor's podium with an open score; the
> conductor itself rendered as the UIAO platform server icon (a
> rounded-rectangle WS2025 host) with a baton. The score sheet is
> labeled with canon artifacts visible on its pages: MOD_A, MOD_B,
> MOD_D, MOD_M, DM_010, DM_020 (small typography). Faint sheet-music
> staves flow from the score to each instrument, representing
> governed plans and evidence. Federal navy + warm paper-tone
> palette; no actual people, all instruments rendered as
> illustrative silhouettes or line-art.

**Size:** 1440×960 (3:2).

---

## Generation checklist

When images are produced, confirm each of:

- [ ] File name matches placeholder exactly (e.g.
      `04-orgpath-fanout.png`).
- [ ] Size within 10% of the prompt's target dimensions.
- [ ] No human figures; no Microsoft-branded iconography beyond
      product-name text labels.
- [ ] Canon identifiers (MOD_A..Z, DM_010..090, OrgPath format) spelled
      exactly per canon.
- [ ] GCC-Moderate boundary visible where the figure touches
      cloud/SaaS scope.
- [ ] Alt-text in the chapter's `.qmd` still describes the figure
      accurately (update if the final image diverges).
- [ ] PNG output (not JPEG); transparent background preferred; if
      opaque, white.
