---
id: metadata-lifecycle-diagram
title: Metadata Lifecycle Diagram
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Lifecycle Diagram

## End-to-End Flow from Document Creation to Schema Evolution

---

## Mermaid Diagram

```mermaid
flowchart TD
    A[Create Document] --> B[Add Metadata]
    B --> C[CI Validation]
    C -->|Pass| D[Publish]
    C -->|Fail| B
    D --> E[Drift Detection]
    E -->|No Drift| D
    E -->|Drift Found| F[Drift Issue Created]
    F --> G[Owner Acknowledgment]
    G --> H[Remediation PR]
    H --> I[CI Validation]
    I -->|Pass| J[Merge + Resolve]
    I -->|Fail| H
    J --> K[Dashboard Update]
    K --> L[Quarterly Review]
    L --> M[Schema Evolution]
    M --> B
```

---

## ASCII Diagram

```
Create --> Metadata --> CI --> Publish
                    |
                    Fail --> back to Metadata

Publish --> Drift Detection --> No Drift --> Publish
                            |
                            Drift --> Issue --> Acknowledge --> Remediate --> CI --> Merge --> Dashboard --> Quarterly Review --> Schema Evolution --> Metadata
```
