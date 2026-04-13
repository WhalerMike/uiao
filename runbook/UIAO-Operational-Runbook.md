# UIAO Operational Runbook Layer

## Overview

The UIAO Operational Runbook Layer turns UIAO from a designed system into an operable system. This is what SREs, compliance operators, and federal program teams use to run UIAO day-to-day, respond to anomalies, and maintain deterministic behavior across tenants and environments.

---

## 1. Operational Procedures

### 1.1 Daily Operations

**Tasks:**
- Confirm evidence ingestion for all tenants
- Review drift deltas for all tenants
- Check enforcement adapter health
- Validate evidence bundle generation
- Confirm OSCAL artifacts are up-to-date
- Review orchestrator job queue for failures

**Daily Success Criteria:**
- No ingestion failures
- No unclassified drift
- No enforcement errors
- No stale evidence (>24h)

### 1.2 Weekly Operations

**Tasks:**
- Regenerate OSCAL SSP/SAP/SAR/POA&M
- Validate control pack versions
- Rotate plugin API keys (optional)
- Review tenant schedules
- Review evidence retention policies

**Weekly Success Criteria:**
- OSCAL artifacts regenerated and validated
- Control packs at current versions
- All tenant schedules operational

### 1.3 Monthly Operations

**Tasks:**
- Full evidence graph audit
- Control pack updates
- Plugin version reviews
- Tenant lifecycle reviews
- Retention policy enforcement

---

## 2. Incident Response Procedures

### 2.1 Evidence Ingestion Failure

**Symptoms:** Missing evidence, stale evidence (>24h), ingestion job failures.

**Procedure:**
1. Check orchestrator job queue for failed jobs
2. Review evidence service logs
3. Verify source system connectivity (SCuBA, M365, Azure AD)
4. Re-trigger ingestion job
5. Validate evidence bundle after recovery
6. Log incident in provenance

### 2.2 KSI Evaluation Failure

**Symptoms:** Missing KSI results, stale evaluation outputs.

**Procedure:**
1. Check evaluation service logs
2. Verify IR schema compatibility with control pack
3. Re-run KSI evaluation
4. Validate results against previous snapshot
5. Log incident

### 2.3 Drift Detection Failure

**Symptoms:** No drift events when evidence changed, false positive drift.

**Procedure:**
1. Compare evidence snapshots manually
2. Verify drift engine configuration
3. Check KSI rule versions
4. Re-run drift engine
5. Log incident

### 2.4 Enforcement Failure

**Symptoms:** Enforcement adapter errors, policy execution failures.

**Procedure:**
1. Check enforcement service logs
2. Verify adapter connectivity
3. Verify adapter permissions
4. Mark enforcement as "advisory only" temporarily
5. Re-attempt enforcement after remediation
6. Log incident

### 2.5 OSCAL Generation Failure

**Symptoms:** Missing OSCAL artifacts, validation errors.

**Procedure:**
1. Check OSCAL service logs
2. Verify evidence bundle integrity
3. Re-run OSCAL emitter
4. Validate OSCAL JSON against schema
5. Publish artifacts
6. Log incident

---

## 3. Evidence Corruption & Recovery Procedures

Evidence corruption is a critical incident.

### 3.1 Detection

Signs of evidence corruption:
- Hash mismatch
- Provenance mismatch
- Missing evidence fields
- Unexpected timestamp gaps

### 3.2 Recovery Procedure

1. Identify corrupted evidence bundle
2. Retrieve previous bundle from retention
3. Re-run Plane 3 (KSI to Evidence)
4. Re-run Plane 4 (Evidence to OSCAL)
5. Recompute provenance
6. Log incident
7. Notify auditor

---

## 4. Drift Anomaly Handling Procedures

A drift anomaly occurs when drift is detected but cannot be explained by:
- Evidence changes
- Control pack changes
- KSI rule changes
- Enforcement actions

### 4.1 Procedure

1. Compare IR snapshots at the field level
2. Review source system change logs
3. Verify KSI rule versions
4. If anomaly confirmed: escalate to human review
5. Document finding in POA&M
6. Log incident with full provenance trail

---

## 5. Enforcement Rollback Procedures

If an enforcement action causes unintended side effects:

### 5.1 Procedure

1. Stop enforcement service for affected tenant
2. Identify enforcement adapter that caused issue
3. Mark adapter as "advisory only"
4. Execute rollback if adapter supports it (rollback: true)
5. Collect post-rollback evidence
6. Update POA&M to reflect rollback
7. Log incident
8. Do not re-enable enforcement without review

---

## 6. OSCAL Regeneration Workflows

### 6.1 Scheduled Regeneration (Weekly)

1. Orchestrator triggers OSCAL emitter
2. OSCAL emitter reads current evidence bundles from Curated Zone
3. SSP, SAP, SAR, POA&M generated
4. Artifacts validated against OSCAL schema
5. Artifacts published to uiao-docs
6. Auditor API updated

### 6.2 On-Demand Regeneration

Triggered by:
- Drift resolution
- POA&M closure
- Control pack update
- Manual operator request

Procedure: Same as scheduled regeneration, with incident logging.

---

## 7. Tenant Onboarding / Offboarding

### 7.1 Tenant Onboarding

1. Create tenant record
2. Generate tenant encryption keys
3. Initialize data lake partitions
4. Enable default plugins (m365.sharing, conditionalaccess)
5. Install default control pack (m365-fedramp-moderate)
6. Create job schedules (SCuBA nightly, OSCAL weekly)
7. Create auditor-scoped API keys
8. Generate tenant onboarding report
9. Verify first successful SCuBA run

### 7.2 Tenant Offboarding

1. Suspend job schedules
2. Archive evidence to retention storage
3. Generate final OSCAL artifacts
4. Revoke API keys
5. Archive tenant record
6. Retain evidence per policy (minimum: 3 years for FedRAMP)

---

## Summary

The UIAO Operational Runbook Layer establishes:

1. **Daily/Weekly/Monthly Procedures** — Routine operational health checks
2. **Incident Response** — 5 incident types with step-by-step procedures
3. **Evidence Corruption Recovery** — Detection and recovery procedures
4. **Drift Anomaly Handling** — Investigation and escalation procedures
5. **Enforcement Rollback** — Safe rollback procedures for enforcement actions
6. **OSCAL Regeneration** — Scheduled and on-demand OSCAL workflows
7. **Tenant Onboarding/Offboarding** — Deterministic lifecycle procedures

This is the layer that makes UIAO **operationally viable**, **auditor-trustworthy**, and **enterprise-ready**.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
