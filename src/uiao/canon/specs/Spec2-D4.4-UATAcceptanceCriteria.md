---
deliverable_id: Spec2-D4.4
title: "UAT Acceptance Criteria"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 4
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-02
updated: 2026-05-02
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_136
upstream_deliverables:
  - Spec2-D4.1
  - Spec2-D4.2
sibling_deliverables:
  - Spec2-D4.3
  - Spec2-D4.5
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D4.4: UAT Acceptance Criteria

> **Status (v0.1, 2026-05-02):** Initial canonical UAT criteria.
> Defines what "user-acceptance test passing" means in
> operator-observable terms — independent of the engineer-side
> integration tests (D4.2) and performance tests (D4.3).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical UAT Acceptance Criteria called
for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 4 → D4.4:

> *User acceptance test criteria per scenario: correct UPN,
> correct OrgPath, correct group membership, correct license,
> correct manager link, account enabled on correct date, account
> disabled on correct date.*

D4.4 is the operator-side complement to D4.2's engineer-side test
matrix. Where D4.2 exercises substrate behavior, D4.4 verifies
business outcomes. Both pass before production cutover.

### 1.1 Audience

- HR operations leads.
- Identity governance leads.
- Compliance / audit reviewers.
- Help-desk leads (the consumers of "did onboarding work").

NOT primarily an engineering audience. Criteria are stated in
business-observable terms, not API responses.

### 1.2 Scope

In scope:

- Per-scenario operator-observable acceptance criteria.
- Sign-off process.
- UAT cycle structure (rounds + timing).
- Pass / fail / re-test semantics.
- Defect classification.

Out of scope:

- Engineer-side test mechanics (D4.2).
- Load testing (D4.3).
- Per-tenant policy criteria (each deployment may layer
  additional checks — UIAO sets the floor).

## 2. UAT Cycle Structure

### 2.1 Rounds

| Round | Cadence | Scope |
|---|---|---|
| UAT-1 | Pre-cutover (2 weeks before go-live) | Full scenario matrix on pre-prod tenant |
| UAT-2 | Pre-cutover (1 week before go-live) | Defect-fix verification + re-test of all UAT-1 failures |
| UAT-3 | Optional 3-day window before go-live | Final smoke test + sign-off |

### 2.2 Per-round structure

Each round runs:

1. **Day 1**: Operator team executes the scenario test plan against
   the pre-prod tenant.
2. **Days 2–N**: Defects logged; engineering remediates.
3. **Final day**: Sign-off meeting; either advance or repeat round.

## 3. Per-Scenario Acceptance Criteria

For each JML scenario, the criteria the operator verifies (NOT the
engineer):

### 3.1 New hire (Joiner — FTE — pre-hire window active)

Operator verifies:

| Criterion | How verified |
|---|---|
| User exists in Entra ID | M365 admin center / Graph Explorer |
| UPN matches expected pattern | Visual inspection of UPN |
| `accountEnabled = false` during pre-hire | M365 admin center user properties |
| Mailbox provisioned (if Posture A) | Exchange admin center |
| Group memberships populated (department / location / FTE / OrgPath) | Group membership lookup |
| License assigned (if Posture A) | License page in M365 admin center |
| Welcome notification NOT yet fired | Notification sink log |

On day-of-hire transition:

| Criterion | How verified |
|---|---|
| `accountEnabled = true` flipped at expected time (tenant TZ) | M365 admin center; provenance store |
| Welcome notification fires once | Notification sink |
| User can interactively sign in | Test login |
| Mailbox accessible | Test login → Outlook |

### 3.2 Termination (Leaver)

Operator verifies (within 5 minutes of `terminationDate` reaching today):

| Criterion | How verified |
|---|---|
| `accountEnabled = false` | M365 admin center |
| Sign-in fails | Attempted test login → error |
| All sessions revoked (active session terminated) | Pre-existing session test |
| Removed from statically-assigned groups | Group membership lookup |
| Mailbox archived → shared | Exchange admin center |
| OrgPath FROZEN at termination value | M365 admin center extensionAttribute1 inspection over time |
| Direct reports' manager-reassignment ticket exists | Operator queue inspection |
| Litigation hold applied (if flagged) | Purview compliance page |

### 3.3 Department transfer (Mover — department change)

| Criterion | How verified |
|---|---|
| `department` updated | M365 admin center |
| `extensionAttribute1` (OrgPath) updated within 15 min p95 | Inspect attribute |
| Old department's dynamic group memberships removed within 30 min | Group lookup |
| New department's dynamic group memberships added within 30 min | Group lookup |
| Intune policy targeting reflects new dept within 1h | Intune assignment-list page |
| Manager link unchanged (this is dept change, not manager change) | manager attribute |
| Old / new manager NOT notified (no notification on dept-only change) | Notification sink |
| Access-review trigger fired | Access reviews queue |

### 3.4 Manager change (Mover — manager change)

| Criterion | How verified |
|---|---|
| `manager` attribute updated to new manager | M365 admin center |
| Old / new manager BOTH notified once | Notification sink |
| Access review on direct-report subtree fires | Access reviews queue |

### 3.5 Name change (Mover — name change)

| Criterion | How verified |
|---|---|
| `displayName` updated | M365 admin center |
| `givenName` / `surname` updated | Same |
| **UPN preserved** (default; per D2.2 §4 step 2) | UPN unchanged |
| Email address unchanged | Same |
| Legacy share permissions unchanged (UPN-bound) | Spot check on shared SharePoint folder |

### 3.6 Rehire (Path A reactivation)

| Criterion | How verified |
|---|---|
| `accountEnabled` flipped from false to true | Admin center |
| Attributes refreshed from current HR record | Spot check |
| **Statically-assigned groups NOT auto-restored** | Group lookup (intentional: requires explicit re-grant per access review) |
| Manager notified (welcome-back) | Notification sink |
| Mandatory access review trigger fires | Access reviews queue |

### 3.7 Contractor → FTE conversion

| Criterion | How verified |
|---|---|
| `extensionAttribute2` (worker-type tag) flipped from CONTRACTOR-* to FTE-* | Admin center |
| License tier upgraded | License page; **acknowledge brief overlap window per D2.5 §5.1** |
| Removed from contractor-restricted groups | Group lookup |
| Added to FTE-only groups | Group lookup |
| **UPN preserved** | UPN unchanged |
| Mandatory access review for role-assignable groups fires | Access reviews queue |

### 3.8 LOA / OnLeave

| Criterion | How verified |
|---|---|
| `accountEnabled = true` (LOA does NOT disable) | Admin center |
| LOA flag attribute (`extensionAttribute3`) set | Admin center |
| Tenant CA policy restricts access per LOA flag | Test login from non-allowed location → blocked |

## 4. Cross-Cutting Criteria

These apply across all scenarios:

| Criterion | How verified |
|---|---|
| Provenance event emitted for every observable state change | Provenance store query by `external_id` |
| No duplicate / orphan accounts | Cross-reference HR feed × Entra user list |
| Quarantine queue NOT growing unboundedly | Dashboard inspection |
| All tier-2 alerts cleared | Alert queue inspection |

## 5. Defect Classification

Defects discovered during UAT classify as:

| Severity | Definition | Cutover impact |
|---|---|---|
| Sev 1 — Blocker | Wrong UPN; wrong OrgPath; account-not-disabled-on-termination; PII leak; security-incident class (D2.6 §5.1) | **Blocks cutover** |
| Sev 2 — Major | Notification missed; access-review-trigger missed; cascade lag exceeds 2× planning value | Blocks cutover OR defer to first-week post-cutover with mitigation |
| Sev 3 — Minor | Cosmetic UI issue; non-load-bearing label; documentation gap | Does NOT block cutover; backlog item |
| Sev 4 — Trivial | Typo in welcome notification template; out-of-scope feature request | Backlog |

## 6. Sign-Off Process

Each round ends in a sign-off meeting. Required sign-offs:

| Role | Sign-off authority |
|---|---|
| Identity governance lead | Substrate behavior |
| HR operations lead | HR-side operational fit |
| Compliance / audit lead | Auditability + provenance completeness |
| Help-desk lead | User-experience fit |

A round passes when ALL four sign-offs are received with no Sev 1
or Sev 2 defects open.

## 7. Reporting

Each round produces:

- A per-scenario pass/fail/blocked-by-defect log.
- A defect inventory with severities + assignment.
- A sign-off summary (who signed; when; any conditions).

Results feed into D4.5 (Validation Report).

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 8.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 4 → D4.4.

### 8.3 Spec 2 sister deliverables

- [Spec2-D4.1 — Test HR Data Set](./Spec2-D4.1-TestHRDataSet.md) — UAT input data.
- [Spec2-D4.2 — Integration Test Plan](./Spec2-D4.2-IntegrationTestPlan.md) — engineer-side parallel.
- [Spec2-D4.3 — Performance & Scale Test Plan](./Spec2-D4.3-PerformanceScaleTestPlan.md) — load profile.
- [Spec2-D4.5 — Validation Report](./Spec2-D4.5-ValidationReport.md) — sign-off destination.
- All D2.x specs — workflow contracts under verification.

### 8.4 Compliance

- NIST SP 800-53 Rev 5: CA-2 (security assessments — UAT is the user-side assessment leg).
