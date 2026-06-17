---
document_id: UIAO_195
title: "Addressing-Plane Drift Taxonomy — DNS and Namespace Governance"
version: "1.0"
status: Draft
owner: Michael Stratton
created_at: "2026-06-17"
updated_at: "2026-06-17"
publish_to_site: true
publication_style: include
lifecycle: aspirational
related_adrs:
  - ADR-108   # Addressing-plane drift gate
  - ADR-012   # Canonical drift taxonomy (identity plane)
  - ADR-033   # DRIFT-BOUNDARY extension
  - ADR-102   # LocPath location addressing
related_canon:
  - UIAO_151  # OrgPath Codebook
  - UIAO_163  # Drift Detection Engine Specification (Model C)
  - UIAO_179  # Canonical Drift Output Schema
  - UIAO_194  # LocPath Codebook
---

# UIAO_195: Addressing-Plane Drift Taxonomy

> The UIAO substrate governs two coordinate planes: the **identity plane**
> (OrgPath / UIAO_151) and the **addressing plane** (DNS namespace / this
> document). The identity plane classifies who/what an object is and where
> it sits organisationally. The addressing plane classifies where it is
> reachable and under whose naming authority. Both planes emit `Finding`
> objects via the shared `drift_core` primitive ([ADR-108](adr/adr-108-addressing-plane-drift-gate.md));
> the gate semantics are identical.

## 1 · Purpose

This document defines:

1. The **twelve drift classes** that apply to the DNS / addressing plane,
   grouped by observability tier (satisfiable from a zone-file read vs.
   requiring live multi-vantage probing).
2. The **severity and posture** assignment for each class.
3. The **intended-binding source** in the SSOT for each class.
4. The **mapping to the OrgPath five-class model** so the drift engine
   reads both planes through a single classification contract.
5. The **deferred observer requirements** for the three classes that cannot
   be satisfied from a static zone export.

The executable implementation lives in
`src/uiao/adapters/addressing/addressing_collector.py`, which imports the
plane-agnostic `Finding` / `gate` / `events_json` primitives from
`src/uiao/governance/drift_core.py`.

## 2 · Background

On-premises AD delivered identity-and-addressing coherence as a single
fused substrate (AD-integrated DNS). Cloud migration dissolves that fusion:
Entra has no DNS role; Azure Private DNS and Private Link are a separate
control plane; GCC-Moderate tenants run Microsoft 365 on commercial Graph
endpoints while Azure Government resources are at `management.usgovcloudapi.net`.
Split-horizon answers, dangling CNAME takeover, and absent SRV locators are
all live failure modes in this fractured landscape — none of which the
identity-plane drift engine can observe.

The addressing-plane taxonomy closes that gap. It is not a replacement for
the identity-plane taxonomy; it is a peer plane with its own SSOT, its own
classifiers, and its own gate.

## 3 · Drift classes

### 3.1 Satisfiable classes (zone-read + manifest + resource list)

| Class | Severity | Posture | OrgPath analog |
|---|---|---|---|
| **DRIFT-BINDING** | P1 (target absent) / P2 (wrong target) | never-autofix / per-policy | Value drift |
| **DRIFT-DANGLING** | P1 | never-autofix | Orphan (but security-grade) |
| **DRIFT-SHADOW** | P1 (governed collision) / P2 (ungoverned) | never-autofix | Phantom |
| **DRIFT-SRV** | P1 | never-autofix | No direct analog — auth-breaking |
| **DRIFT-CONFLICT** | P1 | never-autofix | Format (RFC violation) |
| **DRIFT-WILDCARD** | P2 | per-policy | Slot (masking structural slot) |
| **DRIFT-ORPHAN** | P3 | informational | Orphan |
| **DRIFT-PTR** | P2 | per-policy | No direct analog |
| **DRIFT-TTL** | P3 | informational | Format |

#### DRIFT-BINDING
A governed name (present in the SSOT intended-bindings manifest) resolves
to a target that differs from the canonical record. If the observed target
is itself absent from the live resource set, severity escalates to P1
(dead target = takeover exposure). Otherwise P2.

*Intended-binding source:* `intended_bindings.json` → `bindings[name].target`

#### DRIFT-DANGLING
An **ungoverned** name resolves to a resource (IP, host, CNAME target, MX
target) that is not present in the live resource inventory. Governed names
are handled by DRIFT-BINDING; this class is deliberately non-overlapping.
Dead CNAME and MX records carry identical takeover risk to dead A records.

*Intended-binding source:* `resources.json` (live inventory)

#### DRIFT-SHADOW
A name is present in the observed zone but absent from the SSOT registry
(neither a governed binding nor a declared system name). An out-of-band
record colliding with a governed name escalates to P1; an unknown record in
open space is P2.

*Intended-binding source:* `intended_bindings.json` → `bindings` +
`system_names`

#### DRIFT-SRV
A critical Kerberos/LDAP/GC/kpasswd service-locator SRV record is missing
or its target host is absent. Missing: auth-breaking (P1). Dead target:
P1 — auth will fail silently for clients that received the stale pointer.

*Intended-binding source:* `intended_bindings.json` → `required_srv` plus
the hard-coded CRITICAL_SRV set
(`_kerberos._tcp`, `_ldap._tcp`, `_gc._tcp`, `_kpasswd._tcp`).

#### DRIFT-CONFLICT
A CNAME record coexists with other record types at the same owner name.
RFC 1034 §3.6.2 and RFC 2181 §10.1 prohibit this; resolver behaviour is
undefined and varies by implementation.

*Intended-binding source:* RFC 1034/2181 (normative, not SSOT-derived)

#### DRIFT-WILDCARD
A wildcard record (`*.zone`) is present and an intended-specific name that
should be governed explicitly is absent, meaning the wildcard silently
answers for it. This masks a governance gap: the specific name should have
an explicit record with its own ownership, cert, and policy.

*Intended-binding source:* `intended_bindings.json` → `bindings`

#### DRIFT-ORPHAN
A delegated zone has zero referencing bindings in the SSOT manifest
(`ref_count == 0`). The zone is a retirement candidate; no live governance
path depends on it. P3 — informational.

*Intended-binding source:* `intended_bindings.json` → `zones[zone].ref_count`

#### DRIFT-PTR
A name that requires forward-confirmed reverse DNS (`requires_fcrdns: true`)
has no matching PTR in the observed zone. Affects mail delivery, identity
verification, and some logging pipelines.

*Intended-binding source:* `intended_bindings.json` → `bindings[name].requires_fcrdns`

#### DRIFT-TTL
A governed name carries a TTL that diverges from the policy range. P3 —
hygiene; does not affect resolution correctness but affects failover
responsiveness and cache behaviour.

*Intended-binding source:* `intended_bindings.json` → `bindings[name].ttl_policy`
*(Not yet implemented in the collector; scaffolded here for completeness.)*

### 3.2 Deferred classes (require live observation)

These three classes are declared in the taxonomy and referenced by the
collector but are not classified from a zone-file read. Each lists its
required observation capability. Canonising them here as Provisional allows
the taxonomy to be the stable contract while the observers are built.

| Class | Required observation | Status |
|---|---|---|
| **DRIFT-HORIZON** | Multi-vantage resolution probe — query from internal (on-prem resolver), external (public), and per-VNet (Azure Private Resolver) vantage points; compare answers. A boundary leak is a P1. | Provisional — observer not yet built |
| **DRIFT-CAA/TLSA** | Endpoint TLS cert inspection + CAA record read against the governed CA set. Wrong issuer or cert-name mismatch is P1 (issuance-policy violation). | Provisional — observer not yet built |
| **DRIFT-DELEGATION** | Parent-NS delegation walk + glue record validation. Delegation mismatch is a P2; absent glue that breaks resolution is P1. | Provisional — observer not yet built |

## 4 · OrgPath five-class mapping

The OrgPath identity-plane taxonomy (UIAO_163) defines five drift categories
operating per attribute slot: **Format**, **Value**, **Slot**, **Orphan**,
**Phantom**. The addressing-plane classes map onto that vocabulary as follows,
so the drift engine can aggregate across planes with a single classification
language:

| Addressing class | OrgPath analog | Notes |
|---|---|---|
| DRIFT-BINDING | Value | Name resolves to the wrong target — a value mismatch |
| DRIFT-DANGLING | Orphan + security escalation | Reference to an absent resource; P1 because takeover |
| DRIFT-SHADOW | Phantom | Record exists in zone but not in SSOT |
| DRIFT-SRV | (no direct analog) | Auth-breaking locator failure; unique to addressing plane |
| DRIFT-CONFLICT | Format | RFC violation — structural malformation |
| DRIFT-WILDCARD | Slot | Wildcard occupies and masks a slot that should be explicit |
| DRIFT-ORPHAN | Orphan | Zone with no dependents |
| DRIFT-PTR | (no direct analog) | FCrDNS binding; addressing-plane only |
| DRIFT-TTL | Format | Policy-range deviation |
| DRIFT-HORIZON | (no direct analog) | Boundary leak; closest to DRIFT-BOUNDARY (ADR-033) |
| DRIFT-CAA/TLSA | (no direct analog) | Issuance-policy violation; PKI-plane concern |
| DRIFT-DELEGATION | Slot + Format | Authority mismatch — wrong slot holder |

## 5 · SSOT projection model

The substrate projects the same governed coordinate onto three materialisation
surfaces:

| Surface | Carrier | Plane |
|---|---|---|
| Entra user / device | `extensionAttribute1-15` | Identity |
| Azure ARM resource / Arc machine | ARM tags | Identity + resource |
| DNS name (endpoint) | Zone records — type, target, TTL, CAA | **Addressing** |

The addressing-plane SSOT (`intended_bindings.json`) is the DNS projection of
the same OrgPath + LocPath coordinates that govern the identity plane.
A `name` in the bindings manifest is an endpoint edge of an `AppRef` node
(see UIAO_195 §6 — AppRef is the governed application node that joins
OrgPath authority, LocPath instances, and DNS-name edges).

The drift engine reconciles all three surfaces against the Codebook (UIAO_151)
using `drift_core.Finding` as the universal output shape. UIAO_179 specifies
how `Finding` maps to the canonical `DriftRecord` shape consumed by the
Evidence Fabric.

## 6 · AppRef — the missing third node (design note)

OrgPath answers *who/what organisationally*. LocPath answers *where
physically*. Applications require a third governed node — **AppRef** — that
carries:

- A stable non-DNS identity (Application Client ID / SPN / ARM resource ID).
- Facets: function, environment, tier, trust-boundary.
- An **ownership edge** to OrgPath (who governs this app).
- One-or-many **instance edges** to LocPath (where it runs).
- A set of **DNS-name edges** (each endpoint, with cert/SAN, steering policy,
  and boundary intent flag).

AppRef is *not* a fourth path. Applications form a dependency graph, not a
single-parent hierarchy; a path model (AppPath) would break the
`-startsWith` subtree-inheritance property that makes OrgPath and LocPath
work. AppRef is a faceted node over the dependency graph, joined to the
address plane through its DNS-name edges. This document designates AppRef as
the **boundary-intent carrier** for DRIFT-HORIZON: the `boundary_intent`
facet on a DNS-name edge is what makes "this name is private-only / GCC-only"
machine-readable and testable.

AppRef full specification is deferred; this note establishes it as a planned
primitive so DRIFT-HORIZON has a defined SSOT source when the observer is built.

## 7 · Open decisions

1. **UIAO_195 canon numbering confirmed** — UIAO_194 is LocPath (Draft).
2. **Collector sequencing** — `dns_dhcp_survey.ps1` and the Azure DNS export
   adapter are on the Tier-1 build list. The collector is ready; the data
   pipeline is the constraint.
3. **Issuance-policy CA set** — DRIFT-CAA/TLSA requires a governed set of
   approved CAs per boundary (commercial / GCC-M / GCC-H). Location: TBD
   (likely a facet of the PKI adapter manifest, UIAO_###).
4. **Boundary-intent representation** — `boundary_intent` on the DNS-name
   edge is the SSOT source for DRIFT-HORIZON; deferred to AppRef
   specification (§6 above).
5. **Finding composition policy** — a single name can currently produce
   multiple independent findings (e.g., DRIFT-DANGLING + DRIFT-SHADOW).
   Canon should declare whether findings compose (current: yes, each
   independent defect is reported) or deduplicate to a single root cause.
   **Default: compose.** A shadow name pointing at a live rogue host is a
   different risk than one pointing at nothing; composing both findings
   preserves that distinction.
