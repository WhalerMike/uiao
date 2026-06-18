---
adr_id: adr-109
title: "Active Governance Directory — Write Operations as Governed Intent, Not Store Mutation"
status: PROPOSED
decided: 2026-06-18
deciders: Michael Stratton
updated: 2026-06-18
next_review: 2026-12-18
review_trigger: An LDAP write op is proposed to mutate the AGD projection directly; the AGD is proposed to become a writable LDAP store of record; an autonomous (L4) write path is proposed for the AGD; ADR-092 §1, ADR-100 §2/§3, or ADR-040 (the drift/reconcile engine) is revised; a write op targets a non-governed attribute
impact: "Decides whether and how the Active Governance Directory (ADR-100) may accept LDAP write operations (modify/add/delete/modifyDN). Permits them only as *governed intent*: a write at the LDAP edge is translated into a control-plane operation and routed through the existing OrgPath modernization adapters (ADR-036–039) plan/apply/reconcile into the provider of record — dry-run by default, governance-review-gated, on the ADR-092 §3 actuation ladder. The projection is never written to directly; the AGD never becomes a writable store of record (that remains the ADR-092 §1 / ADR-100 §3 prohibition). Amends ADR-100 §2 (the AGD is no longer strictly 'no write op' — it carries no writable *store*). Doctrine only — no runtime, schema, or registry change lands with this ADR; it gates a future implementation."
supersedes: null
superseded_by: null
amends: adr-100-active-governance-directory-ldap.md
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-109-active-governance-directory-write-as-intent.html
---

# ADR-109: Active Governance Directory — Write Operations as Governed Intent, Not Store Mutation

## Status

**PROPOSED** — June 18, 2026

This ADR **amends ADR-100**. It decides the last item ADR-100 §4 deferred —
whether the AGD may accept LDAP writes — and draws the line that lets it do so
without becoming the writable directory ADR-092 §1 forbids. It is doctrine: no
runtime, schema, or registry change lands with it.

## Context

The Active Governance Directory (ADR-100) is an **in-path read projection**: its
Directory Information Tree is *computed* from the OrgPath Codebook + a principal
snapshot (ADR-100 §3, "a projection, never a store"), and it carries **no write
op** (ADR-100 §2). Writes to governed state flow through the existing OrgPath
**modernization adapters** (ADR-036 dynamic groups, ADR-037 admin units, ADR-038
device-plane OrgPath, ADR-039 policy targeting) into the provider of record, on
the `plan / apply / reconcile` verb shape, gated by the ADR-040 drift engine.

The pull toward LDAP writes is real: AD- and LDAP-bound tooling does not only
read the directory — it **modifies** it (`ldapmodify`, the AD Users-and-Computers
write path, provisioning connectors). An AGD that answers only reads forces
every write back onto a different, non-LDAP surface, which is exactly the
seam a "modern AD replacement" is supposed to remove.

But two doctrines stand in the way of a naïve "make it writable":

1. **There is nothing to write to.** ADR-100 §3 makes the DIT a *projection* of
   canon + snapshot. A `modify` that mutated the projection would either be lost
   on the next recompute or would fork a second source of truth — the SSOT
   violation the whole substrate exists to prevent.
2. **ADR-092 §1 forbids a data-plane mutation position.** A writable directory of
   record *is* a data-plane store; standing one up re-creates the domain
   controller ADR-092 explicitly rejected.

What is missing is the doctrine that lets the LDAP **edge** accept a write
without the AGD becoming a writable **store** — and the guardrails that keep an
implementation on the right side of that distinction.

## Decision

Six positions.

### 1. A write at the edge is a governed intent, never a store mutation

The AGD MAY accept the LDAP write operations `modify`, `add`, `delete`, and
`modifyDN`. It **MUST NOT** apply any of them to its own projection. Instead,
each write is **translated** into the control plane's native unit of work — a
per-facet operation (the ADR-084 `FacetOperation`) — and **routed through the
existing modernization adapters** (`plan / apply / reconcile`, ADR-036–039) into
the provider of record. The AGD is a **write façade over the control plane**,
not a writable directory. The DIT stays computed-from-canon (ADR-100 §3 intact);
a subsequent read reflects the change only once it has landed in the provider
and been re-projected.

### 2. Only governed facets are writable; the structural surface is read-only

A `modify` is honored **only** for the governed `uiaoOrgPath<Facet>` attributes
(the `ldap` binding profile, UIAO_193). A write to a non-governed attribute
(`cn`, `objectClass`, `dn` components, arbitrary attributes) is refused with
`unwillingToPerform` — the AGD does not own those, and inventing a store for them
is exactly position §1 forbids. `add` / `delete` of an **entry** map to a
provisioning / deprovisioning **intent** only where a modernization adapter
implements that lifecycle (e.g. an HR-driven joiner/leaver path, ADR-088);
absent such an adapter they are refused, not faked. `modifyDN` (moving an entry)
is an OrgPath re-assignment intent, subject to the same routing.

### 3. Writes inherit the full governance machinery — dry-run, ladder, review

A translated write is **not** a fast path around governance. It enters the
ADR-040 engine with **`dry_run=True` by default**: the default response to a
write is to compute and return the change-set (a `plan`), not to apply it. Actual
application requires the deployment to be configured for actuation and is bound
by the **ADR-092 §3 actuation ladder** — the write path runs at **L2 (advise)**
or **L3 (gated actuation, human-approved)**; the **federal default ceiling is
L3** and high-blast-radius writes (e.g. anything that re-targets policy at
`directoryScopeId=/`) are **L3-capped permanently** and always route to
governance review. **L4 (autonomous write) is not permitted for the AGD write
path** — a directory edge that auto-applied every `ldapmodify` would be the
unbounded actuator ADR-092 §4 guards against.

### 4. Bidirectional truth applies to writes

Because the write target is the provider of record (not a private store), a
write can collide with drift the engine already tracks. The ADR-074
disposition set therefore applies: a write may be **applied** (force desired
onto actual), **held** (quarantined for review when it conflicts with an open
finding), or surfaced as a **promote-actual** decision when the write merely
ratifies reality. The AGD does not resolve these autonomously; it routes them to
the same human disposition every other governed change uses.

### 5. The boundary line, stated once

| Act | Verdict | Why |
|---|---|---|
| `modify` a governed `uiaoOrgPath<Facet>` → routed `FacetOperation`, dry-run | **Permitted** | Governed intent through the control plane (§1, §3) |
| Apply a translated write after gated approval (L3) | **Permitted** | ADR-040 actuation, governance-review gated |
| Write the AGD projection / DIT directly | **Forbidden** | The projection is not a store (ADR-100 §3) |
| Become a read-write LDAP store of record | **Forbidden** | Data-plane mutation position (ADR-092 §1) |
| `modify` a non-governed attribute (`cn`, `objectClass`, …) | **Forbidden** | The AGD does not own it (§2) |
| Auto-apply writes without a human (L4) | **Forbidden** | Unbounded actuator (ADR-092 §4) |
| Issue a credential / write a password attribute | **Forbidden** | ADR-092 §1; ADR-101 §4 (not a credential authority) |

A PR that crosses any "Forbidden" row is a boundary violation, rejected at
review absent a superseding ADR.

### 6. This amends ADR-100 §2 — "no write op" becomes "no writable store"

ADR-100 §2 said the AGD "carries no write op." That is narrowed: the AGD may
carry write ops at the edge, but it **carries no writable store** — every write
becomes a governed intent against the provider of record, and the read-only
**projection** property (ADR-100 §3) is untouched. The read path (ADR-100,
ADR-101 auth, LDAPS/StartTLS transport) is unchanged. The actuation rung for the
*read* surface stays L1; the *write* surface is L2–L3, never L4.

## Consequences

**Positive.**

- LDAP-bound tooling can issue governed changes in the protocol it already
  speaks, without UIAO becoming a writable directory of record — the
  control-plane posture is preserved while the ergonomics gap closes.
- Every write is, by construction, dry-run-first, ladder-bound, and
  review-gated — an `ldapmodify` cannot silently mutate crown-jewel state. An
  authorizing official can be told "a write is a proposed change-set a human
  approves," which is a sentence an AO can sign.
- The translation reuses the existing adapters and the ADR-040 engine — adding
  the write façade is wiring, not a new actuation stack.

**Negative / costs.**

- A write façade is the highest-value attack surface the AGD will ever expose:
  it accepts mutation requests for identity/policy state. The actuator demands
  the strongest authz (SASL/GSSAPI bind, ADR-101), immutable audit, dry-run,
  rollback, and break-glass — designed before any op class promotes to L3.
- Translating LDAP write semantics (atomic multi-attribute `modify`, `modifyDN`)
  onto per-facet operations is lossy at the edges; some writes will be refused
  as un-translatable rather than partially applied.
- The latency/asynchrony of "write returns a plan, change lands later" differs
  from a classic writable LDAP and must be documented for client expectations.

**Neutral.**

- Doctrine only — no runtime, schema, or registry change lands here (consistent
  with ADR-092, ADR-100, ADR-101).
- Amends ADR-100 §2; composes with ADR-040 (the engine), ADR-074 (bidirectional
  truth), ADR-084 (`FacetOperation`), ADR-092 §3/§4 (ladder + L4 ceiling), and
  ADR-101 (the auth that must gate any write).

## Alternatives considered

- **No writes, ever (status quo).** Rejected as the ceiling. It is the safe
  default and remains the behavior until an implementation ships, but declining
  to offer governed LDAP writes leaves the "different surface for every write"
  seam a modern replacement should close — and the machinery to do it safely
  (ADR-040 + the adapters) already exists.
- **Writable LDAP store of record (real read-write directory).** Rejected. It
  re-creates the domain controller ADR-092 §1 rejected, forks SSOT against the
  projection (ADR-100 §3), and makes the AGD the data-plane master the whole
  design avoids.
- **Write-through to the provider with no governance gate (transparent proxy).**
  Rejected. A transparent write-proxy is an unbounded actuator — it strips the
  dry-run / ladder / review controls (ADR-040, ADR-092 §3) that make actuation
  accreditable, and turns every `ldapmodify` into an immediate production change.

## References

- [ADR-092](adr-092-active-governance.md) — control-plane/data-plane boundary
  (§1), the actuation ladder (§3), the L4 ceiling (§4), bidirectional truth.
- [ADR-100](adr-100-active-governance-directory-ldap.md) — the AGD; §2 ("no write
  op", amended here), §3 (projection, never a store, preserved).
- [ADR-101](adr-101-active-governance-directory-sasl-kerberos.md) — the SASL
  auth that must gate any write path.
- [ADR-040](adr-040-drift-engine.md) — the six-phase drift/reconcile engine
  (`dry_run`, `halt_on_critical`, auto-remediate / governance-review split).
- [ADR-074](adr-074-drift-ssot-contention.md) — bidirectional truth
  (apply / promote-actual / quarantine).
- [ADR-084](adr-084-phase5-consumer-architecture.md) — the `FacetOperation`
  per-facet unit of work a translated write becomes.
- [ADR-036](adr-036-dynamic-group-provisioning.md) / [ADR-037](adr-037-admin-unit-provisioning.md) / [ADR-038](adr-038-device-plane-orgpath.md) / [ADR-039](adr-039-policy-targeting.md) — the `plan / apply / reconcile` modernization adapters a write routes through.
- RFC 4511 §4.5–4.9 — the LDAP modify / add / delete / modifyDN operations.
