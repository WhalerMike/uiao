---
deliverable_id: Spec2-D4.3
title: "Performance and Scale Test Plan"
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
  - Spec2-D3.3
  - Spec2-D4.1
sibling_deliverables:
  - Spec2-D4.2
  - Spec2-D4.5
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D4.3: Performance and Scale Test Plan

> **Status (v0.1, 2026-05-02):** Initial canonical performance test
> plan. Defines the load profile + sizing tests + failure-recovery
> tests every Spec 2 deployment runs before production cutover.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Performance & Scale Test Plan
called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 4 → D4.3:

> *Load testing: bulk provisioning (1,000+ records), incremental
> sync cycle time, provisioning agent throughput, API rate limit
> behavior, recovery after agent outage.*

D4.3 sets the load-shape every Spec 2 deployment characterizes
itself against. Sister to D4.2 (functional integration tests) and
input to D4.5 (Validation Report).

### 1.1 Scope

In scope:

- Bulk-load profile (initial-cutover scale).
- Incremental-sync profile (steady-state scale).
- Rate-limit-stress test (D3.1 §7 envelope verification).
- Agent throughput + HA failover.
- Recovery scenarios (agent outage, Graph 5xx storm, provenance
  store outage).
- Per-tier success criteria.

Out of scope:

- Functional correctness tests (D4.2).
- UAT (D4.4).
- Production-grade SLAs (D5.x — operational; D4.3 covers
  pre-production characterization).

## 2. Load Profiles

### 2.1 Initial bulk load

Simulates first-time tenant cutover: every existing HR record
flows in within hours.

| Property | Value |
|---|---|
| Record count | 10,000 (small tenant) / 100,000 (mid) / 500,000 (large federal) |
| Source rate | Single batch arrives over 24h window |
| Target completion | Per Microsoft daily-tenant cap (2,000 calls/day P1/P2 → 100,000 records/day @ 50/batch; or 6,000/day Governance → 300,000/day) |
| Multi-day spread (large tenants) | Required for >100K records on P1/P2 license |

Test verifies:

- Bulk processing completes within tenant-cap time.
- No record dropped silently.
- Provenance count = record count.
- Quarantine rate within expected percentage.
- Memory + CPU sized appropriately on middleware host(s).

### 2.2 Incremental sync (steady-state)

Simulates daily HR feed delta.

| Property | Value |
|---|---|
| Record delta size | 0.1–1% of total worker count per cycle |
| Cycle frequency | Configurable (15 min / 1h / daily) |
| P95 cycle duration | < 10 min for 1% delta on a 100K-worker tenant |

Test verifies:

- Delta processing completes within cycle budget.
- Mover events trigger correct cascades.
- Provenance store keeps up.

### 2.3 Re-org event (large delta)

Simulates a department reorganization affecting >100 records in a
single cycle (per D3.5 §5).

| Property | Value |
|---|---|
| Delta size | 100 / 1,000 / 10,000 records |
| Cycle expectation | Throttling per D3.5 §5; cascade settles within 1h for 1,000 records |

Test verifies:

- Throttling kicks in at the right threshold.
- Cascade lag stays within 2× planning value (D3.5 §3).
- No middleware panic / OOM under load.

## 3. Rate-Limit Tests

Verify D3.1 §7 throttling envelope:

| Test | Scenario | Expected behavior |
|---|---|---|
| Burst above 40 calls/5s | Push 100 calls in 5s | Token-bucket (D3.2 §3.7) absorbs; 60 are queued, 40 emit |
| Daily cap saturation (P1/P2) | Push >2,000 calls in 24h | Microsoft 429s after cap; middleware backs off cleanly |
| Recovery from 429 | Mock 429 response | Exponential backoff per D3.1 §6.2; eventual success |
| Sustained 429 (Microsoft outage simulation) | Mock 429 for 30 min | Quarantine after retry exhaustion; alerts fire |

## 4. Agent Throughput + HA

Per D3.3 §2 (3 active agents):

| Test | Scenario | Expected |
|---|---|---|
| Single-agent throughput | One active agent, 1,000-record bulk | Throughput baseline measured |
| 3-agent steady-state | All three active, 1,000-record bulk | Throughput ≈ 3× single-agent (within ±15%) |
| 1-agent failure | Kill one agent mid-bulk | Microsoft cloud reroutes to remaining 2; alerts fire; processing continues |
| 2-agent failure | Kill two; only 1 active | Microsoft routes to remaining 1; throughput drops; tier-3 alert fires |
| Full-agent outage | Kill all 3 | Writeback halts; tier-3 alert; cloud-only writes continue |
| Recovery | Restart one agent | Comes online; sync resumes; backlog drains within 1 cycle |

## 5. Recovery Scenarios

| Scenario | Expected recovery |
|---|---|
| Provenance store unreachable for 5 min | Middleware blocks new cycles; alerts fire; resumes when store returns |
| Quarantine store unreachable | Same |
| Graph endpoint hard-503 for 30 min | Retry with backoff; quarantine after exhaustion; alerts fire |
| Agent host reboot | Agent reconnects within 5 min; no data loss |
| Middleware crash mid-batch | On restart, processed records have provenance; unprocessed records re-enter from HR feed; no double-emission (idempotency per D3.1 §8) |
| Token cache poisoned | Cache invalidation; re-acquisition; resumed |

## 6. Acceptance Criteria

The release-candidate acceptance bar:

| Bar | Threshold |
|---|---|
| Initial bulk load completion | Within tenant-cap time × 1.2 (20% headroom) |
| Steady-state cycle p95 duration | < 10 min for 1% delta on 100K tenant |
| Rate-limit recovery | 100% of 429-injected requests eventually succeed |
| Agent failover to N-1 | Throughput drops < 50%, recovers in next cycle |
| Recovery scenario success | All §5 scenarios complete without data loss |

A release candidate that fails any of these bars is BLOCKED from
production cutover.

## 7. Test Environment

The performance-test tenant MUST:

- Run separately from D4.2 integration tenant (load tests
  generate noise that interferes with functional tests).
- Run on production-equivalent middleware host sizing (per
  D3.2 §6 configuration).
- Run on production-equivalent agent host sizing (per D3.3 §3).
- Have its own restricted Graph service principal.
- Monitoring instrumented to capture metrics during the run.

## 8. Cadence

| Test | Cadence |
|---|---|
| Bulk-load test | Pre-cutover; quarterly thereafter |
| Steady-state test | Weekly |
| Re-org event test | Per-release-candidate |
| Rate-limit tests | Per-release-candidate |
| Agent failover | Per-release-candidate |
| Recovery scenarios | Per-release-candidate |

## 9. Reporting

Each run emits:

- Per-test pass/fail.
- Per-test latency / throughput numbers.
- Resource utilization profile (CPU, RAM, disk, network).
- Comparison to prior-run baseline (regression indicator).

Results feed into D4.5 (Validation Report) for the release
candidate.

## 10. References

### 10.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 10.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 4 → D4.3.

### 10.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) §7 — throttling envelope under test.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) §3.7 — rate limiter under test.
- [Spec2-D3.3](./Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) §2 — HA topology under test.
- [Spec2-D4.1 — Test HR Data Set](./Spec2-D4.1-TestHRDataSet.md) — fixture extended for load.
- [Spec2-D4.2 — Integration Test Plan](./Spec2-D4.2-IntegrationTestPlan.md) — sister functional tests.
- [Spec2-D4.5 — Validation Report](./Spec2-D4.5-ValidationReport.md) — output report template.

### 10.4 Compliance

- NIST SP 800-53 Rev 5: SA-11, SC-5 (denial-of-service protection — the rate-limit + recovery tests verify this).
