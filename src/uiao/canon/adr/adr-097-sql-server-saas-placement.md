---
adr_id: adr-097
title: "SQL Server transformation placement — same control plane, adjacent execution"
status: PROPOSED
decided: 2026-06-07
deciders: Michael Stratton
updated: 2026-06-07
next_review: 2026-12-07
review_trigger: The SQL Server transformation is re-implemented from PowerShell into an in-process Python adapter; a customer requires the migration to run from UIAO-hosted infrastructure rather than an in-boundary runner; the control-plane/data-plane lane discipline of ADR-092 is revised; SQL Server itself ships a native Entra-only auth path that removes the host-level migration step
impact: "Settles where the SQL Server Identity Transformation vertical runs relative to the UIAO Azure SaaS (ADR-096): its governance — tenant onboarding, identity model, evidence/KSI, ARM/managed-identity orchestration — lives in the SAME SaaS control plane; its host-level execution (auth audit, Arc enrollment, login migration on the live engine) runs ADJACENT, in the customer's boundary on the Arc-connected host, orchestrated by the control plane and returning signed evidence. Registers `sql-server` in the modernization adapter registry with runner-class on-prem-self-hosted to encode the adjacent-execution lane. No new control plane; no in-container database access."
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-097-sql-server-saas-placement.html
---

# ADR-097: SQL Server transformation placement — same control plane, adjacent execution

## Status

**PROPOSED** — June 7, 2026

## Context

The **SQL Server Identity Transformation** is a mature vertical in the repo:
a narrative companion (Books 01–10) and an executable implementation
companion driven by the `UIAOSqlServerMigration` PowerShell module. It takes a
SQL Server estate off Windows/NTLM authentication and onto Entra-backed
identity via **Azure Arc + a managed identity** (ADR-002, ADR-091), with a
read-only authentication audit, an estate-consolidation gate, an evidence
model, and KSI/CCM-BIR closure.

With the UIAO Azure SaaS now real (ADR-096), the open question is **where this
vertical runs**: inside the same multi-tenant SaaS, or as an adjacent service.
The question is sharper than it looks because the vertical is not one thing —
it has a governance half (discovery, identity mapping, evidence, orchestration)
and an execution half (operations against a live SQL engine that require
sysadmin on that engine and network reachability into the customer estate).

The repo already answers the general form of this question. **ADR-092**
establishes UIAO as a *control plane* that governs provider *data planes* and
"never sits in the runtime data-plane path." **ADR-096** hosts that control
plane on Azure Container Apps with per-tenant managed-identity ARM/Graph
transports. The Azure-native service draft positions every provider as a
*slot* in one control plane, not as a separate product.

## Decision

**SQL Server transformation is the *same* governance plane and an *adjacent*
execution lane. It is not a separate SaaS, and it does not execute inside the
multi-tenant container.**

**1. Same SaaS — the control + evidence plane.**
The governance of the vertical lives in the existing UIAO Azure SaaS:

- tenant onboarding and `data_namespace` isolation (a customer's SQL estate is
  governed under their existing tenant);
- the identity model — "SQL logins → Entra principals" is core OrgPath /
  identity-plane governance, not a sidecar;
- the ARM + managed-identity transport already used for the Arc device plane;
- the one canon-anchored evidence fabric (auth-audit + migration evidence →
  KSI / CCM-BIR / ATO reciprocity).

It maps onto the **server (Arc/ARM) case of the endpoint plane** in
`control-planes.yml`, exactly as Intune, Arc, and NAC are incorporated.

**2. Adjacent — the in-boundary execution lane.**
The host-level, change-making operations — the authentication audit reads, Arc
enrollment, and **login migration on the live engine** — run **in the
customer's boundary**, on the Arc-connected host via its managed identity (a
machine extension or a customer-run PowerShell runner). The SaaS control plane
*orchestrates* them (`plan` / `apply` / `reconcile`, dry-run by default) and
*ingests* the signed evidence they return. The multi-tenant container never
opens a connection to a customer's SQL engine.

**3. Registry encoding.**
`sql-server` is registered in `modernization-registry.yaml` as a
`modernization` adapter with **`runner-class: on-prem-self-hosted`** — the
registry field that records the adjacent-execution lane — and
`tenancy: per-customer`. Status `proposed` until the PowerShell tooling is
wired to the control plane as a runtime adapter.

## Why not the alternatives

**Why not "fully same" (run the migration inside the Container App):**

1. **Reachability** — SQL instances live in the customer network / on-prem /
   Arc; the shared container cannot and should not reach them inline.
2. **Blast radius** — login migration needs **sysadmin on the engine**; that
   credential must live in the customer boundary, never in a multi-tenant
   service. Cross-tenant inline DB access is an unacceptable blast radius.
3. **Runtime mismatch** — `UIAOSqlServerMigration` is PowerShell; the SaaS is
   Python/FastAPI. The execution lane is a runner/extension, not the API
   container.
4. **Lane discipline (ADR-092)** — UIAO governs and observes; it does not sit
   in the runtime data-plane path.

**Why not a separate / adjacent *SaaS* (its own control plane):**

1. It would duplicate onboarding, tenancy, auth, and the control plane.
2. It would **fracture the evidence + ATO-reciprocity chain** — the unified
   canon-anchored evidence fabric is the whole value.
3. SQL login → Entra identity is core identity-plane governance, not a
   standalone product; it is a *slot* in the one plane.

## Consequences

### Positive

- One control plane, one evidence chain, one onboarding flow for SQL as for
  every other provider.
- The adjacent runner keeps sysadmin credentials and live-engine access inside
  the customer boundary — the correct least-privilege and blast-radius posture.
- The placement is encoded in canon (`runner-class: on-prem-self-hosted`), not
  just prose.

### Negative / trade-offs

- Requires an **execution-runner contract** (Arc machine extension or
  customer-run runner) the control plane dispatches to and ingests from — net
  new surface beyond the current PowerShell-run-by-hand model.
- The PowerShell tooling must grow a non-interactive, evidence-emitting run
  mode the orchestrator can drive.

### Security

- The migration credential (sysadmin) never leaves the customer boundary.
- Evidence returned to the SaaS is signed (existing evidence model), so the
  control plane can trust ingested results without holding engine credentials.

## Implementation

- Canon: this ADR + `sql-server` entry in `modernization-registry.yaml`.
- Docs: a placement section in the Azure SaaS operator guide
  (`docs/customer-documents/platform/azure-saas.qmd`) + architecture figure.
- Follow-up (not this ADR): the execution-runner contract and a Python
  orchestration adapter that drives `UIAOSqlServerMigration` and ingests its
  evidence.

## References

- [ADR-096](adr-096-azure-saas-architecture.md) — Azure SaaS architecture.
- [ADR-092](adr-092-active-governance.md) — active governance / lane discipline.
- [ADR-091](adr-091-sql-server-authentication-transformation.md) — SQL Server auth transformation.
- [ADR-002](adr-002-arc-entra-join-no-domain-join.md) — Arc + managed identity.
