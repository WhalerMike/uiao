---
adr_id: adr-092
title: "Active Governance — Control-Plane-Governs-Data-Plane, Provider Incorporation, and the Actuation Maturity Ladder"
status: ACCEPTED
decided: 2026-06-02
deciders: Michael Stratton
updated: 2026-06-14
next_review: 2026-12-01
review_trigger: A control-plane slot promotes an adapter to L4 autonomous reconciliation; a new provider is incorporated that does not fit the enforcement-adapter contract; the federal autonomous-actuation posture (L4 ceiling) is revisited; UIAO_101/UIAO_102 are revised; ADR-066 transport lane discipline is amended
impact: "Establishes Active Governance as UIAO's product posture: the substrate is an active reconciliation control plane that governs provider data planes, not a passive registry. Names the control-plane/data-plane boundary, the provider-incorporation contract (enforcement/evidence adapter bound to a control-plane slot), and the L0-L4 actuation maturity ladder with a federal L3 default ceiling. Gives the loosely-used term 'Active Governance' a single canonical home. Doctrine only; cites and unifies existing machinery (ADR-036-040, ADR-066, ADR-074, UIAO_101, UIAO_102, control-planes.yml) without changing runtime, schema, or registry entries. Positions the customer Platform section as the reader-facing home of Active Governance and Book_17 as the first worked instance."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-092-active-governance.html
---

# ADR-092: Active Governance — Control-Plane-Governs-Data-Plane, Provider Incorporation, and the Actuation Maturity Ladder

## Status

**ACCEPTED** — June 2, 2026

This ADR is doctrine. It fixes UIAO's product posture and the boundary between what UIAO governs and what third-party providers own. It does not change any runtime behavior, schema, or registry entry; it names and unifies machinery that already exists.

## Context

UIAO is frequently described — including in its own earlier framing — as an "out-of-path registry": a single source of truth that records desired state and reports divergence. That description is no longer accurate, and treating it as the ceiling of UIAO's ambition understates what the substrate already does.

**The active machinery already exists.** UIAO is, in practice, an active reconciliation control plane:

- **Change-making adapters** with a `plan / apply / reconcile` shape are canon (ADR-036 dynamic groups, ADR-037 administrative units, ADR-038 device-plane OrgPath, ADR-039 policy targeting). They write to provider management surfaces through the provider's own API.
- **A reconciliation loop** is canon: the ADR-040 OrgTree Drift Detection Engine is a six-phase orchestrator (Snapshot, Compare, Classify, Alert, Remediate, Verify) with `dry_run=True` by default, `halt_on_critical` stop-the-line behavior, per-facet `auto_remediate` flags, and governance-review gating for high-blast-radius operations.
- **A platform for it** is canon: [UIAO_101](../specs/Platform-Overview.md) §4 defines a Compliance Orchestrator with closed-loop automation, and [UIAO_102](../specs/Platform-Services-Layer.md) defines a Platform Services Layer whose Enforcement Marketplace already has adapters advertise `controls_supported`, `side_effects`, `blast_radius`, and `rollback_capable`, with some marked **advisory only**.
- **The provider slots** are canon data: [`control-planes.yml`](../data/control-planes.yml) enumerates six provider-neutral control planes (identity, addressing, network, telemetry, endpoint, security), each naming component roles that real providers fill.

**Book_17 is the first fully worked instance.** The network-admission narrative ([Book_17](../../../../docs/customer-documents/orgpath-narrative/Book_17.qmd), governed by ADR-073) incorporates Cisco ISE, Aruba ClearPass, and the Entra RADIUS Proxy as governed AAA providers through the `OrgTreePolicyTargetingAdapter` — `plan / apply / reconcile`, dry-run by default, with missing/phantom operations routed to human review. It governs the providers; it does not replace them.

**What is missing is the doctrine that binds these together.** Three positions have no single canonical home:

1. The **boundary** — what UIAO governs versus what the provider owns at runtime. ADR-066 stated this as "lane discipline" for the transport plane specifically; it has never been generalized.
2. The **provider-incorporation contract** — the uniform way a third-party provider is *incorporated* (governed) rather than *competed with* (reimplemented).
3. The **ceiling on autonomous actuation** — how far the loop may close without a human, especially in a federal boundary.

The term "Active Governance" is already used loosely across roughly nine documents with no definition. This ADR gives it a home.

## Decision

Six positions.

### 1. UIAO is the control plane; the provider remains the data plane

UIAO **governs**: it holds desired state, observes actual state, classifies drift, and reconciles toward intent. The provider **executes** at runtime: it authenticates, authorizes, routes, resolves, or stores. A modernization-class adapter **MAY** make change-making API calls into a provider's management surface (as `entra-id` does for identity). It **MUST NOT** become the runtime data-plane component: it must not sit inline in the authentication or request path, terminate sessions or tunnels, route packets, issue the production credential, or hold a data-plane position.

This generalizes the ADR-066 transport-plane lane discipline to **every** control plane in `control-planes.yml`. Active Directory conflated the directory (truth) with the domain controller (the in-path enforcer); the modern split keeps them separate, and UIAO is deliberately on the truth-and-reconciliation side of that line.

### 2. Providers are incorporated, not competed with — the provider-incorporation contract

A third-party provider is brought under governance as an evidence/enforcement adapter through the Platform Services Layer (UIAO_102), bound to exactly one control-plane slot (`control-planes.yml`). To be incorporated, an adapter **MUST**:

1. **Bind to one control-plane slot** — identity, addressing, network, telemetry, endpoint, or security.
2. **Expose `plan / apply / reconcile`** — the ADR-036 verb shape; `plan` computes the ordered operation list with no writes, `apply` executes (dry-run by default), `reconcile` is plan-plus-apply.
3. **Carry OrgPath** — every governed object expresses its OrgPath, so the provider's state is addressable in the same terms as every other plane.
4. **Advertise governance metadata** — `controls_supported`, `side_effects`, `blast_radius`, `rollback_capable` (UIAO_102 §4).
5. **Declare a governance mode** — its current rung on the ladder in §3, per operation class.

UIAO does not reimplement the provider's function. It reconciles the provider's state against canon and emits evidence. Worked and candidate instances: Cisco ISE / Aruba ClearPass / Entra RADIUS for network admission (Book_17, ADR-073); Infoblox for addressing (Book_14); SailPoint NERM for identity (ADR-059); CyberArk for privileged access; the SD-WAN/SASE fabric for transport (ADR-066). Each is a seat-holder in a slot, never displaced by UIAO.

### 3. The actuation maturity ladder (L0–L4)

Every governed operation class sits on a five-rung ladder. The rung is a declared property of the adapter, not a global setting:

| Rung | Name | Behavior |
|---|---|---|
| **L0** | Record | Desired state is recorded in canon only. |
| **L1** | Observe | Actual state is collected and drift is detected. Read-only. |
| **L2** | Advise | The specific corrective change-set is generated and surfaced; no writes. ("Advisory only," UIAO_102 §4.) |
| **L3** | Gated actuation | A human approves; UIAO then executes the change-set through the provider API. Dry-run is the default; writes require explicit per-scan approval. |
| **L4** | Autonomous reconciliation | UIAO closes the loop without a human in each cycle, within declared guardrails. |

This ladder is the same gradient the ADR-040 engine already encodes (`dry_run` default, per-facet `auto_remediate`, governance-review gating) and that UIAO_102's "advisory only" mode names; it is now explicit and uniform across providers.

### 4. The autonomous (L4) ceiling — federal default is L3

**The default production ceiling is L3 (human-approved actuation).** L4 autonomous reconciliation is permitted for an operation class **only when all** of the following hold:

1. the operation class is explicitly enumerated in a Governance-Plane-approved decision (an ADR or a governance-board record);
2. `blast_radius` is **low**;
3. `rollback_capable` is **true**;
4. the adapter has a clean dry-run/advisory record over a defined observation window; and
5. `halt_on_critical` remains in force — any finding at or above P1 suspends autonomous remediation for the entire scan until a human resolves it (ADR-040).

High-blast-radius operation classes are **L3-capped permanently** and always route to governance review — for example tenant-wide (`directoryScopeId=/`) role assignment (ADR-040, UIAO_154), and the missing/phantom NAC operations whose single wrong VLAN can affect thousands of devices (Book_17, ADR-073). This codifies the existing auto-remediate / governance-review split rather than inventing a new control.

### 5. Bidirectional truth — actual may be promoted to desired

When actual diverges from desired, reconciliation is not always "force desired onto actual." A legitimate emergency change may make *actual* correct and *desired* stale. Each finding therefore admits three operator dispositions, mirroring the ADR-074 re-ratify / re-direct / retire pattern:

- **Promote actual to desired** — the change was legitimate; update canon to match reality.
- **Force desired onto actual** — the divergence is drift; correct it through the provider API.
- **Quarantine** — neither yet; hold for review.

Autonomous (L4) reconciliation may only **force desired onto actual**, and only for its enumerated low-risk classes. **Promote-actual** and **quarantine** always require human disposition. This prevents an autonomous loop from either stomping a legitimate change or rubber-stamping drift into canon.

### 6. Platform is the home of Active Governance

The **active platform** is the composition of the Compliance Orchestrator loop (UIAO_101 §4), the Platform Services Layer provider-incorporation surface (UIAO_102), and the control-plane slots (`control-planes.yml`), articulated for readers in the customer [Platform](../../../../docs/customer-documents/platform/index.qmd) section. The infrastructure-runbook Platform pages (the Gitea-on-Windows-Server build, ADR-041) describe the **substrate the active platform runs on** — they are the ground, not the active platform itself. The customer Platform section gains an Active Governance page that tells this story and maps each control-plane slot to its incorporated provider(s) and governance mode.

## Consequences

**Positive.**

- "Active Governance" gets one definition every other artifact can cite. The term stops drifting.
- Every provider is incorporated through one uniform contract (slot + verbs + OrgPath + governance metadata + rung), so adding a provider is declarative rather than bespoke.
- The active surface is **accreditable rung-by-rung** — an authorizing official can be told "this op class is at L2, roadmap to L3," which is a sentence an AO can sign. A binary "it enforces things" is not.
- Book_17 retro-fits cleanly as the reference instance; Book_14 (addressing) and the forthcoming Identity-Governance / PAM books inherit the same frame.
- It draws the line that keeps UIAO from being a competitor Microsoft or any incumbent would crush: UIAO governs the data plane it does not own.

**Negative / costs.**

- Actuation means write access to the customer's crown-jewel identity, network, and security systems. The capability that makes Active Governance valuable is also the highest-value attack surface UIAO will ever ship; the actuator demands the strongest authz, immutable audit, dry-run, rollback, and break-glass of anything in the substrate. This must be designed before any op class promotes to L3, not after.
- Every incorporated provider adapter must now declare governance metadata and a rung; existing adapters are retro-annotated.
- The bidirectional-truth disposition (§5) adds an operator decision to each finding that cannot be auto-classified.

**Neutral.**

- Doctrine only — no runtime, schema, or registry change lands with this ADR (consistent with ADR-085, ADR-089).
- Generalizes ADR-066 (transport lane discipline) to all planes; complements ADR-040 (the loop) and ADR-074 (bidirectional truth); operationalizes the positioning of ADR-085 (Active Governance is the product) and gives UIAO_101/UIAO_102 their doctrinal anchor.

## Alternatives considered

- **In-path enforcer (rebuild the domain controller).** Rejected. Re-creates the single point of failure, latency, blast radius, and vendor lock-in that the cloud era deliberately dismantled — and it is unachievable anyway, because the incumbent providers (Entra, Intune, Arc, ISE, ClearPass) will not delegate their runtime path to UIAO.
- **Stay a passive registry.** Rejected. Governance without a closed loop is an audit tool that describes the problem; it does not govern it. The machinery to close the loop already exists (ADR-036–040); declining to name it as doctrine wastes it.
- **Per-provider bespoke integration.** Rejected. It fragments the model into one design per vendor. The uniform adapter contract (§2) plus the control-plane slots keep one governance model across every provider.

## References

- [ADR-036](adr-036-dynamic-group-provisioning.md), [ADR-037](adr-037-admin-unit-provisioning.md), [ADR-038](adr-038-device-plane-orgpath.md), [ADR-039](adr-039-policy-targeting.md) — the `plan / apply / reconcile` change-making adapters.
- [ADR-040](adr-040-drift-engine.md) — the six-phase reconciliation engine; source of `dry_run`, `halt_on_critical`, and the auto-remediate / governance-review split.
- [ADR-066](adr-066-application-aware-networking-and-token-bound-transport.md) — transport-plane lane discipline, generalized here to all planes.
- [ADR-073](adr-073-policy-targeting-nac-third-transport.md) — network-admission incorporation of ISE / ClearPass / Entra RADIUS (the Book_17 worked instance).
- [ADR-074](adr-074-drift-ssot-contention.md) — bidirectional truth (re-ratify / re-direct / retire).
- [ADR-085](adr-085-universal-enterprise-positioning.md) — UIAO as a universal enterprise governance product; Active Governance is that product's posture.
- [UIAO_101 Platform Overview](../specs/Platform-Overview.md) §4 — Compliance Orchestrator / closed-loop automation.
- [UIAO_102 Platform Services Layer](../specs/Platform-Services-Layer.md) — Plugin System and Enforcement Marketplace (the incorporation surface).
- [`control-planes.yml`](../data/control-planes.yml) — the six provider-neutral control-plane slots.
- [Book_17 — OrgPath at the Network Edge](../../../../docs/customer-documents/orgpath-narrative/Book_17.qmd) — the first worked instance of Active Governance.
