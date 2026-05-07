---
deliverable_id: Spec2-D4.2
title: "Integration Test Plan"
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
  - Spec2-D3.1
  - Spec2-D3.2
  - Spec2-D4.1
sibling_deliverables:
  - Spec2-D4.3
  - Spec2-D4.4
  - Spec2-D4.5
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D4.2: Integration Test Plan

> **Status (v0.1, 2026-05-02):** Initial canonical test plan. Drives
> the integration suite that verifies the middleware (D3.2) +
> agent (D3.3) + Microsoft side cooperate correctly across every
> JML scenario, every worker type, and every D2.6 failure_reason
> class.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Integration Test Plan called for
in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 4 → D4.2:

> *Test matrix: every JML scenario × every worker type × cloud-only
> and hybrid target. Include negative tests: bad data, duplicate
> employee IDs, circular manager references.*

D4.2 is the contract every Spec 2 deployment's integration test
suite MUST satisfy before promoting a middleware version to
production. Builds on D4.1 (the test data set) and is consumed by
D4.5 (the validation report).

### 1.1 Scope

In scope:

- The full test matrix (scenarios × worker types × deployment
  modes).
- Negative tests for D2.6 failure_reason coverage.
- Test execution model (where tests run; what resources they
  exercise).
- Pass/fail semantics + acceptance bar.
- Test reporting + CI integration.

Out of scope:

- The test runner / harness implementation (per-deployment
  technology).
- Performance / scale testing (D4.3).
- UAT acceptance criteria (D4.4).
- Production-grade SLAs (D5.x).

## 2. Test Matrix

### 2.1 Cardinality

The minimum integration matrix:

| Axis | Values | Count |
|---|---|---|
| JML event class | Joiner / Mover / Leaver / Rehire / Conversion / Pre-hire / Quarantine | 7 |
| Worker type | FTE / PTE / Contractor / Intern / Vendor / Volunteer | 6 |
| Deployment mode | Cloud-only / Hybrid (with AD writeback) | 2 |
| **Total cells** | | **84** |

NOT every cell needs full coverage; some combinations are
nonsensical (e.g., Volunteer + Conversion-to-FTE is rare). The
posture: **>=70 cells exercised per test run; remaining 14 documented
as N/A**.

### 2.2 Per-cell test definition

For each exercised cell:

| Property | Value |
|---|---|
| Test name | `test_<workflow>_<workerType>_<deployment>` |
| Input | Subset of D4.1 fixture matching the cell |
| Expected SCIM operation | POST or PATCH per D2.x rules |
| Expected `active` value | per workflow rules |
| Expected provenance event_type | per D3.1 §8.2 vocabulary |
| Expected D2.6 failure_reason (if any) | per failure-class assignment |
| Expected downstream cascade (if hybrid) | AD record + OU placement |

## 3. Negative Test Suite

For each D2.6 §2 failure_reason, at least ONE record in D4.1
exercises it. The integration test verifies:

| `failure_reason` | Test verifies |
|---|---|
| `schema-validation` | Record routed to quarantine; provenance event emitted; SCIM call NOT issued |
| `worker-type-unknown` | Same |
| `usage-location-missing` | Same |
| `start-date-invalid` | Same |
| `manager-stale` | Same; quarantine record links to stale-manager `externalId` |
| `orgpath-codebook-miss` | Same; `failure_detail` names the missing codebook entry |
| `upn-collision` | Same; D1.5 collision-resolution exhausted |
| `prehire-window-config` | Operator alert; processing blocked |
| `conversion-path-unsupported` | Same |
| `event-collision` | Two simultaneous events for same `externalId`; precedence rule applied; one event dropped + logged |
| `rehire-active-collision` | Reactivate-already-active; no-op outcome |
| `late-edit-dropped` | HR edit during retention; logged; no SCIM call |
| `upn-flip-unauthorized` | Conversion blocked; quarantine |
| `graph-auth-failure` | Mock 401; record routed; auth-failure escalation |
| `graph-permission-denied` | Mock 403; same |
| `graph-schema-rejection` | Mock 400 with malformed body; same |
| `graph-rate-limit` | Mock 429; retry behavior verified per D3.1 §6.2 |
| `graph-server-error` | Mock 503; retry-then-quarantine |
| `partial-disable` | D2.3 step 1 succeeds, step 2 fails; partial-leaver state surfaced |
| `session-revoke-failed` | Mock revokeSignInSessions failure; security incident escalation |
| `provenance-emission-failed` | Mock provenance store unreachable; transaction rolled back |

## 4. Cross-Source Tests

Multi-source-agency variant (D4.1 §7) drives:

| Test | Purpose |
|---|---|
| Cross-agency manager link | Manager in agency A; report in agency B; resolution works |
| Per-agency OrgPath codebook isolation | Agency A's codebook NOT applied to agency B records |
| Per-source rate limiting | Agency A throttling does not starve agency B |
| Mixed-source bulkUpload batches | Single batch can carry records from both agencies |

## 5. Test Execution Model

### 5.1 Where tests run

| Layer | Environment |
|---|---|
| Middleware unit tests | CI (per-PR) |
| Middleware integration (mocked Graph) | CI (per-PR) |
| **D4.2 integration tests (this spec)** | Dedicated test tenant; nightly + on-demand |
| Performance tests (D4.3) | Dedicated test tenant; weekly + pre-release |
| UAT (D4.4) | Pre-prod tenant; per-release-candidate |

### 5.2 Test tenant requirements

The dedicated test tenant MUST:

- Run a real Microsoft Graph instance (not mocked).
- Have a separate provisioning service principal with restricted
  scope.
- Run a real provisioning agent (when hybrid is being tested).
- Have a small writeable AD (when hybrid).
- Be isolated from any production data.
- Be cleaned (all test users deleted) between runs.

### 5.3 Test isolation

Each test run uses a unique `employeeId` prefix (e.g.,
`TEST-RUN-<timestamp>-EMP-NNNNN`) so concurrent runs don't collide
even within the same test tenant.

## 6. Pass/Fail Semantics

A test cell **passes** when:

1. The expected SCIM operation was issued (or skipped if expected).
2. The expected provenance event was emitted with the expected
   correlation block fields.
3. The expected D2.6 failure_reason was assigned (for negative
   tests).
4. The expected downstream cascade settled within the planning-
   value latency for the cascade stage (D3.5 §3).
5. No unexpected side effects (no extra users created; no extra
   provenance events).

A test cell **fails** if any expected behavior is missing OR any
unexpected behavior occurs.

The release-candidate acceptance bar:

| Bar | Threshold |
|---|---|
| Total cells passing | ≥ 100% (no failures permitted) |
| Negative-test coverage | 100% of D2.6 §2 failure_reason classes |
| Cross-agency tests | All passing (when multi-agency) |
| Performance tests (D4.3) | All passing |

A release candidate that fails any acceptance bar is BLOCKED from
production cutover.

## 7. Test Reporting

Each run emits:

- A per-cell pass/fail line.
- Aggregate counts (cells / passing / failing / skipped).
- Per-failure-cell diagnostic block (test name, expected vs.
  actual, related provenance / quarantine record IDs).
- Cumulative D2.6 failure_reason coverage map.

The report is the input to D4.5 (Validation Report).

## 8. CI Integration

Per-PR CI runs the unit + mocked-Graph tests (fast); full D4.2
integration runs nightly OR on-demand (operator-triggered) OR
pre-release.

The nightly run posts a status badge that the deployment
operator can monitor. Failures page the on-call rotation per D3.7
tier-2 rules.

## 9. Versioning

D4.2 is canonical; the test cell list grows when D2.x specs add
new workflows or D2.6 adds new `failure_reason` values. Updates
require a parallel D4.1 fixture update.

## 10. References

### 10.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 10.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 4 → D4.2.

### 10.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate under test.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — middleware under test.
- [Spec2-D4.1 — Test HR Data Set](./Spec2-D4.1-TestHRDataSet.md) — input fixture.
- [Spec2-D4.3 — Performance & Scale Test Plan](./Spec2-D4.3-PerformanceScaleTestPlan.md) — sister test surface.
- [Spec2-D4.4 — UAT Acceptance Criteria](./Spec2-D4.4-UATAcceptanceCriteria.md) — operator-side acceptance.
- [Spec2-D4.5 — Validation Report](./Spec2-D4.5-ValidationReport.md) — report template.
- All D2.x specs — workflow contracts under test.

### 10.4 Compliance

- NIST SP 800-53 Rev 5: SA-11 (developer security testing).
