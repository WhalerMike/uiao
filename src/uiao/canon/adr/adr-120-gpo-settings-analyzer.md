---
adr_id: adr-120
title: "GPO settings-level analysis: own the parse, consume Microsoft's GPO→MDM crosswalk"
status: PROPOSED
decided: 2026-06-21
deciders: Michael Stratton
updated: 2026-06-21
next_review: 2026-12-21
review_trigger: The Phase-2 Graph path (groupPolicyMigrationReports) is exercised against a real Intune tenant and the per-setting isMdmSupported verdicts are validated end-to-end (this ADR moves toward ACCEPTED); Microsoft publishes a stable, machine-readable GPO→CSP crosswalk we could vendor instead of calling Group Policy Analytics; the setting-name join proves too lossy and needs a structured key (settingType/parentId) instead of name matching; the OU-intent classifier needs GPO contents (not just linkage) to disambiguate intent
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-120-gpo-settings-analyzer.html
impact: "Adds a settings-level GPO analyzer in three layers under src/uiao/adapters: a pure offline gpreport.xml parser + type-based portability triage (gpo_analytics, Phase 1), a Graph adapter that consumes Intune Group Policy Analytics for the authoritative per-setting MDM verdict (intune_gpo_analytics, Phase 2), and a GPO→OrgPath migration planner that scopes each GPO to an OU intent + recommended dynamic-group target and maps each portability bucket to an Intune carrier mechanism (gpo_orgpath_plan, Phase 3). Surfaced as `uiao orgtree gpo analyze|plan`. Registers a new conformance adapter (intune-gpo-analytics) and a gpo-analytics output schema. The decision of record: we own the parse and the OrgPath join but do NOT rebuild Microsoft's GPO→CSP crosswalk."
---

# ADR-120: GPO settings-level analysis — own the parse, consume Microsoft's GPO→MDM crosswalk

## Status

**PROPOSED** — June 21, 2026

## Context

The Active Directory survey (`adapters/modernization/active_directory/survey.py`)
already inventories Group Policy, but only at the **linkage** level: it reads an
OU's `gPLink` to a boolean (`has_gpo`) and classifies OU *intent* from that plus
naming heuristics. It never reads GPO **contents**. So the survey can say "this
OU has a GPO," but it cannot answer the questions a Windows-endpoint
modernization team actually asks:

- What does each GPO *configure*?
- Which of those settings have an Intune (MDM/CSP) equivalent, and which do not?
- Where does each GPO land in the target estate, and who does it target?

This is the hard, valuable 80% of an AD→Intune/Arc migration, and the gap
between "we do GPO assessment" (as positioned) and what the code does (linkage
only) is a credibility liability.

The obvious build would be a complete **GPO→CSP crosswalk**: parse every setting
and map it to its Intune equivalent. That is a trap. The crosswalk is thousands
of settings, it drifts every Windows release, and **Microsoft already ships it
for free** — Intune **Group Policy Analytics** ingests GPO backup XML and reports
per-setting `isMdmSupported` + the MDM setting URI. Rebuilding it is a
multi-month maintenance treadmill we would lose on coverage and freshness.

## Decision

Build the analyzer in three layers, and draw the build-vs-buy line explicitly:

1. **Own the parse (Phase 1, offline).** `gpo_analytics.py` parses
   `Backup-GPO` `gpreport.xml` into a structured, schema-validated inventory of
   every setting, classified by **setting class** (admin-template, security,
   preference, script, folder-redirection, …) and a **coarse, indicative,
   type-based `portability_class`**. It is pure, deterministic, fixture-tested,
   and makes no network calls. The portability class is explicitly labelled a
   triage heuristic, not a verdict.

2. **Consume Microsoft's crosswalk (Phase 2, Graph).**
   `intune_gpo_analytics.py` drives the Intune Group Policy Analytics surface
   (`deviceManagement/groupPolicyMigrationReports` → `groupPolicySettingMappings`)
   over the injected `Transport` seam, and `apply_mdm_verdicts()` joins the
   authoritative per-setting `isMdmSupported` onto the Phase-1 inventory,
   overriding the heuristic `portability_class` (`csp-mappable` / `no-csp`) and
   flagging the source as `intune-gpa`. **We consume Microsoft's GPO→CSP
   crosswalk; we do not rebuild it.**

3. **Own the OrgPath join (Phase 3, offline).** `gpo_orgpath_plan.py` produces
   the part Microsoft does *not*: per GPO, resolve each enabled OU link → OU
   intent (via the survey's `classify_ou_intent`) → a recommended OrgPath
   dynamic-group target, and map each portability bucket → its Intune carrier
   mechanism (Settings Catalog profile, platform script, Account Protection,
   OneDrive KFM, retire). This is the facet-scoped migration plan that reinforces
   UIAO's actual differentiator instead of competing with a free Microsoft
   feature.

Surfaced as `uiao orgtree gpo analyze` and `uiao orgtree gpo plan`. The Graph
layer is registered as the `intune-gpo-analytics` conformance adapter
(`ssot-mutation: never` — the `createMigrationReport` action writes only a
transient analysis object; no governed customer object is mutated).

## Consequences

**Positive.** Closes the linkage-vs-contents gap honestly. The expensive,
perishable crosswalk stays Microsoft's problem. The differentiated value (facet-
scoped planning) is what we own and ship. Phases 1 and 3 are fully offline and
deterministic, so the bulk of the surface is testable without a tenant.

**Negative / risks.** The authoritative verdict requires a live Intune tenant
and `DeviceManagementConfiguration.ReadWrite.All`; like the rest of the OrgPath
device plane, the Graph path has not yet been exercised against a real tenant —
that validation is the named review trigger that moves this ADR to ACCEPTED. The
Phase-2 join matches on (normalized) setting **name**; if names prove unstable
across locales/Windows versions, the join must move to a structured key
(`settingType` + `parentId`). The OU-intent classifier still keys off linkage +
naming, not GPO contents, so a content-driven intent signal is a possible later
refinement.

## Alternatives considered

- **Rebuild a full GPO→CSP crosswalk in-repo.** Rejected: duplicates a free
  Microsoft feature, loses on coverage/freshness, and incurs permanent
  maintenance.
- **Stop at linkage triage (status quo).** Rejected: leaves the positioning gap
  open and provides no settings-level value.
- **Ship a static offline crosswalk only (no Graph).** Rejected as the *primary*
  verdict, but retained as a clearly-labelled indicative heuristic (Phase 1) for
  the no-tenant case.

## References

- `src/uiao/adapters/modernization/active_directory/gpo_analytics.py` (Phase 1)
- `src/uiao/adapters/intune_gpo_analytics.py` (Phase 2)
- `src/uiao/adapters/modernization/active_directory/gpo_orgpath_plan.py` (Phase 3)
- `src/uiao/schemas/gpo-analytics/gpo-analytics.schema.json`
- Microsoft Intune Group Policy Analytics — <https://learn.microsoft.com/mem/intune/configuration/group-policy-analytics>
- ADR-078 (OrgTree Model C), ADR-038 (device-plane OrgPath) — the device-plane lineage this analysis feeds.
