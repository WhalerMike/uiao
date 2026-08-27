---
adr_id: adr-139
title: "Coverage-and-gap doctrine is per-plane — allocate UIAO_015 for the governance plane"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-08-27
next_review: 2027-02-27
review_trigger: Any SailPoint slot promotes from reserved to active (the §2.3 status-reality statement in UIAO_015 stops being true and the doctrine must be revised in the same PR); a third coverage-plane sibling is proposed (network/PAM or the federal attribute services), which tests whether the per-plane pattern generalises or needs a registry of its own; ADR-059 §Decision 5 is superseded, which would invalidate UIAO_015 §4's arbitration table; a non-Entra primary IdP is adopted, which the §4 rule is not written for; the status-disclosure obligation in UIAO_015 §5.3 is proposed for extension to Microsoft claims in UIAO_009 §4.4 (Open Question 1)
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-139-governance-plane-coverage-doctrine.html
impact: "Generalises coverage-and-gap accounting from a Microsoft one-off into a per-plane family, and allocates UIAO_015 as the first sibling — the governance plane (SailPoint identity governance, ServiceNow ITSM). Records that the recurring 'SailPoint+ServiceNow or native?' question is malformed because the registries classify by behaviour (class × mission-class), not by vendor, and adopts a four-step task-classification test that resolves a task from declared registry fields rather than judgement. Explicitly makes NO new decision about SailPoint/Entra SSOT arbitration: UIAO_015 §4 restates ADR-059 §Decision 5 verbatim in effect, and this ADR records that restatement as documentation, not extension. Adds one genuinely new normative obligation — customer-facing governance-platform claims must state the adapter slot's status, so reserved capacity is never presented as deployed capability. Doctrine- and allocation-shaped: no registry entries, no schema change, no runtime code, no adapter implementation."
---

# ADR-139: Coverage-and-gap doctrine is per-plane — allocate UIAO_015 for the governance plane

## Status

**PROPOSED** — 2026-08-27

## Context

### Thread 1 — UIAO_009 was built as a one-off, and the shape generalises

[ADR-049](adr-049-microsoft-adapter-coverage-expansion.md) §Decision 2
directed that the "what Microsoft provides / what UIAO must build"
articulation be promoted from inbox-scratch material to canonical
doctrine. That directive produced
[UIAO_009](../UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md), which
is explicitly and deliberately Microsoft-scoped.

The document's shape turned out to be more general than its subject: a
coverage map (§2), a gap list (§3), a decision frame (§1), and a rule
binding customer-facing claims to both (§4.4). Nothing in that shape is
Microsoft-specific. What is Microsoft-specific is the content.

UIAO_009 §5 records four open items but does not name the largest one:
**the same accounting has never been written for any other plane.**

### Thread 2 — the governance plane is where the absence actually hurts

The substrate declares SailPoint across six adapter slots and ServiceNow
across one, pinned by
[UIAO_210](../specs/external/sailpoint-iiq/UIAO_210_identityiq-api-contract-pin.md)
and
[UIAO_211](../specs/external/servicenow/UIAO_211_servicenow-deployment-contract-pin.md),
and governed by [ADR-059](adr-059-sailpoint-adapter-family.md),
[ADR-092](adr-092-active-governance.md),
[ADR-135](adr-135-sailpoint-isc-governance-option-b-ratification.md), and
[ADR-136](adr-136-sailpoint-identityiq-option-c-slot-allocation.md).

Every piece exists. No document assembles them into an answer to the
question practitioners actually ask: *do we produce compliance evidence
through SailPoint and ServiceNow, through native Entra / Azure / M365, or
both?*

That question recurs because it is **malformed**, and nothing in canon
says so. The registries do not split on vendor. They split on the two
declared axes — `class` (does it write?) and `mission-class` (what does it
claim?) — which is why a product that both observes and acts receives two
declarations, one per registry. UIAO_009 §2.2 already names this for
Intune ("two-axis declaration per ADR-049 §Decision 1"); the SailPoint,
SCuBA, and Defender for Cloud Apps pairs follow the same precedent
without anywhere saying so.

### Thread 3 — the overlap is decided but undiscoverable

`entra-id-governance` covers Access Reviews, Entitlement Management,
Lifecycle Workflows, PIM, and SoD. `sailpoint-isc-governance` covers
certification campaigns, entitlement-management packages,
lifecycle-workflow runs, and SoD findings. That is substantially one
conceptual surface offered by two vendors, and SailPoint additionally
ships native Entra ID and Active Directory connectors.

[ADR-059](adr-059-sailpoint-adapter-family.md) §Decision 5 already rules
on it: UIAO holds SSOT for all Entra/AD writes, and an overlapping writer
must be UIAO-mediated or fail closed. **The ruling is sound and is not
reopened here.** The problem is purely one of discoverability — the rule
lives inside an ADR about allocating one NERM slot, so a practitioner
reasoning about ISC entitlements has no reason to find it.

### Thread 4 — reserved capacity reads as deployed capability

Of the seven governance-platform slots, exactly one — `service-now` — is
`status: active`. Every SailPoint slot is `reserved`, which per ADR-059
§Decision 6 means contract-shaped, not implemented.

A coverage map that lists scope without status therefore reads, to a
customer or an assessor, as a description of working capability. UIAO_009
§4.4 binds claims to the doctrine but says nothing about disclosing
maturity, because at the time it was written the distinction had not
bitten.

## Decision

1. **Coverage-and-gap doctrine is per-plane, not global.** UIAO_009 is
   re-framed as the first member of a family rather than a standalone
   document. Each plane whose surfaces UIAO leverages gets its own
   coverage-and-gap doctrine, sharing UIAO_009's section shape: a decision
   frame, a coverage map with adapter declarations, a gap list, and the
   claim-grounding rule. ADR-049 §Decision 2 is **unchanged** — this ADR
   extends the pattern it started; it does not amend it.

2. **Allocate UIAO_015 for the governance plane.**
   `UIAO_015 — Governance-Platform Coverage And Gap Doctrine`, covering
   SailPoint (identity governance) and ServiceNow (ITSM), at
   `status: Draft`. Allocated in the UIAO_002–UIAO_099 band the
   document-registry header reserves for top-level canon documents,
   adjacent to its UIAO_009 sibling rather than continuing the 200-range
   reserved for operational/runtime artifacts.

3. **Adopt the task-classification test.** A governance or compliance task
   is routed by four questions answered from declared registry fields, in
   order: does it mutate the estate (`class`); what does it claim
   (`mission-class`); what evidence and cadence (`evidence-class`); which
   surface is authoritative. A task that cannot be expressed as a registry
   entry with those fields is not specified well enough to build.

   The corollary is normative: **a vendor is not a category.** Canon shall
   not classify governance work by product name.

4. **No new SSOT decision is made here.** UIAO_015 §4's arbitration table
   is a restatement of [ADR-059](adr-059-sailpoint-adapter-family.md)
   §Decision 5, promoted to a discoverable location. Where the two differ
   in wording, ADR-059 governs. This ADR creates no new rule about
   SailPoint, Entra, or Active Directory write paths.

   One clarification is recorded rather than decided, because it follows
   from the existing rule: on **reads**, both surfaces may observe the
   same governance state, and divergence between them is a drift finding
   per [ADR-040](adr-040-drift-engine.md) — not a conflict to be settled
   by choosing a winner. The SSOT invariant constrains writes.

5. **Status disclosure is obligatory for governance-platform claims.**
   UIAO_015 §5.3 extends the UIAO_009 §4.4 grounding rule: customer-facing
   material claiming "SailPoint provides X" or "ServiceNow provides Y"
   shall ground the claim in the doctrine **and shall state the slot's
   `status`**, so reserved capacity is never presented as deployed
   capability.

   This obligation is scoped to governance-platform claims in this ADR.
   Whether it should also bind Microsoft claims under UIAO_009 §4.4 is
   Open Question 1 below — it is not decided here, because UIAO_009 is not
   this ADR's to amend.

6. **Doctrine-shaped only.** No registry entries change, no schema
   changes, no runtime code, no adapter implementation, and no adapter
   status promotion. UIAO_015 describes declarations that already exist.

7. **Named deferrals, not silent ones.** The planes this doctrine does
   not cover are enumerated in UIAO_015 §6 with reasons: the network plane
   and PAM; the eleven federal attribute services; alternate IdP families;
   and per-slot control mappings. Each is a candidate sibling under
   Decision 1, not an omission.

## Consequences

### Easier

- The recurring "SailPoint+ServiceNow or native?" question has a canonical
  answer, and the answer explains why the question was the wrong shape.
- ADR-059 §Decision 5 becomes discoverable from the place a practitioner
  is actually reading when the overlap matters.
- New adapter proposals on the governance plane have the same gating
  discipline UIAO_009 §4.1 gives Microsoft proposals.
- Customer-facing material has an explicit, checkable rule for not
  overstating reserved slots.

### Harder

- Two doctrine documents must now be kept consistent where they touch
  (the claim-grounding rule, the two-axis classification). Divergence
  between UIAO_009 §4.4 and UIAO_015 §5.3 is now possible and is the
  main maintenance cost this ADR incurs.
- Every future plane invites a sibling document. Without discipline this
  becomes a documentation sprawl; Decision 1 sets the shape precisely to
  bound that, and Open Question 2 asks whether an index is needed.

### Required

- UIAO_015 §2.3 must be revised in the same PR as any slot promotion from
  `reserved` to `active`. This is the `review_trigger` on this ADR.
- Any future coverage-plane doctrine shall follow UIAO_009's section
  shape, so the family stays comparable.

## Notes

### Open questions

1. **Should status disclosure bind Microsoft claims too?** UIAO_009 §2
   lists numerous `reserved` Microsoft adapters — `defender-for-endpoint`,
   `defender-for-servers`, `defender-for-cloud-apps`, `azure-migrate`,
   `azure-policy-arc`, `entra-id-governance`, `entra-workload-identity`,
   the `intune` pair. The overstatement risk Decision 5 addresses is not
   specific to SailPoint. Extending the obligation to UIAO_009 §4.4 is a
   one-line amendment, but amending UIAO_009 is outside this ADR's scope
   and belongs in its own change.

2. **Does the family need an index?** With two members a cross-reference
   in each suffices. At three or more, a coverage-doctrine index — or a
   `plane` field in the document registry — may be warranted.

3. **The §4 arbitration rule assumes Entra is the SSOT holder.** The five
   alternate-IdP slots (`okta-orgpath`, `ldap-orgpath`, `keycloak-orgpath`,
   `auth0-orgpath`, `pingone-orgpath`) are all `proposed`. If any is
   adopted as a primary IdP, the rule needs restating for that topology.

### Provenance of this ADR

Unlike ADR-049 §Decision 2, which directed UIAO_009 into existence, no
directive preceded UIAO_015. The doctrine was authored first — while
answering the practitioner question in Thread 2 — and this ADR was
written afterwards to give it an authorizing decision record and to
separate what UIAO_015 *restates* (Decision 4) from what it *newly
obliges* (Decision 5). Recorded here so the sequence is not mistaken for
a directive that never existed.

### See also

- [UIAO_009](../UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md) — the Microsoft sibling.
- [UIAO_015](../UIAO_015_Governance_Platform_Coverage_And_Gap_Doctrine_v1.0.md) — the document this ADR authorizes.
- [UIAO_003](../UIAO_003_Adapter_Segmentation_Overview_v1.0.md) — the dual-axis taxonomy Decision 3 relies on.
- [ADR-049](adr-049-microsoft-adapter-coverage-expansion.md) §Decision 2 — the directive that created the pattern.
- [ADR-059](adr-059-sailpoint-adapter-family.md) §Decision 5 — the SSOT arbitration rule Decision 4 restates.
- [ADR-092](adr-092-active-governance.md) — control-plane slots and the L0–L4 actuation ladder.
- [ADR-040](adr-040-drift-engine.md) — the drift classification Decision 4's read-divergence clarification relies on.
