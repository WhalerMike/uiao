---
adr_id: adr-129
title: "Non-Federal Vertical Registration and the Commercial Governance Boundary"
status: ACCEPTED
decided: 2026-07-14
deciders: Michael Stratton
updated: 2026-07-14
next_review: 2027-01-14
review_trigger: The SOC 2 vertical pack is promoted from `proposed` to `active` (an operational SOC 2 CI gate or a paying commercial customer exists); a third vertical adapter pack is proposed; a `verticals-registry.yaml` is created (the ADR-085 deferred artifact); the `gcc-boundary` field is renamed to a vertical-neutral name; a second non-federal boundary value beyond `commercial-general` is proposed
supersedes: null
superseded_by: null
publish_to_site: false
publication_style: include
published_at: null
impact: 'Authorizes the first non-federal boundary value on the adapter registry. Adds `commercial-general` to the `gcc-boundary` enum in adapter-registry.schema.json — the boundary for non-federal, commercial-sector vertical adapter packs whose evidence is not scoped to a federal cloud boundary — and updates the field description to distinguish federal boundaries (gcc-moderate + named commercial-product exceptions) from non-federal vertical boundaries. Registers the SOC 2 Trust Services vertical pack (soc2-trust-services-catalog) in adapter-registry.yaml at status `proposed`, resolving the residual federal coupling that kept the ADR-085 vertical-agnosticism proof unregisterable. Does not promote the pack to `active` (no operational SOC 2 gate or customer yet) and does not create verticals-registry.yaml (still deferred). No runtime behavior changes.'
---

# ADR-129: Non-Federal Vertical Registration and the Commercial Governance Boundary

## Status

**ACCEPTED** — 2026-07-14.

This ADR realizes a piece of [ADR-085](adr-085-universal-enterprise-positioning.md)'s "future work": it gives a non-federal vertical adapter pack a place in the registry. It changes the adapter-registry schema (one enum value + a description) and adds one registry entry. It changes no runtime behavior, no canon concept, and no existing adapter.

On acceptance, the SOC 2 pack advances from `proposed` to **`active`**: D3's promotion conditions are met — the pack now has an operational conformance surface (`emit_evidence_bindings()` renders its declared `soc2-evidence-bindings.json` output, exercised by the adapter-conformance CI suite) and this ADR is ratified.

## Context

[ADR-085](adr-085-universal-enterprise-positioning.md) established that the UIAO core is vertical-agnostic and that federal compliance is one vertical adapter pack among many. To make that claim *executable* rather than aspirational, a second (non-federal) vertical adapter pack was authored — `src/uiao/adapters/soc2_trust_services_catalog/` — mapping SOC 2 Type II Trust Services Criteria to the **same** substrate surface slots (`control-planes.yml`) the federal FedRAMP/KSI pack binds. Its conformance tests prove the substrate carries a commercial-regulated regime with no federal coupling.

That pack shipped as a `scaffold` and was deliberately **not registered** in `adapter-registry.yaml`, because registration surfaced a concrete obstruction: the registry schema (`adapter-registry.schema.json`) makes `gcc-boundary` a *required* field whose enum is federal-only:

```
gcc-moderate
commercial-exception-amazon-connect
commercial-exception-sailpoint-nerm
commercial-exception-sailpoint-isc
```

The field's own description reads: *"Sanctioned governance boundary. UIAO canon: GCC-Moderate only. Each Commercial exception is a named-product carve-out approved by its own ADR."* All four values are federal-context: GCC-Moderate itself, or named commercial **products** used inside a federal deployment under a FedRAMP exception. There is **no value for a genuinely non-federal vertical** — a SOC 2 engagement in a commercial-sector environment that is not scoped to any federal cloud boundary at all.

So the substrate is vertical-agnostic, but the **registry schema still carries residual federal coupling**. A truthful SOC 2 registry row cannot be written without either (a) asserting a false `gcc-moderate` boundary — a positioning bug under ADR-085 D1 — or (b) extending the boundary enum, which ADR-085 D3 says must happen *"in lockstep with [an] authorizing ADR."* This is that ADR.

## Decision

### D1. `gcc-boundary` gains one non-federal value: `commercial-general`

Add `commercial-general` to the `gcc-boundary` enum. It denotes the governance boundary for a **non-federal, commercial-sector vertical pack whose evidence is regime-scoped, not federal-cloud-scoped**. Update the field description to state the distinction explicitly: federal packs use `gcc-moderate` or a named commercial-product exception; non-federal vertical packs use `commercial-general`.

This does not weaken the existing discipline. The description's warning — *"never as a generic cloud descriptor"* — was aimed at preventing the field from becoming a loose "which cloud" tag **for federal adapters**, to stop federal-boundary scope creep. `commercial-general` is not a cloud descriptor; it is the boundary marker for the class of packs that sit *outside* the federal boundary regime entirely. Federal adapters remain constrained to `gcc-moderate` and named exceptions.

### D2. The SOC 2 vertical pack is registered and, on acceptance, promoted to `active`

Register `soc2-trust-services-catalog` in `adapter-registry.yaml` with `class: conformance`, `gcc-boundary: commercial-general`, and its Trust Services Criteria (`CC6.x`/`CC7.x`/`CC8.x`) carried in the pack's mapping files rather than the NIST-patterned `controls` field. It lands at `proposed`; on this ADR's acceptance it advances to **`active`** under the D3 conditions below.

### D3. Promotion to `active` requires an operational surface plus ratification

The pack advances to `active` when an operational SOC 2 conformance gate exists (mirroring the federal pack's CI coverage) **and/or** a real commercial engagement consumes it — **and** when this ADR is ratified from PROPOSED to ACCEPTED. Both are now satisfied: the pack ships `emit_evidence_bindings()`, which renders its declared `soc2-evidence-bindings.json` output and is exercised by the conformance suite that runs in the adapter-conformance CI gate; and this ADR is ACCEPTED. `active` here matches the federal pack's own usage — operational and CI-covered — not "has a paying customer"; a real engagement would deepen the bindings' confidence, not change the status. Absent the operational surface, the pack would have stayed at `proposed` so the registry never overclaims.

### D4. `verticals-registry.yaml` remains deferred

ADR-085 also anticipated a `verticals-registry.yaml` that catalogs vertical *packs* the way `adapter-registry.yaml` catalogs individual *adapters*. This ADR does **not** create it. A single registry (adapter-registry) already holds both the federal and non-federal conformance catalogs; a dedicated verticals registry is warranted only once there are enough verticals to justify the second catalog, and it carries its own naming/ownership decisions. It stays deferred to a future ADR, and the `gcc-boundary` → vertical-neutral rename travels with that work.

## Consequences

**Changed in this ADR's landing PR:**

- `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` — `gcc-boundary` enum gains `commercial-general`; description updated for the federal/non-federal split.
- `src/uiao/canon/adapter-registry.yaml` — new `soc2-trust-services-catalog` entry (status `active`, boundary `commercial-general`).
- `src/uiao/adapters/soc2_trust_services_catalog/__init__.py` — `STATUS` → `active`; the "registry admission" note reflects the resolved finding; adds `emit_evidence_bindings()`, the operational renderer for the declared `soc2-evidence-bindings.json` output.
- `tests/conformance/test_soc2_vertical_scaffold.py` — asserts the `active` status, registry resolution with a `commercial-general` boundary, and the emitter's output shape.

**Not changed (deliberate):**

- No existing adapter, and no federal boundary value, is touched. Adding an enum value is backward-compatible: every existing registry row still validates.
- `verticals-registry.yaml` is not created (D4).
- The registry's `controls` field remains NIST-patterned (`^[A-Z]{2}-[0-9]+…`), which cannot express SOC 2 Trust Services Criteria (`CC6.1` etc.). This is a *second* residual federal coupling in the schema, surfaced by registering a non-federal pack. Rather than widen the shared pattern in this pass, the SOC 2 entry omits the (optional) `controls` field and carries its Trust Services Criteria in the pack's `mappings/slot-0N-*.yaml`; the field's vertical-neutral redesign travels with the deferred `verticals-registry.yaml` work (D4).

**Reversal cost:** Low. Removing the enum value and the one registry row reverts the change; no runtime or data migration is involved.

## Alternatives Considered

**A1. Register the SOC 2 pack with `gcc-boundary: gcc-moderate`.** Rejected: it asserts a federal boundary for a non-federal pack — the exact positioning bug ADR-085 D1 forbids, and it would corrupt any boundary-scoped query over the registry.

**A2. Make `gcc-boundary` optional for conformance-class mapping packs.** Rejected as the *first* move: relaxing a required field is a larger, cross-cutting schema change that weakens the constraint for every adapter, federal included. Adding one authorized enum value is the minimal, targeted change ADR-085 D3 sanctions. The optional/rename path is folded into the deferred `verticals-registry.yaml` work (D4), where the field's vertical-neutral redesign belongs.

**A3. Create `verticals-registry.yaml` now and register the SOC 2 pack there instead.** Rejected for scope: it duplicates the catalog the federal conformance pack already lives in (adapter-registry), and it carries independent naming/ownership decisions. One vertical does not justify a second registry; D4 keeps it deferred.

**A4. Leave the pack unregistered as a permanent scaffold.** Rejected: that leaves ADR-085's vertical-agnosticism claim provable in code but unrepresented in the registry — the very asymmetry that reads as "federal is still special." Registering it (even at `proposed`) is what makes the registry itself vertical-agnostic.

## References

- [ADR-085: Universal-Enterprise Positioning of the UIAO Core Engine](adr-085-universal-enterprise-positioning.md) — D1 (core is vertical-agnostic), D3 (boundary enum extended in lockstep with an authorizing ADR), and the "future work" this ADR realizes.
- [`src/uiao/canon/adapter-registry.yaml`](../adapter-registry.yaml) — the catalog this ADR extends.
- [`src/uiao/schemas/adapter-registry/adapter-registry.schema.json`](../../schemas/adapter-registry/adapter-registry.schema.json) — the schema whose `gcc-boundary` enum this ADR extends.
- `src/uiao/adapters/soc2_trust_services_catalog/` — the non-federal vertical pack registered here (SOC 2 Trust Services Criteria over the shared surface slots).
