---
adr_id: adr-138
title: "Ephemeral Governance Engine — decompose the substrate by lifetime, not by function"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-08-25
next_review: 2027-02-25
review_trigger: The AGD's LDAP-bound consumer base is characterised (this ADR turns on that answer — see §Decision 5); a deployment requires a standing HTTP surface the ephemeral posture cannot serve; ADR-096's multi-tenant SaaS tier acquires a paying tenant (the cost/benefit this ADR defers becomes concrete); ADR-004's Workload Identity Federation default is weakened or an exception is granted; the L3 ceiling in ADR-092 §4 is revisited; a control-plane compromise or near-miss occurs in any UIAO deployment
supersedes: null
superseded_by: null
amends:
  - adr-092-active-governance.md
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-138-ephemeral-governance-engine.html
impact: "Sets UIAO's default deployment posture to an ephemeral engine: canon stays a git repository under ADR-090 HA, the drift/OSCAL/KSI engine runs as CLI in CI under per-run federated credentials with no standing privilege, and actuation routes through in-boundary actuators the customer has already accredited (the ServiceNow MID Server) rather than a UIAO-operated worker fleet. Amends ADR-092 §6, which located the active platform in a hosted composition, by declaring that the platform is a posture rather than a running service. Answers the 2026-08-21 internal HA/redundancy review, whose Tier-0 master-key finding is accepted and whose four-host remedy is not: every role in that remedy is already filled by a component under accreditation. Explicitly does NOT retire the ADR-096 SaaS tier or the ADR-100 Active Governance Directory — the hosted tiers become justified-per-deployment options rather than the default, and the AGD's fate is deferred to a named open question. Registry- and doctrine-shaped; no runtime, schema, or registry-content change lands with this ADR."
---

# ADR-138: Ephemeral Governance Engine — decompose the substrate by lifetime, not by function

## Status

**PROPOSED** — 2026-08-25

This ADR is doctrine. It fixes the default deployment posture of the substrate
and the boundary between what must run continuously and what must not run at
all between invocations. It changes no runtime code, schema, or registry entry.

## Context

Four threads converge here.

### Thread 1 — an internal review found the platform server is a master key

An internal cybersecurity and resilience review of the UIAO Platform
(13 documents, 2026-08-21, produced with Microsoft Copilot and filed under
`UIAO-Platform-HA-Redundancy`) reached one load-bearing finding across seven
numbered items: the platform operates as a **single Tier-0 control plane**
bridging on-premises Active Directory and the Entra/Azure cloud, holding
wide-ranging administrative credentials and API keys, and therefore
constitutes *"a single master key for the entire IT environment."* Its
sharpest formulation is that conventional redundancy does not help — an
attacker at control-plane level can *"dismantle recovery and security first,
then cause damage,"* so multiple regions and multiple domain controllers
mitigate nothing.

**That finding is correct and this ADR accepts it without qualification.**
Even at rung L3 with federated credentials, a long-lived host that can reach
Microsoft Graph, Intune, an IPAM grid and network AAA is the highest-value
target the substrate will ever present.

### Thread 2 — the review's remedy pays a tax rather than removing the premise

The same review proposed a four-role decomposition: a canonical authority
server, one or more policy-execution workers, a read-only compliance monitor,
and supporting services (an HSM or vault, break-glass access, an isolated
backup node) — plus PAW/jump-host administration and mutually-authenticated
transport between components.

The architecture is sound. Its own conclusion is the problem: *"the authority
remains a Tier-0 asset that must be heavily protected — splitting roles does
not eliminate the need to secure the core,"* and the decomposition
*"raises the bar for engineering and operations."* Four hardened hosts each
need the hardening, patching, monitoring and configuration-drift control that
the exercise exists to reduce.

The stronger reading of the review's own findings is that **its findings 1, 2,
3 and 5 are all consequences of a host that holds standing privilege
continuously.** They are not properties of governance; they are properties of
*a server that is always running with credentials on it*. Remove the standing
host and those findings do not need mitigating — they stop applying. An
ephemeral CI runner holding a ten-minute federated token is not a master key,
and there is nothing on it to steal between runs.

### Thread 3 — two of the review's premises were already closed by canon

The review is calibrated against an architecture parts of which UIAO had
already rejected, which matters for scoring residual risk honestly:

- **Standing credentials.** [ADR-004](adr-004-workload-identity-federation-default.md)
  makes Workload Identity Federation the default for every external platform
  integration and **prohibits client secrets for new integrations**;
  certificate auth is permitted only where a platform has no OIDC issuer.
  Tokens are minutes-lived and scoped by subject claim. The review's
  "trove of sensitive secrets" is not a property of the current design.
- **Autonomous actuation.** [ADR-092](adr-092-active-governance.md) §3 defines
  the L0–L4 actuation ladder and §4 sets the federal production ceiling at
  **L3 — human-approved actuation, dry-run by default**, with
  high-blast-radius classes permanently L3-capped. The review's scenario of
  UIAO pushing hostile policy *"with the same ease that UIAO normally uses to
  enforce good policy"* describes an L4 posture the canon does not authorise.

The review also predates the Active Governance Directory
([ADR-100](adr-100-active-governance-directory-ldap.md),
[ADR-109](adr-109-active-governance-directory-write-as-intent.md)) and the
multi-tenant SaaS runtime ([ADR-096](adr-096-azure-saas-architecture.md),
hardened by [ADR-115](adr-115-saas-production-readiness.md),
[ADR-116](adr-116-azure-saas-deployment-hardening.md) and
[ADR-119](adr-119-saas-private-networking.md)), so its scope covers a subset
of what now exists.

### Thread 4 — the substrate has four server surfaces and unequal need for them

UIAO today can present four running surfaces, and they are not equally
load-bearing:

| Surface | Module | What actually requires it |
|---|---|---|
| Single-tenant REST API | `src/uiao/api/` | An HTTP consumer; gated behind the `[api]` extra |
| Multi-tenant SaaS runtime | `src/uiao/saas/` | A tenant paying for hosted governance (ADR-096) |
| Active Governance Directory | `src/uiao/directory/` | LDAP-bound clients that must query over the wire (ADR-100) |
| CLI and library | `uiao.cli.app:app`, the package | Nothing — it is invoked, not served |

Most of what the substrate is *for* — canon, OrgPath and LocPath addressing,
the ADR-040 drift engine, OSCAL and KSI generation, CQL, the evidence graph —
is reached through the CLI and the library. The enforcement runtime is already
declared **library-only** in AGENTS.md's public-surface inventory, and the
REST API is already an optional extra. The hosted tiers are, in the deployment
in front of us, carrying risk out of proportion to the work they do.

What is missing is the doctrine that says which of these must run continuously,
and why.

## Decision

Six positions.

### 1. Decompose by lifetime, not by function

The substrate is partitioned by **how long a component must exist**, not by
what it does. Three lifetimes, and nothing else is sanctioned by default:

| Lifetime | Component | Privilege held at rest |
|---|---|---|
| **Durable** | Canon — a git repository | None. It is data, not an actor |
| **Ephemeral** | The engine — drift, OSCAL, KSI, plan computation | None between runs; a per-run federated token during one |
| **Borrowed** | Actuation — an in-boundary actuator the customer already operates and has accredited | The actuator's own least-privilege identity, never UIAO's |

This replaces "which server runs what" as the organising question. A component
that cannot be placed in one of these three rows needs an ADR of its own before
it is deployed.

### 2. Canon is the only durably-available component, and it is a repository

The single thing that must be continuously available is the canon, and the
canon is a **git repository**, not an application server.
[ADR-090](adr-090-substrate-high-availability.md) already governs its
availability: exactly one node binds a commit at any instant, made continuously
available through a synchronously-replicated hot standby and a witness-gated
failover. That invariant is untouched here and satisfies the review's own
authority-server requirement in full.

A repository is a materially smaller target than an application server. It
holds no credential for any governed system, makes no outbound call, and
cannot actuate anything. Compromising it corrupts desired state — serious, and
addressed by §6's two-person review and isolated backups — but it does not
hand an attacker the estate.

### 3. The engine is ephemeral, with no standing privilege

Drift detection, OSCAL and KSI generation, evidence bundling and plan
computation run as **the `uiao` CLI, invoked in CI**, under a per-run
credential issued by Workload Identity Federation per ADR-004 and scoped by
subject claim to a specific repository, branch and environment. Between runs
there is no process, no host holding a token, and no credential material at
rest anywhere in the substrate.

This is the position that answers the review's findings 1, 2, 3 and 5 — not by
mitigating them, but by removing the thing they are findings *about*.

Two constraints make this a decision rather than a preference:

- **No governance operation may require a resident process.** A feature that
  needs a daemon to be correct is a design defect under this ADR, not a reason
  to deploy one.
- **Ephemerality is not a security control on its own.** A CI runner with a
  standing, over-scoped federated credential is the same master key with a
  shorter lease. The subject-claim scoping in ADR-004 is what makes this
  posture worth anything, and it is load-bearing here.

### 4. Actuation is borrowed from an accredited in-boundary actuator

Where the substrate must change provider state, it does so through an actuator
the customer already operates and has already accredited, under that actuator's
own least-privilege identity — **not** through a UIAO-operated worker fleet.

The worked instance is the **ServiceNow MID Server**: registered inside the ATO
boundary, reached through a scoped service identity that Vol VII Book 00
requires to hold *"never standing write authority over the estate it is meant
to govern."* This is the review's "policy execution servers" role, filled by
something already under accreditation rather than by new Tier-0 hosts.

This does not weaken [ADR-092](adr-092-active-governance.md) §1: UIAO remains
the control plane and the provider remains the data plane. It narrows *how* a
change-making adapter reaches the provider's management surface, and it does
not license UIAO to take a data-plane position.

### 5. Exactly one long-lived listener may be sanctioned, and its fate is an open question

The **Active Governance Directory** (ADR-100) is the only component identified
that genuinely requires a persistent socket: LDAP-bound clients open a
connection and expect an answer. It is also, by construction, the safest thing
to leave running — it answers `BIND`, `SEARCH` and `UNBIND` only, carries no
add/modify/delete op, holds no identity store of its own, and issues no
production credential. It is the review's own read-only observer role, and it
already exists.

**This ADR does not decide whether to keep it.** That turns on a fact nobody
has yet established: whether the LDAP-bound consumer base in the target
deployment is real and material. The two outcomes are genuinely different
architectures —

- **Consumers are real** → a one-read-only-listener architecture. The AGD is
  the sole sanctioned standing surface, and ADR-109's write-as-intent façade
  remains available on the terms that ADR sets.
- **Consumers are not real** → there are no standing servers at all, and
  ADR-100/109 should be revisited on their own terms.

Recording the question rather than guessing at it is the point. This ADR's
`review_trigger` names it first.

### 6. The hosted tiers become justified-per-deployment, not retired

`src/uiao/api/` and `src/uiao/saas/` are **not** retired by this ADR, and
ADR-096 is not superseded. They are demoted from *the* deployment model to
*a* deployment option, which a given deployment must justify against this
ADR's default posture before standing one up.

This restraint is deliberate. ADR-096 and its hardening line (ADR-115, ADR-116,
ADR-117, ADR-119) represent substantial shipped work, and the multi-tenant SaaS
tier answers a business question — hosted governance for a tenant who wants it
— that this ADR is not competent to settle. Retiring either tier is a separate
decision requiring its own ADR and its own justification.

What changes is the burden of proof: a standing HTTP surface is now the
exception that argues for itself, not the assumed shape.

### 7. Amendment to ADR-092 §6

ADR-092 §6 locates "the active platform" in the composition of the Compliance
Orchestrator loop (UIAO_101 §4), the Platform Services Layer (UIAO_102) and the
control-plane slots (`control-planes.yml`). That composition stands. What is
amended is the implication that the active platform is therefore **a running
service**:

> The active platform is a **posture**, not a process. Its components are the
> orchestrator loop, the provider-incorporation surface and the control-plane
> slots; the loop's default execution model is an ephemeral invocation against
> a durable canon, not a resident service. A deployment that runs the platform
> as a continuously-hosted surface is exercising the option in ADR-138 §6, and
> owes the justification that section requires.

Nothing else in ADR-092 changes. §1 (control plane governs data plane), §3 (the
ladder), §4 (the L3 ceiling) and §5 (bidirectional truth) are untouched.

## Consequences

**Positive.**

- The review's findings 1, 2, 3 and 5 stop applying rather than needing
  permanent mitigation. There is no standing host to harden, patch, monitor for
  intrusion, or wrap in a PAW estate.
- The four-role decomposition's security benefit is obtained without building
  four Tier-0 hosts: the authority role is the git canon under ADR-090, the
  execution role is the customer's accredited MID Server, the observer role is
  the conformance adapters (declared `ssot-mutation: never`) and SailPoint at
  rung L1 per [ADR-135](adr-135-sailpoint-isc-governance-option-b-ratification.md) §3,
  and the secrets-service role is answered by ADR-004 having no secret to store.
- The accreditation surface shrinks. An ephemeral CLI invocation inside an
  existing CI boundary is a materially smaller thing to put in front of an
  authorising official than a hosted Tier-0 service.
- The posture is honest about what UIAO is: an engine that computes governance
  from canon, not a product that must be running for governance to exist.

**Negative / costs.**

- **Availability depends on CI.** If the pipeline is down, governance *changes*
  stall. Existing provider configuration continues to hold — nothing the
  substrate has already actuated reverts — but drift detection and evidence
  generation pause. This is the review's finding 4, and this ADR does not close
  it.
- **Operational brittleness is unaddressed.** The review's finding 7 — that
  administrators lose practice in manual intervention as automation deepens —
  is a cultural risk no topology fixes.
- **No live query surface by default.** Consumers that expect to ask UIAO a
  question over HTTP must either use the `[api]` extra as a justified exception
  or consume generated artifacts instead.
- **Latency to detection rises.** A scheduled invocation detects drift on its
  cadence, not continuously. Deployments that need tighter detection must say
  so and justify the surface that provides it.

**Neutral.**

- Doctrine only — no runtime, schema, or registry change lands with this ADR
  (consistent with ADR-085, ADR-089, ADR-092, ADR-134, ADR-135).
- The CLI-in-CI execution model is already how canon, drift, OSCAL and KSI are
  exercised in this repository's own CI. This ADR names the existing practice
  as the default posture rather than introducing a new mechanism.

### Adopted from the review, independent of this decision

Five of the review's recommendations hold under any topology and are adopted
as written:

1. **Break-glass accounts excluded from UIAO governance**, held out-of-band,
   and periodically tested — the ultimate recourse if the control plane is
   unavailable or wrong.
2. **An isolated, write-only backup path for the canon**, so an attacker with
   control of the primary environment cannot reach historical backups.
3. **Two-person review on canon commits.** Single-approver merge on a
   governance repository is a real gap, and it is the gap that matters most
   once the canon is the substrate's most valuable asset (§2).
4. **A rehearsed manual path and periodic drills**, against the brittleness
   cost named above.
5. **PAW / hardened administrative access** for any privileged surface that
   remains.

Items 1–4 are the mitigations for the residual risks this ADR explicitly does
not close.

## Alternatives considered

- **Adopt the review's four-host decomposition.** Rejected as the default. It
  is sound architecture that buys containment rather than removal, at the cost
  of four Tier-0 hosts to harden and keep from drifting — and its own
  conclusion concedes the core still requires the same protection. Every role
  in it is already filled by a component under accreditation.
- **Keep the single platform server and harden it further.** Rejected. This is
  the position the review attacked successfully. Hardening reduces the
  probability of compromise and does nothing about its consequence, which is
  the part the review is actually about.
- **Retire `src/uiao/saas/` outright in this ADR.** Rejected as out of scope.
  The multi-tenant tier answers a business question this ADR cannot settle, and
  retiring shipped, hardened work by side effect of a posture decision would be
  the kind of quiet over-reach ADR-000 exists to prevent. §6 demotes it; a
  future ADR may retire it.
- **Decide the AGD's fate now.** Rejected. The answer depends on a fact about
  the target deployment that has not been established. Guessing it in either
  direction would put a wrong architecture in canon — and §5's two outcomes are
  different enough that the guess would matter.
- **Treat ephemerality as sufficient security.** Rejected explicitly in §3. A
  short-lived but over-scoped credential is the same master key with a shorter
  lease; the subject-claim scoping in ADR-004 is what makes this posture sound.

## Sourcing note

The 2026-08-21 review is an **internal decision input**, not an external
authority. Its security argument is reproduced here on its own reasoning;
its own citations for the control-plane claims are vendor blog posts, and its
assertion about the share of large enterprises that have fully eliminated
on-premises Active Directory carries no source at all. Per
[ADR-000](adr-000-adr-process.md) §"ADRs Are Decision Records, Not Sources of
Truth," none of those claims is authoritative by virtue of appearing here, and
any downstream artifact that needs the Tier-0 principle as an *external* fact
must cite a primary source (NIST SP 800-53 Rev 5 AC-6 and CM-5, Microsoft's
published privileged-access guidance, or a CISA advisory) rather than this ADR
or that review.

## References

- [ADR-004](adr-004-workload-identity-federation-default.md) — Workload Identity
  Federation as default; the no-stored-secrets position §3 depends on.
- [ADR-040](adr-040-drift-engine.md) — the six-phase reconciliation loop that
  §3 makes ephemeral.
- [ADR-090](adr-090-substrate-high-availability.md) — single-logical-authority
  and the hot-standby/witness posture §2 relies on unchanged.
- [ADR-092](adr-092-active-governance.md) — Active Governance; §1, §3 and §4
  cited, §6 amended by §7 of this ADR.
- [ADR-096](adr-096-azure-saas-architecture.md),
  [ADR-115](adr-115-saas-production-readiness.md),
  [ADR-116](adr-116-azure-saas-deployment-hardening.md),
  [ADR-119](adr-119-saas-private-networking.md) — the hosted SaaS tier that §6
  demotes without retiring.
- [ADR-100](adr-100-active-governance-directory-ldap.md),
  [ADR-109](adr-109-active-governance-directory-write-as-intent.md) — the read
  projection and write-as-intent façade whose retention §5 leaves open.
- [ADR-135](adr-135-sailpoint-isc-governance-option-b-ratification.md) —
  SailPoint bound at rung L1, feeding the ServiceNow-coordinated pipeline §4
  borrows.
- `docs/customer-documents/orgcomp-series/Vol_VII_Book_00_OrgComp_ServiceNow_Automation_Overview.qmd`
  — the in-boundary MID Server and least-privilege service-identity discipline
  §4 depends on.
- `scripts/servicenow-harness/` — the gates that make the borrowed-actuator
  path reviewable rather than asserted.
