<!-- NEW (Proposed) -->
# Phase 5 — Runtime Drift Model

> **Status:** NEW (Proposed)  
> **Version:** 0.1.0  
> **Last Updated:** 2026-03-26  
> **Parent:** `PHASE5_OperationalGovernance.md`  

---

## 1. Purpose

Defines drift categories, detection methods, severity levels, and remediation paths for each UIAO control plane domain.

---

## 2. Drift Categories

| Domain | Drift Type | Detection Method | Severity |
|---|---|---|---|
| Identity | Stale accounts, orphaned credentials | Entra ID audit logs, lifecycle scans | Critical |
| Identity | MFA policy non-compliance | Conditional Access policy audit | High |
| Addressing | IP allocation mismatch | IPAM reconciliation | High |
| Addressing | DNS record staleness | DNS zone audit | Medium |
| Network | Overlay inconsistency | TIC 3.0 telemetry validation | High |
| Network | Firewall rule drift | NSG/firewall policy diff | Critical |
| Telemetry | Collection gap | Log Analytics coverage audit | High |
| Telemetry | Retention policy violation | Storage lifecycle audit | Medium |
| Certificates | Expiration risk | Certificate inventory scan | Critical |
| Certificates | Algorithm non-compliance | Certificate attribute audit | High |
| CMDB | Asset record mismatch | CMDB-to-reality reconciliation | Medium |
| CMDB | Ownership drift | Asset owner validation | Low |

---

## 3. Severity Levels

| Level | Response Time | Escalation |
|---|---|---|
| Critical | 4 hours | Architecture Lead + Canon Steward |
| High | 24 hours | Architecture Lead |
| Medium | 72 hours | Domain Owner |
| Low | Next sprint | Domain Owner |

---

## 4. Remediation Paths

| Drift Type | Remediation | Automation |
|---|---|---|
| Stale accounts | Disable/remove via lifecycle workflow | `detect_drift.py` |
| MFA non-compliance | Enforce Conditional Access policy | Compliance engine |
| IP mismatch | Reconcile IPAM records | `detect_drift.py` |
| Overlay inconsistency | Re-validate TIC 3.0 overlay | `update_crosswalks.py` |
| Collection gap | Extend diagnostic settings | Drift detection workflow |
| Certificate expiration | Rotate/renew certificate | Certificate automation |
| CMDB mismatch | Reconcile CMDB records | `detect_drift.py` |

---

## 5. Drift Event Log Schema

```json
{
  "event_id": "string",
  "timestamp": "ISO-8601",
  "domain": "Identity | Addressing | Network | Telemetry | Certificates | CMDB",
  "drift_type": "string",
  "severity": "Critical | High | Medium | Low",
  "description": "string",
  "remediation_status": "Open | In Progress | Resolved",
  "owner": "string"
}
```

---

## 6. Integration

- Triggered by: `drift-detection.yml` workflow
- Script: `scripts/detect_drift.py`
- Issue template: `governance-drift-report.yml`
- Reports to: `reports/drift-report.json`
