# UIAO-Core Database Adapter Drift Detection Specification  
### Version 1.0 — Canonical Definition

Database Adapter drift detection ensures that UIAO-Core can continuously verify the integrity, stability, and correctness of database‑backed claims. Drift detection is essential for **continuous ATO**, **KSI validation**, and **federated modernization**, enabling UIAO to detect when a database’s structure, semantics, or behavior deviates from the expected baseline.

This document defines the **drift types**, **detection methods**, **DriftReport schema**, **severity thresholds**, **KSI integration**, **alerting patterns**, and **remediation workflows** for all Database Adapters.

---

# 1.0 Drift Types

Database Adapters must detect **five canonical drift types**. Each drift type represents a deviation from the expected baseline that may impact claim correctness, evidence validity, or system integrity.

## 1.1 Schema Drift
Changes to the structural definition of the database.

Examples:
- Columns added, removed, or renamed  
- Data types changed  
- New tables or collections introduced  
- Indexes added or removed  

## 1.2 Constraint Drift
Changes to relational or structural constraints.

Examples:
- Primary key changes  
- Foreign key changes  
- Unique constraint changes  
- Index cardinality or ordering changes  

## 1.3 Cardinality Drift
Unexpected changes in the number of rows or documents.

Examples:
- Sudden spikes or drops in row counts  
- Missing expected records  
- Duplicate records appearing  

## 1.4 Semantics Drift
Changes in the meaning or interpretation of data.

Examples:
- Enum values added or removed  
- Business logic encoded in fields changes  
- Timestamp semantics change (e.g., UTC → local)  
- Field meaning shifts without schema change  

## 1.5 Query Plan Drift
Changes in how the database executes canonical queries.

Examples:
- Query plan hash changes  
- Index usage changes  
- Execution time anomalies  
- Vendor optimizer behavior changes  

---

# 2.0 Drift Detection Methods

Each drift type requires a specific detection method. Database Adapters must implement all applicable methods.

## 2.1 Schema Drift Detection
- Compare current schema metadata to baseline snapshot  
- Compute schema hash (sorted, canonicalized JSON)  
- Detect added/removed/renamed fields  
- Detect type changes  
- Detect index changes  

## 2.2 Constraint Drift Detection
- Compare PK/FK definitions  
- Compare uniqueness constraints  
- Compare index definitions and ordering  
- Detect constraint violations during extraction  

## 2.3 Cardinality Drift Detection
- Compare row counts to expected ranges  
- Detect sudden spikes or drops  
- Detect missing required records  
- Detect duplicate primary keys  

## 2.4 Semantics Drift Detection
- Compare enum sets  
- Compare field value distributions  
- Detect timestamp format changes  
- Detect field meaning changes via heuristics or vendor metadata  

## 2.5 Query Plan Drift Detection
- Capture vendor query plan  
- Compute plan hash  
- Compare to baseline plan hash  
- Detect index usage changes  
- Detect execution time anomalies  

---

# 3.0 DriftReport Schema (JSON)

All drift detection results must be emitted as a **DriftReport** object. This object is included in the EvidenceObject and the KSI Evidence Bundle.

```json
{
  "drift_id": "string-uuid",
  "adapter_id": "string",
  "drift_type": "schema | constraint | cardinality | semantics | query_plan",
  "severity": "low | moderate | high | critical",
  "first_observed": "2026-03-31T12:00:00Z",
  "last_observed": "2026-03-31T12:05:00Z",
  "description": "Human-readable explanation of the drift condition.",
  "recommended_remediation": "Steps to resolve the drift.",
  "baseline_hash": "sha256-hex-string",
  "current_hash": "sha256-hex-string"
}
```

### Required Fields
- **drift_id** — Unique identifier for this drift event  
- **adapter_id** — Database Adapter identifier  
- **drift_type** — One of the five canonical drift types  
- **severity** — Drift severity level  
- **first_observed** — When drift was first detected  
- **last_observed** — Most recent detection timestamp  
- **description** — Human-readable explanation  
- **recommended_remediation** — Clear guidance for operators  
- **baseline_hash** — Hash of expected baseline state  
- **current_hash** — Hash of current observed state  

---

# 4.0 Drift Severity Levels & Thresholds

Drift severity determines how UIAO responds to drift conditions.

| Severity | Description | Example Conditions |
|----------|-------------|-------------------|
| **Low** | Minor deviation, no impact on claims | Enum value added |
| **Moderate** | Potential impact on claims | New column added |
| **High** | Significant impact on claims or evidence | PK change, missing records |
| **Critical** | Evidence invalid, KSI cannot be validated | Schema rewrite, major semantics drift |

### Threshold Examples

#### Schema Drift
- Low: New optional column  
- Moderate: Column type change  
- High: Column removed  
- Critical: Table removed or renamed  

#### Cardinality Drift
- Low: ±5% deviation  
- Moderate: ±20% deviation  
- High: ±50% deviation  
- Critical: >75% deviation or missing required rows  

#### Query Plan Drift
- Low: Minor plan hash change  
- Moderate: Index usage change  
- High: Full plan rewrite  
- Critical: Query fails or returns inconsistent results  

---

# 5.0 Integration with KSI Validation Pipeline

Drift detection integrates directly with the **KSI Validator Engine**:

- DriftReports are included in each **EvidenceObject**  
- Drift indicators surface in:
  - ValidationResult  
  - Evidence Bundle  
  - OSCAL Observations  
  - Quarto Dashboard  

### Drift Impact on KSI Status
- **Critical drift** → KSI status = `fail`  
- **High drift** → KSI status = `fail`  
- **Moderate drift** → KSI status = `stale`  
- **Low drift** → KSI status unaffected but noted  

### Drift in Evidence Bundle
Drift appears under:

```json
"drift_indicators": [
  "Schema drift detected: column 'role_list' removed"
]
```

---

# 6.0 Alerting & Notification Patterns

UIAO-Core supports multiple drift alerting patterns:

## 6.1 Local Alerts
- Logged to adapter logs  
- Included in EvidenceObject  
- Included in KSI validation summary  

## 6.2 Dashboard Alerts
- Drift indicators appear in Quarto dashboard  
- Highlighted in red/yellow based on severity  
- Evidence freshness timers reflect drift impact  

## 6.3 External Notifications (Optional)
Adapters may integrate with:
- SIEM systems  
- Email alerts  
- Webhooks  
- Incident response pipelines  

---

# 7.0 Remediation Workflows

Each drift type has a recommended remediation workflow.

## 7.1 Schema Drift Remediation
- Review schema changes with vendor  
- Update canonical mapping rules  
- Update KSI rules if needed  
- Recompute baseline schema hash  

## 7.2 Constraint Drift Remediation
- Validate PK/FK integrity  
- Rebuild or adjust indexes  
- Update constraint expectations  

## 7.3 Cardinality Drift Remediation
- Investigate missing or duplicate records  
- Validate upstream ingestion pipelines  
- Restore expected cardinality  

## 7.4 Semantics Drift Remediation
- Update canonical field definitions  
- Update ClaimObject normalization logic  
- Update KSI rules if semantics changed  

## 7.5 Query Plan Drift Remediation
- Review vendor optimizer changes  
- Adjust indexes or query hints  
- Update canonical query translation  

---

# 8.0 Summary

Database Adapter drift detection is a **core requirement** for UIAO-Core. It ensures:

- Deterministic extraction  
- Stable canonical mappings  
- Reliable KSI validation  
- Accurate evidence generation  
- Early detection of breaking changes  

By implementing the drift detection methods, DriftReport schema, severity thresholds, and remediation workflows defined in this document, vendors and implementers ensure that UIAO remains **trustworthy, auditable, and drift‑resistant** across all database integrations.
