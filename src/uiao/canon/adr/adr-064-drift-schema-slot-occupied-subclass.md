---
id: ADR-064
title: "DRIFT-SCHEMA::slot-occupied — Sub-class for Pre-existing Non-OrgPath Values"
status: accepted
date: 2026-05-11
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-012
  - ADR-035
  - ADR-063
canon_refs:
  - UIAO_151_OrgPath_Codebook
  - UIAO_163_Drift_Detection_Engine_Specification
  - UIAO_167_SLA_Escalation_Playbooks
  - UIAO_173_Canonical_Error_Taxonomy
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-064-drift-schema-slot-occupied-subclass.html
---

# ADR-064: DRIFT-SCHEMA::slot-occupied — Sub-class for Pre-existing Non-OrgPath Values

## Status

Accepted

## Context

[ADR-063](adr-063-orgpath-storage-slot-binding.md) ratified
`extensionAttribute1` as the canonical OrgPath storage slot for users,
devices, and service principals. It also explicitly deferred a
follow-up:

> "5. **New drift sub-class (deferred).** A future ADR will introduce
>    `DRIFT-SCHEMA::slot-occupied` distinguishing 'the value at
>    `extensionAttribute1` is a well-formed but non-OrgPath string'
>    from generic Schema Drift (regex fail)."

In production today, three distinguishable conditions all land in the
same drift bucket:

| Condition | Today's classification | Operator-correct response |
|-----------|-----------------------|---------------------------|
| `extensionAttribute1 = "ORG-FIN-AP-east"` (lowercase) | `DRIFT-SCHEMA`, P1 | Fix the upstream caller that wrote it |
| `extensionAttribute1 = "ORG-FIN-MISSING"` (codebook miss) | `DRIFT-VALUE`, P2 | Reconcile with HR; add code or correct the value |
| `extensionAttribute1 = "CC-5847"` (legacy cost-center value) | `DRIFT-SCHEMA`, P1 | **Do NOT overwrite** — run the rebind procedure from ADR-063 §3 |

The third row is operationally distinct from the first but currently
indistinguishable to automation. An operator triaging a `DRIFT-SCHEMA`
queue cannot tell whether the malformed value is an upstream-script
bug to patch or a pre-existing tenant investment that must be
preserved through the rebind procedure. The remediation playbook
(UIAO_167) routes both the same way, which is wrong: malformed
upstream writes need a code fix; legacy values need a tenant cutover.

[ADR-012](adr-012-canonical-drift-taxonomy.md) is explicit that the
drift-class taxonomy can only be extended via Governance-Plane-
approved ADRs, and existing types cannot be modified. This ADR
therefore *does not* add a new top-level `drift_class`; it introduces
a *sub-qualifier* within `DRIFT-SCHEMA` that operators and
playbook-routing logic can use without breaking existing consumers of
the six canonical drift classes.

## Decision

1. **Sub-class introduction.** Add the qualifier `slot-occupied` to
   `DRIFT-SCHEMA`. Findings emitted with this qualifier are
   structurally identical to ordinary `DRIFT-SCHEMA` findings — the
   `drift_class` field remains the string `"DRIFT-SCHEMA"`, preserving
   compatibility with every existing consumer. The sub-qualifier
   appears in one or both of:

   - The `reason` field, with the canonical prefix
     `"[slot-occupied]"` followed by the operator-readable diagnosis.
   - A new optional `sub_class` field on `DriftFinding`, of type
     `Optional[str]`. When present, value is `"slot-occupied"`.

   Existing consumers that read only `drift_class` continue to
   function. Consumers that route on sub-class read either the
   `reason` prefix or the new `sub_class` field.

2. **Detection signal.** The drift engine classifies a finding as
   `DRIFT-SCHEMA::slot-occupied` when *all* of the following hold for
   a non-empty `extensionAttribute1` value `v`:

   1. `v` does not match the OrgPath regex
      `^ORG(-[A-Z0-9]{2,6}){0,8}$`.
   2. `v` does not begin with the literal `ORG` (case-insensitive) —
      a malformed OrgPath that *does* begin with `ORG` is a regular
      `DRIFT-SCHEMA` (upstream-write bug, the operator should fix the
      caller).
   3. The tenant configuration declares `legacy_ext1_use: true` in
      its onboarding manifest, OR the assessment phase recorded a
      population-threshold breach (≥1% of in-scope users carrying
      non-OrgPath values per ADR-063 §3).

   Conditions 1+2 alone classify as plain `DRIFT-SCHEMA`. The
   `legacy_ext1_use` flag (condition 3) is what distinguishes
   "legitimate prior tenant use, follow the rebind procedure" from
   "rogue value, investigate the upstream caller." This separation
   is intentional: only tenants that have *explicitly declared* a
   prior use of `extensionAttribute1` get the protective routing.
   Unflagged tenants surface the same data as plain `DRIFT-SCHEMA`,
   which is the safer default.

3. **Severity and auto-fix.** `DRIFT-SCHEMA::slot-occupied` retains
   `DRIFT-SCHEMA`'s severity floor (P1 Critical) and `auto_remediate`
   semantics:

   - `severity = "P1"`
   - `auto_remediate = false` (never)
   - `halt_on_critical = true` (a P1 finding still halts the scan's
     remediation pass)

   The rationale for keeping P1: legacy values represent a real prior
   investment whose loss has audit consequences. They are not low-
   priority warnings. The difference is in *which playbook fires*,
   not in how urgent the finding is.

4. **Playbook routing.** [UIAO_167](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/UIAO_167_SLA_Escalation_Playbooks.md)
   gains a routing rule keyed off the sub-qualifier:

   - `DRIFT-SCHEMA` (no sub-qualifier) → existing playbook:
     "investigate upstream caller; fix the writer; re-scan."
   - `DRIFT-SCHEMA::slot-occupied` → new playbook:
     "execute ADR-063 §3 rebind procedure; do not overwrite; snapshot
     to Evidence Fabric; coordinate upstream relocation; only then
     enable OrgPath writes."

   The new playbook is authored as a small companion document under
   `src/uiao/canon/playbooks/` (or wherever UIAO_167 declares its
   sub-files); this ADR mandates its existence and routing wire-up,
   not its exact prose.

5. **Error taxonomy entry.** [UIAO_173](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/UIAO_173_Canonical_Error_Taxonomy.md)
   gains an entry for the sub-qualifier so dashboards and exports can
   filter and report on it independently of plain Schema Drift. The
   entry inherits severity and auto-fix policy from `DRIFT-SCHEMA`
   and adds the routing pointer to the new playbook.

6. **Implementation surface.** The classifier change lands in
   `src/uiao/governance/drift_engine.py` as a small extension to the
   `DRIFT-SCHEMA` classification branch. The tenant flag
   `legacy_ext1_use` is read from the onboarding manifest, with
   default `false` (safe — unflagged tenants get plain
   `DRIFT-SCHEMA`, no behavior change). Tests under
   `tests/test_drift_engine.py` cover the three rows of the
   classification table above.

## Consequences

**Positive**

- Operators can route legitimate legacy values away from the
  "fix-the-upstream-caller" playbook into the rebind procedure
  without per-finding human triage.
- Audit dashboards can report on slot-occupied findings as a
  distinct cohort, surfacing how many tenants are mid-rebind vs.
  how many have rogue values from broken upstream writers.
- ADR-012's taxonomy invariant is preserved — the six top-level
  drift classes are unchanged.
- Default-false tenant flag means existing tenants get *no* behavior
  change until they opt in by recording `legacy_ext1_use: true` in
  their onboarding manifest.

**Negative / deferred**

- The classifier now has a tenant-flag dependency, which means a
  misconfigured onboarding manifest (forgetting to set
  `legacy_ext1_use: true` when it applies) silently routes findings
  to the wrong playbook. The mitigation is the assessment-phase
  population-threshold check in ADR-063 §3, which forces the flag
  during onboarding when the threshold trips.
- Consumers reading `drift_class` alone cannot distinguish the sub-
  qualifier without parsing `reason` or reading the new optional
  `sub_class` field. This is the price of preserving ADR-012's
  taxonomy contract; the alternative (a new top-level class) would
  break every existing dashboard and rule.
- A future tenant rebind that's *complete* still leaves the
  `legacy_ext1_use` flag set unless an operator clears it. The
  cleanup procedure for the flag itself is a small follow-up and is
  deferred to a separate ADR.

## Related work

- ADR-012 established the canonical drift taxonomy and the rule that
  it can only be extended. This ADR honors that constraint by
  introducing a sub-qualifier rather than a new top-level class.
- ADR-035 bound the codebook to executable canon. The slot-occupied
  case is detected against the same codebook regex defined there.
- ADR-063 ratified the storage slot binding and committed to this
  ADR as a deferred follow-up. ADR-064 closes that commitment.
- UIAO_167's new sub-playbook for `slot-occupied` routing is the
  implementation artifact this ADR mandates; its prose lives outside
  this ADR.
- UIAO_173's new error-taxonomy entry is the discoverability artifact
  that lets reporting tools filter on the sub-qualifier.
