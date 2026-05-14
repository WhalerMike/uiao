---
document_id: UIAO_010
title: "OrgPath in Azure Policy"
version: "0.1"
status: Draft
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-05-14"
updated_at: "2026-05-14"
# foundational-trace: <reserved — populate when Charter Restoration PR-E lands>
---

# OrgPath in Azure Policy

> **Purpose.** This document is the operator-facing narrative that wraps
> the executable canon for OrgPath-driven Azure Policy targeting. It does
> not introduce new mechanism — every binding, schema, and adapter
> behavior is decided in [ADR-039](adr/adr-039-policy-targeting.md) and
> declared in
> [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml).
> This document explains *what an operator does, in what order, and
> what catches them when they get it wrong*.
>
> **Companion document:** [UIAO_011 OrgPath in Intune & Device Governance](UIAO_011_OrgPath_in_Intune_and_Device_Governance.md)
> covers the Intune-side surface of the same ADR. The two transports
> share one decision (ADR-039 §"Decision") but diverge in operator
> workflow, drift surface, and integration touchpoints — hence two
> narrative documents over one combined doc.

## Scope

In scope:

- Azure Policy assignments on Arc-enrolled machines, scoped by the
  `OrgPath` ARM tag.
- The `arc_policy_assignments[]` section of
  `canon/data/orgpath/policy-targets.yaml`.
- Cross-canon integrity rules between policy targeting, the OrgPath
  codebook (UIAO_151), and device-plane writebacks (UIAO_153).

Out of scope:

- Intune device profile and compliance-policy targeting — see
  [UIAO_011 OrgPath in Intune & Device Governance](UIAO_011_OrgPath_in_Intune_and_Device_Governance.md).
- Authoring of Azure Policy *definition bodies*. Definition bodies are
  produced by the Azure Landing Zone authoring workflow and are
  consumed by reference (`policy_definition.match_by: displayName`).
- Entra-joined client targeting. Entra-joined clients are governed
  through Intune profiles (UIAO_011), not Azure Policy.

## Authoritative artifacts

| Role | Artifact |
|---|---|
| Canonical data | [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml) — `arc_policy_assignments[]` |
| JSON Schema | [`schemas/orgpath/policy-targets.schema.json`](../schemas/orgpath/policy-targets.schema.json) |
| Decision record | [ADR-039: OrgTree Policy Targeting — Intune + Azure Policy Dual Transport](adr/adr-039-policy-targeting.md) |
| Loader / cross-canon validator | `src/uiao/modernization/orgtree/policy_targets.py` |
| Reference adapter | `uiao.adapters.entra_policy_targeting.EntraPolicyTargetingAdapter` |
| OrgPath codebook (selector vocabulary) | [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md) |
| Device-plane OrgPath writes (Arc tag origin) | [UIAO_153_Attribute_Mapping_Table](UIAO_153_Attribute_Mapping_Table.md) + [ADR-038](adr/adr-038-device-plane-orgpath.md) |
| Substrate handoff | [UIAO_164_Execution_Substrate_Integration_Layer](UIAO_164_Execution_Substrate_Integration_Layer.md) |

If any pair in the table above goes out of sync (data references a
codebook prefix that no longer exists, schema rejects an assignment the
data declares, ADR contradicts the loader), that is a `DRIFT-PROVENANCE`
finding by definition (see UIAO-SSOT §"Drift baseline").

## The targeting model

OrgPath governs Azure Policy on Arc by **tag selector**, not by group
membership:

```
+----------------------------+     +----------------------------+
| canon/data/orgpath/        |     | canon/data/orgpath/        |
| codebook.yaml              |     | policy-targets.yaml        |
| (UIAO_151 / ADR-035)       |     | (this document)            |
| ORG, ORG-IT, ORG-IT-INF... |     | arc_policy_assignments[]   |
+--------------+-------------+     +--------------+-------------+
               | active prefix                    | references prefix
               v                                  v
        +---------------------------------------------+
        | EntraPolicyTargetingAdapter (loader)        |
        |  - validates every prefix is in codebook    |
        |  - validates assignment_name uniqueness     |
        |  - emits 4-op Arc plan                      |
        +-----------------------+---------------------+
                                |
                                v
        +---------------------------------------------+
        | Azure Resource Manager                      |
        |  - reads OrgPath= tag on Arc machine        |
        |    (written by UIAO_153 / ADR-038)          |
        |  - applies policy where tag matches         |
        |    orgpath_selector (startsWith | equals)   |
        +---------------------------------------------+
```

Two consequences flow from this:

1. **The Arc machine must already carry an `OrgPath` tag** before any
   policy assignment authored here can take effect on it. That tag is
   written by the device-plane work (UIAO_153 / ADR-038), not by this
   document. A policy assignment that targets `prefix: ORG-IT-INF` on a
   machine whose tag is `ORG-FIN-AP` simply does not match — there is
   no error condition; the policy is silently inapplicable. Operators
   must verify Arc-tag coverage before relying on a policy binding.
2. **Azure Policy definitions targeted via OrgPath MUST accept two
   parameters.** Per ADR-039 §6, every Arc-targeted policy definition
   accepts `orgPathPrefix: string` and `matchMode: enum[startsWith,
   equals]`. The adapter drift-checks the assigned parameter values
   against the canonical `orgpath_selector`. Policy definitions that
   omit these parameters will surface as `arc-policy-phantom` even if
   their assignment names match — the parameter shape is itself part
   of the governance invariant.

## Selector grammar

Each entry in `arc_policy_assignments[]` carries an `orgpath_selector`
with two fields:

| Field | Type | Constraint |
|---|---|---|
| `prefix` | string | Either the literal root `ORG`, or an active codebook entry from UIAO_151. Deprecated codes are rejected at PR CI by the loader. |
| `match_mode` | enum | `startsWith` (subtree) or `equals` (single node). |

`startsWith` is the default and the right choice for almost every
policy. Use `equals` only when the policy must scope to one OrgPath
node and not its descendants — which is rare; if you find yourself
reaching for `equals` repeatedly, reconsider whether your subtree
shape is what you want.

Subtree examples:

- `prefix: ORG`, `match_mode: startsWith` — every governed Arc
  machine. Used for tenant-wide assertions (e.g.,
  `Azure-Arc-Defender-Enrollment`).
- `prefix: ORG-IT-INF`, `match_mode: startsWith` — IT Infrastructure
  subtree, including any future child segments.
- `prefix: ORG-IT-SEC-SOC`, `match_mode: startsWith` — only SOC-owned
  Arc machines.

Whenever you add a new prefix, the binding ADR (ADR-035) for the
codebook must already include that prefix as an active entry, or the
loader will fail PR CI.

## Operator workflows

### Add a new Arc policy binding

1. **Confirm the policy definition exists** in the tenant. The
   `policy_definition.value` field resolves by `displayName`. If the
   tenant does not yet hold a definition with that name, the next
   `plan` produces an `arc-policy-definition-missing` op — not an
   error, but a governance-review op that will not auto-apply.
2. **Confirm the policy definition accepts `orgPathPrefix` and
   `matchMode` parameters.** A definition that lacks these will
   surface as `arc-policy-phantom` after assignment because its
   parameter shape diverges from canonical.
3. **Pick a selector.** Default to `match_mode: startsWith`. Use the
   tightest active codebook prefix that still covers every machine you
   intend to govern; do not target with a wider prefix and rely on
   exclusions (Arc selectors do not support exclusions in Phase 5 —
   ADR-039 §"Negative / deferred").
4. **Pick a unique `assignment_name`.** **Required format
   (review-enforced):** `OrgTree-<scope>-<purpose>` (e.g.,
   `OrgTree-IT-Infra-Baseline`, `OrgTree-FIN-Data-Residency`). The
   loader rejects duplicate names today; a regex check on the format
   itself is a follow-up. Until then, this format is enforced at PR
   review.
5. **PR the change.** The loader runs in CI. Cross-canon integrity
   surfaces immediately:
   - prefix not in active codebook → loader error
   - duplicate `assignment_name` → loader error
   - duplicate `(profile_ref, target_group, intent)` tuple — for the
     paired Intune side — → loader error
6. **After merge, the adapter `plan` against the tenant** will emit
   one of:
   - `arc-policy-create` — tenant has no assignment by this name; will
     auto-apply on the next reconcile cycle.
   - `arc-policy-update` — tenant has an assignment by this name but
     parameters or scope differ; will auto-apply.
   - `arc-policy-definition-missing` — tenant lacks the definition;
     governance review.
   - `arc-policy-phantom` — tenant has an OrgTree-named assignment
     this canon does not declare; governance review.

### Change the scope of an existing binding

Edit `orgpath_selector.prefix` or `match_mode` in place, PR the change,
let the loader validate. The next reconcile will produce
`arc-policy-update`. Do not rename the `assignment_name` in the same
PR — a rename produces a `create` + `phantom` pair, which doubles the
governance-review surface for a single operator intent.

### Retire a binding

Delete the entry. The next reconcile will produce
`arc-policy-phantom` against the assignment that still exists in the
tenant. Phantom ops never auto-apply — an operator must decide whether
the tenant assignment should be torn down or whether canon should
re-adopt it. This is intentional: deletion of a policy binding has the
broadest blast radius in the OrgTree stack.

## Canonical operation vocabulary (Arc subset)

ADR-039 §5 defines four Arc ops. Restated here for convenience:

| Op | Auto-applies | Meaning |
|---|---|---|
| `arc-policy-create` | yes | Canon declares an assignment the tenant lacks. |
| `arc-policy-update` | yes | Canon and tenant diverge on definition reference, scope, or parameters. |
| `arc-policy-definition-missing` | **no** — governance review | The referenced policy definition does not exist in the tenant yet. |
| `arc-policy-phantom` | **no** — governance review | Tenant has an OrgTree-named assignment canon does not declare; possible unauthorized policy-consumer drift. |

Auto-apply versus governance-review is not a CLI flag. It is a property
of the op itself, enforced by the adapter. An operator cannot mark a
phantom op auto-apply; the only ways out are: (a) declare it in canon
(re-adoption), or (b) tear it down out-of-band and let the next
reconcile clear the finding.

## Boundary rules

- Every Arc machine the adapter touches MUST be in the GCC-Moderate
  boundary. The loader's per-entry `gcc-boundary: gcc-moderate`
  invariant matches the boundary metadata of every adapter (see
  [adapter-registry.yaml](adapter-registry.yaml)).
- Arc machines outside the boundary are not visible to this adapter.
  Cross-boundary policy targeting is out of scope until the boundary
  enum is extended (Charter Restoration Plan PR-C).
- The instruction set the adapter dispatches to the execution substrate
  carries `boundary:m365-gcc-moderate` in its `constraints` array, per
  UIAO_164 §"Boundary Rules".

## Drift considerations

Three drift classes apply directly:

| Class | Trigger |
|---|---|
| `DRIFT-PROVENANCE` | An entry references a codebook prefix that no longer exists in `canon/data/orgpath/codebook.yaml`. Loader catches at PR CI. |
| `DRIFT-AUTHZ` | An `arc-policy-phantom` op surfaces an OrgTree-named assignment in the tenant the canon does not declare — possible unauthorized policy authoring. |
| `DRIFT-SEMANTIC` | A canonical assignment's parameters diverge from `orgpath_selector` after tenant-side edit (e.g., a portal user widened the prefix). Surfaces as `arc-policy-update` until canon reabsorbs or the tenant edit is reverted. |

`DRIFT-IDENTITY` does not apply directly — Arc machines are device
identities, but the device-plane writeback that originally stamped the
`OrgPath` tag (UIAO_153) carries that drift class.

## Forcing-function rationale

OrgPath-driven Azure Policy targeting exists because:

1. **Microsoft is forcing federal agencies onto Azure Arc** for
   off-Azure server governance. Arc is the only first-party transport
   that lets one policy plane (Azure Policy) reach Linux/Windows
   servers regardless of where they run.
2. **NIST 800-53 Rev 5 CM-2, CM-6, and CM-7** require a single
   authoritative control plane for configuration baselines across the
   accreditation boundary. Per-machine GPO or per-fleet ad-hoc tooling
   does not satisfy this.
3. **The OrgPath tag, populated deterministically from HR data via
   ADR-038**, is the only attribute on an Arc machine that survives
   tenant moves, OS reinstalls, and rejoin events. Targeting on
   anything else (resource group, subscription, computer name) drifts.

This rationale will be canonized as **ADR-MS (Microsoft-Forced
Transition Rationale)** per Charter Restoration Plan PR-A through
PR-D. Until ADR-MS lands, this section is the authoritative statement
of *why* this binding plane exists.

## Governance alignment

This document implements the substrate's commitment to PR-reviewable,
canon-first policy governance. Three invariants are visible from here:

1. **No portal-authored OrgTree-named policy assignment is invisible
   to canon.** Phantom ops surface them all.
2. **No canon binding is silently inapplicable.** Definition-missing
   ops surface every binding the tenant cannot fulfill.
3. **No assignment widens scope without a PR.** The reconcile surfaces
   any divergence between canonical `orgpath_selector` and tenant-side
   parameter values as `arc-policy-update`, blocking apply until canon
   reabsorbs.

## Related canon

- [UIAO_011 OrgPath in Intune & Device Governance](UIAO_011_OrgPath_in_Intune_and_Device_Governance.md) — Intune-side companion (same ADR, different transport).
- [UIAO_007_OrgTree_Modernization_AD_to_EntraID](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) — programmatic context for the OrgTree work.
- [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md) — selector vocabulary.
- [UIAO_152_Dynamic_Group_Library](UIAO_152_Dynamic_Group_Library.md) — Intune-side targeting (paired surface, see UIAO_011).
- [UIAO_153_Attribute_Mapping_Table](UIAO_153_Attribute_Mapping_Table.md) — Arc tag origin.
- [UIAO_163_Drift_Detection_Engine_Specification](UIAO_163_Drift_Detection_Engine_Specification.md) — generic drift engine; this document's ops feed the policy-consumer plane.
- [UIAO_164_Execution_Substrate_Integration_Layer](UIAO_164_Execution_Substrate_Integration_Layer.md) — substrate handoff contract.
- [ADR-035](adr/adr-035-orgpath-codebook-binding.md), [ADR-036](adr/adr-036-dynamic-group-provisioning.md), [ADR-038](adr/adr-038-device-plane-orgpath.md), [ADR-039](adr/adr-039-policy-targeting.md) — the OrgTree decision chain.
