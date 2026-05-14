---
document_id: UIAO_011
title: "OrgPath in Intune & Device Governance"
version: "0.1"
status: Draft
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-05-14"
updated_at: "2026-05-14"
# foundational-trace: <reserved — populate when Charter Restoration PR-E lands>
---

# OrgPath in Intune & Device Governance

> **Purpose.** This document is the operator-facing narrative that wraps
> the executable canon for OrgPath-driven Intune device targeting. It
> does not introduce new mechanism — every binding, schema, and adapter
> behavior is decided in [ADR-036](adr/adr-036-dynamic-group-provisioning.md)
> and [ADR-039](adr/adr-039-policy-targeting.md), and declared in
> [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml)
> alongside [`canon/data/orgpath/dynamic-groups.yaml`](data/orgpath/dynamic-groups.yaml).
> This document explains *what an operator does, in what order, and
> what catches them when they get it wrong*.
>
> **Companion document:** [UIAO_010 OrgPath in Azure Policy](UIAO_010_OrgPath_in_Azure_Policy.md)
> covers the Arc-side surface of the same ADR. The two transports
> share one decision (ADR-039 §"Decision") but diverge in operator
> workflow, drift surface, and integration touchpoints — hence two
> narrative documents over one combined doc.

## Scope

In scope:

- Intune **configuration profiles** and **device compliance policies**
  assigned to OrgTree-* dynamic groups for **Entra-joined clients**.
- The `intune_assignments[]` section of
  `canon/data/orgpath/policy-targets.yaml`.
- The dynamic-group → OrgPath binding contract that makes Intune
  targeting deterministic ([UIAO_152](UIAO_152_Dynamic_Group_Library.md)
  / [ADR-036](adr/adr-036-dynamic-group-provisioning.md)).
- Three-plane device model interactions ([ADR-034](adr/adr-034-three-plane-device-model.md))
  that determine which devices are reachable from this targeting
  surface in the first place.

Out of scope:

- Azure Policy targeting on Arc-enrolled servers — see **UIAO_010**.
- Authoring of Intune profile *bodies*. Profile bodies are produced by
  the GPO-to-Intune migration workflow and consumed by reference
  (`profile_ref.match_by: displayName`).
- Administrative Unit scoping ([UIAO_154](UIAO_154_Delegation_Matrix_AUs_Roles.md)
  / [ADR-037](adr/adr-037-admin-unit-provisioning.md)) — AUs scope
  *delegation*, not policy targeting; they appear in this document
  only where they bound an operator's reachable assignment surface.
- Hybrid-Azure-AD-joined (HAADJ) clients. HAADJ is deprecated per
  [ADR-001](adr/adr-001-haadj-deprecated-entra-join-only.md);
  Entra-join is the only governed client posture.

## Authoritative artifacts

| Role | Artifact |
|---|---|
| Canonical data | [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml) — `intune_assignments[]` |
| Dynamic-group canon (target groups) | [`canon/data/orgpath/dynamic-groups.yaml`](data/orgpath/dynamic-groups.yaml) — `OrgTree-*` library |
| JSON Schema | [`schemas/orgpath/policy-targets.schema.json`](../schemas/orgpath/policy-targets.schema.json) |
| Decision records | [ADR-036: Dynamic Group Provisioning](adr/adr-036-dynamic-group-provisioning.md) (group binding) + [ADR-039: OrgTree Policy Targeting — Intune + Azure Policy Dual Transport](adr/adr-039-policy-targeting.md) (assignment binding) |
| Loader / cross-canon validator | `src/uiao/modernization/orgtree/policy_targets.py` |
| Reference adapter | `uiao.adapters.entra_policy_targeting.EntraPolicyTargetingAdapter` |
| OrgPath codebook (rule vocabulary) | [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md) |
| Three-plane device model (reachability) | [UIAO_007](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) + [ADR-034](adr/adr-034-three-plane-device-model.md) |
| HAADJ deprecation context | [ADR-001](adr/adr-001-haadj-deprecated-entra-join-only.md) |
| Substrate handoff | [UIAO_164_Execution_Substrate_Integration_Layer](UIAO_164_Execution_Substrate_Integration_Layer.md) |

If any pair in the table above goes out of sync (an Intune assignment
references a group UIAO_152 no longer declares, schema rejects an
assignment the data declares, ADR contradicts the loader), that is a
`DRIFT-PROVENANCE` finding by definition (see UIAO-SSOT §"Drift
baseline").

## The targeting model

OrgPath governs Intune by **dynamic group membership**, not by tag
selector:

```
+----------------------------+     +----------------------------+
| canon/data/orgpath/        |     | canon/data/orgpath/        |
| dynamic-groups.yaml        |     | policy-targets.yaml        |
| (UIAO_152 / ADR-036)       |     | (this document)            |
| OrgTree-IT-Users,          |     | intune_assignments[]       |
| OrgTree-FIN-Users, ...     |     |                            |
+--------------+-------------+     +--------------+-------------+
               | named group                      | references group
               v                                  v
        +---------------------------------------------+
        | EntraPolicyTargetingAdapter (loader)        |
        |  - validates every target_group is in       |
        |    UIAO_152 dynamic-groups.yaml             |
        |  - validates (profile_ref, target_group,    |
        |    intent) tuple uniqueness                 |
        |  - emits 4-op Intune plan                   |
        +-----------------------+---------------------+
                                |
                                v
        +---------------------------------------------+
        | Microsoft Graph                             |
        |  - resolves profile_ref by displayName | id |
        |  - POST /deviceManagement/{kind}s/{id}/     |
        |    assignments                              |
        |  - applies profile to dynamic-group         |
        |    members per intent (include | exclude)   |
        +---------------------------------------------+
```

Three consequences flow from this:

1. **The dynamic group must already exist in canon** before any Intune
   assignment authored here can target it. A declared assignment whose
   `target_group` is not in `dynamic-groups.yaml` fails the loader at
   PR CI — there is no apply path that creates a group on demand. Group
   creation is its own ADR-036 governance event.
2. **Group membership is attribute-driven, not click-driven.** Every
   `OrgTree-*` group's membership rule keys off the OrgPath
   extension attribute on user objects (per UIAO_152 / ADR-036). Adding
   a user to an OrgTree-* group is *not a manual operation* — change
   the user's OrgPath, the group membership recomputes. This is the
   property that makes Intune targeting deterministic, but it is also
   the one operators most often misunderstand on first contact.
3. **Profile authoring and profile assignment are separate
   workflows.** This document governs assignment only. Profile bodies
   are authored by the GPO-to-Intune migration or directly in the
   portal/IaC, named per the canonical convention, and then bound by
   `displayName` in this canon. A profile that exists in canon by name
   but not in the tenant surfaces as `intune-profile-missing`.

## Profile reference grammar

Each entry in `intune_assignments[]` carries a `profile_ref`:

| Field | Type | Constraint |
|---|---|---|
| `kind` | enum | `configurationPolicy` (Endpoint Manager configuration profile) or `deviceCompliancePolicy` (device compliance policy). The two kinds map to different Graph endpoints; the adapter dispatches accordingly. |
| `match_by` | enum | `displayName` (recommended — stable, IaC-friendly) or `id` (fixed GUID, tenant-specific, brittle to redeploys). |
| `value` | string | The display name or GUID. **Required format (review-enforced)** for `displayName`: `Intune-<scope>-<purpose>` (e.g., `Intune-Baseline-Endpoint-Security`, `Intune-FIN-Data-Handling`). Loader does not regex-check the format today; convention is enforced at PR review until paired with a regex check. |

Default to `match_by: displayName`. Reach for `id` only when two
profiles share a display name in the tenant and you must
disambiguate — which itself is a governance smell worth fixing
upstream rather than working around here.

## Intent grammar

Each entry carries an `intent`:

| Intent | Effect | Use when |
|---|---|---|
| `include` | Adds the dynamic group as an inclusion target on the profile's `assignments[]`. Members get the profile. | Default for any positive policy assertion. |
| `exclude` | Adds the dynamic group as an exclusion target on the profile's `assignments[]`. Members are exempted from the profile (even if they match an inclusion elsewhere). | Carving out a privileged subset (e.g., IT admins) from a broad inclusion. |

The Intune transport supports both — unlike Arc (UIAO_010), where
exclusions are deferred per ADR-039 §"Negative / deferred". An
exclusion is a strong statement: it overrides any matching inclusion.
Use sparingly, and prefer narrowing the inclusion scope first.

## Operator workflows

### Add a new Intune assignment

1. **Confirm the profile exists** in the tenant. The `profile_ref.value`
   resolves by `displayName`. If the tenant does not yet hold a profile
   with that name, the next `plan` produces an `intune-profile-missing`
   op — not an error, but a governance-review op that will not
   auto-apply.
2. **Confirm the target dynamic group exists in canon.** Group must be
   declared in `canon/data/orgpath/dynamic-groups.yaml` (UIAO_152). If
   not, declare the group via the ADR-036 workflow first; do not edit
   policy-targets.yaml to reference a group that does not yet exist in
   canon — the loader will reject the PR.
3. **Pick the tightest target group** that still covers every device
   you intend to govern. Membership keys off OrgPath; selecting a
   wider group and relying on exclusion to subtract is acceptable for
   admin carve-outs (see existing `Intune-Unmanaged-Exclusion` pattern)
   but should not be the default — narrower targeting reduces blast
   radius.
4. **Pick the intent.** Default `include`. Reach for `exclude` only to
   carve out a privileged subset from a broader inclusion declared
   elsewhere in this same file.
5. **PR the change.** The loader runs in CI. Cross-canon integrity
   surfaces immediately:
   - `target_group` not in UIAO_152 dynamic-groups → loader error
   - duplicate `(profile_ref, target_group, intent)` tuple → loader error
6. **After merge, the adapter `plan` against the tenant** will emit
   one of:
   - `intune-assign-create` — tenant has no assignment binding this
     profile to this group with this intent; will auto-apply on the
     next reconcile cycle.
   - `intune-assign-update` — tenant has the binding but its parameters
     differ; will auto-apply.
   - `intune-profile-missing` — tenant lacks the profile; governance
     review.
   - `intune-assign-phantom` — tenant has an OrgTree-named assignment
     this canon does not declare; governance review.

### Change the target group of an existing assignment

Edit `target_group` in place, PR the change, let the loader validate.
The next reconcile produces `intune-assign-update`. Do **not** rename
both the profile reference and the target group in the same PR — it
will read as a delete + create across two governance-review surfaces
and double the operator review cost.

### Convert an inclusion into an exclusion (or vice versa)

Edit `intent` in place. The loader treats `(profile_ref, target_group,
include)` and `(profile_ref, target_group, exclude)` as distinct tuples
for uniqueness purposes — so the edit is one tuple replacing another,
which is fine. The next reconcile produces `intune-assign-update`.

### Retire an assignment

Delete the entry. The next reconcile produces `intune-assign-phantom`
against the assignment that still exists in the tenant. Phantom ops
never auto-apply — an operator must decide whether the tenant
assignment should be torn down or whether canon should re-adopt it.

## Canonical operation vocabulary (Intune subset)

ADR-039 §5 defines four Intune ops. Restated here for convenience:

| Op | Auto-applies | Meaning |
|---|---|---|
| `intune-assign-create` | yes | Canon declares an assignment the tenant lacks. |
| `intune-assign-update` | yes | Canon and tenant diverge on profile reference, target group, or intent. |
| `intune-profile-missing` | **no** — governance review | The referenced profile does not exist in the tenant yet. |
| `intune-assign-phantom` | **no** — governance review | Tenant has an OrgTree-named assignment canon does not declare; possible unauthorized policy-consumer drift. |

Auto-apply versus governance-review is not a CLI flag. It is a property
of the op itself, enforced by the adapter. Phantom and missing ops
never auto-apply by design — Intune assignment changes can reconfigure
every device in a dynamic group atomically; the policy-consumer layer
has the broadest blast radius in the OrgTree stack.

## Three-plane device model interactions

[ADR-034](adr/adr-034-three-plane-device-model.md) declares three
device planes — each with a different OrgPath origin:

| Plane | OrgPath source | Reachable from this canon? |
|---|---|---|
| **Entra-joined client** | OrgPath written to device extension attribute via UIAO_153 mapping | **Yes** — Intune profiles assigned per `intune_assignments[]` reach these. |
| **Arc-enrolled server** | OrgPath written to ARM tag via UIAO_153 / ADR-038 | No — see UIAO_010 (Azure Policy is the targeting plane for Arc). |
| **Hybrid (HAADJ)** | OrgPath origin would be AD-side; deprecated per ADR-001 | No — not governed; should be migrated to Entra-join. |

A device that lives in the Hybrid plane is invisible to this canon
and to UIAO_010 alike. It is a `DRIFT-IDENTITY` finding against the
ADR-001 deprecation directive, not a policy-targeting gap.

## Boundary rules

- Every Entra-joined client the adapter touches MUST be in the
  GCC-Moderate boundary. The loader's per-entry `gcc-boundary:
  gcc-moderate` invariant matches the boundary metadata of every
  adapter (see [adapter-registry.yaml](adapter-registry.yaml)).
- Cross-tenant device targeting is out of scope. A device whose
  primary tenant is not the governed tenant is invisible to this
  adapter — it is not in the dynamic-group membership population to
  begin with.
- The instruction set the adapter dispatches to the execution substrate
  carries `boundary:m365-gcc-moderate` in its `constraints` array, per
  UIAO_164 §"Boundary Rules".

## Drift considerations

Three drift classes apply directly:

| Class | Trigger |
|---|---|
| `DRIFT-PROVENANCE` | An entry references a `target_group` that no longer exists in `canon/data/orgpath/dynamic-groups.yaml`. Loader catches at PR CI. |
| `DRIFT-AUTHZ` | An `intune-assign-phantom` op surfaces an OrgTree-named assignment in the tenant the canon does not declare — possible unauthorized profile authoring. |
| `DRIFT-SEMANTIC` | A canonical assignment's intent or target diverges from the tenant after portal-side edit. Surfaces as `intune-assign-update` until canon reabsorbs or the tenant edit is reverted. |

`DRIFT-IDENTITY` applies indirectly: an Entra-joined client whose
OrgPath extension attribute is missing or stale will fall out of every
OrgTree-* dynamic group, and the device will receive no policies from
this canon. The drift class fires against the device-plane writeback
(UIAO_153), not against this assignment canon.

## Forcing-function rationale

OrgPath-driven Intune targeting exists because:

1. **Microsoft is forcing federal agencies onto Intune** as the
   first-party MDM/EMM. Per [ADR-001](adr/adr-001-haadj-deprecated-entra-join-only.md),
   Hybrid Azure AD Join is deprecated; Entra-join + Intune is the only
   governed client posture going forward.
2. **NIST 800-53 Rev 5 CM-2, CM-6, CM-7, and CM-8** require a single
   authoritative configuration plane across the accreditation boundary
   for managed endpoints. Per-OU GPO authority does not survive the
   AD-to-Entra modernization; Intune profiles assigned via dynamic
   groups are the cloud-native equivalent.
3. **Dynamic group membership keyed on OrgPath, populated
   deterministically from HR data via UIAO_153 and ADR-038**, is the
   only attribute on a user/device that survives reorganizations,
   transfers, and rejoin events without manual remediation. Targeting
   on assigned-group-by-hand drifts the moment HR moves a person.

This rationale will be canonized as **ADR-MS (Microsoft-Forced
Transition Rationale)** per Charter Restoration Plan PR-A through
PR-D. Until ADR-MS lands, this section is the authoritative statement
of *why* this binding plane exists.

## Governance alignment

This document implements the substrate's commitment to PR-reviewable,
canon-first policy governance. Three invariants are visible from here:

1. **No portal-authored OrgTree-named Intune assignment is invisible
   to canon.** Phantom ops surface them all.
2. **No canon binding is silently inapplicable.** Profile-missing ops
   surface every binding the tenant cannot fulfill; group-missing
   conditions cannot occur because the loader rejects them at PR CI.
3. **No assignment widens scope without a PR.** The reconcile surfaces
   any divergence between canonical `target_group` / `intent` and
   tenant-side state as `intune-assign-update`, blocking apply until
   canon reabsorbs.

## Related canon

- [UIAO_010 OrgPath in Azure Policy](UIAO_010_OrgPath_in_Azure_Policy.md) — Arc-side companion (same ADR, different transport).
- [UIAO_007_OrgTree_Modernization_AD_to_EntraID](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) — programmatic context for the OrgTree work.
- [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md) — selector vocabulary that drives dynamic-group membership.
- [UIAO_152_Dynamic_Group_Library](UIAO_152_Dynamic_Group_Library.md) — the OrgTree-* group catalog this document targets.
- [UIAO_153_Attribute_Mapping_Table](UIAO_153_Attribute_Mapping_Table.md) — OrgPath extension-attribute writeback origin.
- [UIAO_154_Delegation_Matrix_AUs_Roles](UIAO_154_Delegation_Matrix_AUs_Roles.md) — Administrative Unit scoping (delegation, not targeting).
- [UIAO_163_Drift_Detection_Engine_Specification](UIAO_163_Drift_Detection_Engine_Specification.md) — generic drift engine; this document's ops feed the policy-consumer plane.
- [UIAO_164_Execution_Substrate_Integration_Layer](UIAO_164_Execution_Substrate_Integration_Layer.md) — substrate handoff contract.
- [ADR-001](adr/adr-001-haadj-deprecated-entra-join-only.md), [ADR-034](adr/adr-034-three-plane-device-model.md), [ADR-035](adr/adr-035-orgpath-codebook-binding.md), [ADR-036](adr/adr-036-dynamic-group-provisioning.md), [ADR-038](adr/adr-038-device-plane-orgpath.md), [ADR-039](adr/adr-039-policy-targeting.md) — the OrgTree decision chain.
