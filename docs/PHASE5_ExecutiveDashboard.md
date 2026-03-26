# PHASE 5 — Executive Dashboard Specification

> **UIAO Control Plane — Phase 5: Operational Readiness**
>
> Version: 1.0 
> Date: 2025-07-13 
> Classification: **CUI** — Executive Use Only 
> Status: **NEW (Proposed)**

---

## 1. Purpose

This document specifies the Executive Dashboard for the UIAO Control Plane, providing real-time visibility into operational health, compliance posture, drift status, and incident response across all six control plane domains. The dashboard serves as the single pane of glass for executive leadership, ISSO/ISSM, and Authorizing Officials to monitor the UIAO program's operational readiness.

---

## 2. Audience

| Role | Access Level | Primary View |
|---|---|---|
| Authorizing Official (AO) | Full | Executive Summary |
| ISSO / ISSM | Full | Compliance + Incident Detail |
| Program Manager | Full | All operational views |
| Domain Owners | Domain-scoped | Domain-specific metrics |
| SOC Analysts | Incident-scoped | Incident and alert views |
| Executive Leadership | Summary only | Executive Summary |

---

## 3. Dashboard Architecture

### 3.1 Data Flow

```
Data Sources → Collection Layer → Processing → Dashboard API → Visualization
     ↓                ↓               ↓              ↓               ↓
 Entra ID         Azure Monitor   Aggregation   REST API      Web Dashboard
 IPAM/DNS         GitHub Actions  Scoring       WebSocket     Power BI
 Overlay          SIEM            Alerting      GraphQL       Teams Integration
 Telemetry        Scripts         Trending
 Certificates
 CMDB
```

### 3.2 Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Data Collection | Azure Monitor, GitHub Actions | Source data ingestion |
| Processing | Azure Functions / Logic Apps | Aggregation, scoring, alerting |
| Data Store | Azure SQL / Cosmos DB | Metric history, trend data |
| API Layer | Azure API Management | Dashboard data serving |
| Visualization | Power BI Embedded / Web App | Dashboard rendering |
| Alerting | Azure Monitor Alerts | Threshold-based notifications |
| Integration | Teams Webhooks | Status notifications |

---

## 4. Dashboard Views

### 4.1 Executive Summary View

The top-level view provides at-a-glance program health:

| Widget | Data Source | Refresh Rate |
|---|---|---|
| Overall Health Score | Composite of all domains | 5 minutes |
| Compliance Posture (%) | Compliance automation pipeline | 15 minutes |
| Active Incidents | Incident tracking system | Real-time |
| Open POA&Ms by Severity | POA&M automation | 15 minutes |
| Drift Events (24h) | Drift detection workflows | 15 minutes |
| Domain Health Cards (6) | Per-domain health scores | 5 minutes |

### 4.2 Domain Health Cards

Each of the six domains displays a health card:

| Domain | Key Metrics |
|---|---|
| Identity | MFA coverage %, Conditional Access compliance, stale accounts, privilege anomalies |
| Addressing | IPAM accuracy %, DNS resolution health, allocation utilization, conflict count |
| Network | Overlay validation status, TIC 3.0 compliance %, segmentation integrity |
| Telemetry | Collection completeness %, log retention compliance, SIEM latency |
| Certificates | Certificates expiring < 30d, PKI health, rotation compliance |
| CMDB | Baseline accuracy %, unauthorized changes (24h), asset coverage |

### 4.3 Compliance Detail View

| Widget | Description |
|---|---|
| NIST 800-53 Control Coverage | Heat map of control family compliance |
| FedRAMP ConMon Status | Monthly scan, POA&M, and assessment tracking |
| Evidence Freshness | Age of most recent evidence per control |
| POA&M Aging Report | Open POA&Ms by age and severity |
| Compliance Trend (90d) | Score trending over past quarter |
| Upcoming Deadlines | Assessments, renewals, reporting due dates |

### 4.4 Incident Response View

| Widget | Description |
|---|---|
| Active Incidents | List with severity, domain, owner, age |
| Incident Timeline | Visual timeline of recent events |
| MTTD / MTTR / MTTC | Rolling averages with trend arrows |
| Escalation Status | Incidents approaching or past SLA |
| Federal Reporting Queue | US-CERT reports pending or submitted |
| Tabletop Exercise Tracker | Schedule compliance and results |

### 4.5 Drift Detection View

| Widget | Description |
|---|---|
| Active Drift Events | By domain, severity, and age |
| Drift Trend (30d) | New vs. resolved drift events |
| Top Drift Categories | Most frequent drift types |
| Remediation Pipeline | Drift events in remediation workflow |
| Auto-Remediation Rate | Percentage resolved automatically |
| Drift Heat Map | Cross-domain drift concentration |

---

## 5. Health Scoring Model

### 5.1 Composite Health Score

The overall health score is calculated as a weighted composite:

| Domain | Weight | Score Components |
|---|---|---|
| Identity | 25% | MFA coverage, CA compliance, lifecycle health |
| Addressing | 15% | IPAM accuracy, DNS health, conflict rate |
| Network | 15% | Overlay validation, TIC compliance, segmentation |
| Telemetry | 15% | Collection completeness, retention, SIEM health |
| Certificates | 15% | Expiration risk, rotation compliance, PKI health |
| CMDB | 15% | Baseline accuracy, change control, coverage |

### 5.2 Score Thresholds

| Score Range | Status | Color | Action |
|---|---|---|---|
| 95–100% | Healthy | Green | No action required |
| 85–94% | Warning | Yellow | Review and address within SLA |
| 70–84% | Degraded | Orange | Immediate investigation required |
| < 70% | Critical | Red | Escalation to ISSO/AO |

---

## 6. Alerting and Notifications

### 6.1 Alert Thresholds

| Metric | Warning Threshold | Critical Threshold | Notification Channel |
|---|---|---|---|
| Overall Health Score | < 90% | < 80% | Teams + Email |
| Domain Health Score | < 85% | < 75% | Teams + Domain Owner |
| Open Critical POA&Ms | >= 1 | >= 3 | ISSO + AO |
| Active SEV-1 Incidents | >= 1 | N/A | SOC + ISSO + AO |
| Drift Events Unresolved > 24h | >= 3 | >= 5 | Domain Owner + ISSO |
| Evidence Staleness | > 48h | > 72h | Compliance Automation |

### 6.2 Notification Schedule

| Notification | Trigger | Recipients |
|---|---|---|
| Daily Health Summary | 08:00 ET daily | All stakeholders |
| Weekly Compliance Digest | Monday 09:00 ET | ISSO, ISSM, Domain Owners |
| Critical Alert | Real-time | SOC, ISSO, AO |
| Monthly Executive Brief | 1st business day | AO, Executive Leadership |

---

## 7. Data Retention and History

| Data Type | Retention Period | Granularity |
|---|---|---|
| Real-time metrics | 30 days | 5-minute intervals |
| Daily aggregates | 1 year | Daily |
| Weekly summaries | 3 years | Weekly |
| Monthly reports | 7 years | Monthly |
| Incident records | 7 years | Per event |
| Compliance evidence | Per NIST requirements | Per artifact |

---

## 8. Access Control

### 8.1 Role-Based Access

| Role | Dashboard Access | Data Export | Configuration |
|---|---|---|---|
| AO | All views, all domains | Yes | No |
| ISSO / ISSM | All views, all domains | Yes | Alert thresholds |
| Program Manager | All views, all domains | Yes | Dashboard layout |
| Domain Owner | Domain-specific views | Domain only | Domain alerts |
| SOC Analyst | Incident views | Incident data | No |
| Read-Only Stakeholder | Executive summary only | No | No |

### 8.2 Authentication

- Entra ID SSO required for all dashboard access
- MFA enforced via Conditional Access policy
- Session timeout: 30 minutes idle, 8 hours absolute
- All access logged to audit trail

---

## 9. Implementation Roadmap

| Phase | Deliverable | Timeline |
|---|---|---|
| Phase 1 | Data collection pipeline + API scaffolding | Weeks 1–2 |
| Phase 2 | Executive Summary view + health scoring | Weeks 3–4 |
| Phase 3 | Domain health cards + compliance detail | Weeks 5–6 |
| Phase 4 | Incident response + drift detection views | Weeks 7–8 |
| Phase 5 | Alerting, notifications, Teams integration | Weeks 9–10 |
| Phase 6 | UAT, refinement, go-live | Weeks 11–12 |

---

## 10. References

| Reference | Description |
|---|---|
| `docs/00_ControlPlaneArchitecture.md` | Control Plane architecture overview |
| `docs/PHASE5_OperationalGovernance.md` | Operational governance charter |
| `docs/PHASE5_RuntimeDriftModel.md` | Runtime drift detection model |
| `docs/PHASE5_ComplianceContinuity.md` | Compliance continuity framework |
| `docs/PHASE5_IncidentResponseIntegration.md` | Incident response integration plan |
| NIST SP 800-137 | Continuous Monitoring guidance |
| FedRAMP Continuous Monitoring Guide | Dashboard and reporting requirements |

---

## 11. Approval

| Role | Name | Date |
|---|---|---|
| Document Author | UIAO Program Team | 2025-07-13 |
| Reviewed By | _________________ | __________ |
| ISSO Approval | _________________ | __________ |
| AO Approval | _________________ | __________ |

---

> **NO-HALLUCINATION PROTOCOL**: All technology references and compliance frameworks are sourced from published standards. Dashboard specifications reference the canonical UIAO repository structure and architecture. Items marked **NEW (Proposed)** are generated artifacts pending review.
