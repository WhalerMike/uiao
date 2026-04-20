---
id: ADR-039
title: "OrgTree Policy Targeting — Intune + Azure Policy Dual Transport"
status: accepted
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
  - device-management-steward
supersedes: []
related_adrs:
  - ADR-035
  - ADR-036
  - ADR-037
  - ADR-038
canon_refs:
  - MOD_A_OrgPath_Codebook
  - MOD_B_Dynamic_Group_Library
  - MOD_C_Attribute_Mapping_Table
  - MOD_N_Execution_Substrate_Integration_Layer
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
---

# ADR-039: OrgTree Policy Targeting — Intune + Azure Policy Dual Transport

## Status

Accepted

## Context

Phases 2–4 delivered the OrgTree governance surface:

* **Phase 2** — OrgTree-* dynamic groups (MOD_B)
* **Phase 3** — Restricted Management AUs + scoped roles (MOD_D)
* **Phase 4** — device-plane OrgPath on Entra devices + Arc machines (MOD_C)

That surface is inert until policy consumers point at it. The session
notes that kicked off this work cite the gap directly:

> *"Map GPOs to Intune profiles against those groups — with clean OrgPath-scoped
> device groups, GPO → Intune mapping becomes deterministic: each GPO's OU
> scope translates to a corresponding dynamic device group, and the
> configuration profile targets that group."*

Two policy consumers cover nearly all governed devices:

1. **Intune** — configuration profiles and compliance policies for
   Entra-joined clients, assigned to OrgTree-* dynamic groups with
   include / exclude intent via
   ``POST /deviceManagement/{kind}s/{id}/assignments``.
2. **Azure Policy** — assignments for Arc-enrolled servers, scoped by
   the ``OrgPath`` ARM tag Phase 4 writes.

Three gaps before this ADR:

- No canon file bound Intune profiles to OrgTree groups. Operators had
  a library of canonical groups but no canonical record of *which
  profile targets which group*.
- No canon file bound Azure Policy definitions to OrgPath tag
  selectors.
- The two transports (Graph for Intune; ARM for Azure Policy) need
  different credentials and different JSON bodies. A single adapter
  that hides that difference risks silently mismatching capabilities.

## Decision

1. Publish `src/uiao/canon/data/orgpath/policy-targets.yaml` as
   executable canon. Two sections:
   - ``intune_assignments[]`` — each entry binds an Intune profile
     (resolved by ``displayName`` or ``id``) to an OrgTree-* dynamic
     group with ``include`` / ``exclude`` intent.
   - ``arc_policy_assignments[]`` — each entry binds an Azure Policy
     definition to an ``OrgPath`` ARM tag selector (``prefix`` +
     ``match_mode: startsWith | equals``).
2. Ship a JSON Schema at
   `src/uiao/schemas/orgpath/policy-targets.schema.json` that pins the
   ``intent`` enum, the Intune ``kind`` enum, the ``match_mode`` enum,
   and the OrgPath regex for selector prefixes.
3. Provide a loader at
   `src/uiao/modernization/orgtree/policy_targets.py` that additionally
   enforces **cross-canon integrity**:
   - every Intune ``target_group`` must resolve to a live MOD_B dynamic
     group (ADR-036) — a policy that targets a non-existent group is
     caught at PR CI, not at apply time;
   - every Arc ``orgpath_selector.prefix`` must be either the root
     ``ORG`` or an active code in the MOD_A codebook — no Arc
     assignment may scope to a deprecated or absent OrgPath;
   - ``(profile_ref, target_group, intent)`` tuples are unique;
     ``assignment_name`` values are unique.
4. Introduce modernization adapter
   `uiao.adapters.entra_policy_targeting.EntraPolicyTargetingAdapter`
   with three verbs (``plan`` / ``apply`` / ``reconcile``) that mirror
   Phase 2–4 adapters.
5. Eight-op plan vocabulary across two transports:
   - ``intune-assign-create``, ``intune-assign-update`` — Graph, auto-applied.
   - ``arc-policy-create``, ``arc-policy-update`` — ARM, auto-applied.
   - ``intune-profile-missing``, ``arc-policy-definition-missing`` —
     canonical policy doesn't exist in tenant yet; governance review.
   - ``intune-assign-phantom``, ``arc-policy-phantom`` — tenant has an
     OrgTree-named assignment the canon doesn't declare; governance
     review (potential unauthorised policy-consumer drift).

   **All four governance-review ops are never auto-applied.** The
   policy-consumer layer has the broadest blast radius in the OrgTree
   stack — a wrong assignment reconfigures every device it targets.

6. **Azure Policy filter parameters are canonical.** Every Arc policy
   assignment that OrgTree-governs MUST accept two parameters:
   ``orgPathPrefix`` and ``matchMode``. The adapter drift-checks these
   parameter values against the canonical ``orgpath_selector``. Policy
   authors who add OrgTree-targeted policies follow this contract or
   surface as drift.
7. ``apply(dry_run=False)`` raises by design — Graph and ARM need
   distinct credentials; operators subclass ``_execute`` for their
   tenant.

## Consequences

**Positive**

- Policy targeting becomes a governed, PR-reviewable canon file. A
  change to who-gets-which-policy flows through the normal MOD_V
  contributor workflow, not an admin clicking in a portal.
- Cross-canon integrity surfaces breakages early. Removing a dynamic
  group from MOD_B breaks the loader for any policy-target canon that
  still references it; CI catches the broken reference before any
  tenant sees a bad plan.
- Phantom-policy drift becomes first-class. An OrgTree-named Intune
  assignment or Azure Policy assignment that isn't in canon is an
  unambiguous governance finding — the adapter won't delete it, but
  it also won't pretend everything is fine.
- Unblocks Phase 6 (drift engine / MOD_M). The drift engine now has a
  fourth plane (policy-consumer) to diff.

**Negative / deferred**

- **Policy bodies are not authored here.** Only the binding. The Intune
  profile ``Intune-Baseline-Endpoint-Security`` must exist in the
  tenant (authored via the GPO-to-Intune migration or portal-author)
  before the adapter can bind a group to it. ``intune-profile-missing``
  surfaces this explicitly.
- **Azure Policy definition bodies must accept canonical parameters.**
  Policy definitions not built to accept ``orgPathPrefix`` +
  ``matchMode`` will always surface as drift. This is intentional —
  the canonical parameter shape is itself part of the governance
  invariant.
- **No exclusion support on Arc.** Phase 5 scope: Arc assignments are
  inclusive prefix scopes. Exclusions (``notIn`` / ``notStartsWith``)
  can be added in a follow-up once real policy bodies prove the need.
- **Read-side wiring for Graph and ARM is the caller's job.** The
  adapter consumes pre-fetched tenant state; future Phase 5.5 can add
  readers that fetch Intune + Azure Policy lists automatically.

## Alternatives considered

- **One adapter per transport.** Rejected; same reasoning as ADR-038
  (device planes): the governance story is one — "OrgTree governs
  policy targeting" — and splitting the adapter doubles the artefact
  without adding clarity.
- **Embed policy bodies in canon.** Rejected for Phase 5. Policy
  authoring is a separate workflow (GPO migration, Azure Landing Zone
  baselines). Canon claims the binding, not the content — reducing
  blast radius of canon changes.
- **Use Microsoft Graph Entitlement Management instead of direct
  assignments.** Rejected for this phase — EM adds a workflow/request
  layer the OrgTree does not need for attribute-driven targeting. May
  revisit for privileged access policies in a later phase.

## Related work

- ADR-035 / Phase 1 — OrgPath codebook. Arc selectors validate here.
- ADR-036 / Phase 2 — Dynamic groups. Intune targets resolve here.
- ADR-038 / Phase 4 — Device-plane OrgPath. Arc tags written by Phase 4
  are matched by Phase 5 selectors.
