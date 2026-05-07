---
deliverable_id: Spec2-D5.5
title: "Provisioning Drift Detection Rules"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 5
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-02
updated: 2026-05-02
canonical_adrs:
  - ADR-003
  - ADR-040
canonical_docs:
  - UIAO_007
  - UIAO_136
upstream_deliverables:
  - Spec2-D3.1
  - Spec2-D3.5
sibling_deliverables:
  - Spec2-D5.3
  - Spec2-D5.6
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D5.5: Provisioning Drift Detection Rules

> **Status (v0.1, 2026-05-02):** Initial canonical drift-rule set
> for the Spec 2 substrate. Implements ADR-040 against the
> provisioning surface specifically; D3.5 §8 specifies the
> per-stage drift-class contracts; D5.5 makes them operational
> rules.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Provisioning Drift Detection
Rules called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 5 → D5.5:

> *OSCAL-aligned rules: orphaned accounts (no matching HR record),
> zombie accounts (terminated in HR but active in Entra),
> attribute drift (Entra values != HR values), OrgPath staleness.*

D5.5 is the operational rule set the drift engine (ADR-040)
applies against the Spec 2 substrate.

### 1.1 Scope

In scope:

- The four canonical drift detection classes (orphaned, zombie,
  attribute, OrgPath staleness).
- Per-rule definition (trigger, severity, expected action).
- OSCAL-aligned compliance mapping.
- Rule cadence (when each is evaluated).
- False-positive handling.
- Rule versioning.

Out of scope:

- The drift engine itself (ADR-040 owns).
- Per-tenant exception lists (each deployment manages).
- Non-provisioning drift (e.g., device-plane drift covered by
  D3.5 stage-8 contract).

## 2. The Four Canonical Rule Classes

### 2.1 RULE-PROV-ORPHAN — Orphaned account

| Property | Value |
|---|---|
| Definition | An Entra user with `accountEnabled = true` whose `externalId` does NOT match any record in the most-recent HR feed |
| Severity | High (Sev 2 per D2.6 §5.1 escalation framework) |
| Cadence | Per HR-sync cycle |
| Expected action | Investigate within 24h. Either: (a) HR record should exist but doesn't (HR data quality); (b) account predates UIAO and was never reconciled; (c) bug in middleware |
| OSCAL control mapping | AC-2 (Account Management); CA-7 (Continuous Monitoring) |
| False-positive class | Service accounts; break-glass admin accounts; B2B guests — these are excluded by category from scope |

### 2.2 RULE-PROV-ZOMBIE — Zombie account

| Property | Value |
|---|---|
| Definition | An Entra user with `accountEnabled = true` whose corresponding HR record has `employmentStatus = Terminated` AND `terminationDate < today` |
| Severity | **Critical** (Sev 1 — security incident) |
| Cadence | Per HR-sync cycle |
| Expected action | Immediate triage (within 15 min per D2.6 §5.1 partial-disable SLA). Either Leaver (D2.3) workflow failed mid-way, or HR-feed lag, or middleware bug |
| OSCAL control mapping | AC-2; AC-12 (Session Termination); AU-2; IR-4 (Incident Response) |
| False-positive class | Records in tenant-defined post-termination grace window (e.g., 24h after `terminationDate` for retention-bound systems); records flagged for litigation hold with explicit policy override |

### 2.3 RULE-PROV-ATTR — Attribute drift

| Property | Value |
|---|---|
| Definition | An Entra user attribute whose value disagrees with what the current canonical mapping (D1.3) computes from the current HR record |
| Severity | Medium (Sev 3) |
| Cadence | Per HR-sync cycle (delta checked) + weekly full-pass |
| Expected action | Investigate within 7 days. Either: (a) Mover (D2.2) failed silently; (b) Entra-side manual modification (should not happen per D5.3 governance); (c) mapping rule changed without re-stamp |
| OSCAL control mapping | AC-2; CM-3 (Configuration Change Control); CA-7 |
| False-positive class | Attributes explicitly tenant-policy-excluded from drift detection (e.g., `employeeOrgData` if not in canonical mapping) |

### 2.4 RULE-PROV-ORGPATH-STALE — OrgPath staleness

| Property | Value |
|---|---|
| Definition | An Entra user's `extensionAttribute1` (OrgPath) was emitted by a calculator version older than the currently-deployed calculator version, AND re-running the current calculator on the user's current HR record produces a different value |
| Severity | Medium (Sev 3) |
| Cadence | After codebook update (ADR-035 per-update); daily background pass |
| Expected action | Re-stamp affected records via on-demand recompute. The middleware exposes a `uiao orgpath restamp <externalId>` CLI for targeted re-stamping |
| OSCAL control mapping | CM-3; CA-7 |
| False-positive class | Records with manual OrgPath override per D3.5 §7 (overrides intentionally bypass calculator) |

## 3. Rule Evaluation Mechanics

### 3.1 Cadence summary

| Rule | Per-cycle | Daily | Weekly | On-demand |
|---|---|---|---|---|
| RULE-PROV-ORPHAN | ✓ | | | |
| RULE-PROV-ZOMBIE | ✓ | | | |
| RULE-PROV-ATTR | ✓ (delta) | | ✓ (full) | |
| RULE-PROV-ORGPATH-STALE | | ✓ | | ✓ (after codebook update) |

### 3.2 Evaluation surface

The drift engine queries:

| Source | Purpose |
|---|---|
| UIAO provenance store (D3.1 §8) | What was emitted; when; what version stamped |
| Microsoft Entra (Graph API read) | Current state of users + attributes |
| HR feed snapshot (most-recent cycle) | Current state of HR records |
| OrgPath calculator (D3.2 §3.2) — invoked synchronously | Compute what current OrgPath SHOULD be |

### 3.3 Finding shape

Each finding emits:

```yaml
finding_id: <UUID>
rule: RULE-PROV-<class>
detected_at: <ISO-8601 UTC>
external_id: <employeeId>
upn: <UPN>
severity: <Sev 1 | 2 | 3 | 4>
detail:
  observed: <current state>
  expected: <what should be>
  delta: <description>
provenance_correlation:
  related_provisioning_event: <provenance_id of the related D2.x event>
  emission_version_stamp: <middleware version at emission time>
  current_deployed_version: <middleware version now>
control_evidence:
  - AC-2
  - <other applicable controls>
recommended_action: <one-line action>
status: open | triaged | resolved | accepted-as-known
```

## 4. False-Positive Handling

The drift engine maintains a per-tenant exclusion list:

```yaml
drift_exclusions:
  service_accounts:
    - "svc-mailrelay@agency.gov"
    - "svc-monitor@agency.gov"
  break_glass:
    - "emergencyaccess1@agency.gov"
    - "emergencyaccess2@agency.gov"
  litigation_hold_overrides:
    - external_id: "EMP-12345"
      reason: "Active litigation; account preserved by Compliance"
      expires_at: "2027-12-31"
  excluded_attributes_for_drift:
    - "employeeHireDate"   # tenant-managed differently
    - "officeLocation"     # not in UIAO canonical mapping
```

Each exclusion has an audit trail. Adding to the exclusion list is
a governance change (D5.3 §4).

## 5. Compliance Mapping

NIST SP 800-53 Rev 5 controls satisfied by D5.5:

| Control | Rule(s) |
|---|---|
| AC-2 (Account Management) | RULE-PROV-ORPHAN, RULE-PROV-ZOMBIE, RULE-PROV-ATTR |
| AC-12 (Session Termination) | RULE-PROV-ZOMBIE |
| AU-2 (Audit Events) | All rules — every finding is an audit event |
| AU-6 (Audit Review) | All — D5.3 §2.6 weekly review |
| CA-7 (Continuous Monitoring) | All — drift IS continuous monitoring |
| CM-3 (Configuration Change Control) | RULE-PROV-ATTR, RULE-PROV-ORGPATH-STALE |
| IR-4 (Incident Response) | RULE-PROV-ZOMBIE (Sev 1 routes to incident response) |

OSCAL component definitions for each rule SHOULD be authored per
the OSCAL-aligned format the deployment's compliance orchestrator
consumes (UIAO_100 / Compliance Orchestrator).

## 6. Rule Versioning

The rule set is canon. Adding a rule:

1. New ADR documenting rationale + scope.
2. Update D5.5 §2 with new rule.
3. Drift engine implementation update.
4. Canon registry update.

Modifying an existing rule (e.g., severity reclassification, cadence
change):

1. ADR documenting the change.
2. D5.5 update.
3. Re-baseline finding history (existing findings under old rule
   archived; new rule starts fresh).

## 7. Operator Surface

The operator-facing surface for drift findings:

| Capability | Implementation target |
|---|---|
| List open findings | `uiao drift list --rule <class>` |
| Show finding detail | `uiao drift show <finding-id>` |
| Triage / resolve / accept-as-known | `uiao drift triage <finding-id> --status <state>` |
| Re-stamp on-demand (RULE-PROV-ORGPATH-STALE) | `uiao orgpath restamp <externalId>` |
| Force quarantine investigation (RULE-PROV-ZOMBIE security incident) | `uiao drift escalate <finding-id> --to security` |
| Per-rule dashboard | D3.7 §6 dashboard panel + D5.6 dashboard |

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-040](../adr/) — drift engine.

### 8.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 5 → D5.5.

### 8.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) §8 — provenance contract drift engine reads.
- [Spec2-D3.5](./Spec2-D3.5-OrgPathPopulationPipeline.md) §8 — drift-class contracts.
- [Spec2-D5.3](./Spec2-D5.3-ProvisioningGovernanceSpecification.md) §2.6 — drift findings governance review.
- [Spec2-D5.6](./Spec2-D5.6-ProvisioningHealthDashboard.md) — drift surfaces in dashboard.

### 8.4 Compliance

- NIST SP 800-53 Rev 5: AC-2, AC-12, AU-2, AU-6, CA-7, CM-3, IR-4.
