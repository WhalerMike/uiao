---
id: ADR-037
title: "Delegation Matrix — Executable Canon + Entra AU/Role Provisioning Adapter"
status: accepted
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
  - security-steward
supersedes: []
related_adrs:
  - ADR-012
  - ADR-034
  - ADR-035
  - ADR-036
canon_refs:
  - MOD_A_OrgPath_Codebook
  - MOD_B_Dynamic_Group_Library
  - MOD_D_Delegation_Matrix_AUs_Roles
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
---

# ADR-037: Delegation Matrix — Executable Canon + Entra AU/Role Provisioning Adapter

## Status

Accepted

## Context

MOD_D (`src/uiao/modernization/orgtree/MOD_D_Delegation_Matrix_AUs_Roles.md`)
is the OrgTree's delegation SSOT: 14 Administrative Units across three
tiers (Enterprise / Division / Department), 15 role assignments binding
canonical groups to AU-scoped built-in roles, and an enforced
*Restricted Management* invariant that prevents Global Admins from
bypassing division-level delegation.

Before this ADR, MOD_D existed only as prose + PowerShell. Three concrete
consequences:

1. Nothing in the drift engine could distinguish a MOD_D-sanctioned role
   assignment from a tenant-wide (`directoryScopeId=/`) privilege
   escalation.
2. The `isMemberManagementRestricted` invariant had no runtime check —
   an AU could silently be created unrestricted and nothing flagged it.
3. Cross-canon references (MOD_D → MOD_A codebook, MOD_D → MOD_B groups)
   could drift: MOD_D might reference `OrgTree-FIN-Admins` with no
   matching entry anywhere, or a role assignment could point at a
   deprecated OrgPath.

## Decision

1. Publish the delegation matrix as executable canon at
   `src/uiao/canon/data/orgpath/admin-units.yaml` — enumerating AUs,
   built-in role **template IDs** (well-known Graph GUIDs — so
   reconciliation is deterministic without display-name lookups),
   admin-group references, and role assignments.
2. Ship a JSON Schema at
   `src/uiao/schemas/orgpath/admin-units.schema.json` that:
   - pins `restricted: true` as a `const` on every AU (the invariant
     can't be disabled through the canon);
   - enforces the AU naming regex (`^AU-ORG(-[A-Za-z0-9]+)*$`) and the
     admin-group naming regex (`^OrgTree-…-Admins$`);
   - requires `roleDefinitionId` values to be 8-4-4-4-12 GUIDs.
3. Provide a loader at `src/uiao/modernization/orgtree/admin_units.py`
   that additionally enforces **cross-canon integrity**:
   - every AU `orgpath_refs` entry must be **active** in MOD_A (reuses
     the ADR-035 codebook loader);
   - every AU `membership_rule` must quote each of its declared refs
     verbatim (same invariant MOD_B enforces — prevents ref/rule skew);
   - every `role_assignment.principal_group` must resolve to a **live
     canon entity**: either a MOD_B dynamic group (ADR-036) or one of
     the admin groups declared in this file. A role assignment that
     points at an orphan group name is rejected at load, before any
     tenant call.
4. Introduce the modernization adapter
   `uiao.adapters.entra_admin_units.EntraAdminUnitsAdapter` with three
   verbs (`plan` / `apply` / `reconcile`) that mirror ADR-036's
   Phase 2 adapter.
5. Six-op plan vocabulary — the AU plane and the role-assignment plane
   have distinct lifecycles so the plan surfaces them explicitly:
   - `au-create`, `au-update` — auto-applied when `dry_run=False`.
   - `role-create` — auto-applied when `dry_run=False` *and* the
     principal + AU IDs resolve at apply time.
   - `au-delete-phantom` — **never** auto-applied (governance finding).
   - `role-delete-unscoped` — **never** auto-applied; tenant-wide
     assignments (`directoryScopeId=/`) are potential privilege
     escalations per MOD_D §Governance Rule 4.
   - `role-delete-phantom` — **never** auto-applied; role assignments
     outside the matrix are investigated manually.

## Consequences

**Positive**

- Drift engine can emit five of the six MOD_D §Drift Detection rules
  with zero manual stubbing: AU Membership Drift (`au-update`), Missing
  AU (`au-create`), Unrestricted AU (`au-update` with the restriction
  reason), Role Assignment Drift (`role-delete-phantom`), and the
  MOD_D §Governance Rule 4 violation for unscoped assignments.
- Cross-canon integrity shuts the door on broken references: a PR that
  deletes an OrgPath from MOD_A or renames a MOD_B group will fail the
  admin-units loader at CI time rather than produce an invalid plan
  against a tenant.
- Role template IDs are stored in canon — the adapter never has to
  resolve roles by display name, which removes a whole class of
  localization/translation bugs.
- `role-delete-unscoped` turns the existing MOD_D prose rule into a
  **machine-checked** policy. Any Global Admin who grants a tenant-wide
  role creates a drift finding the adapter surfaces on the next
  reconcile.

**Negative / deferred**

- **Admin-group provisioning is out of scope.** MOD_D admin groups
  (`OrgTree-*-Admins`) are governance-approved assigned groups
  (MOD_E Workflow 5). The adapter references them by name but never
  creates, updates, or populates them — that's the Workflow 5 tool's
  job. The canon still declares the names so loader integrity can
  assert references resolve; no tenant write happens against them.
- `role-create` write path requires resolved principal-group IDs and AU
  IDs. Phase 3 ships the plan + skeleton; plumbing the resolver to fetch
  live `GET /groups` / `GET /administrativeUnits` at apply time is
  Phase 3.5 (a small follow-up). Until then, `apply(dry_run=False)` on
  role-create will raise — explicit and safe.
- PIM (Privileged Identity Management) eligibility/activation is not
  modelled. All assignments here are "active" assignments; PIM-wrapped
  assignments belong to a later phase with its own drift rules.
- Custom role definitions are intentionally excluded — MOD_D §Governance
  Rule 2 requires built-in roles only. If a future workflow approves a
  custom role, it gets its own MOD_D section and a new ADR.

## Alternatives considered

- **Store role assignments keyed by display name instead of template
  ID.** Rejected: Graph accepts both, but tenant locales can render
  display names differently, and template IDs are stable across the
  Microsoft cloud (GCC, GCC-Moderate, Commercial). Keeping the GUID in
  canon also makes the drift check a byte comparison.
- **Provision admin groups too.** Rejected for this phase: MOD_D is
  explicit that admin-group membership is a governed decision, not an
  attribute-driven automation. Wiring that to MOD_E Workflow 5 is the
  correct layer, not an IaC-style reconcile.

## Related work

- ADR-035 — MOD_A OrgPath codebook binding. This ADR depends on it.
- ADR-036 — MOD_B dynamic-group provisioning. This ADR depends on it
  for the principal_group ↔ group name cross-check.
- ADR-034 — Three-plane device model. AUs here scope **user** delegation
  only; device-plane AUs (Intune, Arc) are reserved for Phase 4+.
