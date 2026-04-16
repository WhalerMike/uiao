---
title: "Appendix C-02: Drift Taxonomy"
appendix: "C-02"
family: "Drift Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-012"]
---

# Appendix C-02: Drift Taxonomy

## Purpose

This appendix defines the canonical taxonomy of drift types and severity levels used by the UIAO Drift Fabric. The taxonomy enables consistent classification, routing, and escalation of drift events across all adapters and integrated systems.

## Drift Types

### DT-01: Configuration Drift

A system's configuration settings deviate from the canonical baseline stored in the Truth Fabric.

**Examples:**
- A firewall rule was added outside the managed change process
- An application configuration parameter was changed without a governance record
- A cloud resource tag was removed

**Default severity:** MEDIUM (unless the configuration change affects a security control, in which case HIGH)

### DT-02: Identity Drift

A subject's identity attributes, memberships, or access assignments deviate from the canonical identity record.

**Examples:**
- A user was added to a privileged group without a corresponding access request claim
- A service account's permissions were elevated outside the managed process
- A device's compliance status changed from compliant to non-compliant

**Default severity:** HIGH (identity changes with security implications are always HIGH minimum)

### DT-03: Compliance Drift

A system that previously satisfied a compliance control is now observed to be non-compliant.

**Examples:**
- MFA was disabled on an account that is required to have MFA
- A patch that satisfies a vulnerability management control was removed
- An audit logging configuration was changed to stop capturing required events

**Default severity:** HIGH (compliance drift is always HIGH minimum; CRITICAL if the control is a FedRAMP High or CMMC L2 requirement)

### DT-04: Relationship Drift

The relationships between subjects deviate from the canonical model.

**Examples:**
- A user was removed from a project without a corresponding offboarding claim
- Two systems that should be isolated are now connected
- A dependency relationship between services changed

**Default severity:** LOW to MEDIUM (depends on the sensitivity of the relationship)

### DT-05: Data Integrity Drift

A data record in an integrated system deviates from the canonical record in the Truth Fabric.

**Examples:**
- A canonical claim's assertion fields differ from the current state in the source system
- A record that was supposed to be immutable was modified

**Default severity:** HIGH if the record is a governance artifact; MEDIUM otherwise

## Severity Levels

| Severity | Description | Automatic Action |
|---|---|---|
| INFO | Drift detected but within expected tolerance bands | Evidence Fabric log only |
| LOW | Minor deviation; no immediate governance impact | Evidence Fabric log; included in next governance report |
| MEDIUM | Deviation requires review; possible governance impact | Evidence Fabric WARN event; Governance Plane notification within 24 hours |
| HIGH | Significant deviation; governance impact confirmed | Evidence Fabric HIGH event; Governance Plane immediate notification; reconciliation triggered |
| CRITICAL | Severe deviation; active compliance violation or security incident | Evidence Fabric CRITICAL event; Governance Plane immediate alert; adapter SUSPENDED; incident response triggered |

## Severity Override

The Governance Plane may override the default severity classification for specific drift types, adapters, or subjects by adding override rules to the Drift Fabric configuration. Override rules are governance artifacts and MUST be documented in the Evidence Fabric.

## Dependencies

- **ADR-012:** Canonical drift taxonomy decision record
- **Appendix C-01:** Drift detection algorithm
- **Appendix D-02:** Audit event taxonomy (drift events are a subset)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
