# OrgPath / Active Governance as an Azure-Native Service — Architecture Draft

> **Status: INBOX DRAFT — not canon.** This is draft staging under `inbox/`
> (AGENTS.md: "content that isn't canonized yet"). Nothing here is a decision.
> Forward-looking design is **speculative** until it lands as an ADR with a
> `UIAO_NNN` allocation. Where this draft asserts a *canon fact* it cites the
> source; where it asserts a *design proposal* it says so.
>
> **Provenance anchor:** [ADR-092 — Active Governance](../src/uiao/canon/adr/adr-092-active-governance.md)
> (control-plane/data-plane boundary, provider-incorporation contract, L0–L4
> actuation ladder, federal L3 ceiling). Secondary: ADR-084 (Phase 5 consumer
> architecture), ADR-038 (device-plane OrgPath), ADR-078 (15-facet Model C),
> ADR-033 (cloud boundary), `control-planes.yml` (the six slots),
> UIAO_151 (Codebook), UIAO_163 (drift engine), UIAO_174 (governance telemetry).
>
> **Occasion:** assessment of a CoPilot analysis ("how hard is it to build
> OrgPath/Active Governance as an Azure service, and to make it *active* inside
> the M365/Azure portals?") against the actual codebase. Build/timeline figures
> attributed to CoPilot are flagged as **external estimates**, not canon.

---

## 1. Executive takeaway

Building OrgPath / Active Governance as an Azure-native service is **medium
difficulty, not high** — because the architecture already *is* an Azure-shaped
architecture. UIAO is, in canon and in code, an **active reconciliation control
plane** that governs provider **data planes** (ADR-092). That is precisely the
control-plane/data-plane split every first-party Azure governance service
(Azure Policy, Arc, Automation) is built on. The port is therefore an
**adaptation of an existing engine to managed-PaaS hosting**, not a rewrite.

Two distinct questions, two different answers:

| Question | Difficulty | Why |
|---|---|---|
| Build OrgPath as a managed Azure service | **Medium** (engineering) | The control plane, the `plan/apply/reconcile` adapters, the drift loop, the Codebook, and the **two cloud-aware write transports already exist** in the repo. The work is hosting, multi-tenancy, and certification — not inventing the engine. |
| Make OrgPath "active" inside M365 / Azure portals | **Low technically, high politically** | OrgPath writes only **native** values (Entra `onPremisesExtensionAttributes`, Arc ARM tags, dynamic-group `membershipRule`, CA predicates). The portals already read those. First-class *OrgPath-branded* portal surfaces need Microsoft product-team buy-in; everything else works as "magic behind the scenes" today. |

The real obstacle is **not engineering** — it is that OrgPath **unifies control
planes Microsoft keeps as separate products** (Entra, Intune, Arc, Azure Policy,
Conditional Access, Defender, Sentinel). That is exactly why it is defensible IP
(ADR-092 Consequences: "draws the line that keeps UIAO from being a competitor
Microsoft would crush"), and exactly why native first-party adoption is a
partnership problem, not a code problem.

> **Crucial doctrinal guardrail.** Going "Azure-native" must **not** drift the
> product across the control-plane/data-plane line. ADR-092 §1 is explicit: a
> modernization adapter MAY call a provider's management API; it MUST NOT become
> the runtime data-plane component (sit inline in auth, terminate sessions,
> route packets, issue the production credential). An Azure-hosted OrgPath is
> still the control plane. Hosting changes *where the loop runs*, never *which
> side of the line it sits on*.

---

## 2. What already exists in the repo (the honest baseline)

Before designing the target, here is the ground truth the port starts from —
none of this is hypothetical:

- **Active control plane, in code.** `uiao.governance.orgpath_runtime.OrgPathGovernanceRuntime`
  (UIAO_163 / UIAO_174) composes the drift engine + Phase 5 adapters into a
  runnable governance loop. Surfaced as `uiao orgtree govern`. **Dry-run by
  default; transport-free until a transport is injected** (AGENTS.md public
  surface inventory).
- **Two cloud-aware write planes, in code.**
  - `uiao.adapters.graph_transport.GraphTransport` — Entra/Graph plane (httpx +
    MSAL via `EntraTokenProvider`), cloud-resolved by `resolve_graph_base`.
    Writes device facets to `onPremisesExtensionAttributes` (ADR-038).
  - `uiao.adapters.arm_transport.ArmTransport` — ARM plane for the Arc
    device-plane writeback (`management.azure.com` / `management.usgovcloudapi.net`),
    **distinct token audience** (`arm_token_scope`). A Graph-audience token sent
    to ARM is rejected 401 — the two planes need distinct transports.
- **Codebook as SSOT.** `src/uiao/canon/data/orgpath/codebook.yaml` (UIAO_151),
  schema-validated (`codebook.schema.json` v2.0.0). 10 named facets across
  `extensionAttribute1–10` + 5 reserved slots (Model C, ADR-078). `uiao orgtree
  validate codebook` gates it.
- **Drift engine.** Six-phase reconciliation (Snapshot → Compare → Classify →
  Alert → Remediate → Verify), `dry_run=True` default, `halt_on_critical`
  stop-the-line, per-facet `auto_remediate`, governance-review gating (ADR-040 /
  UIAO_163). Five drift classes; P1 = codebook-integrity, never auto-remediated.
- **Governance telemetry.** UIAO_174 events (`SnapshotCreated`, `DriftDetected`,
  `DriftRemediated`, `EscalationTriggered`) emitted on every pass.
- **Read-only governance UI.** `uiao.api.web.console` (ADR-084 §C7) — an
  Azure-Portal-style, **read-only** Jinja2 console under `/orgpath`
  (drift dashboard, codebook explorer, principal lookup, dry-run pass). **No
  writes.**
- **Current hosting surface.** FastAPI (`uiao.api`, `[api]` extra) on
  **Windows Server 2025 + IIS** (loopback uvicorn behind IIS TLS termination;
  `deploy/windows-server/run.py`). App-only OAuth2 client-credentials via MSAL;
  machine-level env vars for tenant/client/secret-or-cert.

The gap between this and "an Azure service" is **hosting model + multi-tenancy +
certification**, not the engine.

---

## 3. Target: the Azure-native OrgPath service

The design principle is **lift the existing engine onto managed Azure compute
and storage, change nothing about the control-plane/data-plane line.** Each
existing component has a near-1:1 managed-Azure counterpart.

### 3.1 Component mapping (current repo → Azure-native)

| Concern | Today (repo) | Azure-native target | Notes |
|---|---|---|---|
| Control-plane host | FastAPI on Windows Server + IIS | **Container Apps** (or AKS) for the API/console; **Functions** for the scheduled drift loop | The runtime is already transport-agnostic; the host is swappable. |
| Codebook (desired-state SSOT) | `codebook.yaml` in-package | **Cosmos DB** (per-tenant container) or **Blob Storage** with versioning | Keep YAML as the authoring format; Cosmos/Blob is the served, versioned copy. Schema validation (`codebook.schema.json`) stays the gate. |
| Drift loop | `uiao orgtree govern` (CLI / runtime) | **Functions** (timer-triggered) or a **KEDA-scaled** Container Apps job | Six-phase loop is already idempotent + stateless → cloud-native by construction. |
| Entra/Graph writeback | `GraphTransport` (httpx + MSAL) | Same code, auth swapped to **Managed Identity** (federated credential → Graph `.default`) | Removes client-secret env vars; secrets → Key Vault / MI. |
| Arc/ARM writeback | `ArmTransport` (ARM-audience token) | Same code, **Managed Identity** with an Azure RBAC role (Tags Contributor, least privilege) on the Arc scope | Already the documented least-privilege model in the impl bundle. |
| Evidence / telemetry | UIAO_174 events → `GovernanceReport` JSON (`--out`) | **Log Analytics / Sentinel** (custom tables) + **immutable Blob** for the report | Telemetry is already structured events; emit to Log Analytics instead of (or alongside) a file. |
| Read-only console | `/orgpath` Jinja2 (ADR-084 §C7) | Same console in Container Apps; **optionally** Azure Portal blades (§4) | Read-only invariant is preserved verbatim. |
| Provider adapters | Phase 5 consumer adapters + transports | **Extension modules** loaded by the Platform Services Layer (UIAO_102) | Mirrors how Azure Policy/Arc/Automation load providers. |
| Secrets / credentials | Machine env vars (MSAL client-credentials) | **Managed Identity** first; **Key Vault** for anything that must be a secret | Net security improvement over env-var secrets. |

### 3.2 Architecture, plane by plane

**Managed control plane.** The `OrgPathGovernanceRuntime` and Phase 5 adapters
run as a containerized service (Container Apps / AKS). The read-only console
(ADR-084 §C7) is served from the same image. The scheduled reconcile loop
(assess → govern dry-run → optional gated writeback → capture, per the impl
bundle Guide 7) runs as a timer-triggered Function or KEDA job. Nothing in the
loop holds session state, so horizontal scale is free.

**Desired-state store (Codebook).** YAML stays the human authoring format and
the schema gate (`uiao orgtree validate codebook` in CI). The *served* Codebook
lives in Cosmos DB (one container per tenant) or versioned Blob Storage so the
control plane reads per-tenant desired state without a redeploy. Reserved slots
(11–15) still refuse to write without a declared facet (governed PR), exactly as
today.

**Writeback via Managed Identity.** The single biggest security upgrade. The two
existing transports already separate the Graph and ARM audiences; the only
change is the credential source: a **user-assigned Managed Identity** with a
federated credential acquires the Graph `.default` token (admin-consented
application permissions still gate the actual write), and an Azure RBAC role
assignment (least-privilege **Tags Contributor** on the Arc scope) authorizes
the ARM tag writes. Client secrets in env vars go away.

**Evidence pipeline.** UIAO_174 telemetry events stream to a Log Analytics
custom table (and onward to Sentinel for correlation/alerting); the full
`GovernanceReport` lands in an immutable (WORM) Blob container as the audit
artifact, traceable to the Codebook version that classified it. This is the
direct cloud analogue of the impl bundle's `--out evidence/orgpath-$(date).json`
pattern.

**Provider adapters as extensions.** New providers (SailPoint NERM, CyberArk,
Infoblox, Cisco ISE / Aruba ClearPass / Entra RADIUS) are incorporated through
the Platform Services Layer (UIAO_102) as extension modules — bound to one
control-plane slot, exposing `plan/apply/reconcile`, carrying OrgPath, and
advertising governance metadata + a ladder rung (ADR-092 §2). This is the same
extension pattern Azure Policy/Arc use for their providers.

---

## 4. Making it "active" in the M365 / Azure portals

"Active" means OrgPath facets actually drive native enforcement, and the portals
reflect it:

- **Dynamic groups** update automatically off facet predicates
  (`membershipRule` composed from `extensionAttribute*` — Model C boolean
  predicates, not `-startsWith` on a composite string).
- **Conditional Access** targets facet predicates ("privileged Finance users get
  phishing-resistant MFA" → `(extensionAttribute2 -eq "Finance") and
  (extensionAttribute10 -eq "Privileged")`).
- **Intune** dynamic groups target the device `onPremisesExtensionAttributes`
  OrgPath writes (ADR-038 / impl bundle Guide 5).
- **Azure Policy** targets the Arc ARM **tags** OrgPath writes (impl bundle
  Guide 6).
- **NAC/AAA** uses OrgPath in the network slot (Book_17 — ISE / ClearPass /
  Entra RADIUS).

**Why this is technically easy:** every value OrgPath writes is **native** —
Entra extension attributes, Arc tags, dynamic-group membership rules, CA
predicates, Azure Policy targeting. The portals already read these. **No portal
modification is required** for OrgPath to *work*; it simply feeds the existing
surfaces better, validated, drift-resisted data.

**The only hard part — first-class portal surfaces.** OrgPath-*branded* blades
(a facet explorer, a drift-findings blade, a reorg-simulation blade, a
governance-evidence blade) inside the Entra/Azure portals require Microsoft
product-team buy-in. Two honest tiers:

1. **Without Microsoft (available now).** OrgPath runs as the control plane and
   the data shows up in the *existing* native surfaces — it appears as "magic
   behind the scenes." The repo already ships the read-only `/orgpath` console
   (ADR-084 §C7) as the OrgPath-side surface; it can be hosted in Azure
   (Container Apps) and linked from a tenant's admin tooling.
2. **With Microsoft (partnership).** First-class blades inside the portals.
   Strictly additive — they *read* the same native values; they don't change the
   architecture. This is the partnership track, out of scope for the engineering
   port.

---

## 5. The actuation ladder in Azure terms (and why the federal ceiling holds)

Going managed-PaaS does **not** loosen the L0–L4 ladder (ADR-092 §3) or the
**federal L3 ceiling** (§4). If anything, Azure-native makes the ladder *easier
to accredit*, because each control is a named Azure primitive an authorizing
official recognizes:

| Rung | Behavior (ADR-092 §3) | Azure-native realization |
|---|---|---|
| L0 Record | Desired state recorded only | Codebook in Cosmos/Blob |
| L1 Observe | Actual collected, drift detected, read-only | Timer Function snapshots tenant → drift classified → Log Analytics |
| L2 Advise | Change-set generated, surfaced, no writes | `GovernanceReport` rendered in console / Sentinel workbook |
| L3 Gated | Human approves, then UIAO writes via provider API | **Approval gate** (Logic App / Sentinel SOAR / manual) → MI-authenticated `apply` |
| L4 Autonomous | Loop closes without a human, within guardrails | Function dispatches `apply` **only** for enumerated low-blast-radius, rollback-capable op classes; `halt_on_critical` still suspends the scan on any P1 |

**The L3 default ceiling is non-negotiable doctrine, hosting aside.** L4 is
permitted only when *all* of ADR-092 §4 holds (op class enumerated in a
governance-approved decision, `blast_radius` low, `rollback_capable` true, clean
advisory record, `halt_on_critical` in force). High-blast-radius ops (tenant-wide
role assignment; a VLAN change touching thousands of devices) are **L3-capped
permanently**. Bidirectional truth (§5) still applies: an autonomous loop may
only *force desired onto actual*; *promote-actual* and *quarantine* always
require human disposition.

> **ADR-092 Consequences, restated for the Azure context.** "Actuation means
> write access to the customer's crown-jewel identity, network, and security
> systems… the actuator demands the strongest authz, immutable audit, dry-run,
> rollback, and break-glass of anything in the substrate. This must be designed
> before any op class promotes to L3, not after." Managed Identity + Key Vault +
> immutable Log Analytics/Blob + the existing dry-run default + `halt_on_critical`
> are the Azure-native expression of that requirement — but the **actuator
> security design is a prerequisite, not a follow-on.**

---

## 6. What is actually hard

Engineering is the easy part. The hard parts, in rough order:

1. **Multi-tenant scaling.** The current engine is single-tenant by deployment
   (one app registration, one Codebook, machine-level credentials). A managed
   service needs per-tenant isolation of the Codebook, credentials (per-tenant
   Managed Identity / federated credentials), evidence, and blast radius. This is
   the largest genuinely-new engineering work.
2. **Sovereign-cloud boundaries.** Already *partially* solved: the transports are
   cloud-aware (`resolve_graph_base` / `resolve_arm_base`, `--cloud`
   commercial/gcc-high/dod), and ADR-033 establishes commercial-audience serving
   GCC-Moderate. A managed service must enforce that a commercial-audience token
   never reaches a sovereign endpoint, per-tenant — the code path exists; the
   multi-tenant *enforcement* of it is the work.
3. **Azure Marketplace certification.** Transactable managed-app / SaaS offer
   packaging, partner attestations, support SLAs.
4. **FedRAMP authorization.** The federal vertical is the most mature adapter
   pack (AGENTS.md), and the deployment boundary today is **GCC-Moderate (M365
   SaaS)** with two named Commercial exceptions (ADR-059). A managed Azure
   service introduces an *Azure* boundary distinct from the M365 SaaS boundary —
   it would require its own authorization path and its own `gcc-boundary` enum
   in lockstep with an authorizing ADR.
5. **Microsoft product politics (the real obstacle).** OrgPath unifies Entra,
   Intune, Arc, Azure Policy, Conditional Access, NAC, Defender, and Sentinel —
   products Microsoft keeps as separate teams. Native first-party adoption means
   Microsoft reorganizing around a unification it doesn't currently sell. This is
   why OrgPath is durable IP, and why the partnership track is the slow one.

### External build estimates (CoPilot — not canon)

The originating CoPilot analysis offered the following figures. They are
**external estimates**, recorded here for traceability, **not** repo
commitments and **not** validated against any internal plan:

- 6–9 months to a production-grade Azure PaaS version
- 3–4 engineers if the UIAO codebase is reused
- 12–18 months to FedRAMP Moderate authorization

These are plausible *given* the baseline in §2 (the engine exists), but any real
commitment needs a phased plan (§7) and an actuator-security design first.

---

## 7. Suggested phasing

A conservative, doctrine-preserving sequence. Each phase is independently
shippable and never crosses the control-plane/data-plane line.

1. **Phase A — Lift, single-tenant.** Containerize the existing API + console;
   move the drift loop to a timer Function; swap MSAL client-secret auth for
   Managed Identity (Graph + ARM). Codebook still in-package. **No new behavior**
   — same engine, Azure host. Validates the port with zero doctrine change.
2. **Phase B — Externalize state + evidence.** Codebook → Cosmos/Blob (per-tenant
   ready, single-tenant used); UIAO_174 telemetry → Log Analytics/Sentinel;
   `GovernanceReport` → immutable Blob. Now it *looks* like an Azure governance
   service.
3. **Phase C — Actuator security + L3 gating.** Design the actuator (authz,
   immutable audit, rollback, break-glass) **before** enabling any live write in
   the service. Wire the L3 approval gate (Logic App / SOAR). This is the ADR-092
   prerequisite, made concrete.
4. **Phase D — Multi-tenant.** Per-tenant isolation of Codebook, identity,
   evidence, blast radius, and sovereign-boundary enforcement. The hardest
   engineering phase.
5. **Phase E — Marketplace + authorization.** Managed-app/SaaS packaging;
   FedRAMP path against the *Azure* boundary (new `gcc-boundary` enum + ADR).
6. **Phase F (parallel, partnership) — Portal blades.** First-class
   OrgPath surfaces inside the portals. Gated entirely on Microsoft buy-in;
   strictly additive; never on the critical path for the service working.

---

## 8. What this draft does NOT change (invariants to preserve)

- **Control plane governs data plane (ADR-092 §1).** Azure hosting does not put
  OrgPath in any runtime path. It still never authenticates, routes, terminates,
  or issues the production credential.
- **Incorporate, don't compete (ADR-092 §2).** Azure-native OrgPath still rides
  on top of Entra/Intune/Arc/ISE/Infoblox; it reconciles their state and emits
  evidence. It does not reimplement them.
- **Read-only console stays read-only (ADR-084 §C7).** The `/orgpath` UI
  observes; it never writes.
- **Dry-run default + `halt_on_critical` (ADR-040 / UIAO_163).** Preserved
  verbatim; managed hosting does not change the safety defaults.
- **L3 federal ceiling (ADR-092 §4).** Hosting model is irrelevant to the
  autonomous-actuation ceiling.
- **Two distinct write audiences (AGENTS.md / impl bundle).** Graph and ARM keep
  separate transports/audiences under Managed Identity, same as today.

---

## 9. Open questions (each needs an ADR before it becomes real)

1. **New Azure deployment boundary.** A managed Azure service is a boundary
   distinct from the current GCC-Moderate M365 SaaS boundary — needs a new
   `gcc-boundary` enum + authorizing ADR (per the AGENTS.md lockstep rule).
2. **Codebook store of record.** Does Cosmos/Blob become authoritative at
   runtime, or is the in-package YAML still SSOT with the store as a derived
   cache? (SSOT discipline, AGENTS.md Operating Principle 1.)
3. **Actuator security design.** Required *before* any service-side live write
   (ADR-092 Consequences). Its own ADR.
4. **Multi-tenant model.** Per-tenant identity/isolation/blast-radius — doctrine
   plus design.
5. **Hosting target.** Container Apps vs AKS vs Functions split — an
   implementation ADR, not doctrine, but worth pinning.

---

## 10. References (provenance)

- [ADR-092 — Active Governance](../src/uiao/canon/adr/adr-092-active-governance.md)
  — control/data plane, incorporation contract, L0–L4 ladder, L3 ceiling,
  bidirectional truth, actuator-security consequence.
- [ADR-084 — Phase 5 Consumer Architecture](../src/uiao/canon/adr/adr-084-phase5-consumer-architecture.md)
  — Codebook-as-shared-dependency; read-only console (§C7).
- ADR-038 (device-plane OrgPath), ADR-078 (15-facet Model C), ADR-040 (drift
  engine), ADR-033 (cloud boundary), ADR-059 (Commercial exceptions).
- [`control-planes.yml`](../src/uiao/canon/data/control-planes.yml) — six
  provider-neutral control-plane slots.
- UIAO_151 (Codebook), UIAO_163 (drift engine), UIAO_174 (governance telemetry).
- Code: `uiao.governance.orgpath_runtime`, `uiao.adapters.graph_transport`,
  `uiao.adapters.arm_transport`, `uiao.api.web.console`,
  `deploy/windows-server/`.
- Uploaded source bundles (author: Michael Stratton): *Platform Bundle* (Active
  Governance customer page; Git-server build), *OrgPath Narrative Bundle*
  (Books 01–17), *OrgPath Implementation Bundle* (Guides 1–7: prerequisites,
  Codebook, AD assessment, dry-run governance, Intune writeback, Arc writeback,
  operate/troubleshoot).
- External estimates (§6) attributed to the originating CoPilot analysis — not
  canon, not a repo commitment.
