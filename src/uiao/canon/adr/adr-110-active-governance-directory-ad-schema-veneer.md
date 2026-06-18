---
adr_id: adr-110
title: "Active Governance Directory — AD-Compatible Schema as a Read-Only Synthesized Veneer, Not an AD Store"
status: PROPOSED
decided: 2026-06-18
deciders: Michael Stratton
updated: 2026-06-18
next_review: 2026-12-18
review_trigger: The AGD is proposed to issue authoritative SIDs / be domain-joinable / implement AD naming contexts or replication; a synthesized AD attribute is proposed to become writable or governed; the AGD is proposed to issue a Kerberos PAC; ADR-092 §1, ADR-100 §2/§3, or ADR-109 is revised
impact: "Decides whether and how the Active Governance Directory (ADR-100) may expose AD-specific schema (sAMAccountName, userPrincipalName, objectClass user/computer, objectSid). Permits a bounded, opt-in, READ-ONLY synthesized veneer — AD-shaped attributes derived at read time from the governed principal data, never stored. The synthetic objectSid is deterministic, namespaced, and explicitly non-authoritative; the AGD never issues authoritative SIDs, implements the AD partition layout / replication / global catalog, accepts domain join, or issues a Kerberos PAC (the AD-DC roles ADR-092 §1 rejects). The veneer does not widen the write surface (ADR-109): synthesized AD attributes are read-only and not governed facets. Amends ADR-100 §4 (the AD-schema deferral). Doctrine only — no runtime, schema, or registry change lands with this ADR."
supersedes: null
superseded_by: null
amends: adr-100-active-governance-directory-ldap.md
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-110-active-governance-directory-ad-schema-veneer.html
---

# ADR-110: Active Governance Directory — AD-Compatible Schema as a Read-Only Synthesized Veneer, Not an AD Store

## Status

**PROPOSED** — June 18, 2026

This ADR **amends ADR-100**. It resolves the final item ADR-100 §4 deferred —
AD-specific schema — and draws the line that lets the AGD *look* AD-compatible to
read tooling without *becoming* an Active Directory. Doctrine only: no runtime,
schema, or registry change lands with it.

## Context

The Active Governance Directory (ADR-100) speaks generic LDAPv3 plus the
`uiaoOrgPath<Facet>` auxiliary objectClass (the `ldap` binding profile, UIAO_193).
That is enough for modern LDAP tooling, but the **AD-native** read surface — the
tooling this is meant to interoperate with — keys off **AD-specific schema** that
the AGD does not project: `sAMAccountName`, `userPrincipalName`, `objectClass`
of `user` / `computer`, `displayName`, and above all `objectSid`. ADR-100 §4
listed "AD-specific schema" as explicit roadmap, *not shipped*.

The pull is to "just add the AD attributes." The risk is that AD schema is not
only attributes — it implies an **authority model**: a real `objectSid` is a
security principal a Windows access check honors, issued by a domain that owns a
SID namespace; AD schema lives in a partitioned directory (the Schema and
Configuration naming contexts) replicated between domain controllers, reachable
by domain-joined machines, and backed by a KDC that stamps SIDs into Kerberos
PACs. Projecting the *attributes* without owning the *authority* is fine; being
mistaken for (or trying to be) the *authority* re-creates the domain controller
ADR-092 §1 rejected.

What is missing is the doctrine that separates the compatibility *shape* from the
directory *authority*, and the guardrails that keep the veneer read-only and
non-authoritative.

## Decision

Five positions.

### 1. A bounded, opt-in, read-only AD-compatibility veneer

The AGD MAY project a fixed allow-list of **AD-shaped attributes** —
`sAMAccountName`, `userPrincipalName`, `objectClass` (`user` / `computer` /
`group` as appropriate), `displayName`, and `objectSid` — **synthesized at read
time** from the governed principal data. The veneer is **opt-in** (a deployment
toggle / binding option, off by default) and **bounded** to that allow-list; it
adds no attribute the AGD cannot deterministically derive from canon + the
principal snapshot. It is a projection (ADR-100 §3): synthesized on read, never
stored.

### 2. Synthesized, explicitly non-authoritative — especially the SID

The synthetic `objectSid` is a **deterministic, namespaced, clearly
non-authoritative** value: derived by hashing the stable principal id into a
**reserved synthetic domain SID** that no real AD domain issues, so it can never
collide with or be mistaken for an authoritative SID. It exists for *read
correlation* (tools that index by SID can group the projection), **not** as a
security principal: no Windows access check, token, or ACL should ever honor it,
and the AGD advertises it as synthetic. The AGD **does not issue authoritative
SIDs** — that is the identity authority's role (ADR-092 §1). The same holds for
every synthesized attribute: it mirrors governed truth, it does not mint it.

### 3. No AD-DC role — schema shape without the directory authority

The AGD **MUST NOT**, under this ADR:

- implement the AD **partition layout** (the Schema or Configuration naming
  contexts, the `rootDSE` AD-DC markers, the global catalog port);
- expose the AD **replication** surface (DRSUAPI / RPC) or present as a
  replication partner;
- be **domain-joinable** or answer the DC-locator (`_ldap._tcp` SRV / CLDAP
  ping) as a domain controller;
- issue a **Kerberos PAC** or stamp group SIDs into tickets (ADR-101 §4 already
  forbids the AGD being a credential authority).

It projects the *schema shape* AD tools read; it is not the *directory
authority* those tools' write/auth/replication paths expect.

### 4. The veneer does not widen the write surface

Synthesized AD attributes are **read-only and not governed facets**. A `modify`
of `sAMAccountName`, `objectSid`, `userPrincipalName`, etc. is refused
`unwillingToPerform` — they are derived, not stored, so there is nothing to write
and no adapter to route to (ADR-109 §2 already refuses non-governed writes). The
veneer changes what the AGD *reads like*, never what it *accepts as a write*.

### 5. The boundary line, stated once

| Act | Verdict | Why |
|---|---|---|
| Synthesize `sAMAccountName` / `UPN` / `objectClass` from governed data (read) | **Permitted** | Read projection of canon (§1, ADR-100 §3) |
| Synthesize a namespaced, non-authoritative `objectSid` for read correlation | **Permitted** | Mirrors truth, advertised synthetic (§2) |
| Issue an authoritative `objectSid` honored as a security principal | **Forbidden** | Issuing the production credential (ADR-092 §1) |
| Implement AD naming contexts / replication / global catalog | **Forbidden** | Becoming an AD-DC authority (§3) |
| Answer DC-locator / accept domain join | **Forbidden** | Presenting as a domain controller (§3) |
| Issue a Kerberos PAC / stamp SIDs into tickets | **Forbidden** | ADR-101 §4 (not a credential authority) |
| `modify` a synthesized AD attribute | **Forbidden** | Not a governed facet; nothing to write (§4, ADR-109 §2) |

A PR that crosses any "Forbidden" row is a boundary violation, rejected at
review absent a superseding ADR.

## Consequences

**Positive.**

- AD-native read tooling can consume the projection in the shape it expects
  (`sAMAccountName`, `objectClass`, a correlatable SID) without UIAO standing up
  an Active Directory or claiming an authority it does not have.
- The non-authoritative-SID rule makes the disclosure honest: nothing the AGD
  emits can be mistaken for a security principal, so the veneer cannot become an
  accidental privilege surface.
- Bounded + opt-in + read-only keeps the blast radius small and the §3/§4
  prohibitions auditable.

**Negative / costs.**

- A synthesized AD veneer invites the assumption that the AGD *is* an AD; the
  synthetic-SID advertisement and documentation must make the non-authoritative
  posture unmissable, or an operator could wire it where a real DC is expected.
- Deriving stable, collision-free synthetic identifiers (SID, sAMAccountName)
  from principal data is a design task with its own edge cases (renames,
  truncation, uniqueness) the implementation must handle deterministically.
- Some AD tools will probe for the partition/replication surface the AGD
  deliberately lacks and degrade; that is the intended boundary, not a bug.

**Neutral.**

- Doctrine only — no runtime, schema, or registry change lands here (consistent
  with ADR-092, ADR-100, ADR-101, ADR-109).
- Amends ADR-100 §4; composes with ADR-100 §3 (projection, not store), ADR-101
  §4 (not a credential authority), and ADR-109 §2 (non-governed writes refused).

## Alternatives considered

- **No AD schema (status quo).** Rejected as the ceiling. Generic LDAPv3 is
  enough for modern tools but leaves AD-native read tooling unable to consume the
  projection — the interop gap a modern AD replacement should close. The veneer
  closes it without crossing into authority.
- **Full AD emulation (Samba-AD / a real DC).** Rejected. Implementing the AD
  partition layout, replication, global catalog, domain join, and PAC issuance
  *is* rebuilding the domain controller ADR-092 §1 rejected, and makes the AGD a
  credential/authority data plane.
- **Authoritative SIDs from a UIAO-owned domain SID.** Rejected. Minting SIDs a
  Windows access check would honor makes UIAO a security-principal authority — the
  "issue the production credential" act ADR-092 §1 forbids. Synthetic,
  advertised-non-authoritative SIDs give the read-correlation benefit without the
  authority.

## References

- [ADR-092](adr-092-active-governance.md) — control-plane/data-plane boundary;
  §1 forbids issuing the production credential / a data-plane authority position.
- [ADR-100](adr-100-active-governance-directory-ldap.md) — the AGD; §3
  (projection, never a store), §4 (the AD-schema deferral this ADR resolves).
- [ADR-101](adr-101-active-governance-directory-sasl-kerberos.md) §4 — the AGD is
  not a credential authority (no KDC, no PAC).
- [ADR-109](adr-109-active-governance-directory-write-as-intent.md) §2 —
  non-governed attributes are not writable (so synthesized AD attrs stay read-only).
- RFC 4519 / Microsoft `[MS-ADTS]` — the AD/LDAP attribute shapes (`sAMAccountName`,
  `objectSid`, `objectClass`) the veneer mirrors at read time.
