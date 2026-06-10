---
adr_id: adr-100
title: "Active Governance Directory — The In-Path LDAP Projection Plane and the Read-Only Data-Plane Exception"
status: PROPOSED
decided: 2026-06-10
deciders: Michael Stratton
updated: 2026-06-10
next_review: 2026-12-10
review_trigger: A write op (add/modify/delete) is proposed for the AGD; a Kerberos/SASL or StartTLS module is proposed; the AGD is proposed for a federal boundary deployment; ADR-092's control-plane/data-plane boundary is revised; the ldap binding profile (UIAO_193) changes facet→attribute names
impact: "Sanctions the Active Governance Directory (AGD): an in-path LDAPv3 server that projects the governance substrate over the LDAP wire protocol. Carves a narrow, read-only exception to the ADR-092 §1 rule that UIAO must not hold a data-plane position — the AGD sits on the LDAP request path but carries no write op, so it cannot mutate canon or the provider of record. Adds the uiao.directory package (BER codec, LDAPv3 protocol, DIT projection, asyncio server) and the uiao directory CLI sub-app. Establishes the actuation rung (L1, read projection) and the explicit roadmap boundary: Kerberos/KDC, write ops, SASL/StartTLS, and AD-specific schema are out of scope for this increment. Runtime + CLI change; no schema or registry change to canon data."
supersedes: null
superseded_by: null
amends: adr-092-active-governance.md
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-100-active-governance-directory-ldap.html
---

# ADR-100: Active Governance Directory — The In-Path LDAP Projection Plane and the Read-Only Data-Plane Exception

## Status

**PROPOSED** — June 10, 2026

This ADR **amends ADR-092**. It does not retire the control-plane/data-plane
boundary; it carves one narrow, explicitly-bounded exception to it and adds the
runtime that occupies that exception.

## Context

UIAO already implements the substance of "Active Governance" (ADR-092): OrgPath
canonical addressing (UIAO_151), a six-phase drift/reconciliation engine
(ADR-040), the L0–L4 actuation ladder, and a vendor-neutral projection layer
whose `ldap` binding profile (UIAO_193 / ADR-098) already declares the
`uiaoOrgPath<Facet>` auxiliary objectClass. What it has **not** had is a way for
the vast installed base of **LDAP-bound tooling** — the clients that still speak
to Active Directory and other directories over the wire — to *query the
governance directory in the protocol they already speak*.

The pull is to "replace Active Directory" outright: stand up an in-path LDAP
server (and, eventually, a Kerberos KDC) that authenticates and authorizes
Windows domains. Taken literally, that collides head-on with **ADR-092 §1**,
which states UIAO is the control plane and **MUST NOT** "sit inline in the
authentication or request path… issue the production credential, or hold a
data-plane position," and which **explicitly rejects** the "rebuild the domain
controller / in-path enforcer" alternative.

Both positions have a point. ADR-092 §1 is right that UIAO must not become the
runtime *authenticator* — the single point of failure, blast radius, and
vendor-lock the cloud era dismantled. But a directory has two faces: the
**authentication path** (bind-as-credential-check, the thing ADR-092 protects)
and the **read/query path** (search-the-tree, the thing every directory-bound
report, sync job, and lookup tool actually uses most). The read face can be
served in-path *without* UIAO becoming the authenticator, because a **read
projection holds no write op and issues no production credential**. That is the
seam this ADR cuts.

## Decision

Five positions.

### 1. The Active Governance Directory is sanctioned as an in-path **read** projection

The **Active Governance Directory (AGD)** is an LDAPv3 server
(`uiao.directory`) that answers `BIND`, `SEARCH`, and `UNBIND` over TCP,
projecting the governance substrate as LDAP entries. It is **in-path** — a
client opens a socket to it and gets directory answers — which is precisely the
position ADR-092 §1 guards. This ADR sanctions that position **for the read
projection only**.

### 2. The read-only data-plane exception (amends ADR-092 §1)

ADR-092 §1 is amended to admit one exception:

> UIAO MAY occupy an in-path directory data-plane position **when, and only
> when, the surface is a read projection** — it serves `SEARCH` (and the `BIND`
> required to gate read access) and carries **no** add / modify / delete /
> moddn op. A read projection cannot mutate canon, cannot mutate the provider of
> record, and cannot issue a production credential; it therefore does not
> recreate the single-point-of-enforcement risk ADR-092 §1 exists to prevent.

Everything ADR-092 §1 forbids that *writes* or *authenticates-as-source-of-
truth* remains forbidden. The AGD is a window onto the substrate, not a new
master.

### 3. The AGD is a projection, never a store

The AGD has **no identity database of its own**. Its Directory Information Tree
is *computed* from two governed inputs at load time: the OrgPath **Codebook**
(UIAO_151, facet semantics) and a **principal snapshot** (the same
`{principal_id, principal_type, attributes}` shape the OrgPath governance
runtime consumes). Every governed facet slot is surfaced under its canonical
LDAP attribute name from the **`ldap` binding profile** (UIAO_193) — the wire
schema is traceable to canon, not invented at the server. Because the tree is a
projection, read-only is a property of construction, not merely policy: there is
no entry to write to.

### 4. Actuation rung and the explicit roadmap boundary

On the ADR-092 §3 ladder, the AGD is **L1 (Observe / read projection)**. The
following are **explicitly out of scope** for this increment and require their
own governed decision before they land:

- **Write ops** (add / modify / delete / moddn) — would forfeit the §2
  exception and re-enter the full ADR-092 §1 prohibition; writes must continue
  to flow through the existing OrgPath modernization adapters into the provider
  of record.
- **Kerberos / KDC and SASL / GSSAPI** — the authentication-path face ADR-092 §1
  protects; not built.
- **StartTLS / LDAPS** — required before any non-loopback deployment; the
  current server is plaintext and binds `127.0.0.1` by default.
- **AD-specific schema** (`sAMAccountName`, `objectSid`, the AD partition
  layout) — the AGD speaks generic LDAPv3 + the `uiaoOrgPath` auxiliary class,
  not the AD schema.

Unsupported protocol ops answer `unwillingToPerform` rather than dropping the
connection, so the boundary is observable on the wire.

### 5. Bind policy is gate-only, not source-of-truth

The AGD's `BIND` exists to gate *read* access, not to be an authentication
authority. Anonymous bind yields the projection; simple bind is checked against
an operator-supplied credential map. The AGD never becomes the place an
organization's passwords live — that remains the incumbent IdP's job. SASL/
Kerberos bind (the path a real AD replacement would need) is deferred per §4.

Anonymous bind exposing the full projection without a prior-bind gate on
`SEARCH` is **acceptable for this increment** specifically because the
projection carries only already-governed facet data (OrgPath region,
department, role, etc.) — never secrets, credentials, or password material.
The disclosure surface is therefore the governed org structure, which is not
sensitive at the Moderate/Commercial boundary this targets. Per-bind read
scoping (restricting which facets/subtrees an anonymous vs. authenticated bind
may read) is a §4 roadmap control to add before any sensitive-facet projection
or non-loopback deployment.

## Consequences

**Positive.**

- LDAP-bound tooling can query the Active Governance Directory in its native
  protocol, delivering the "expose its own LDAP interface" goal of the
  AGD vision **without** UIAO becoming the authenticator.
- The boundary is now a single, observable line: read projection in-path is
  sanctioned; write/authenticate-as-master is not. An authorizing official can
  be told "it answers searches, it cannot change anything," which is a sentence
  an AO can sign.
- The wire schema reuses the existing `ldap` binding profile (UIAO_193), so the
  projected attributes are already canon — no new schema surface.
- It is pure-stdlib (`asyncio` + a hand-rolled BER subset); no new runtime
  dependency, so the blocking CI surface is unaffected.

**Negative / costs.**

- An in-path server, even read-only, is a new network-reachable surface. It must
  not leave loopback without StartTLS/LDAPS (§4) and read-authorization scoping
  — designed before any multi-host deployment, not after.
- A read projection can leak: directory search is an information-disclosure
  surface. Bind gating and per-bind read scoping (roadmap) are the controls;
  until they harden, the default posture is loopback + anonymous-read-of-non-
  sensitive-facets only.
- The §2 exception is a genuine narrowing of ADR-092 §1; it must be policed.
  Any PR that adds a write op to `uiao.directory` is a boundary violation and is
  rejected at review absent a superseding ADR.

**Neutral.**

- Amends ADR-092 (§1 exception) without disturbing ADR-092 §§2–6. The
  control-plane posture, provider-incorporation contract, ladder, L4 ceiling,
  and bidirectional-truth rules are unchanged.
- The AGD is the protocol-projection plane the ADR-098 binding profiles
  anticipated; `microsoft-entra`, `aws`, etc. remain projection *targets* UIAO
  writes *to*, while the AGD is a projection UIAO *serves*.

## Alternatives considered

- **Full in-path AD replacement (LDAP server + KDC in the auth path).**
  Deferred, not adopted. It is the literal vision, but it forfeits the §2
  read-only seam, re-enters the full ADR-092 §1 prohibition, and is months of
  Kerberos/schema work. The read projection is the buildable, boundary-safe
  first brick; the authentication-path face is gated behind its own future ADR.
- **Offline LDIF export only (no server).** Rejected as the *only* deliverable —
  it does not let live clients bind and search, which is the actual
  compatibility requirement. (The `uiao directory tree` command still emits LDIF
  for inspection; it is additive, not the substitute.)
- **Depend on a third-party LDAP server (389-ds, OpenLDAP) fronting the
  substrate.** Deferred. Viable for a hardened production deployment, but it puts
  a stateful store back in the path and couples the projection to that store's
  schema lifecycle. The pure-projection server keeps "no store of its own" (§3)
  literally true and is dependency-free for the first increment.

## References

- [ADR-092](adr-092-active-governance.md) — Active Governance; §1 is the
  control-plane/data-plane boundary this ADR amends; §3 the actuation ladder.
- [ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md) — the
  vendor-neutral binding profiles; the AGD serves the `ldap` profile.
- [UIAO_151](../UIAO_151_OrgPath_Codebook.md) — the OrgPath Codebook (facet
  semantics the DIT projects).
- [UIAO_193](../UIAO_193_OrgPath_MultiCloud_Binding.md) — the multi-cloud
  binding spec; §ldap fixes the `uiaoOrgPath<Facet>` attribute names.
- RFC 4511 — Lightweight Directory Access Protocol (v3): the wire protocol the
  AGD implements (BindRequest, SearchRequest, the Filter choice, LDAPResult).
