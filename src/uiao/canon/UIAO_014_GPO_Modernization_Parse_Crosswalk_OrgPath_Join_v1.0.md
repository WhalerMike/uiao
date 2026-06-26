---
document_id: UIAO_014
title: "GPO Modernization — Parse, Crosswalk, OrgPath Join"
version: "1.0"
status: Draft
owner: "Michael Stratton"
created_at: "2026-06-21"
updated_at: "2026-06-21"
canonical_adrs:
  - ADR-122
  - ADR-036
  - ADR-039
  - ADR-040
  - ADR-049
canonical_docs:
  - UIAO_009
  - UIAO_007
  - UIAO_152
  - UIAO_164
publish_to_site: true
publication_style: include
---

# UIAO_014 — GPO Modernization: Parse, Crosswalk, OrgPath Join

## Overview

This specification is the planning artifact for the GPO→Intune modernization
surface. Its decision record is
[ADR-122](adr/adr-122-gpo-modernization-parse-crosswalk-orgpath.md); its doctrinal
home is [UIAO_009 §3.3](UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md)
(Gap #3 — "GPO → Intune mapping with operational sequencing"). Where ADR-122
fixes *what UIAO builds, consumes, and differentiates on*, this document fixes
*the schema, the phases, and the interfaces* that realize that decision.

The surface is decomposed into three parts with deliberately different
ownership, per ADR-122:

| Part | UIAO posture | Why |
|---|---|---|
| **Parse** → GPO intermediate representation (GPO-IR) | **Build** | Finite, deterministic, offline. No Microsoft surface emits a governance-grade IR of GPO scope. |
| **Crosswalk** → GPO setting → MDM/CSP equivalent | **Consume** (Microsoft Group Policy Analytics via Graph) | Infinite, perishable, Microsoft-owned. Rebuilding it is a maintenance treadmill that collapses ROI. |
| **OrgPath join** → sequenced migration plan | **Differentiate** | The only proprietary leverage; no Microsoft surface produces the cross-cohort order. |

The three parts compose as a pipeline: `parse → consume → join`. Each stage has
a single, schema-defined output; the next stage consumes only that output, never
the raw inputs of the stage before it. This is what lets the parser run offline,
the consume stage be the only live-tenant dependency, and the join stage be pure
over its two structured inputs.

## Principles

1. **Own the parse.** The GPO-IR is UIAO canon-grade structured data. The parser
   is pure and offline — no tenant, no Graph, no network — so it is the cheapest
   stage to test and the right one to build first.
2. **Consume the crosswalk; never freeze it.** The GPO→MDM mapping is read live
   from Group Policy Analytics at migration time. UIAO stores the *contract*
   with GPA (resource shapes, license gate, beta-surface risk), never a static
   copy of the mapping rows. A frozen crosswalk rots silently; a contract does
   not.
3. **Differentiate on the join.** UIAO's value is the binding of parsed GPO
   scope to OrgPath cohorts and the topological migration order over them — the
   one clause Microsoft does not provide for free.
4. **Unsupported is a first-class outcome.** A setting GPA reports as having no
   MDM equivalent is recorded in the IR and routed to the residual-GPO backlog.
   It is never silently dropped.
5. **The join result is drift-classifiable.** A half-migrated GPO must surface
   as a finding in the canonical five-class taxonomy (ADR-040), not as a blind
   spot.
6. **De-risk the live dependency first.** The only unvalidated dependency is the
   live GPA-through-Graph read; Phase 2 validates it against a real tenant
   before the parser build is hardened (ADR-122 §Decision 7).

## 1. Architecture — the three-stage pipeline

```
 GPO backup XML ┐
 registry.pol   ├─▶ [ Stage 1: Parse ]──▶ GPO-IR ──┐
 SYSVOL scope   ┘     (offline, owned)              │
                                                    ├─▶ [ Stage 3: Join ]──▶ Migration Plan
 Microsoft GPA  ──▶ [ Stage 2: Consume ]──▶ Crosswalk ┘     (OrgPath cohorts,    (sequenced,
 (Graph beta)        (live tenant)          Result          policy targeting,     drift-classified)
                                                            topological order)
```

- **Stage 1 (Parse)** consumes only on-disk GPO artifacts and emits the GPO-IR
  (§2). No tenant, no network. UIAO-owned.
- **Stage 2 (Consume)** submits the GPO to Group Policy Analytics and reads the
  `groupPolicyMigrationReport` back through Microsoft Graph, emitting the
  Crosswalk Result (§3). The only live-tenant stage; the only stage that can
  fail on a Microsoft dependency.
- **Stage 3 (Join)** is pure over (GPO-IR, Crosswalk Result) + the OrgPath
  substrate and emits the Migration Plan (§4). UIAO's differentiator.

## 2. GPO-IR — the parser output (UIAO-owned)

The GPO intermediate representation is the normalized model of *what a GPO sets*
and *whom it scopes to*. It is the SSOT output of Stage 1 and the left input of
Stage 3.

```yaml
gpo_ir_version: "1.0"          # IR schema version (independent of GPA / Graph)
gpo:
  id: "{GPO GUID}"
  display_name: "..."
  enabled: true                 # computer/user enabled flags collapsed per side
  scope:                        # whom this GPO applies to — the join key for Stage 3
    links:                      # OU/site/domain links, in evaluation order
      - target: "OU=Workstations,OU=Corp,DC=example,DC=test"
        enforced: false
        link_order: 1
    security_filtering:         # SDDL-derived principals the GPO applies to
      - sid: "S-1-5-21-..."
        type: "group"           # group | user | computer
    wmi_filter:                 # optional; opaque to the join, surfaced for review
      id: "{WMI filter GUID}"
      query: "SELECT ... FROM Win32_OperatingSystem WHERE ..."
  settings:                     # the policy payload, one entry per resolved setting
    - source: "registry.pol"    # registry.pol | gpo-xml | gpp | security-template
      side: "computer"          # computer | user
      key: "Software\\Policies\\..."
      value_name: "..."
      value_type: "REG_DWORD"
      value: 1
      gpa_setting_ref: null     # populated in Stage 3 from the Crosswalk Result
```

Schema notes:

- `gpo_ir_version` is versioned independently of Microsoft's surfaces so a GPA
  contract change (§3) does not force an IR-schema bump.
- `scope` is the load-bearing field for the join — `links` and
  `security_filtering` are what Stage 3 resolves to OrgPath cohorts.
- `wmi_filter` is captured but treated as **opaque** by the join: it is surfaced
  for human review and recorded on the residual backlog when it cannot be
  expressed as a cohort predicate, never silently honored or dropped.
- The parser emits one IR document per GPO; a `registry.pol` setting and its
  GPO-XML counterpart resolve to a single `settings` entry (last-writer-wins per
  GPO precedence), so the IR is already de-duplicated before the join.

## 3. Crosswalk consumption contract (Microsoft GPA via Graph)

UIAO **consumes** the crosswalk; it does not author one. This section is the
*contract* with Group Policy Analytics — the only thing UIAO stores about the
mapping. The mapping rows themselves are read live and never snapshotted into
canon (ADR-122 §Decision 3).

| Concern | Contract |
|---|---|
| Source resource | `groupPolicyMigrationReport` (per imported GPO) and its `groupPolicySettingMapping` children (per-setting rows). |
| Transport | Microsoft Graph, **beta** endpoint, resolved via `uiao.adapters._graph_clouds.resolve_graph_base()` (never a hardcoded host), `graph_api_version: beta`. |
| Precondition | An active Intune license on the tenant; the Graph permission scope for device-management read. A missing license is a typed precondition failure, not a parser error. |
| Inputs UIAO sends | The `groupPolicyObjectFile` (the parsed GPO, re-serialized to the import format). |
| Output UIAO reads | Per setting: the MDM/CSP equivalent (if any) and a support status. |
| Support status | `supported` \| `unsupported` \| `deprecated` — normalized into the IR. `unsupported` routes the setting to the residual-GPO backlog (§4), a first-class outcome. |
| Persistence | **None.** The Crosswalk Result is an in-flight artifact of a migration run. Canon stores this contract, not its rows. |
| Failure posture | Stage 2 failures (license, scope, beta-contract drift) are isolated to the consume adapter; Stages 1 and 3 are unaffected and a cached prior result can still drive a re-run of the join. |

The Crosswalk Result handed to Stage 3 is the GPO-IR with each `settings` entry's
`gpa_setting_ref` populated (MDM equivalent + support status) — i.e. the consume
stage *annotates* the IR rather than producing a parallel structure.

## 4. OrgPath join — the Migration Plan (UIAO differentiator)

Stage 3 is pure over (annotated GPO-IR, OrgPath substrate). It produces the
Migration Plan: the sequenced, cohort-bound, drift-classified output that is the
part Microsoft does not provide.

```yaml
migration_plan_version: "1.0"
gpo_id: "{GPO GUID}"
cohort_bindings:                 # GPO scope resolved to OrgPath cohorts
  - gpo_scope:
      link: "OU=Workstations,OU=Corp,DC=example,DC=test"
      security_filter_sid: "S-1-5-21-..."
    orgpath_cohort: "uiao://orgpath/.../workstations"   # UIAO_152 dynamic group
    intune_assignment_ref: "..."                         # UIAO_164 policy targeting
    supported_setting_count: 42
    residual_setting_count: 3    # unsupported/deprecated → backlog
sequence:                        # topological order over cohorts
  - wave: 1
    cohort: "uiao://orgpath/.../pilot-ring"
    blocks: ["uiao://orgpath/.../broad-ring"]
    rationale: "inherited settings + overlapping membership resolved first"
residual_backlog:                # settings with no MDM equivalent, never dropped
  - key: "Software\\Policies\\..."
    reason: "gpa:unsupported"
    disposition: "manual-review" # manual-review | retain-on-prem | compensating-control
drift_findings:                  # half-migrated state surfaced, not hidden
  - class: "DRIFT-SEMANTIC"      # per ADR-040 five-class taxonomy
    detail: "GPO setting migrated for cohort A but not overlapping cohort B"
```

The three things that make this UIAO's leverage and not a Microsoft feature:

1. **Cohort binding** — GPO `links` + `security_filtering` resolve to OrgPath
   dynamic-group cohorts (UIAO_152 / ADR-036) and bind to Intune assignments via
   policy targeting (UIAO_164 / ADR-039). Microsoft maps the *setting*; UIAO maps
   the *audience*.
2. **Topological sequencing** — cohorts with overlapping membership and
   inherited settings are ordered into waves so no cohort is migrated before the
   GPOs it depends on. This is the "order" of UIAO_009 §3.3.
3. **Drift classification** — the join result is reconciled against observed
   tenant state and classified into the five-class taxonomy (ADR-040), so a
   partial migration is an observable finding.

## 5. Phase plan

| Phase | Goal | Tenant required? | Exit criterion |
|---|---|---|---|
| **P1 — Parser** | GPO backup XML + `registry.pol` + SYSVOL scope → GPO-IR (§2) | No | Round-trips a real GPO backup to IR; golden-file tests over a fixture corpus pass. |
| **P2 — Consume spike (de-risk first)** | Import one real GPO, read its `groupPolicyMigrationReport` back through Graph | **Yes** | Live read succeeds; supported/unsupported ratio reported. **This is scheduled before P1 is hardened** (ADR-122 §Decision 7) — it validates the only unvalidated dependency. |
| **P3 — Consume adapter** | Productionize Stage 2 against the §3 contract; annotate the IR | Yes | IR annotated with `gpa_setting_ref` for a multi-GPO estate; failure postures (no license, scope, beta drift) handled as typed errors. |
| **P4 — OrgPath join** | Cohort binding + topological sequence + drift findings (§4) | No (pure over IR + substrate) | Migration Plan emitted for an estate with overlapping cohorts; drift findings classify per ADR-040. |
| **P5 — Adapter activation** | Promote the reserved `gpo-modernization` adapter to `active` under its own per-adapter ADR | — | Per-adapter ADR ratified; registry entry flips `reserved → active` (ADR-049 lifecycle). |

Phase ordering note: P2 deliberately precedes a hardened P1. The parser is
offline and low-risk; the live consume path is where reality can contradict the
plan, so it is validated first against a real tenant.

## 6. Module interfaces (forward-looking)

Implementation lands in follow-on PRs (ADR-122 §Decision 6); these are the
intended seams, not committed code:

- `uiao.adapters.gpo.parser` — Stage 1. `parse_gpo(path) -> GpoIr`. Pure,
  offline, no Graph import.
- `uiao.adapters.gpo.crosswalk` — Stage 2. `annotate(gpo_ir, graph_client) ->
  GpoIr`. Resolves the Graph base via `_graph_clouds.resolve_graph_base()`;
  `graph_api_version="beta"`; fails closed on a missing Intune license.
- `uiao.adapters.gpo.join` — Stage 3. `plan(gpo_ir, orgpath) ->
  MigrationPlan`. Pure over the annotated IR and the OrgPath substrate.
- Registry: a reserved `gpo-modernization` entry in
  [`modernization-registry.yaml`](modernization-registry.yaml)
  (`class: modernization`, `mission-class: integration` per UIAO_003), added in
  a follow-on PR, promoted to `active` at P5.

## 7. Open items

| # | Item | Why deferred |
|---|---|---|
| 1 | Group Policy Preferences (GPP) extension coverage in the parser (drive maps, printers, scheduled tasks) | v1.0 GPO-IR targets `registry.pol` + administrative-template + security-template settings; GPP is a v1.1 IR extension. |
| 2 | WMI-filter → cohort-predicate translation | Captured as opaque in v1.0; expressing a WMI filter as an OrgPath predicate is its own design pass. |
| 3 | Behavior if/when Microsoft promotes the GPA resources from Graph beta to v1.0 | The §3 contract pins `beta`; promotion is a tracked `review_trigger` on ADR-122 and a v1.1 contract update. |
| 4 | Non-Intune MDM crosswalk | The "consume Microsoft" decision is Intune-specific; another MDM target would re-open ADR-122 §Decision 3. |

## 8. Cross-references

- Decision record: [ADR-122](adr/adr-122-gpo-modernization-parse-crosswalk-orgpath.md).
- Doctrine: [UIAO_009 §3.3](UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md) (the gap), [UIAO_009 §1](UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md) (the build/consume/structure frame).
- OrgPath substrate: [UIAO_152 Dynamic Group Library](UIAO_152_Dynamic_Group_Library.md) / [ADR-036](adr/adr-036-dynamic-group-provisioning.md) (cohorts); [UIAO_164 (policy targeting)](adr/adr-039-policy-targeting.md) / [ADR-039](adr/adr-039-policy-targeting.md) (Intune assignment binding).
- Drift: [ADR-040](adr/adr-040-drift-engine.md) (five-class taxonomy).
- Transformation context: [UIAO_007 OrgTree Modernization](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md), [ADR-049](adr/adr-049-microsoft-adapter-coverage-expansion.md).
- Microsoft surface (external authority): [Group Policy Analytics (Microsoft Intune)](https://learn.microsoft.com/en-us/intune/intune-service/configuration/group-policy-analytics); [groupPolicyMigrationReport (Microsoft Graph beta)](https://learn.microsoft.com/en-us/graph/api/resources/intune-gpanalyticsservice-grouppolicymigrationreport?view=graph-rest-beta).
