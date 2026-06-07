# Azure OrgPath as a Hidden Miracle Service — Document & Implementation Plan

> **Status: INBOX DRAFT — not canon.** Draft staging under `inbox/` (AGENTS.md:
> "content that isn't canonized yet"). Forward-looking design is **speculative**
> until it lands as an ADR with a `UIAO_NNN` allocation. Canon facts are cited;
> design proposals are flagged. Build/timeline figures attributed to the
> originating CoPilot analysis are **external estimates**, not repo commitments.
>
> **Companion:** [`orgpath-azure-service-architecture.md`](orgpath-azure-service-architecture.md)
> — the component-level architecture analysis. *This* document is the
> product-framing + phased implementation plan that sits on top of it.
>
> **Provenance anchor:** [ADR-092 — Active Governance](../src/uiao/canon/adr/adr-092-active-governance.md).
> Secondary: ADR-084 (Phase 5 / read-only console), ADR-038 (device-plane
> OrgPath), ADR-078 (15-facet Model C), ADR-040 (drift engine), ADR-033 (cloud
> boundary), ADR-059 (Commercial exceptions), `control-planes.yml` (six slots),
> UIAO_151 (Codebook), UIAO_163 (drift engine), UIAO_174 (governance telemetry).

---

## 1. The thesis: a hidden miracle service

When Active Directory is retired, what is lost is not a directory — it is the
**closed loop**. AD governed because it sat in the path: it authenticated the
logon, evaluated the group, pushed the policy. Truth and enforcement were the
same act. The cloud era deliberately tore that apart: identity in one provider,
devices in another, network admission in a third, privileged access in a fourth
— each keeping its own copy of the truth. A registry that merely records intent
and reports divergence can *see* the gap; it cannot *close* it.

**OrgPath closes the loop again — but invisibly.** It runs as an Azure control
plane that holds the organizational coordinate system, reconciles every provider
plane against it, and writes back **only native values** — Entra
`extensionAttributes`, Arc tags, dynamic-group `membershipRule`s, Conditional
Access predicates, Azure Policy targeting. The portals already read those
values. So the cloud begins to **behave as if it understands your organization**
— without a single portal being modified, and without waiting on Microsoft to
build anything.

That is the "hidden miracle": **the value lands in the surfaces customers already
use, through the data those surfaces already consume.** No new UI is required for
the miracle to be real. First-class OrgPath-branded portal blades are *upside*,
gated on a Microsoft partnership — never on the critical path.

![OrgPath, the hidden miracle service — three panels: the loss (AD retired, the closed loop gone, portals cannot see the org); the mechanism (OrgPath the hidden control plane, holds the Codebook, reconciles every plane, writes only native values); the miracle (portals just work, dynamic groups/CA/Intune/Azure Policy self-target, no portal change, no Microsoft buy-in).](images/orgpath-azure-service-diagram-06-hidden-miracle.png)

### Why "hidden" is a feature, not a limitation

- **No adoption friction.** Admins don't learn a new console; their existing
  Entra/Intune/Arc/Azure-Policy workflows simply start reflecting the org.
- **No vendor dependency on the critical path.** The miracle works on day one
  against stock Microsoft surfaces (ADR-092 Alternatives: the incumbents "will
  not delegate their runtime path" — so OrgPath never asks them to).
- **No control-plane/data-plane violation.** Writing native values *is* the
  mechanism; OrgPath never sits in a runtime path (ADR-092 §1).
- **Strategically defensible.** OrgPath unifies planes Microsoft keeps as
  separate products. The unification is the IP; the invisibility is what makes
  it shippable before Microsoft ever blesses it.

---

## 2. Why it *can* be hidden — the native-values argument

The miracle is only possible because every value OrgPath writes is a **first-class
native attribute** the Microsoft surfaces already consume. Nothing proprietary
sits between OrgPath and the portal.

| OrgPath writes (native) | Surface that already reads it | Effect, with zero portal change |
|---|---|---|
| Entra device `onPremisesExtensionAttributes` (ADR-038) | Intune dynamic device groups | Devices self-sort into the right groups by org facet |
| Entra user `extensionAttribute1–10` (Model C, ADR-078) | Entra dynamic groups, Conditional Access | Groups + CA policies target facet predicates |
| Arc machine **ARM tags** | Azure Policy scopes | Policy initiatives self-target servers by org facet |
| Dynamic-group `membershipRule` | Entra group membership engine | Membership recomputes automatically |
| CA predicates over facets | Conditional Access engine | "Privileged Finance → phishing-resistant MFA" evaluates natively |
| NAC attributes (VLAN / dACL / SGT) | ISE / ClearPass / Entra RADIUS | 802.1X admission decisions reflect org position (Book_17) |

The portals do not change. They simply receive **validated, drift-resisted,
policy-bearing** data where before they received whatever free-form string a sync
tool happened to move. (Microsoft's own sync tools are a *transport* — they move
an attribute value; they do not constrain it, notice when it stops matching the
org chart, or compose it into policy. OrgPath is the control plane one layer up.)

---

## 3. Architecture at a glance

The service is a managed Azure control plane over the six canonical control-plane
slots (`control-planes.yml`), incorporating each provider rather than competing
with it (ADR-092 §2).

![Azure-native OrgPath service architecture: Azure/M365 portals read native state on top; the managed OrgPath control plane (Mapping, Codebook, Drift Engine, Reconcile Orchestrator + the UIAO_102 provider-adapter layer across six control-plane slots) in the middle; provider data planes at the runtime bottom.](images/orgpath-azure-service-diagram-01-architecture.png)

Component-level detail (current repo → Azure-native mapping, plane by plane) lives
in the [architecture companion](orgpath-azure-service-architecture.md §3). The
short version: the engine already exists in code (`orgpath_runtime`,
`graph_transport`, `arm_transport`, the drift engine, the Codebook, the read-only
console); the work is hosting it on managed Azure compute/storage, adding
multi-tenancy, and certifying it.

---

## 4. The reconcile loop (how the miracle actually runs)

Steady-state OrgPath is an **idempotent loop**, because HR data and device
populations change. Every step is dry-run by default; live writes happen only
after an L3 approval, and `halt_on_critical` stops the line on any P1
(codebook-integrity) finding.

![Reconcile loop sequence: Scheduler triggers Mapping; Mapping validates derived facets against the Codebook; Drift Engine reads actual state from the provider data plane, classifies drift; Reconcile Orchestrator plans the change-set dry-run, applies via Graph/ARM/RADIUS after L3 approval; evidence emits UIAO_174 telemetry; portals read the resulting native state.](images/orgpath-azure-service-diagram-02-reconcile-sequence.png)

1. **Codebook** defines the org — desired state (UIAO_151).
2. **Mapping** derives facets from AD / HR; unmapped values become findings, not
   silent writes.
3. **Drift Engine** validates each facet independently and classifies divergence
   (UIAO_163; five drift classes; P1 = codebook-integrity, never auto-remediated).
4. **Reconcile Orchestrator** plans corrections (`plan / apply / verify`),
   dry-run by default.
5. **Provider adapters** (UIAO_102) apply on the right plane — Graph → Entra /
   Intune, ARM → Arc / Azure Policy, RADIUS/REST → NAC, REST → Infoblox — L3
   human-gated; L4 only for enumerated low-blast-radius, rollback-capable ops.
6. **Evidence** emits to Log Analytics / Sentinel (UIAO_174).
7. **Portals reflect** the corrected state — they read the native attributes/tags
   the loop wrote. *This is the miracle step, and it requires no code in the
   portals.*

---

## 5. Deployment (single-tenant first)

The whole control plane is a handful of managed Azure resources. The biggest
security upgrade over the current Windows/IIS surface is replacing client-secret
env vars with **Managed Identity**.

![Single-tenant Azure deployment: a Subscription/Resource-Group boundary containing Container Apps (API + read-only console), Functions (timer reconcile loop), Cosmos/Blob (Codebook), immutable Blob (evidence), Key Vault, a user-assigned Managed Identity, Log Analytics and Sentinel; with Managed-Identity-authenticated arrows crossing the boundary to Microsoft Graph, ARM, NAC, and Infoblox.](images/orgpath-azure-service-diagram-03-deployment.png)

- **Compute:** Container Apps (API + the read-only `/orgpath` console, ADR-084
  §C7) + timer-triggered Functions for the reconcile loop. The runtime is already
  stateless and transport-agnostic, so the host is swappable.
- **State:** Cosmos DB / versioned Blob for the served Codebook; immutable (WORM)
  Blob for `GovernanceReport` evidence.
- **Identity:** a user-assigned **Managed Identity** with a federated credential
  acquires the Graph `.default` token (admin-consented app permissions still gate
  the write) and holds a least-privilege Azure RBAC role (**Tags Contributor**)
  for ARM tag writes. Key Vault for anything that must remain a secret.
- **Observability:** Log Analytics for UIAO_174 telemetry → Sentinel for
  correlation/alerting.
- **Control plane only:** every outbound write goes to a provider *management*
  API. OrgPath never sits in any runtime path (ADR-092 §1).

---

## 6. Multi-tenant SaaS

The shared control plane is stateless and horizontally scaled; **isolation is
per-tenant and is an invariant**. Each tenant gets its own Codebook, its own
Managed Identity / federated credential, its own evidence store, and its own
blast-radius boundary — and writes **only** to its own data plane.

![Multi-tenant SaaS: a shared stateless control plane (Tenant Router + engines + adapter layer) over three per-tenant isolation columns (each with its own Codebook container, Managed Identity, evidence store, and blast-radius boundary), each writing only to its own Entra/Arc data plane.](images/orgpath-azure-service-diagram-04-multitenant-saas.png)

- **Shared:** the engine (Mapping / Drift / Reconcile + the UIAO_102 adapter
  layer) and the Tenant Router. Stateless → scales horizontally.
- **Per-tenant (isolated):** Codebook (Cosmos container/partition), identity
  (per-tenant federated credential), evidence, blast radius, and
  **sovereign-boundary enforcement** (a commercial-audience token must never
  reach a sovereign endpoint — see §7).
- **Why this is the hardest phase:** single-tenant today assumes one app
  registration, one Codebook, one credential set. True multi-tenancy is the
  largest genuinely-new engineering work (architecture companion §6).

---

## 7. Federal / sovereign deployment (GCC-M and Azure Government)

The transports are already cloud-aware: `resolve_graph_base()` /
`resolve_arm_base()` and `--cloud {commercial | gcc-high | dod}` derive the
correct host **and** token audience **and** login authority per cloud. The
discipline a managed service must enforce is that **the right-audience token
only ever reaches the right-cloud endpoint.**

![Federal/sovereign deployment: the OrgPath control plane with cloud-aware transports routing commercial-audience tokens to graph.microsoft.com / management.azure.com and government-audience tokens to graph.microsoft.us / management.usgovcloudapi.net; a red REJECTED-401 path shows a wrong-audience token being refused by a sovereign endpoint.](images/orgpath-azure-service-diagram-05-federal-gccm.png)

- **Today's boundary:** GCC-Moderate, M365 SaaS (ADR-033), with two named
  Commercial exceptions (ADR-059). The federal vertical is the most mature
  adapter pack.
- **The teaching point (red path in the figure):** a Graph-audience token is
  rejected by ARM (HTTP 401); a commercial-audience token is rejected by a
  sovereign endpoint. The two planes need distinct transports/audiences — which
  the repo already encodes.
- **The new boundary:** a managed *Azure* service is a deployment boundary
  distinct from the M365 SaaS boundary. It needs **its own authorization path**
  and **its own `gcc-boundary` enum in lockstep with an authorizing ADR**
  (AGENTS.md lockstep rule). This is an open decision, not a settled one (§10).
- **Evidence for FedRAMP:** UIAO_174 telemetry → Sentinel; KSI / OSCAL artifacts
  the substrate already produces feed the continuous-monitoring story.

---

## 8. Implementation plan

The plan is sequenced so the **miracle ships first** (Phases A–D deliver a
working hidden service) and **productization/partnership follow** (E–F). Each
phase is independently shippable and never crosses the control-plane/data-plane
line. Effort figures in *italics* are **external CoPilot estimates**, recorded
for traceability, not repo commitments.

### Phase A — Lift (single-tenant)
**Goal:** the existing engine, unchanged in behavior, running on managed Azure.
- Containerize `uiao.api` + the read-only console; deploy to Container Apps.
- Move the reconcile loop to a timer-triggered Function.
- Swap MSAL client-secret auth → **Managed Identity** for both Graph and ARM.
- Codebook stays in-package; no new behavior.
- **Acceptance:** a dry-run `govern` pass runs on a schedule in Azure and emits a
  `GovernanceReport`; no client secrets in the environment; `substrate walk`
  clean.

### Phase B — Externalize state + evidence
**Goal:** it looks and audits like an Azure governance service.
- Codebook → Cosmos/Blob (single-tenant use, per-tenant-ready schema).
- UIAO_174 telemetry → Log Analytics; `GovernanceReport` → immutable Blob.
- Sentinel workbook renders the drift dashboard from telemetry.
- **Acceptance:** evidence is queryable in Log Analytics and immutable in Blob;
  the read-only console reads the externalized Codebook.

### Phase C — Actuator security + L3 gating  *(prerequisite for ANY live write)*
**Goal:** make the actuator safe before it ever writes in the service.
- Design + build the actuator security envelope: strong authz, immutable audit,
  dry-run, rollback, break-glass (ADR-092 Consequences — "must be designed
  before any op class promotes to L3, not after").
- Wire the L3 approval gate (Logic App / Sentinel SOAR / manual approval).
- **Acceptance:** no live write is possible without a recorded L3 approval; every
  write is reversible and audited; `halt_on_critical` verified to suspend the
  scan on a synthetic P1.

### Phase D — Multi-tenant
**Goal:** turn the single-tenant service into SaaS.
- Per-tenant Codebook, identity (federated credentials), evidence, blast radius.
- Per-tenant sovereign-boundary enforcement (commercial vs Azure Government).
- Tenant router + cross-tenant isolation tests (the isolation invariant, §6).
- **Acceptance:** a write initiated for Tenant A can never touch Tenant B's data
  plane (proven by test); per-tenant boundary audiences enforced.

### Phase E — Marketplace + authorization
**Goal:** a transactable, authorizable product.
- Managed-app / SaaS offer packaging; partner attestations; support SLAs.
- FedRAMP path against the **Azure** boundary: new `gcc-boundary` enum + ADR.
- **Acceptance:** offer passes Marketplace certification; authorization boundary
  documented and ADR-ratified.

### Phase F — Portal blades  *(parallel, partnership-gated, OPTIONAL)*
**Goal:** first-class OrgPath surfaces inside the portals — **upside, not
critical path.**
- Facet explorer, drift-findings, reorg-simulation, governance-evidence blades.
- Strictly additive: they *read* the same native values the miracle already
  writes; they change nothing architecturally.
- **Acceptance:** gated entirely on Microsoft product-team buy-in. **The service
  is fully functional without this phase** — that is the whole point of "hidden."

### Phasing summary

| Phase | Delivers | Gates | External est. |
|---|---|---|---|
| A Lift | Engine on Azure, MI auth | — | *part of 6–9 mo* |
| B State/evidence | Cosmos/Blob, Sentinel | A | *↑* |
| C Actuator security | Safe live writes, L3 gate | B; **blocks all live writes** | *↑* |
| D Multi-tenant | SaaS isolation | C | *largest eng. effort* |
| E Marketplace/FedRAMP | Transactable + authorized | D | *12–18 mo to FedRAMP Mod* |
| F Portal blades | First-class UI | **Microsoft buy-in** | *out of scope / upside* |

> **External totals (CoPilot, not canon):** ~6–9 months to a production-grade
> Azure PaaS (Phases A–D) with ~3–4 engineers reusing the UIAO codebase;
> ~12–18 months to FedRAMP Moderate (Phase E). Recorded for traceability only.

---

## 9. Risks & guardrails (doctrine that must not bend)

The hidden-miracle framing is *more* tempting to over-reach on, because the
service is invisible and writing native values feels harmless. It is not. These
guardrails are load-bearing:

- **Never cross the control-plane/data-plane line (ADR-092 §1).** Hosting on
  Azure changes *where the loop runs*, never *which side of the line it sits on*.
  No inline auth, no session/tunnel termination, no packet routing, no issuing
  the production credential.
- **Actuator security is a prerequisite, not a follow-on (ADR-092 Consequences).**
  Write access to a customer's crown-jewel identity/network/security systems is
  the highest-value attack surface OrgPath will ever ship. Phase C blocks all
  live writes until that envelope exists.
- **Dry-run default + `halt_on_critical` are non-negotiable (ADR-040 / UIAO_163).**
  Managed hosting does not relax the safety defaults.
- **Federal L3 ceiling holds (ADR-092 §4).** L4 autonomy only for enumerated,
  low-blast-radius, rollback-capable op classes with a clean advisory record.
  High-blast-radius ops (tenant-wide role assignment; a VLAN change touching
  thousands of devices) are L3-capped permanently.
- **Read-only console stays read-only (ADR-084 §C7).**
- **Cross-tenant isolation is an invariant (§6).** A write for one tenant can
  never reach another tenant's data plane.
- **Sovereign-audience discipline (§7).** A commercial-audience token must never
  reach a sovereign endpoint; the two planes keep distinct transports/audiences.
- **Incorporate, never replace (ADR-092 §2).** The provider keeps its runtime
  seat; OrgPath reconciles its state and emits evidence.

---

## 10. Open decisions (each needs an ADR before it becomes real)

1. **New Azure deployment boundary** — a managed Azure service is distinct from
   the GCC-Moderate M365 SaaS boundary; needs a new `gcc-boundary` enum +
   authorizing ADR (AGENTS.md lockstep rule).
2. **Codebook store of record** — does Cosmos/Blob become authoritative at
   runtime, or is in-package YAML still SSOT with the store as a derived cache?
   (SSOT discipline, AGENTS.md Operating Principle 1.)
3. **Actuator security design** — required before any service-side live write
   (Phase C); its own ADR.
4. **Multi-tenant model** — per-tenant identity / isolation / blast-radius;
   doctrine plus design.
5. **Hosting target** — Container Apps vs AKS vs Functions split; an
   implementation ADR, not doctrine.
6. **Partnership posture (Phase F)** — whether to pursue first-class portal
   blades at all, or commit permanently to the hidden-service model.

---

## 11. One-paragraph summary

OrgPath as an Azure service is **medium engineering difficulty** because the
engine already exists as an active reconciliation control plane (ADR-092) with
two cloud-aware write transports in code. Hosted on managed Azure compute and
storage with Managed-Identity writeback, it delivers a **hidden miracle**: the
M365/Azure portals behave as if the cloud understands the organization, because
OrgPath feeds them validated, drift-resisted, policy-bearing **native** values
they already read — with no portal change and no Microsoft dependency. The plan
ships the miracle first (Phases A–D), productizes and authorizes it next (E), and
treats first-class portal blades as partnership upside (F), never as the critical
path. The hard parts are multi-tenancy, sovereign boundaries, certification, and
Microsoft's product politics — not the engine. Every phase preserves the
control-plane/data-plane line, the dry-run default, and the federal L3 ceiling.

---

## 12. References (provenance)

- [ADR-092 — Active Governance](../src/uiao/canon/adr/adr-092-active-governance.md)
  — control/data plane, incorporation contract, L0–L4 ladder, L3 ceiling,
  bidirectional truth, actuator-security consequence.
- [ADR-084 — Phase 5 Consumer Architecture](../src/uiao/canon/adr/adr-084-phase5-consumer-architecture.md)
  — Codebook-as-shared-dependency; read-only console (§C7).
- ADR-038 (device-plane OrgPath), ADR-078 (15-facet Model C), ADR-040 (drift
  engine), ADR-033 (cloud boundary), ADR-059 (Commercial exceptions).
- [`control-planes.yml`](../src/uiao/canon/data/control-planes.yml) — six
  canonical control-plane slots.
- UIAO_151 (Codebook), UIAO_163 (drift engine), UIAO_174 (governance telemetry).
- Code: `uiao.governance.orgpath_runtime`, `uiao.adapters.graph_transport`,
  `uiao.adapters.arm_transport`, `uiao.api.web.console`, `deploy/windows-server/`.
- Companion draft: [`orgpath-azure-service-architecture.md`](orgpath-azure-service-architecture.md).
- Figures (blueprint register, ADR-093; SVG = source of truth, PNG = artifact):
  `images/orgpath-azure-service-diagram-01-architecture.svg` …
  `…-06-hidden-miracle.svg`.
- Uploaded source bundles (author: Michael Stratton): *Platform Bundle*,
  *OrgPath Narrative Bundle* (Books 01–17), *OrgPath Implementation Bundle*
  (Guides 1–7).
- External build/timeline estimates attributed to the originating CoPilot
  analysis — not canon, not a repo commitment.
