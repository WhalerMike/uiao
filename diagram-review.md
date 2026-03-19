# UIAO Architecture Diagram Review (Simplified)

---

## 1: UIAO Logic Flow

```mermaid
graph TD
    YAML_Data[YAML Single Source of Truth] --> Jinja2[Jinja2 Engine]
    Jinja2 --> Identity[Identity Pillar]
    Jinja2 --> Addressing[Addressing Pillar]
    Jinja2 --> Overlay[Overlay Pillar]
    Identity --> Docs[Generated Documentation]
    Addressing --> Docs
    Overlay --> Docs
```

---

## 2: High-Level Core Stack

```mermaid
graph LR
    subgraph Identity
        INR[Microsoft INR]
    end
    subgraph Addressing
        IB[Infoblox IPAM]
    end
    subgraph Overlay
        CAT[Cisco Catalyst]
    end
    INR --> CAT
    IB --> CAT
    CAT --> IB
    style Identity fill:#f9f,stroke:#333
    style Addressing fill:#bbf,stroke:#333
    style Overlay fill:#dfd,stroke:#333
```

---

## 3: Identity-to-Packet Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant User as Endpoint
    participant IB as Infoblox
    participant SDWAN as Cisco Catalyst
    participant DC as Data Center
    User->>IB: DHCP Request
    IB-->>User: Assign IP
    User->>SDWAN: Packet Ingress
    SDWAN->>DC: Route via Fabric
    SDWAN-->>IB: Export D1 Telemetry
```

---

## 4: Modernization Roadmap

```mermaid
gantt
    title UIAO Timeline 2026
    dateFormat YYYY-MM-DD
    section Phase 1
    TIC 3.0 Alignment :done, a1, 2026-01-01, 30d
    Identity Setup :active, a2, 2026-02-01, 45d
    section Phase 2
    C1 IPAM Integration :a3, after a2, 60d
    D1 Telemetry :a4, after a3, 45d
```

---

## 5: Conceptual Seven-Layer Model

```mermaid
graph TD
    L7[7. Application] --> L6[6. User Identity]
    L6 --> L5[5. Security Policy]
    L5 --> L4[4. Addressing Overlay]
    L4 --> L3[3. Unified Fabric]
    L3 --> L2[2. Transport Underlay]
    L2 --> L1[1. Physical/Cloud]
```

---

## 6: Frozen Domain Transition

```mermaid
stateDiagram-v2
    [*] --> Legacy
    Legacy --> Freezing
    Freezing --> Managed
    Managed --> [*]
```

---

## 7: Data Schema Relationship

```mermaid
erDiagram
    PROGRAM ||--o{ APPENDICES : references
    ROADMAP ||--o{ APPENDICES : references
    ROADMAP ||--|| PROGRAM : supports
```

---

## 8: C1 IPAM Deployment Pattern

```mermaid
graph LR
    Edge1[Catalyst Edge] --> IB_CP[Infoblox Cloud]
    Edge2[Catalyst Edge] --> IB_CP
    IB_CP --> IB_Grid[Infoblox Grid]
    IB_Grid --> IB_CP
    IB_Grid --> Legacy[Legacy DHCP]
```

---

## 9: Generator Script Flow

```mermaid
graph TD
    YAML[YAML Files] --> Script[generate.py]
    Templates[Jinja2 Templates] --> Script
    Script --> Output[Generated Markdown]
```

---

## 10: Appendix Canon Mapping

```mermaid
classDiagram
    Appendix_Canon <|-- Family_A_Z
    Appendix_Canon <|-- Family_AA_AZ
    Appendix_Canon <|-- Family_BA_BZ
    Appendix_Canon <|-- Family_CA_CZ
```

---

## 11: D1 Telemetry Flow

```mermaid
graph TD
    Edge[Catalyst Edge] --> Manager[SD-WAN Manager]
    Manager --> Collector[Telemetry Collector]
    Collector --> Infoblox[Infoblox IPAM]
    Infoblox --> Alerts[NOC Alerts]
```

---

## 12: GitHub Actions Workflow

```mermaid
sequenceDiagram
    participant Git as GitHub Repo
    participant GA as GitHub Actions
    participant Py as generate.py
    Git->>GA: Trigger on Push
    GA->>Py: Run Script
    Py->>Git: Commit Site Updates
```
