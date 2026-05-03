---
deliverable_id: Spec2-D5.2
title: "Legacy Provisioning Decommission Plan"
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
  - Spec2-D5.1
sibling_deliverables:
  - Spec2-D5.3
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D5.2: Legacy Provisioning Decommission Plan

> **Status (v0.1, 2026-05-02):** Initial canonical decommission
> plan. Invoked from D5.1 step 11 after a successful parallel-run
> period.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Legacy Provisioning Decommission
Plan called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 5 → D5.2:

> *Plan to shut down existing manual/MIM/FIM provisioning after
> API-driven pipeline is validated. Include: parallel run period,
> comparison reconciliation, final cutover, decommission sign-off.*

D5.2 names the canonical sequence; the actual legacy system varies
per deployment (Microsoft Identity Manager, ForeFront Identity
Manager, custom scripts, manual ops). The shape of the
decommission is universal.

### 1.1 Pre-conditions

| Pre-condition | Source |
|---|---|
| D5.1 cutover steps 1–9 complete | D5.1 cutover record |
| Parallel-run period ≥ N days complete with zero unexplained divergence | D5.1 step 10 |
| Validation Report (D4.5) sign-offs include Identity Governance + Compliance | D4.5 |
| Legacy-system inventory complete (knows what to decommission) | Operations |
| Communications notice sent to all upstream consumers of legacy provisioning | Change communications |

## 2. The 7-Step Decommission Sequence

### Step 1 — Inventory legacy artifacts

Catalog everything to be decommissioned:

| Class | Examples |
|---|---|
| Software | MIM portal/service, FIM agents, custom Python/PowerShell ETL scripts |
| Service accounts | The legacy system's run-as account, AD permissions granted to it |
| Scheduled jobs | Cron / Task Scheduler entries that triggered legacy syncs |
| Network rules | Firewall openings between legacy system and HR/AD/Entra |
| Credentials | API keys, certificates the legacy system used |
| Documentation | Runbooks, knowledge-base articles referencing legacy |
| Monitoring | Alert rules, dashboards specific to legacy |

### Step 2 — Disable scheduled triggers

Stop the legacy system from being invoked:

- Disable cron / Task Scheduler entries.
- Disable any portal triggers.
- Pause API endpoints if the legacy exposed an API.

The legacy system continues to run but does not act.

### Step 3 — Confirm UIAO is sole source

For 7 days after step 2, monitor:

- Provisioning logs (Microsoft side) — confirm 100% of changes
  carry the UIAO middleware's request_id (no legacy-side writes).
- AD-side changes — confirm 100% in the writeback OU come from
  the gMSA (no legacy-side writes).

Any legacy-side write during this window indicates step 2 was
incomplete; investigate, complete, restart the 7-day window.

### Step 4 — Stop legacy services

After the clean 7-day window: stop the legacy services entirely.

- Stop MIM/FIM Windows services.
- Decommission scheduled-task or cron entries (disabled in step 2;
  now removed).
- Disable API endpoints.

The legacy system no longer runs.

### Step 5 — Revoke legacy credentials + permissions

| Item | Action |
|---|---|
| Legacy service account in AD | Disable (do NOT delete yet — see step 6) |
| Legacy service account permissions | Revoke (record what was revoked for rollback) |
| Legacy API keys / certs | Revoke at issuing authority |
| Firewall openings | Close (per network change-control) |

### Step 6 — Retention period

Keep the legacy system's STATE (database, logs, config) for the
agency's archive retention period (typically 2 years for non-
audit-class artifacts; 7 years for audit-class). The system is
DOWN but the data is NOT deleted.

This protects against late-discovered audit needs.

### Step 7 — Final removal + sign-off

After retention period:

- Delete legacy software installations.
- Delete legacy service accounts.
- Decommission VMs/hosts.
- Archive documentation references.
- Sign-off meeting:

| Role | Sign-off |
|---|---|
| Identity Engineering lead | Technical removal |
| Identity Governance lead | Substrate posture confirmed |
| Compliance / Audit lead | Retention satisfied; archive complete |
| Agency CISO | Risk acceptance for final removal |

The legacy system is fully decommissioned.

## 3. Rollback Considerations

| Step | Rollback feasibility |
|---|---|
| Step 1–2 | Trivial; just re-enable triggers |
| Step 3 | Trivial; ditto |
| Step 4 (stopped) | Restart services; resume |
| Step 5 (credentials revoked) | Re-grant credentials; restart |
| Step 6 (retention period) | Possible but increasingly expensive |
| Step 7 (final removal) | NOT feasible; this is a one-way door |

Step 7 is the irreversible boundary. UIAO governance recommends
the agency CISO sign-off be explicit and documented.

## 4. Per-Legacy-System Notes

### 4.1 Microsoft Identity Manager (MIM)

- MIM portal: shut down IIS site.
- MIM synchronization service: stop Windows service.
- MIM management agents (MAs): stop schedule.
- MIMWAL workflows: stop schedule.
- MIM service database: retained per step 6.

### 4.2 Forefront Identity Manager (FIM)

- Older than MIM; same shutdown sequence applies.
- FIM is end-of-life as of Microsoft's lifecycle; agencies still
  running it have additional motivation to decommission.

### 4.3 Custom ETL scripts

- Identify all scripts (often scattered across cron, Task
  Scheduler, agency-internal job-runners).
- Disable, then remove.
- Source-control history retained (don't delete the repo).

### 4.4 Manual / spreadsheet provisioning

- Disable the access-control mechanism that enabled manual
  provisioning (typically: revoke the operators' broad Entra
  scopes; lock down to scoped delegated admin units only).
- The "system" is human; decommission means policy change, not
  service shutdown.

## 5. Decommission Record

```yaml
decommission_id: <UUID>
deployment: <tenant id>
legacy_system: <name>
related_cutover_id: <D5.1 cutover_id>
window:
  step_2_disabled_triggers: <ISO-8601>
  step_3_clean_window_end: <ISO-8601>
  step_4_services_stopped: <ISO-8601>
  step_5_credentials_revoked: <ISO-8601>
  step_6_retention_end: <ISO-8601>
  step_7_final_removal: <ISO-8601>
parallel_run_divergences: <count>
sign_offs:
  - role: <…>
    name: <…>
    date: <…>
```

## 6. References

### 6.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 6.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 5 → D5.2.

### 6.3 Spec 2 sister deliverables

- [Spec2-D5.1 — Production Cutover Runbook](./Spec2-D5.1-ProductionCutoverRunbook.md) — invokes D5.2 in step 11.
- [Spec2-D5.3 — Provisioning Governance Specification](./Spec2-D5.3-ProvisioningGovernanceSpecification.md) — steady-state after decommission.

### 6.4 Compliance

- NIST SP 800-53 Rev 5: CM-2 (baseline configuration), CM-3, AU-11 (audit retention).
