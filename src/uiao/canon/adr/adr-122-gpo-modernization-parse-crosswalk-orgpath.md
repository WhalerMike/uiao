---
adr_id: adr-122
title: "GPO Modernization — Own the Parse, Consume Microsoft's Crosswalk, Differentiate on the OrgPath Join"
status: PROPOSED
decided: 2026-06-21
deciders: Michael Stratton
updated: 2026-06-21
next_review: 2026-12-21
review_trigger: The Phase 2 spike validates (or invalidates) live consumption of the Group Policy Analytics migration report through Microsoft Graph against a real tenant (this ADR moves toward ACCEPTED); Microsoft retires or restructures the groupPolicyMigrationReport / groupPolicySettingMapping beta surface; Microsoft Graph promotes the Group Policy Analytics resources from beta to v1.0 (the dependency-risk posture changes); the parser intermediate representation needs to cover a GPO extension family (drive maps, printer deployment, GPP) the v1.0 scope deferred; a non-Intune MDM crosswalk is required and the "consume Microsoft" decision needs re-examination
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-122-gpo-modernization-parse-crosswalk-orgpath.html
impact: "Records the build-vs-buy split for the GPO→Intune modernization surface — Gap #3 of UIAO_009 §3.3 — as a three-part decomposition: UIAO BUILDS a deterministic GPO parser (finite, owned), CONSUMES Microsoft's Group Policy Analytics crosswalk live through Graph rather than rebuilding the per-setting GPO→MDM mapping (perishable, Microsoft's domain), and DIFFERENTIATES on the OrgPath join — binding parsed GPO scope to OrgPath device cohorts (UIAO_152 / ADR-036) and Intune assignments (UIAO_164 / ADR-039) to produce the sequenced migration order Microsoft does not provide. Allocates UIAO_014 as the technical specification (schema, phases, interfaces). Registry-shaped, not implementation-shaped: a reserved `gpo-modernization` modernization adapter and any code land in follow-on PRs per the ADR-049 precedent."
---

# ADR-122: GPO Modernization — Own the Parse, Consume Microsoft's Crosswalk, Differentiate on the OrgPath Join

## Status

**PROPOSED** — June 21, 2026

Operationalizes [Gap #3 of UIAO_009 §3.3](../UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md)
("GPO → Intune mapping with operational sequencing"), which ADR-049 §Decision 2
named as a UIAO-owned gap with "no current adapter; future work." This ADR is
that future work's decision record: it fixes *which parts of the surface UIAO
builds and which it consumes* before any code is written.

## Context

On-premises Group Policy is the largest unmigrated configuration estate in a
typical AD-to-Entra modernization. Moving it to Intune is squarely inside UIAO's
mission, and [UIAO_009 §3.3](../UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md)
already records *that* it is a gap UIAO owns. What UIAO_009 does **not** settle is
the build-vs-buy boundary inside the surface — and that boundary is the whole
decision. Get it wrong in the expensive direction and the program spends a
quarter rebuilding something Microsoft gives away and re-obsoletes on its own
release cadence.

The surface decomposes into three parts with sharply different economics. Naming
them separately is what makes the decision obvious:

| Part | Character | Who should own it |
|---|---|---|
| **Parse** — turn GPO backup XML / `registry.pol` / SYSVOL artifacts into a normalized, queryable model of *what each policy sets and whom it scopes to* | **Finite, deterministic, tractable.** The GPO file formats are documented and change slowly; a correct parser is a bounded engineering problem with a clear "done." | **UIAO builds.** |
| **Crosswalk** — map each individual GPO setting to its cloud/MDM (Intune CSP / settings-catalog) equivalent, where one exists | **Infinite, perishable, Microsoft's domain.** The mapping spans thousands of settings, gains and loses entries every Intune release, and is only authoritative coming from Microsoft. | **UIAO consumes — does not rebuild.** |
| **OrgPath join** — bind the parsed GPO scope (links, security filtering, WMI filters) to OrgPath device cohorts and emit a *sequenced* migration order | **The only proprietary leverage.** No Microsoft surface produces the cross-cohort order; this is where UIAO's OrgPath substrate is the differentiator. | **UIAO differentiates.** |

The three parts map one-to-one onto the three outcomes of the UIAO_009 §1
two-question frame: Parse is **Build** (no Microsoft surface for a
governance-grade IR), Crosswalk is **Declare-and-consume** (Microsoft-provided
and sufficient), and the OrgPath join is **Declare-and-structure** (Microsoft
data plane, UIAO structure on top).

### Microsoft already ships the crosswalk

Microsoft's **Group Policy Analytics** (GPA) imports a GPO backup and reports,
per setting, whether a cloud MDM equivalent exists and what it is — and it
exposes the result through Microsoft Graph (beta), not just the Intune admin UI.
The relevant resources are `groupPolicyMigrationReport` (the per-GPO analysis),
its `groupPolicySettingMapping` children (the per-setting GPO→MDM crosswalk
rows), `groupPolicyObjectFile` (the imported GPO), and
`groupPolicyConfiguration` / `groupPolicyConfigurationAssignment` (the resulting
Intune policy and its assignment). The surface requires an active Intune license
on the tenant. See **References**.

This is the decisive fact. The crosswalk is not a gap — it is a *consumable
Microsoft surface*. Rebuilding a per-setting GPO→CSP table inside UIAO would
mean re-deriving, and then re-validating every Intune release, a mapping
Microsoft maintains as a first-party product. Microsoft's velocity makes that
unwinnable as a standalone UIAO feature: the maintenance burden compounds each
release and collapses the ROI of the whole effort. The honest framing is that a
hand-maintained crosswalk silently rots — it looks complete on the day it ships
and is wrong by the next Intune wave, with no signal to the operator that it has
drifted.

### Where Microsoft stops — and UIAO's leverage begins

GPA maps settings. It does **not** answer the question a migration actually
turns on: *in what order do we move these GPOs, given a device population with
overlapping OU links, security-group filtering, and inherited settings?* That
sequencing is exactly the "order" UIAO_009 §3.3 names as the part Microsoft does
not provide. It is the only clause in the whole surface UIAO does not get for
free — and it is the clause that keeps the project honest, because it is the
only part where UIAO's OrgPath substrate is doing work no vendor replicates.

UIAO already owns the machinery the join needs: OrgPath device cohorts as
dynamic groups (UIAO_152 / ADR-036), policy targeting that binds Intune
assignments to those cohorts (UIAO_164 / ADR-039), and the OrgPath dependency
graph (ADR-035, ADR-038). The missing piece is the GPO-scope → OrgPath-cohort
binding and the topological sequencing on top of it.

## Decision

1. **Adopt the three-part decomposition (parse / crosswalk / OrgPath join) as
   the canonical build-vs-buy split for the GPO→Intune surface.** This is the
   load-bearing decision; every item below follows from it. The decomposition
   refines UIAO_009 §3.3 from "a gap UIAO owns" to "a gap UIAO owns *one third
   of*, structures the second third of, and consumes the middle third from
   Microsoft."

2. **BUILD the GPO parser (UIAO-owned).** UIAO authors a deterministic parser
   that reads GPO backup XML, `registry.pol`, and the SYSVOL scope artifacts
   (GPO links, security filtering, WMI filters) and emits a normalized,
   versioned **GPO intermediate representation (GPO-IR)** — the model of *what
   each policy sets* and *whom it scopes to*. The parser is the build because the
   formats are finite and documented, the output is canon-grade structured data
   UIAO controls, and no Microsoft surface emits a governance-IR of GPO scope.
   Parsing is pure and offline: it requires no tenant and no Graph call, which is
   precisely why it is the right thing to build first and the cheapest to test.

3. **CONSUME Microsoft's crosswalk through Graph — do not rebuild it.** UIAO
   submits the parsed GPO to Group Policy Analytics and consumes the
   `groupPolicyMigrationReport` / `groupPolicySettingMapping` result through
   Microsoft Graph as the authoritative per-setting GPO→MDM mapping. UIAO does
   **not** author or maintain its own GPO→CSP table.
   - The crosswalk is treated as a **live, perishable external dependency**:
     consumed at migration time, never snapshotted into canon as a static map.
     A frozen copy is the maintenance burden that collapses ROI; canon records
     the *contract* with GPA (resource shapes, license requirement, beta-surface
     risk), not the mapping rows themselves.
   - Where GPA reports a setting as **unsupported** (no MDM equivalent), that is
     a first-class IR outcome, not an error — it feeds the residual-GPO backlog
     the OrgPath sequencing must account for, never a silently dropped setting.

4. **DIFFERENTIATE on the OrgPath join (UIAO structure on Microsoft data).**
   UIAO joins the parsed GPO scope (GPO-IR) to OrgPath device cohorts and emits
   the sequenced migration plan:
   - GPO link/filter scope → OrgPath cohort (UIAO_152 dynamic groups / ADR-036);
   - migrated settings → Intune assignment to that cohort (UIAO_164 policy
     targeting / ADR-039);
   - a **topologically ordered migration sequence** over cohorts with
     overlapping membership and inherited settings — the "order" UIAO_009 §3.3
     names as the Microsoft gap;
   - drift classification of the result into the canonical five-class taxonomy
     (ADR-040), so a half-migrated GPO is an observable finding, not a blind
     spot.

5. **Allocate UIAO_014 as the technical specification.** The schema (GPO-IR +
   the GPA consumption contract + the OrgPath-join output), the phase plan, and
   the module interfaces land in
   [`UIAO_014`](../UIAO_014_GPO_Modernization_Parse_Crosswalk_OrgPath_Join_v1.0.md),
   registered in `document-registry.yaml` alongside this ADR. UIAO_014 is the
   planning artifact; this ADR is the decision it implements.

6. **Registry- and spec-shaped, not implementation-shaped (ADR-049 precedent).**
   This ADR creates no Python and edits no adapter registry. A reserved
   `gpo-modernization` modernization adapter
   (`class: modernization`, `mission-class: integration` per UIAO_003) is a
   follow-on PR; it promotes to `active` under its own per-adapter ADR when
   implementation begins, exactly as ADR-049 §Decision 4 prescribes for the
   surfaces it declared.

7. **De-risk the consume path first (the one-day spike).** The parser is offline
   and low-risk; the **only unvalidated dependency** is live consumption of the
   Group Policy Analytics report through Graph against a real tenant — the beta
   surface, the Intune-license gate, and the permission scope have never been
   run live in this stack. Phase 2 of UIAO_014 is a one-day spike that imports
   one real GPO and reads its `groupPolicyMigrationReport` back through Graph,
   scheduled **before** the parser build is hardened, so the decision to consume
   is validated against reality rather than against the documentation.

## Consequences

### Positive

- **Bounded, finite build.** UIAO builds the parser and the OrgPath join — both
  tractable, both UIAO-controlled — and consumes the one infinite, perishable
  part from its first-party owner. The estimate is a ~4–5 week build for
  parse + join versus the 3–6 month treadmill a self-maintained crosswalk would
  become.
- **No crosswalk rot.** Because the GPO→MDM mapping is read live from GPA,
  UIAO inherits Microsoft's per-release coverage updates for free and never
  ships a map that is silently stale.
- **The differentiator is isolated.** The OrgPath join is the only proprietary
  surface, and it is exactly where UIAO already has substrate (OrgPath cohorts,
  policy targeting, drift engine). Investment concentrates on the part no vendor
  replicates.
- **Doctrine stays consistent.** The decomposition is a clean instance of the
  UIAO_009 §1 frame, reinforcing rather than special-casing the coverage
  doctrine.

### Negative / costs

- **A live Graph + Intune-license dependency on the critical path.** The
  migration cannot run crosswalk analysis air-gapped; it requires a tenant with
  an Intune license and the Graph permission scope. The parser and the OrgPath
  join degrade gracefully (parse is offline; the join can run against a cached
  report), but a *fresh* crosswalk needs the live call.
- **Beta-surface exposure.** The Group Policy Analytics resources are on the
  Graph **beta** endpoint. UIAO accepts beta-contract instability as a tracked
  risk (see `review_trigger`) rather than insulating against it by rebuilding —
  insulation here *is* the treadmill.
- **One more canon document and a reserved adapter to carry.** UIAO_014 is one
  allocation; the reserved adapter is one registry row in a follow-on PR. Both
  are cheap relative to the surface they govern.

### Risks

- **GPA restructure or deprecation.** If Microsoft reorganizes the
  `groupPolicyMigrationReport` surface, the consumption contract in UIAO_014
  must be revised. Mitigation: the contract is small and isolated to the
  consume adapter; the parser (GPO-IR) and the OrgPath join are unaffected
  because they sit on either side of it.
- **Coverage assumption.** If GPA's MDM-equivalent coverage is materially worse
  than assumed for a given estate, the residual-GPO backlog dominates and the
  migration value drops. The Phase 2 spike surfaces this early by reporting the
  supported/unsupported ratio on a real GPO before the build is committed.

## References

- [Use Microsoft Intune to import and analyze group policies (Group Policy Analytics)](https://learn.microsoft.com/en-us/intune/intune-service/configuration/group-policy-analytics) — Microsoft Intune documentation (what GPA is; Intune-license requirement).
- [groupPolicyMigrationReport resource type — Microsoft Graph beta](https://learn.microsoft.com/en-us/graph/api/resources/intune-gpanalyticsservice-grouppolicymigrationreport?view=graph-rest-beta) — the per-GPO analysis resource consumed by Decision 3.
- [Migrate your imported group policy to a policy in Microsoft Intune](https://learn.microsoft.com/en-us/intune/intune-service/configuration/group-policy-analytics-migrate) — the `groupPolicyConfiguration` migration path.
- [UIAO_009 §3.3 — GPO → Intune mapping with operational sequencing](../UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md) — the gap this ADR operationalizes.
- [ADR-049 — Microsoft Modernization Adapter Coverage Expansion](adr-049-microsoft-adapter-coverage-expansion.md) — §Decision 2 names this gap; §Decision 4 sets the registry-shaped/follow-on precedent.

## See Also

- [UIAO_014 — GPO Modernization technical specification](../UIAO_014_GPO_Modernization_Parse_Crosswalk_OrgPath_Join_v1.0.md)
- [ADR-036 — Dynamic Group Provisioning](adr-036-dynamic-group-provisioning.md) (OrgPath cohorts)
- [ADR-039 — Policy Targeting](adr-039-policy-targeting.md) (Intune assignment binding)
- [ADR-040 — OrgTree Drift Detection Engine](adr-040-drift-engine.md) (drift classification of the join result)
- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
