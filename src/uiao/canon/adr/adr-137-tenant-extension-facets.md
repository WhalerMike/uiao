---
adr_id: adr-137
title: "Tenant-extension facets — admin tier, device type, and environment on slots 11-13"
status: ACCEPTED
decided: 2026-08-21
deciders: Michael Stratton
updated: 2026-08-21
next_review: 2027-02-21
review_trigger: A tenant needs a fourth extension facet and slot 14 is the last one free (note that site is not a candidate — see the Site is not the fourth facet section); a rule library stops targeting one of these three (it should then be demoted to projected:false rather than deleted); directory schema extensions escape the 15-slot cap; admin tiering is superseded by a Microsoft-native construct that carries the tier itself
supersedes: null
superseded_by: null
amends:
  - adr-121-orgpath-projection-subset.md
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-137-tenant-extension-facets.html
impact: 'Promotes the three reserved codebook slots extensionAttribute11-13 to declared facets — admin_tier (Tier0/Tier1/Tier2), device_type (Kiosk/Workstation/Server/GitServer) and environment (Production/Staging/Dev) — each enumerated and projected. Amends ADR-121: attributes written per object rises from 7 to 10, leaving extensionAttribute14 as the only unclaimed extension slot. Motivated by shipped Conditional Access, Intune and PKI rule libraries that were targeting these three concepts through the role, classification and cost_center facets, which mean something else and (for role and cost_center) are not projected at all, so those rules could never match. Each is projected but optional (allow_empty), which this ADR extends from typed to enumerated facets so an unpopulated slot is a legitimate state rather than drift — without that, device_type would put a permanent finding on every user. Touches codebook.yaml (schema_version 2.2.0), codebook.schema.json, the Codebook loader, the drift engine, the OrgPath inventory, UIAO_151, and the rule libraries that referenced the wrong slots.'
---

# ADR-137: Tenant-extension facets — admin tier, device type, and environment on slots 11-13

## Status

**ACCEPTED** — 2026-08-21

Amends **ADR-121** (projection subset). ADR-078's slot bindings for facets 1-10
are untouched; ADR-127's derived path on slot 15 is untouched, and its
`derived_from` composition (region, department, division) is deliberately
unchanged — see §Decision 4.

## Context

A sweep of the corpus for facet values outside their own enumerations returned
roughly sixty hits. Grouped by facet, they were not missing values. They were
three coherent concepts, each being written into a facet that means something
else:

| Facet | What it means | What the rule libraries put in it |
| :--- | :--- | :--- |
| `role` (`extensionAttribute4`) | Job seniority — Analyst, Engineer, Architect, Manager, Director, VP, CISO, CIO, CTO | `Tier0`, `Tier1`, `Tier2` — administrative tiering (18 occurrences) |
| `classification` (`extensionAttribute6`) | Worker type — Employee, PartTime, Contractor, Intern, Executive, Volunteer | `Kiosk`, `Workstation`, `Server`, `GitServer` — device type (9 occurrences) |
| `cost_center` (`extensionAttribute5`) | Accounting codes — `CC-4100` … `CC-9100` | `Production`, `Staging`, `Dev` — deployment environment (10 occurrences) |

The Conditional Access library, the Intune policy templates, the PKI
modernization guide and the CLI operations guide all target these values.

Two things follow. First, the rules are wrong twice over: `role` and
`cost_center` are **not projected** under ADR-121, so nothing is written to
slots 4 and 5 on any object, and a rule reading them matches nobody regardless
of the value. ADR-121's own `review_trigger` anticipated exactly this —
"a shipped rule needs one of the demoted facets (role / cost_center)
re-projected".

Second, the obvious repair — adding the values to the enumerations that already
hold them — would make `role` mean both "Analyst" and "Tier0", and
`classification` mean both "Contractor" and "Kiosk". The codebook's entire
purpose is per-facet validation; a facet that admits two unrelated vocabularies
cannot reject anything useful, and the drift engine loses the ability to flag a
device type stamped on a person.

The codebook already reserves slots 11-14 for precisely this situation, with
the instruction to declare semantics "via a governed PR before populating
values in the tenant." This is that PR.

## Decision

**Promote three reserved slots to declared, enumerated, projected facets.**

1. **`admin_tier` — `extensionAttribute11`.** Administrative tiering of the
   principal: `Tier0` (identity/control plane), `Tier1` (server and
   application administration), `Tier2` (workstation and helpdesk).
   Orthogonal to `role`: a Director and an Engineer can both be Tier0, and
   tier governs blast radius while role governs seniority. Conditional Access
   targets it directly.

2. **`device_type` — `extensionAttribute12`.** Form factor and purpose of a
   device object: `Kiosk`, `Workstation`, `Server`, `GitServer`. Applies to
   device principals; `classification` remains a property of people.

3. **`environment` — `extensionAttribute13`.** Deployment environment:
   `Production`, `Staging`, `Dev`. Distinct from `cost_center`, which is an
   accounting code and answers "who pays", not "what breaks if this is
   misconfigured".

4. **`derived_from` is unchanged.** The derived OrgPath on slot 15 still
   composes region, department, division only. None of these three is a
   hierarchy level — a Tier0 account is not "beneath" anything — so adding
   them to the path would produce a string that is not a hierarchy and would
   break subtree prefix matching. They are targeted by facet composition, not
   by prefix.

5. **All three are projected, and all three are optional.** They exist to be
   targeted by live Conditional Access, Intune and Azure Policy rules, which
   read directory attributes, so an unprojected facet is invisible to those
   engines. But projection alone would make every existing principal
   non-compliant the moment this ADR lands, and `device_type` cannot apply to
   a user at all — every user would carry a permanent finding for a facet
   that is meaningless on them.

   So each carries `allow_empty: true`, and this ADR extends that flag's
   meaning from typed facets to enumerated ones: **an unpopulated slot is a
   legitimate state, while any populated value is still validated against the
   enumeration.** A tenant adopts admin tiering, device typing and
   environment scoping incrementally, and the drift engine reports only real
   errors — a wrong value, never an absent one. No enumerated facet used
   `allow_empty` before this ADR, so the semantic extension changes nothing
   already in the codebook.

6. **`extensionAttribute14` stays reserved.** One unclaimed extension slot
   remains.

## Consequences

### Positive

- The shipped CA, Intune and PKI rules can match for the first time: the values
  they target are now written to slots that exist, under facets that mean what
  the rules assume.
- Each facet keeps one vocabulary, so the drift engine can still reject a
  device type stamped on a person, or a tier value in the seniority facet.
- No hierarchy facet changes, so the derived path, every subtree rule, and
  `Get-OrgPathPrefix` are untouched.
- Honouring `allow_empty` in the inventory's completeness check also retires
  a latent false positive: `term_date` is empty by design for anyone still
  employed, and the survey had been counting it as a missing facet on every
  active person.

### Negative / deferred

- **Attributes written per object rises from 7 to 10** where all three are
  adopted, amending ADR-121's count. Because they are optional, a tenant that
  adopts none still writes 7. Projected slots are now 1, 2, 3, 6, 9, 10, 11, 12, 13 plus the
  derived path on 15. This spends most of the headroom ADR-121 bought; the
  slot-scarcity argument in that ADR still stands, and the answer to a fourth
  extension concept is more likely to be directory schema extensions than
  slot 14.
- Slots 4, 5, 7 and 8 remain defined-but-unprojected. Demoting a facet is
  cheap; the ledger above is the reason to keep them that way.
- Hybrid-synced users carry the ADR-127 trap on the new slots as well:
  `onPremisesExtensionAttributes` is read-only in the cloud, so these must be
  stamped on-prem and allowed to sync, or deferred until the object is
  cloud-only.
- Existing tenants that populated slots 11-13 for their own purposes now
  conflict with a canonical declaration. There are no production adopters at
  ratification time, so no migration is defined; a future tenant in that
  position takes the ADR-063 rebind procedure and the
  `DRIFT-SCHEMA::slot-occupied` finding delivered by ADR-064.

## Alternatives considered

**Add the values to the existing enumerations.** Rejected: it makes `role` and
`classification` each mean two unrelated things permanently, in the one file
whose job is validation, and it would not fix the rules, because `role` and
`cost_center` are unprojected and stay unmatched.

**Re-project `role` and `cost_center` and use them as-is.** Rejected for the
same conflation reason, and because it spends two slots to encode the wrong
concepts — an admin tier is not a job title.

**Leave the rules broken and correct the documentation instead.** Rejected:
the CA and Intune libraries describe controls the programme intends to ship.
Rewriting them to target facets that exist today would silently drop admin
tiering, kiosk handling and environment scoping from the control set.

## Site is not the fourth facet

The same sweep found two rules scoped by **site** — a place name (`HQ`,
`HeraldHarbor`) sitting in the `department` facet. That is the identical
defect class, and the obvious symmetry would be to spend `extensionAttribute14`
on a `site` facet.

**Do not.** Physical place is already a governed, first-class axis:
[ADR-102](adr-102-locpath-location-addressing.md) establishes **LocPath**
(`/Country/Region/Site/Building/Floor/Space`, Site as the minimum governance
unit), specified by [UIAO_194](../UIAO_194_LocPath_Codebook.md). ADR-102 §D5 is
explicit that LocPath *"is not a sixteenth OrgPath facet and claims no
`extensionAttribute` slot"* — governance rules predicate on the **OrgPath ×
LocPath matrix**, prefix-matching on each axis independently.

So a site-scoped policy targets the LocPath exposure's site group or
Administrative Unit (`LocPath-Site-<SITE>-Users`, `AU-Site-<SITE>`), whose
membership is **assigned** from the governed Primary-LocPath assignments rather
than read from a stamped attribute. A deployment that later adopts LocPath
storage-on-target gets a locator through an
[ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md) binding profile —
a per-target parameter, never a claimed slot.

This ADR therefore leaves `extensionAttribute14` unclaimed *and* records why the
most likely candidate for it is not a candidate at all. The site-scoped rules
found by the sweep were repointed to LocPath site groups, not to a new facet.
