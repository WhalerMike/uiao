---
deliverable_id: Spec2-D5.1
title: "Production Cutover Runbook"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 5
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
  - Spec2-D3.4
  - Spec2-D4.5
sibling_deliverables:
  - Spec2-D5.2
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D5.1: Production Cutover Runbook

> **Status (v0.1, 2026-05-02):** Initial canonical runbook. The
> specific timing, personnel, and tenant identifiers are
> per-deployment fill-ins; this is the canonical sequence.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Production Cutover Runbook called
for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 5 → D5.1:

> *Step-by-step production deployment: middleware deployment,
> provisioning app configuration, agent deployment, initial full
> sync, incremental sync enablement, legacy provisioning
> decommission.*

D5.1 is the canonical sequence for promoting a Spec 2 substrate
release-candidate (gated by D4.5 Validation Report) into production.
Deployment-specific instances of this runbook are operational
artifacts archived alongside the corresponding Validation Report.

### 1.1 Pre-conditions

Before D5.1 executes:

| Pre-condition | Source |
|---|---|
| D4.5 Validation Report signed (CUTOVER recommended) | D4.5 sign-off block |
| Production tenant Microsoft Graph permissions granted (D3.8 §4) | Identity governance |
| Production AD writeback OU created + gMSA permissions granted (D3.3 §4) | AD operations |
| Production middleware host(s) provisioned per D3.2 §6 | Infrastructure |
| Production provisioning agent host(s) provisioned per D3.3 §3 | Infrastructure |
| Production provenance + quarantine stores provisioned | Infrastructure |
| Production monitoring + alerting wired per D3.7 | Operations |
| Cutover window + freeze period agreed | Change advisory board |
| Communication plan prepared (HR ops, help-desk, agency users) | Change communications |

### 1.2 Audience

- Identity Engineering on-call.
- Change-advisory-board members during the cutover window.
- HR operations + help-desk leads (consumers of the cutover
  outcome).

## 2. The Canonical 12-Step Sequence

### Step 1 — Pre-cutover snapshot

Capture baseline:

- HR feed record count (current).
- Existing Entra user count.
- Existing AD user count (if hybrid).
- Existing legacy provisioning state (whatever MIM / FIM /
  custom solution was in place).

Stamp these into the cutover record as the baseline-of-record.

### Step 2 — Communication T-minus

Send pre-cutover communication:

- HR ops: notice + on-call contact.
- Help-desk: expected behavior changes (none for end-users on a
  successful cutover).
- Agency users: usually none (the cutover is invisible to them).

### Step 3 — Deploy middleware

Deploy the validated release-candidate middleware version to the
production host(s) per D3.2 platform.

Verify:

- Health endpoint returns 200.
- Readiness endpoint returns 200 (token cache warm; configuration
  validates; provenance store reachable).
- Configuration version matches what the Validation Report
  validated.

### Step 4 — Configure synchronization job

In the production Entra tenant, configure the bulkUpload
synchronization job per D3.4 §4 (Layer 2 attribute mapping).

Verify:

- Mapping configuration matches what the deployment repository
  has.
- Scoping filter is the canonical UIAO scope rule per D2.8 §5.

### Step 5 — Deploy provisioning agents (if hybrid)

Deploy three agents per D3.3 §2 to the production AD-adjacent
hosts. Install gMSA credentials per D3.3 §4. Verify all three are
online in the Microsoft cloud sync portal.

### Step 6 — DRY-RUN initial sync

Configure the middleware in **dry-run mode** (config flag): it
processes HR feed records and computes what it WOULD emit, but
does NOT call bulkUpload.

Run for one full cycle.

Verify:

- Record count expected vs. actual.
- Quarantine count within expected percentage (target ≤1%).
- Computed UPNs match expected pattern.
- Computed OrgPaths match codebook expectations.

If dry-run reveals issues: HALT. Fix. Re-validate.

### Step 7 — LIVE initial full sync

Disable dry-run; enable live mode. The middleware emits to
production Entra.

Initial bulk completion expected duration: per D4.3 §2.1 numbers.

Monitor:

- D3.7 dashboard: per-cycle progress.
- Quarantine queue: should grow proportionate to the bad-data
  rate.
- Microsoft Graph throttling indicators: 429 rate.
- Provisioning logs (Microsoft side): cross-reference with
  middleware-side provenance.

### Step 8 — Verify initial sync outcome

Once initial sync completes:

| Verification | How |
|---|---|
| User count delta | Entra user count ≈ HR record count − quarantine count |
| Spot-check 50 random records | Compare HR record vs. Entra user attributes |
| Spot-check 20 records of each worker type | Same |
| Spot-check 20 quarantined records | Verify expected `failure_reason` |
| OrgPath cascade settled | Dynamic group memberships reflect OrgPath values |
| AD writeback (if hybrid) | Spot-check 20 records in AD |

### Step 9 — Enable incremental sync

Configure the middleware's HR-feed cron per D3.2 §6 (default
every 15 min). The middleware now picks up HR-side changes.

Run for one full cycle. Verify a known HR-side delta (e.g., a
test-record department change) flows through within expected
timing.

### Step 10 — Run parallel for N days

The legacy provisioning solution (MIM / FIM / custom) continues
to run for N days (N ≥ 7, typically 14). UIAO is now the
primary; legacy is a passive shadow.

Daily parallel-run reconciliation:

- Compare Entra-side state vs. legacy-side expectation.
- Flag any divergences.
- Investigate + remediate.

### Step 11 — Decommission legacy provisioning

After N parallel days with zero unexplained divergences: execute
D5.2 Legacy Provisioning Decommission Plan.

### Step 12 — Cutover sign-off

Post-cutover meeting:

- All §1.1 sign-off roles confirm cutover stable.
- Cutover record archived alongside the Validation Report.
- Operations transitions from cutover-mode to steady-state per
  D5.3 governance specification.

## 3. Rollback Plan

If at any point during steps 6–10 a Sev 1 issue surfaces:

| Step at which issue surfaces | Rollback action |
|---|---|
| Step 6 (dry-run) | No rollback needed; halt and fix |
| Step 7 (live initial sync) | Disable live mode; re-enable legacy provisioning if it was disabled; restore last-known-good Entra state from snapshot if necessary |
| Step 8 (verification) | Same as 7 |
| Step 9 (incremental enabled) | Disable incremental; legacy reasserts; investigate |
| Step 10 (parallel run) | Trivial — legacy is still running |

The rollback decision is made by the Identity Engineering on-call
+ Change Advisory Board chair. Document the rollback in the
cutover record.

## 4. Special Considerations

### 4.1 Multi-source deployments

When the deployment ingests from multiple HR systems:

- Step 6 dry-runs each source independently.
- Step 7 live-syncs sources serially (first one alone, validate;
  then add the next, validate; etc.).
- Step 10 parallel-run period is per source.

### 4.2 Federal-specific

For federal civilian deployments:

- Cutover window typically excludes Friday + Saturday (no
  business hours for help-desk).
- Pre-coordinate with agency Change Advisory Board.
- FedRAMP boundary: confirm boundary controls are in place
  before live mode.

## 5. Cutover Record

Each cutover instance produces a cutover record:

```yaml
cutover_id: <UUID>
deployment: <tenant id>
release_candidate: <version>
validation_report_id: <D4.5 instance id>
window:
  start: <ISO-8601 UTC>
  end: <ISO-8601 UTC>
  rollback: <true|false>
steps:
  - step: 1
    started: <timestamp>
    completed: <timestamp>
    notes: <free text>
    operator: <name>
  - step: 2
    ...
final_state:
  middleware_version: <semver>
  entra_user_count: <int>
  ad_user_count: <int>      # if hybrid
  quarantine_count: <int>
  divergence_count: <int>   # from parallel-run reconciliation
sign_offs:
  - role: Identity Engineering on-call
    name: <name>
    date: <ISO-8601>
  - role: Change Advisory Board chair
    name: <name>
    date: <ISO-8601>
  ...
```

## 6. References

### 6.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 6.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 5 → D5.1.

### 6.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — what's deployed in step 3.
- [Spec2-D3.3](./Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) — what's deployed in step 5.
- [Spec2-D3.4](./Spec2-D3.4-AttributeMappingEngineConfiguration.md) — configured in step 4.
- [Spec2-D4.5 — Validation Report](./Spec2-D4.5-ValidationReport.md) — gates this runbook.
- [Spec2-D5.2 — Legacy Provisioning Decommission Plan](./Spec2-D5.2-LegacyProvisioningDecommissionPlan.md) — invoked in step 11.

### 6.4 Compliance

- NIST SP 800-53 Rev 5: CM-3 (configuration change control), CM-4 (security impact analysis).
