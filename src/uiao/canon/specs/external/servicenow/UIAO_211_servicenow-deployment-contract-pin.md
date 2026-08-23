---
document_id: UIAO_211
title: "ServiceNow Deployment Contract — Schema Pin"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-08-20"
updated_at: "2026-08-20"
---

# ServiceNow Deployment Contract — Schema Pin

> **Purpose:** Pin the **deployment half** of UIAO's ServiceNow contract — the
> tables and custom columns the adapters actually depend on — and give it a
> gate. Applies to ServiceNow the two-part pin doctrine ADR-136 §Decision 5
> established for SailPoint IdentityIQ, and which ADR-136 explicitly named
> ServiceNow as the other live case.

## 1. Why this pin exists

ServiceNow is the one active adapter in UIAO with a live write path, and its
contract was never written down anywhere a gate could read.

The consequence was not theoretical. The adapters compiled their hostname in
and named the commercial cloud rather than the agency's GCC instance, in three
different spellings across seven call sites, with recorded test fixtures that
asserted the mistake — so the suite agreed with the bug and stayed green
(fixed in PR #1436). The defect class was not a typo. It was that **no
artifact existed for any gate to compare the code against.**

That fix addressed the host. This pin addresses the schema, which is the
larger surface and the one where a vendor specification cannot help at all.

## 2. Why the vendor spec is not enough

ServiceNow has supported OpenAPI export since the Tokyo release, and pinning an
instance OAS export is worth doing. It is also insufficient on its own, because
almost everything UIAO depends on is deployment-defined rather than shipped:

- Custom columns on out-of-box tables (`u_uiao_orgpath`, `u_uiao_routing_key`,
  and nine more) exist only because someone created them on this instance.
- Scoped applications rename the mandatory column prefix from `u_` to
  `x_<scope>_` and change cross-scope access rules.
- Custom tables (`cmdb_ci_privileged_id`) exist in no vendor catalogue.
- Business rules, ACLs, and Flow Designer flows can alter what a write does
  after the API accepts it.

The authority for all of that is `sys_dictionary` and `sys_db_object` on the
instance itself. **The instance is the specification.** A vendor doc page is,
at best, a description of the parts nobody customised.

This is the same shape as UIAO_210 §4 for SailPoint IdentityIQ, where custom
Capabilities and SPRights — the `IDM.SailPointSecurity` class of object — sit
outside any vendor spec. Two vendors, one structural problem.

## 3. The two sides

| Side | Artifact | Status |
|---|---|---|
| **Assertion** — what the code requires | [`canon/data/servicenow/expected-schema.yaml`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/data/servicenow/expected-schema.yaml) | **Present.** 6 tables, 12 custom columns, each with the call site that proves the dependency |
| **Evidence** — what the instance has | `canon/data/servicenow/deployment/sys-dictionary.<env>.json` | **Absent.** Requires instance read access |

`scripts/check_servicenow_schema_pin.py` enforces three things:

1. **Structure** — the assertion file is internally coherent: required keys,
   no duplicate columns, every `conflict:` id resolving to an `unresolved:`
   entry.
2. **Code agreement** — every column the assertion file names actually appears
   in the source file its `code-ref` cites. This runs today, with no instance
   access, and it is what stops the assertion side quietly drifting away from
   the code it claims to describe.
3. **Instance agreement** — when an export exists, every asserted column is
   present on the instance, **and** every UIAO-looking column on the instance
   is claimed by some code path. An orphaned `u_uiao_*` column nobody reads is
   as much a finding as a missing one.

With no export the third check reports *pending* and the gate passes. That is
deliberate: the pin should land and start holding the line on what it can
verify, rather than waiting on an artifact only an operator can produce.
`--strict` flips it to a failure once the export is in.

## 4. What the export must contain

Per [`deployment/README.md`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/data/servicenow/deployment/README.md), which carries the exact Table API queries:

| File | Source | Purpose |
|---|---|---|
| `sys-dictionary.<env>.json` | `sys_dictionary` | Column-level truth: existence, type, owning scope |
| `sys-db-object.<env>.json` | `sys_db_object` | Table-level truth: existence, label, parent, owning scope |
| `oas.<env>.json` *(optional)* | Instance OpenAPI export | The vendor half, instance-flavoured |

**Configuration inventory only.** Table names, column names, types, labels,
scopes. Never record data — no incidents, no catalog requests, no user
references, no business-record `sys_id` values. The documented `sysparm_fields`
make that structural rather than a matter of operator discipline.

## 5. What the pin already found

Writing the assertion side surfaced three discrepancies that were invisible
while the contract lived only in code. All three are recorded under
`unresolved:` in the assertion file, and all three block promoting the gate to
`--strict`.

### 5.1 `control-id-prefix` (high)

The control-id column is spelled two ways. The **write** path stamps
`u_uiao_control_id` on incidents, change requests, and problems. The **read**
path requests and normalizes `uiao_control_id`.

Whichever spelling is real on the instance, **the read path cannot see what the
write path writes.** Normalization falls back to a hard-coded default — `AC-2`
in the adapter, `IR-4` in the OSCAL emitter — so control attribution on
collected evidence is silently wrong rather than visibly absent. Wrong is worse
than absent: absent shows up as a gap, wrong shows up as a claim.

This pin does **not** resolve it, and that is a deliberate limit. On a stock
instance a custom column on an out-of-box table takes `u_`, and a scoped
application takes `x_<scope>_`, so a bare `uiao_control_id` should not exist —
but it can, if the column arrived by import or the table belongs to a scoped
app. Only `sys_dictionary` settles it. Choosing a spelling from the repository
would be a guess wearing the costume of a decision.

### 5.2 `fixtures-assert-unprefixed` (medium)

Every recorded tier-2 fixture returns `uiao_control_id` unprefixed, and
`tests/conformance/test_servicenow_conformance.py:108` reads that spelling out
of the request body it just built. The suite therefore agrees with itself and
**cannot detect 5.1**. The fixtures are a recording of what the code does, not
evidence of what the instance returns — the same failure mode as the hostname
fixtures in PR #1436.

### 5.3 `scoped-app-unknown` (medium)

Whether UIAO's columns live in the global scope or inside a scoped application
is unknown; no `sys_scope` reference exists anywhere in the repo. It determines
the mandatory prefix, the cross-scope access rules, and whether the columns are
portable between instances.

### 5.4 A registry finding, recorded not fixed

The `service-now` entry in `modernization-registry.yaml` declares
`scope: incident-tickets, change-requests, problem-records`. The identity JML
write path posts to **`sc_request`** — Service Catalog. The declared scope does
not cover what the code does, and the entry's controls (IR-4/5/6, CM-3) are
incident and change controls rather than the AC-2 family the JML path implies.

That is a registry decision, not a schema one, so this pin flags it
(`registry-gap: true` on the `sc_request` entry) and leaves it.

## 6. Relationship to other pins

- **ADR-136 §Decision 5** — establishes the two-part doctrine and names
  ServiceNow as the other live case. This document is that case. Ratified
  2026-08-22, so the citation is an authority rather than a cross-reference.
- **UIAO_210** — the SailPoint IdentityIQ pin, whose §4 states the same
  requirement for IIQ's deployment half.
- **UIAO_143** — the RFC 7643 substrate pin, and the shape all of these follow:
  verbatim artifact, hash anchor, supersession rather than in-place edit.

## 7. Provenance and drift

- **Source of truth for the assertion side** — the code. When adapter or
  collector code starts touching a new table or column, it is added to
  `expected-schema.yaml` in the same commit. Check 2 makes the reverse
  direction enforceable; the forward direction is a review responsibility.
- **Source of truth for the evidence side** — the instance. Re-export whenever
  the deployment changes shape: a column added, a scoped app installed, a
  custom table created. A stale export is the same class of defect as a stale
  vendor spec.
- **Hash anchoring** — each committed export records its SHA-256 in the
  deployment README's export log, matching UIAO_210 §2.
- **Promotion** — once the export lands and §5.1–5.3 are resolved, the
  pre-commit hook moves to `--strict` and a missing or divergent export becomes
  a failure.

## 8. References

- [`expected-schema.yaml`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/data/servicenow/expected-schema.yaml) — the assertion side
- [`deployment/README.md`](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/data/servicenow/deployment/README.md) — export procedure and log
- [`scripts/check_servicenow_schema_pin.py`](https://github.com/WhalerMike/uiao/blob/main/scripts/check_servicenow_schema_pin.py) — the gate
- ADR-136 — SailPoint IdentityIQ Option-C slot allocation and vendor contract pin (two-part doctrine)
- UIAO_210 — SailPoint IdentityIQ REST API vendor contract pin
- UIAO_143 — SCIM Core Schema (RFC 7643) substrate pin
- UIAO_003 — Adapter Segmentation Overview
