---
adr_id: adr-101
title: "Active Governance Directory — SASL/GSSAPI (Kerberos) Bind as Gate-Only Ticket Validation"
status: PROPOSED
decided: 2026-06-11
deciders: Michael Stratton
updated: 2026-06-11
next_review: 2026-12-11
review_trigger: A SASL mechanism other than GSSAPI is proposed for the AGD; the AGD is proposed to issue Kerberos tickets / act as a KDC / hold user secrets; a write op is proposed for the AGD; the AGD is proposed for a federal-boundary deployment with Kerberos; ADR-092 §1 or ADR-100 §2/§5 is revised
impact: "Decides whether and how the Active Governance Directory (ADR-100) may authenticate LDAP clients via SASL. Permits exactly one mechanism — GSSAPI (Kerberos) — and only as gate-only ticket validation: the AGD validates a service ticket the incumbent KDC issued, to decide read-authorization scope, and never becomes a credential authority (no KDC, no ticket issuance, no user-secret store beyond its own service keytab). Extends ADR-100 §5's bind gate from a simple-credential map to standards-based Kerberos while keeping the read-only data-plane exception (ADR-100 §2) intact. Doctrine only — no runtime, schema, or registry change lands with this ADR; it gates a future [kerberos]-extra implementation."
supersedes: null
superseded_by: null
amends: adr-100-active-governance-directory-ldap.md
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-101-active-governance-directory-sasl-kerberos.html
---

# ADR-101: Active Governance Directory — SASL/GSSAPI (Kerberos) Bind as Gate-Only Ticket Validation

## Status

**PROPOSED** — June 11, 2026

This ADR **amends ADR-100**. It decides a question ADR-100 §4 explicitly
deferred — whether the AGD may authenticate clients with Kerberos — and draws
the line that keeps that capability on the governance side of the ADR-092 §1
boundary. It is doctrine: no runtime, schema, or registry change lands with it.

## Context

The Active Governance Directory (ADR-100) exposes the governance substrate over
LDAPv3 as an **in-path read projection**. Its authentication is deliberately
minimal: ADR-100 §5 makes `BIND` a *gate* (anonymous vs. a simple-credential
map) rather than an authentication authority, and ADR-100 §4 lists
**SASL/Kerberos bind** as explicit roadmap, *not shipped* — precisely because it
is the face that touches the authentication path ADR-092 §1 guards.

Two facts now pull toward closing that gap:

1. **The installed base authenticates with Kerberos.** The LDAP- and
   AD-bound tooling the AGD exists to serve does not present passwords over a
   simple bind in production — it presents **Kerberos tickets** via SASL/GSSAPI.
   An AGD that only accepts anonymous or simple bind is, in a Kerberized
   environment, either wide open (anonymous) or asking clients to do something
   they no longer do (send a password). Per-bind read scoping (ADR-100 §5)
   cannot meaningfully distinguish an *authenticated* reader without a real
   authentication mechanism behind it.

2. **The hard line is credential issuance, not credential validation.**
   ADR-092 §1 forbids UIAO from "issuing the production credential" or holding a
   "data-plane position." A KDC issues credentials. **Validating a ticket the
   KDC already issued is a different act** — it is reading an assertion the
   incumbent authority made, which is exactly the posture (govern/observe, do
   not become the authority) the whole substrate is built on.

What is missing is the doctrine that says which side of that line a SASL bind
sits on, and the guardrails that keep an implementation from drifting across it.

## Decision

Five positions.

### 1. Exactly one SASL mechanism: GSSAPI (Kerberos)

The AGD MAY offer **SASL with the single mechanism `GSSAPI`** (RFC 4752 —
Kerberos V5 over SASL). `PLAIN`, `EXTERNAL`, `DIGEST-MD5`, `SCRAM`, and every
other mechanism are **out of scope** and MUST NOT be advertised. A
single-mechanism surface keeps the attack surface and the doctrine small:
GSSAPI is the one mechanism that authenticates against an *external* authority
(the KDC) rather than against a secret the AGD would have to hold.

### 2. Gate-only ticket validation — the AGD is not a credential authority

A SASL/GSSAPI bind authenticates the client by **validating a Kerberos service
ticket the incumbent KDC issued** to the AGD's service principal
(`ldap/<host>@REALM`). The AGD:

- **MUST** accept the GSSAPI security context using only **its own service
  keytab** (the standard requirement for any Kerberized service);
- **MUST NOT** become a KDC, issue TGTs or service tickets, run an AS/TGS
  exchange, or proxy/forward credentials;
- **MUST NOT** store, cache, or have any access to **user** secrets, passwords,
  or keytabs — only its own service key;
- **MUST** treat the validated client principal name as an **assertion made by
  the KDC**, used solely to decide read-authorization scope.

This keeps the AGD on the governance side of ADR-092 §1: the **KDC issues the
production credential**; the AGD merely reads the ticket the KDC signed. Holding
one's own service keytab to accept a context is not "issuing the production
credential" — every Kerberized read service does it, and none of them is a KDC.

### 3. Authentication gates reads only — the read-only exception is preserved

A successful GSSAPI bind unlocks **read scope**, nothing more. It does not add a
write op, does not change the projection, and does not move the AGD off the
read-only data-plane exception of **ADR-100 §2**. The actuation rung stays
**L1** (ADR-092 §3): authenticating a reader is a gate, not actuation. The
authenticated Kerberos principal feeds **ADR-100 §5 per-bind read scoping** —
e.g. anonymous sees non-sensitive facets, an authenticated principal may see
sensitive facets (clearance, cost-center) or a principal-scoped subtree, per the
operator's `ReadPolicy`. This ADR makes the §5 gate *mean something* in a
Kerberized environment; it does not widen what a reader can do.

### 4. The boundary line, stated once

| Act | Verdict | Why |
|---|---|---|
| Accept a GSSAPI context with the AGD's own service keytab | **Permitted** | Validating the KDC's assertion (gate-only, §2) |
| Map the validated principal → read scope | **Permitted** | ADR-100 §5 per-bind read scoping |
| Issue a TGT / service ticket; run AS/TGS; be a KDC | **Forbidden** | Issuing the production credential (ADR-092 §1) |
| Store/cache user passwords or user keytabs | **Forbidden** | Becoming a credential store (ADR-100 §5) |
| Forward/delegate the client's credential onward | **Forbidden** | Holding a data-plane credential position (ADR-092 §1) |
| Any add/modify/delete op | **Forbidden** | Forfeits the read-only exception (ADR-100 §2) |

A PR that crosses any "Forbidden" row is a boundary violation, rejected at review
absent a superseding ADR.

### 5. Implementation is gated, dependency-isolated, and federal-deferred

This ADR ships **no code**. A future implementation:

- lands the SASL framing (BindRequest `[3] SaslCredentials`, the multi-step
  bind handshake, `serverSaslCreds`) and the GSSAPI accept loop behind a new
  **`[kerberos]` optional extra** (e.g. lazy-imported `gssapi`), so the core AGD
  stays pure-stdlib and the blocking CI surface is unaffected;
- maps the authenticated principal into `ReadPolicy` (ADR-100 §5);
- is **deferred for any federal-boundary deployment** until the keytab
  custody, realm-trust, and audit story is designed and an authorizing
  official has signed it — Kerberos in a federal boundary is its own review,
  triggered per this ADR's `review_trigger`.

## Consequences

**Positive.**

- The AGD becomes usable in the Kerberized environments it targets without
  asking clients to present passwords, and ADR-100 §5 read scoping gains a real
  authenticated identity to scope against.
- The boundary is drawn so the capability cannot drift into being an
  authenticator-of-record: validate yes, issue never. An authorizing official
  can be told "it checks the ticket your KDC signed; it is not a KDC."
- One mechanism (GSSAPI) keeps the surface and the doctrine minimal.

**Negative / costs.**

- A SASL bind is, mechanically, an authentication exchange the AGD participates
  in — a heavier surface than anonymous/simple bind. Service-keytab custody
  becomes a first-class operational concern and the highest-value secret the
  AGD touches; it must be designed (least privilege, rotation, no user-key
  access) before the first deployment.
- GSSAPI pulls a native dependency (`gssapi`/MIT-krb5 or Heimdal). Isolating it
  behind `[kerberos]` keeps the core clean but adds a build/runtime matrix.
- Multi-step SASL binds add state to the per-connection loop (currently each op
  is largely independent).

**Neutral.**

- Doctrine only — no runtime, schema, or registry change lands here (consistent
  with ADR-092, ADR-100 §1).
- Amends ADR-100 (resolves the §4 SASL deferral; gives §5 a real mechanism)
  without disturbing the read-only exception (§2) or the projection-not-store
  rule (§3).

## Alternatives considered

- **Keep simple-bind / anonymous only (do nothing).** Rejected. In a Kerberized
  estate that leaves the AGD either anonymous-open or unusable, and makes ADR-100
  §5 read scoping unable to identify an authenticated reader.
- **Support a broad SASL mechanism set (PLAIN, SCRAM, DIGEST-MD5, …).**
  Rejected. PLAIN/SCRAM authenticate against a secret the AGD would have to
  hold — that is the credential-store posture ADR-100 §5 forbids. GSSAPI is the
  one mechanism whose authority is external (the KDC).
- **Run an integrated KDC (the FreeIPA-style "AD for Linux" path).** Rejected.
  Issuing tickets is exactly the "issue the production credential" act ADR-092 §1
  forbids and the "rebuild the domain controller" alternative ADR-092 already
  rejected. The AGD validates the incumbent KDC's tickets; it never becomes one.
- **Pass-through / credential delegation to a backend.** Rejected. Forwarding
  the client credential puts the AGD in a data-plane credential position
  (ADR-092 §1).

## References

- [ADR-092](adr-092-active-governance.md) — control-plane/data-plane boundary;
  §1 forbids issuing the production credential / holding a data-plane position.
- [ADR-100](adr-100-active-governance-directory-ldap.md) — the AGD; §2 the
  read-only data-plane exception, §4 the SASL/Kerberos deferral this ADR
  resolves, §5 per-bind read scoping this ADR gives a real mechanism.
- RFC 4752 — The Kerberos V5 (GSSAPI) SASL Mechanism.
- RFC 4511 §4.2 — LDAP BindRequest / SASL authentication choice and the
  multi-step bind handshake.
