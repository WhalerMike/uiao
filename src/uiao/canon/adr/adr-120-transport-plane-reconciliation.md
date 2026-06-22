---
adr_id: adr-120
title: "Transport-Plane Reconciliation — Rename the Sixth Mission Class to `overlay`, Re-Allocate ADR-066's Squatted Spec Slots"
status: PROPOSED
decided: 2026-06-22
deciders: Michael Stratton
updated: 2026-06-22
next_review: 2026-12-22
review_trigger: "The first overlay-plane spec (UIAO_203/204/205) is drafted and registered; a customer declares an SD-WAN / SASE / service-mesh fabric as an active governance target; ADR-066 is moved toward ACCEPTED; the `overlay` mission-class name is contested by a later ADR; the GCC-Moderate token-issuer Path A/B decision (ADR-066 §GCC-Moderate boundary impact) is taken."
supersedes: null
superseded_by: null
amends: adr-066
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-120-transport-plane-reconciliation.html
impact: "Corrects two bookkeeping defects in ADR-066 (Application-Aware Networking and Token-Bound Transport Plane) without changing its doctrine. (1) Renames the proposed sixth mission class from `transport` to `overlay`, because `transport` is already the established name for identity-plane write-back seams (uiao.adapters.okta_transport, ldap_transport, keycloak_transport, auth0_transport, pingone_transport — ADR-098/099/113), and a sixth mission class sharing that token would be permanently ambiguous. The drift class renames `DRIFT-TRANSPORT` → `DRIFT-OVERLAY` for consistency; `overlay-fabric.schema.json` keeps its name. (2) Re-allocates ADR-066's three reserved spec slots — UIAO_122/123/124 — which were silently squatted by unrelated adapter-program docs (Adapter Developer Training Program, Adapter Integration & Test Plan, Adapter Operations Runbook). The corrected reservations are UIAO_203 / UIAO_204 / UIAO_205. No spec is authored here and no document-registry entry is added (registering a path that does not yet resolve would emit a blocking DRIFT-PROVENANCE finding); the slots are entered into document-registry.yaml when each spec is drafted, with this ADR as the reservation of record. Changes no shipped code, no facet semantics, no boundary scope."
---

# ADR-120: Transport-Plane Reconciliation

## Status

**PROPOSED** — 2026-06-22.

This ADR **amends** [ADR-066](adr-066-application-aware-networking-and-token-bound-transport.md)
(Application-Aware Networking and Token-Bound Transport Plane). ADR-066 is
itself still `PROPOSED`; this ADR does not supersede it and does not alter
its doctrinal direction. It corrects two bookkeeping defects that block
ADR-066's downstream work from starting cleanly, and it locks in a naming
decision before the first artifact is written.

## Context

ADR-066 ratified the *direction* — promote the network path to a
first-class governed concern via a sixth mission class, token-bound
per-call authorization, and a typed `OverlayTunnel` object — six weeks
ago. None of its verification checklist has landed. In the interval, two
problems surfaced that make a verbatim resumption of ADR-066 unsafe.

### Problem 1 — the `transport` mission-class name is already taken

ADR-066 §Decision #1 proposes adding **`transport`** as the sixth
canonical mission class to UIAO_003. But since ADR-066 was drafted, the
word `transport` became the established name for a *different* concept:
the identity-plane **write-back seam**. ADR-098 / ADR-099 / ADR-113
shipped a family of `mission-class: identity` adapters whose Python
modules are `uiao.adapters.okta_transport`, `ldap_transport`,
`keycloak_transport`, `auth0_transport`, and `pingone_transport` — each
a `(method, path, body) -> dict` HTTP write seam against an IdP. That is
not the network/overlay path ADR-066 means; it is the wire over which an
identity facet is written back to a binding target.

A sixth mission class literally named `transport`, sitting next to a
half-dozen `*_transport` identity adapters, would be a permanent source
of ambiguity in every grep, registry scan, and conformance conversation.
The collision must be resolved *before* UIAO_003 §4.8 is written, not
after.

### Problem 2 — ADR-066's reserved spec slots were squatted

ADR-066 §Consequences ("Canon work required") reserves three UIAO_NNN
allocations for its downstream specs:

| ADR-066 reservation | Intended spec |
|---|---|
| UIAO_122 | Token-Based Transport Authorization Specification |
| UIAO_123 | Application-Aware Overlay Fabric Model |
| UIAO_124 | Transport Plane Telemetry Contract |

All three IDs are now held in `document-registry.yaml` by **unrelated**
documents:

| ID | Actual occupant (current) |
|---|---|
| UIAO_122 | `specs/adapter-developer-training-program.md` |
| UIAO_123 | `specs/adapter-integration-test-plan.md` |
| UIAO_124 | `specs/adapter-operations-runbook.md` |

The reservation lived only in ADR-066's prose, so nothing stopped the
next allocator from taking the numbers. This is the same failure mode
ADR-066 documents about *itself* (its ADR-047 → ADR-057 → ADR-066
renumber history), one layer down — a prose-only reservation is not a
reservation.

## Decision

### D1 — Rename the sixth mission class `transport` → `overlay`

The sixth canonical mission class added to UIAO_003 is **`overlay`**, not
`transport`. Rationale:

- It matches the object ADR-066 already names — the **`OverlayTunnel`** —
  and the **Overlay Fabric** enforcement layer already canonical in
  `specs/zero-trust.md` (UIAO_120) and ADR-030 §2.
- It is disjoint from the `*_transport` identity-adapter vocabulary, so
  the two senses never collide.
- `overlay-fabric.schema.json` (ADR-066's reserved schema name) already
  uses the `overlay` root, so the schema name is unchanged.

For the same consistency reason the proposed drift class is
**`DRIFT-OVERLAY`**, not `DRIFT-TRANSPORT`. Severity guidance from
ADR-066 §"Drift taxonomy extension" carries over verbatim; only the class
name changes.

The role statement is unchanged from ADR-066 §"Lane discipline":
`mission-class: overlay` adapters **observe** the live overlay/path
state, **reconcile** it against canonical intent, and **emit** evidence —
they do **not** route packets, terminate tunnels, or hold a data-plane
position.

### D2 — Re-allocate the spec trio to UIAO_203 / 204 / 205

ADR-066's three downstream specs are re-reserved at the next free
allocations (the registry's highest current ID is UIAO_202):

| New ID | Spec (title carried from ADR-066, "Transport" → "Overlay") |
|---|---|
| **UIAO_203** | Token-Based Overlay Authorization Specification |
| **UIAO_204** | Application-Aware Overlay Fabric Model (`OverlayTunnel` object, lease semantics, drift binding) |
| **UIAO_205** | Overlay-Plane Telemetry Contract (NetFlow / IPFIX / eBPF ingestion for `mission-class: overlay` conformance adapters) |

### D3 — Reservation discipline (how the squat does not recur)

No spec is authored in this ADR, and **no `document-registry.yaml` entry
is added here.** Registering a UIAO_NNN whose `path` does not yet resolve
would emit a blocking `DRIFT-PROVENANCE` finding from the substrate
walker (`src/uiao/substrate/walker.py` — a registry document that is
missing on disk is a P-level drift). The entry for each of UIAO_203/204/205
is added to the registry **in the same PR that drafts that spec**, when
the file exists.

Until then, **this ADR is the reservation of record.** The standing rule:
before allocating any UIAO_NNN ≥ 203, check open ADRs for an outstanding
reservation on that number. The durable fix for prose-only squatting is
to register the slot (as a `status: Draft` stub) the moment work starts —
not to leave it in prose, which is what failed here.

## Consequences

### What this ADR changes

- ADR-066's `transport` mission class is read as **`overlay`** everywhere
  downstream (UIAO_003 §4.8, the schema, the drift taxonomy, the reserved
  adapter slots, the executive-orders pillar row).
- ADR-066's `DRIFT-TRANSPORT` is read as **`DRIFT-OVERLAY`**.
- ADR-066's UIAO_122/123/124 reservations are **void**; the live
  reservations are **UIAO_203/204/205**.
- A forward-pointer banner is added to ADR-066 so a reader who lands there
  first is routed to this reconciliation.

### What this ADR does NOT change

- No doctrine. ADR-066's three decisions (sixth mission class; token-bound
  per-call authorization; typed `OverlayTunnel`) stand exactly as written;
  only the *name* of the class and the *numbers* of the specs move.
- No shipped code, no adapter behavior, no facet semantics (UIAO_151), no
  GCC-Moderate boundary scope. The `*_transport` identity adapters are
  untouched and keep their names — they were never the sixth mission
  class.
- No registry entries (see D3).

### Refreshed downstream checklist (replaces ADR-066 §Verification)

Each item below is its own future PR with its own allocation/registration;
none is in scope for this ADR:

- [ ] **UIAO_203** — Token-Based Overlay Authorization Spec drafted and
  registered (`status: Draft`) in `document-registry.yaml`. Must select
  the GCC-Moderate token-issuer **Path A (in-boundary, preferred)** or
  document a **Path B** exception with Amazon-Connect-grade rigor
  (ADR-066 §"GCC-Moderate boundary impact").
- [ ] **UIAO_204** — Application-Aware Overlay Fabric Model drafted and
  registered.
- [ ] **UIAO_205** — Overlay-Plane Telemetry Contract drafted and
  registered.
- [ ] **UIAO_003 §4.8** — "Overlay Adapter Class" section added, with
  ratification evidence pointing at the first reserved slot.
- [ ] **`overlay-fabric.schema.json`** — added under `src/uiao/schemas/`;
  `schema-validation.yml` row added.
- [ ] **`DRIFT-OVERLAY`** — added to the taxonomy SSOT
  (`docs/docs/16_DriftDetectionStandard.qmd`); `substrate-drift.yml`
  extended to surface it.
- [ ] **Reserved adapter slots** (`status: reserved`,
  `phase: phase-planning`): `sdwan-fabric`, `service-mesh`,
  `token-issuer`, `sase-egress` (modernization, `mission-class: overlay`);
  `flow-telemetry`, `posture-telemetry` (conformance,
  `mission-class: overlay`).
- [ ] **`canon/compliance/executive-orders.md`** (UIAO_004) — pillar row
  added: *Token-bound overlay authorization* → UIAO_003 §4.8, UIAO_203,
  UIAO_204. Citation chain: EO 14028 §3, EO 14144, *Cyber Strategy for
  America* (March 2026).

## Rejected alternatives

- **Keep the name `transport` and document the coexistence.** Rejected.
  Two unrelated meanings of `transport` (a mission class vs. an
  identity-adapter naming convention already in shipped code) would force
  a disambiguation footnote into every registry scan and conformance
  review in perpetuity. A clean, already-canonical synonym (`overlay`)
  exists; use it.
- **Edit ADR-066 in place instead of writing a reconciliation ADR.**
  Rejected for process hygiene. ADR-066 is `PROPOSED` so an in-place edit
  is not strictly barred, but recording *why* the name and numbers moved —
  the `*_transport` collision and the squat — has audit value that an
  in-place overwrite would erase. A discrete amending record matches how
  ADR-066 itself documented its renumber history.
- **Pre-register UIAO_203/204/205 now to lock them.** Rejected. The
  registry path-existence check (`DRIFT-PROVENANCE`, blocking) means a
  reservation entry without a file breaks CI. The slot is registered when
  the file lands (D3).
- **Name the class `path` instead of `overlay`.** Considered. `overlay`
  wins because it is already canonical vocabulary (`OverlayTunnel`,
  Overlay Fabric layer); `path` would introduce a third new term.

## Verification

This ADR's own acceptance is verified by:

- [ ] ADR-066 carries a forward-pointer banner to ADR-120.
- [ ] The ADR index lists ADR-120 alongside ADR-066.
- [ ] No `document-registry.yaml` change ships in this PR (D3).

The substantive verification is the refreshed checklist above; each line
ratifies its own implementation in a later PR.

---

This ADR ratifies the *correction*; ADR-066 still ratifies the
*direction*, and each downstream spec ratifies its own *implementation*.
