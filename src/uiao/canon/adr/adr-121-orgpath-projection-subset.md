---
adr_id: adr-121
title: "OrgPath projection subset — stamp fewer attributes per object than the codebook defines"
status: PROPOSED
decided: 2026-06-21
deciders: Michael Stratton
updated: 2026-06-21
next_review: 2026-12-21
review_trigger: A tenant deployment validates the 6-facet projection against a real directory (this ADR moves toward ACCEPTED); a shipped rule needs one of the demoted facets (role / cost_center) re-projected; the agency decides to drop cleared-only and division-scoped policies and wants the 4-facet projection; directory schema extensions are adopted to escape the 15-slot cap entirely (would supersede the slot-projection framing)
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-121-orgpath-projection-subset.html
impact: "Adds a `projected` boolean to each codebook facet (default true). Non-projected facets keep their semantics but are not stamped to a directory extensionAttribute slot, so attributes-written-per-object drops from 10 to 6 on the canonical codebook (region/department/division/classification/clearance_level/account_type projected; role/cost_center/hire_date/term_date demoted). Touches codebook.py (Facet.projected + Codebook.projected_facets), codebook.schema.json (+optional projected), the canonical codebook.yaml, and the device-plane writer (skips non-projected alongside reserved). In-memory codebooks default projected=true, so existing fixtures and the shipped rule libraries (which reference only projected facets) are unaffected."
---

# ADR-121: OrgPath projection subset — stamp fewer attributes per object than the codebook defines

## Status

**PROPOSED** — June 21, 2026

Amends the projection policy of **ADR-078** (the 15-facet Model C schema). ADR-078's
slot bindings are unchanged; this ADR adds a control over *which* facets are written.

## Context

ADR-078 defined ten named facets, each bound to its own `extensionAttribute`
slot (1–10), and the device/user writers stamp all ten per object. That clean
one-facet-per-slot design is what makes the dynamic-group rules simple
(`device.extensionAttribute2 -eq "Finance"`). But ten attributes per object
collides with hard, real-world constraints:

1. **The 15 `extensionAttribute` slots are a shared, tenant-wide resource.**
   Exchange, AD-sync, and other governance tooling routinely already occupy
   several of the fifteen. Claiming ten for OrgPath is often infeasible in a
   brownfield tenant.
2. **For hybrid-synced users, `onPremisesExtensionAttributes` are read-only in
   Entra** — they sync *from* on-prem AD and cannot be written via Graph. The
   more user facets OrgPath tries to write to Entra, the more of them silently
   can't be written for exactly the synced users most agencies have.
3. **15 is a hard ceiling** with no headroom.

Not every defined facet needs to occupy a scarce directory slot. Several are
never the subject of a dynamic-group / Conditional-Access / Intune rule:
inspection of the shipped libraries (`dynamic-groups.yaml`,
`policy-targets.yaml`, `admin-units.yaml`) shows **no** rule references `role`,
`cost_center`, `hire_date`, or `term_date`. The two date facets are lifecycle
(JML) inputs, not targeting keys; `cost_center` is chargeback/reporting data;
`role` has no current rule.

## Decision

Introduce a **projection subset**: a `projected` boolean on each facet
(default `true`). A non-projected facet keeps its full semantics — it is still a
validated facet for HR-SSOT, reporting, drift-on-input, and JML — but it is
**not stamped to a directory slot**. "Attributes written per object" therefore
equals the *projected* count, not the *defined* count.

On the canonical codebook, demote the four facets no rule uses:

- **Projected (6):** `region`, `department`, `division`, `classification`,
  `clearance_level`, `account_type`.
- **Not projected (4):** `role`, `cost_center` (reporting → HR-SSOT),
  `hire_date`, `term_date` (lifecycle → JML workflow).

Enforcement is at the device-plane writer (`device_orgpath.plan_device`), which
already skips `reserved` facets and now also skips non-projected ones. The
default `projected=true` means in-memory codebooks, test fixtures, and the
shipped rule libraries (which reference only projected facets) are unaffected.

## Consequences

**Positive.** Drops stamped attributes 10 → 6, freeing four directory slots
per object for other tenant tooling and shrinking the hybrid-synced read-only
exposure. Reversible and per-facet: re-projecting `role` (or any facet) is a
one-line governed codebook edit. No shipped rule breaks. The defined facet set
and all facet semantics are preserved.

**Negative / limits.** This does not reach a 4-facet projection: `division` and
`clearance_level` are still projected because the shipped libraries target them
(division-scoped AUs/groups; cleared-only Conditional Access). Demoting those
two would require dropping or rewriting those policies — a capability decision
for the deploying organization, deliberately left out of this ADR. Projection
also does not fix the device write-target question (cloud device
`extensionAttributes` vs `onPremisesExtensionAttributes`) — that is a separate
correctness fix.

## Alternatives considered

- **Delete the four facets outright.** Rejected: ripples through nine binding
  profiles and ~twenty test files, and loses HR-SSOT/JML semantics the facets
  still legitimately carry. Projection keeps the definitions and confines the
  change to the write path.
- **Composite-pack several facets into one slot** (`-contains`/`-match` rules).
  Rejected here as the default: it trades clean `-eq` matching for fragile
  substring rules and partially reverses Model C. Still available to tenants
  that exhaust slots.
- **Directory schema extensions** (escape the 15-slot cap, cloud-writable for
  synced users). The cleanest long-term fix to the underlying constraints, but
  larger plumbing; tracked as a review trigger, not done here.

## References

- `src/uiao/canon/data/orgpath/codebook.yaml` (projection flags + header)
- `src/uiao/modernization/orgtree/codebook.py` (`Facet.projected`, `Codebook.projected_facets`)
- `src/uiao/modernization/orgtree/device_orgpath.py` (writer skips non-projected)
- `src/uiao/schemas/orgpath/codebook.schema.json` (`projected` property)
- ADR-078 (Model C 15-facet schema — amended, not superseded), UIAO_151 (codebook narrative canon).
