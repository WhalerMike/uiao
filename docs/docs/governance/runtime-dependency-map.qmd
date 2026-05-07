---
id: runtime-dependency-map
title: Governance Runtime Dependency Map
owner: governance-steward
status: DRAFT
---

# UIAO Governance Runtime Dependency Map

## Canonical Architecture Dependencies Across CI, Workflows, API, DB, and Dashboard

This map defines the dependencies that govern how drift events, SLA timers, and metadata updates flow through the runtime.

---

## 1. High-Level Dependency Graph

GitHub
--> Webhook Handler
--> Governance API
--> PostgreSQL (drift_events, sla_timers, metadata_snapshots)
--> Dashboard
--> Governance Stewards

---

## 2. Component Dependencies

### A. GitHub

- Depends on: none
- Provides: issues, PRs, CI events, workflow triggers

### B. Webhook Handler

- Depends on: GitHub
- Provides: normalized events, SLA updates, drift ingestion
- Critical dependencies: schema version, CI signatures

### C. Governance API

- Depends on: Webhook Handler, PostgreSQL
- Provides: dashboard data, SLA timers, drift summaries

### D. PostgreSQL

- Depends on: API writes
- Provides: drift history, SLA state, reliability snapshots

### E. Dashboard

- Depends on: Governance API
- Provides: corpus index, heatmaps, reliability trends

### F. CI Validator

- Depends on: schema version
- Provides: metadata validation, drift detection

### G. Weekly Drift Workflow

- Depends on: CI validator, schema
- Provides: drift reports, systemic drift signals

---

## 3. Failure Propagation

### CI Failure

--> Incorrect drift detection
--> Incorrect SLA timers
--> Dashboard inaccuracies

### Webhook Failure

--> Missing drift events
--> SLA timers not updated
--> Systemic drift undetected

### DB Failure

--> Dashboard stale
--> SLA enforcement breaks

---

## 4. Governance Controls

- Schema version pinning
- CI validator versioning
- Webhook handler health checks
- DB integrity checks
- Dashboard freshness monitoring

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
