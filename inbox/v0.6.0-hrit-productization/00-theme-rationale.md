# 00 — Theme Rationale: HRIT Single-ATO Reciprocity Productization

> **Status:** Inbox draft. Not canon. Authored 2026-05-05.
>
> **Renumber note (2026-05-11):** The proposed ADR-058 referenced below
> was renumbered to **ADR-065** to resolve a slot collision with
> `adr-058-microsoft-purview-conformance-adapter-coverage.md` (accepted
> 2026-05-07). The spec slot moved similarly: UIAO_143 → **UIAO_144**
> (UIAO_143 is now SCIM Core Schema per PR #342). Historical inbox
> drafts retain original numbers for traceability.

## Why this theme, why now

ADR-054 + UIAO_140 + Spec2-D6.1 ratified the **Single-ATO Reciprocity Model**
on 2026-05-04 — a single SSP, single ATO, N consuming agencies under
reciprocity, anchored to OPM Solicitation 24322626R0007. The doctrine is
airtight; the runtime that emits per-agency reciprocity records, enforces
the 30/45-day cadence, and aggregates per-agency evidence bundles is
**explicitly deferred** in ADR-054 §Implementation (lines 157–164).

Picking this as the v0.6.0 mission theme is defensible on five axes:

1. **Doctrine is fresh and complete.** No ratification gap to close before
   building. The contract is already in canon.
2. **Federal anchor is concrete.** OPM Solicitation 24322626R0007 Amd 4 PWS
   §5.1.1 #5 + Q&A #43/44/47/48 + Clause 1752.239-74 give crisp acceptance
   criteria (30-day draft SSP, 45-day final, single code line,
   configuration-only differentiation, OPM CIO is final ATO authority).
3. **Schema foundation is in place.** `reciprocal-consumption-registry.schema.json`
   is shipped (#315). The registry YAML exists empty, awaiting its first
   runtime consumer.
4. **No path collisions.** Proposed paths (`src/uiao/oscal/reciprocity_record.py`,
   `src/uiao/cli/reciprocity.py`, `tests/test_reciprocity_*.py`,
   `examples/hrit/`, `docs/docs/22_HRITProductization.qmd`) are all clear.
5. **Reciprocity is the founder's stated v1 goal.** Throughout the
   assessment thread the maintainer named transferable / reciprocal ATOs
   as a career-driven design conviction. ADR-054 turned that conviction
   into canon. v0.6.0 turns canon into a shippable runtime.

## What this theme is *not*

- **Not Login.gov adapter activation** — that's ADR-056 Stage 3, citizen-
  facing, parallel work. Could run alongside but doesn't depend on this.
- **Not KYC adapter implementation** — that's ADR-055 + UIAO_141/142,
  customer-side. Complementary, not blocking.
- **Not Microsoft Tier-1 adapter completion** — that's the #299 Phase 2
  follow-on. Independent work stream.
- **Not transport plane (ADR-057 candidate, pending renumber)** —
  speculative doctrine, recommend keeping queued.

## Acceptance for v0.6.0

A maintainer at OPM (or any agency operating a single-ATO platform) can:

1. Run `uiao reciprocity onboard-agency --controlling-ato <id> --consuming-agency <code>`
   and receive a signed reciprocity-record artifact for the agency.
2. Verify the record validates against the reciprocity-record JSON Schema.
3. Verify it integrates with the evidence graph as an `ato-decision` →
   `reciprocity-record` edge.
4. Enforce 30/45-day SSP cadence + 30-day reauthorization SLA via
   `uiao conmon ato-cadence-check`.
5. Detect configuration outside the SSP's enumerated latitude as a
   `DRIFT-SCHEMA` finding.
6. Aggregate per-agency evidence into a bundle that any consuming agency
   AO can independently verify without UIAO platform access.

A stranger walks the v0.6.0 quickstart end-to-end against a synthetic
"OPM + Treasury + IRS" three-agency fixture in under 15 minutes and
produces three signed reciprocity records.

## What gets ratified before any code lands

Phase 0 (single sequential session, after maintainer reviews this inbox
package):

1. Promote `02-proposed-adr-058-draft.md` to
   `src/uiao/canon/adr/adr-065-hrit-productization-mission.md` (Accepted)
   — note: originally proposed as ADR-058, renumbered to ADR-065 to
   resolve slot collision
2. Allocate **UIAO_144** (HRIT Productization Operational Spec) in
   `document-registry.yaml` — note: originally proposed as UIAO_143,
   renumbered to UIAO_144 (UIAO_143 is now SCIM Core Schema)
3. Stub `src/uiao/canon/specs/hrit-productization.md` (UIAO_144)
4. Stub `src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`
5. Create branch scaffolding for the 10 Batch A workstreams in
   `03-batch-plan.md`
6. Tag baseline commit `v0.5.x-pre-hrit`

Then Batch A runs in parallel (up to 10 concurrent AI sessions).
