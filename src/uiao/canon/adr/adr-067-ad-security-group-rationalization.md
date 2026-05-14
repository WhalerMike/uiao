---
adr_id: adr-067
title: "AD Security Group Rationalization — Distribution Lists, Mail-Enabled Groups, and Nested-Group Flattening"
status: ACCEPTED
decided: 2026-05-13
deciders: Michael Stratton
updated: 2026-05-13
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Entra ID group-type model change
impact: UIAO_135 §3.2 (Partially Defined gap closure); ADR-036 (dynamic-group-provisioning) consumes the classification taxonomy this ADR defines
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-067: AD Security Group Rationalization — Distribution Lists, Mail-Enabled Groups, and Nested-Group Flattening

## Status

**ACCEPTED** — May 13, 2026

## Context

ADR-036 (dynamic-group-provisioning) and ADR-039 (policy-targeting) cover the transformation pattern for **OrgTree-derived security groups** — the canonical dynamic groups that materialize the OrgPath attribute as Entra ID memberships. That covers one of four AD group categories. The other three remain without an explicit canonical pattern in canon as of UIAO_135 §3.2:

1. **Distribution groups** — mail distribution lists not used for access control.
2. **Mail-enabled security groups** — dual-purpose groups that grant access AND distribute mail.
3. **Nested security groups** — assignment-class groups with deep nesting that cannot be expressed natively in Entra ID.

UIAO_135 §3.2 explicitly flags this as a gap. Without a canonical transformation pattern, agencies migrating from AD to Entra ID end up with:

- Distribution lists either getting lost (no Entra ID equivalent for mail-only) or being created as Microsoft 365 Groups without the access-control hygiene that distinguishes them from security groups.
- Mail-enabled security groups duplicating into both a Microsoft 365 Group (for mail) and a separate security group (for access) without a documented mapping.
- Nested security groups carried over verbatim and exhausting Entra ID's evaluation depth limits, or flattened ad-hoc with no consistent rule.

Each migration team makes per-engagement decisions that diverge across customers, producing post-migration directories where group semantics are inconsistent and access-review tooling cannot correlate group purpose to control intent.

## Decision

**Every AD security group migrating to Entra ID is classified into exactly one of four canonical group types, with a per-type transformation pattern:**

| AD Source | Entra ID Target | Pattern |
|---|---|---|
| Security group used for OU-derived access | OrgTree-* dynamic group (ADR-036) | Already covered |
| Security group used for explicit role assignment | Assigned (static) Entra ID security group, **flattened** — no nesting | Direct membership, no transitive groups |
| Distribution list (mail-only) | **Microsoft 365 Group** with `groupTypes: ["Unified"]`, `securityEnabled: false` | Mail-only; **never** used for access control |
| Mail-enabled security group | **Two-object pattern**: Microsoft 365 Group (mail) + Assigned security group (access) with `OrgPath` extension attribute correlating them | Documented mapping in the migration manifest |

**Nested groups are flattened during migration.** A user who is transitively a member of `Group A → Group B → Group C` in AD becomes a direct member of `Group C` in Entra ID, with the transitive chain recorded in the migration audit. Source-side nesting that exists for legitimate hierarchical reasons (e.g., regional → corporate → global) is replaced with **OrgPath-bounded dynamic groups** per ADR-036 rather than carried over as nested static groups.

## Rationale

1. **Distribution and security responsibilities cannot share an object.** Mail-enabled security groups in AD blur the operational distinction between "who gets the email" and "who has access". Splitting them in Entra ID makes each side independently reviewable: mail recipients flow through M365 Group governance; access flows through Entra ID Access Reviews.

2. **Nesting is hostile to access review.** Auditing access via a transitively-nested group requires expanding the chain, which Entra ID can do but the human reviewer cannot scan at a glance. Flattening + recording the chain in the migration manifest preserves the audit history without preserving the operational fragility.

3. **OrgPath-bounded dynamic groups replace organic hierarchy.** AD groups nested for regional / functional hierarchy are an inheritance-by-naming-convention pattern. OrgPath dynamic groups (ADR-036) provide the same hierarchical membership semantics but anchored in the canonical OrgTree rather than fragile group nesting. Migration teams should not preserve nested static groups when OrgPath dynamic groups give them the same end-state.

4. **Microsoft 365 Group is the canonical mail-distribution surface.** Entra ID security groups can be mail-enabled but the practice is discouraged by Microsoft for new tenants. The M365 Group provides a richer mail surface (shared mailbox, shared calendar, governance lifecycle) that distribution lists in AD did not have.

5. **Two-object pattern preserves migration reversibility.** Splitting a mail-enabled security group into two objects with a correlated `OrgPath` extension attribute means a future engagement can re-correlate them (e.g., for unified governance reporting) without losing the source-side correspondence.

## Transformation Matrix

| Source pattern | Detection signal | Target | Mail | Access |
|---|---|---|---|---|
| Security group, no nesting, used for direct ACL grants | `groupType: Security` AND `mail: $null` AND no transitive members | Assigned Entra ID security group | n/a | Direct |
| Security group, OU-anchored (membership matches an OU) | Membership query equals OU enumeration | OrgTree-* dynamic group (ADR-036) | n/a | OrgPath rule |
| Distribution list | `groupType: Distribution` AND `mail: <addr>` | Microsoft 365 Group, `securityEnabled: false` | M365 mail | None |
| Mail-enabled security group | `groupType: SecurityMailEnabled` AND `mail: <addr>` | M365 Group + Assigned security group (correlated by extensionAttribute1 OrgPath) | M365 mail | Assigned security group |
| Nested security group | `member` includes other security groups | Flattened: direct memberships of the transitive closure; nesting chain recorded in migration audit | n/a | Direct |

## Consequences

**Positive:**
- One canonical mapping per source group type — migration teams stop making per-engagement decisions.
- Mail and access governance separable.
- Access reviews see flat memberships; transitive complexity moves to the audit record.
- Future re-correlation of mail and access (via the OrgPath correlation attribute) is preserved.

**Negative:**
- Mail-enabled security groups become two objects, which doubles the migration object count for that class.
- Nested-group flattening can produce very large flat memberships in cases where hierarchical role was the legitimate intent — this should trigger a review against OrgPath modeling rather than a direct carry-over.
- Distribution lists become M365 Groups, which carry SharePoint site + Teams + Planner side-effects unless those features are explicitly disabled per tenant policy.

**Operationally accepted:** the migration audit must record every distribution-list → M365 Group conversion with the disabled-side-effects setting, and every mail-enabled-security-group split with the correlation attribute, so the post-migration directory state is fully traceable.

## Implementation Plan

1. **Discovery** — Use existing AD group enumeration (covered by `Spec1-D1.1` and related discovery deliverables) to classify each group into one of the four canonical types.
2. **Pre-migration validation** — Flag groups where the classification is ambiguous (e.g., distribution lists that also appear in ACL grants — rare but legitimate as a one-off audit signal).
3. **Transformation** — Apply the per-type pattern via the migration pipeline (PowerShell DSC + Microsoft Graph) with explicit `dry_run=True` first run.
4. **Post-migration audit** — Verify every source group has exactly one (or two, for mail-enabled-security) target representation; verify nested chains are recorded in the audit.

## References

- ADR-036 — OrgTree dynamic group provisioning
- ADR-039 — Policy targeting (Intune + Azure Policy dual transport)
- UIAO_135 §3.2 — Partially Defined transformation gaps
- UIAO_136 Spec 1 — Computer Object Transformation Spec (parallels this group-side spec)
- Microsoft Learn: "Compare groups" — https://learn.microsoft.com/entra/fundamentals/concept-learn-about-groups
