---
id: metadata-quality-remediation-diagram
title: Metadata Quality Remediation Workflow Diagram
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Quality Remediation Workflow Diagram

## Visual Flow from Drift Detection to SLA Resolution

---

## Mermaid Diagram

```mermaid
flowchart TD
    A[Drift Detected] --> B[Owner Acknowledgment]
    B --> C[Metadata Review]
    C --> D{Type of Drift?}
    D -->|Structural| E[Fix Required Fields]
    D -->|Referential| F[Fix IDs & References]
    D -->|Ownership| G[Update Owner Metadata]
    D -->|Semantic| H[Correct Status/Classification]
    D -->|Automation| I[Escalate to Maintainers]
    E --> J[Local Validation]
    F --> J
    G --> J
    H --> J
    I --> K[Automation Patch]
    J --> L[Open Remediation PR]
    L --> M[CI Validator]
    M -->|Pass| N[Merge + Resolve]
    M -->|Fail| C
    N --> O[Dashboard Update]
    O --> P[Governance Verification]
    P --> Q[Close SLA]
```

---

## ASCII Diagram

```
Drift --> Acknowledge --> Review --> Classify
         |-> Structural --> Fix fields
         |-> Referential --> Fix IDs/refs
         |-> Ownership --> Update owner
         |-> Semantic --> Correct status
         |-> Automation --> Escalate

Fix --> Validate --> Remediation PR --> CI --> Merge --> Dashboard --> Governance --> Close SLA
```
