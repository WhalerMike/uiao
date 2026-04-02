---
title: "Comparison"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Legacy vs. Modernized Infrastructure

To move at the speed of the agency's mission, we must transition away from manual, ticket-based workflows to an automated, policy-driven model.

## The Transformation
The diagram below contrasts our current "Siloed" state with the "Unified" model implemented by the uiao-core project.

![Legacy vs Modernized](./images/legacy_vs_modern.png)

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

```mermaid
graph TB
  subgraph "LEGACY STATE (Manual, Siloed, Fragile)"
      L_ID[Siloed Identity<br/>AD/On-Prem]
      L_AM[Manual IPAM<br/>Excel Spreadsheets]
      L_OP[Static Overlay<br/>Fixed VLANs/Complex ACLs]
      L_TM[Fragmented Telemetry<br/>Reactive/Manual Logs]
      L_ID -.-> L_AM
      L_AM -.-> L_OP
      L_OP -.-> L_TM
      classDef legacy fill:#ffcdd2,stroke:#c62828,stroke-width:2px;
      class L_ID,L_AM,L_OP,L_TM legacy;
  end
  ModernizationAtlas[Modernization Atlas<br/>(uiao-core)] -->|Automation| uiao_model
  subgraph "MODERNIZED STATE (uiao-core Unified Model)"
      direction TB
      subgraph Planes
          direction LR
          ID[Identity Plane<br/>Unified Azure/ISE]
          AM[Addressing Plane<br/>Automated Infoblox]
          OP[Overlay Plane<br/>Programmable SDA/SDWAN]
      end
      TM[Telemetry Plane<br/>Proactive/Closed-Loop]
      ID <--> TM
      AM <--> TM
      OP <--> TM
      classDef modernized fill:#c8e6c9,stroke:#2e7b32,stroke-width:2px;
      class ID,AM,OP,TM modernized;
  end
  style ModernizationAtlas fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
```

</details>

</details>

### Key Value Transitions
| Capability | Legacy State | Modernized (uiao-core) |
| :--- | :--- | :--- |
| **Provisioning** | Manual (Hours/Days) | Automated (Minutes) |
| **Policy** | Static (VLAN-based) | Dynamic (Identity-based) |
| **Visibility** | Reactive (Logs) | Proactive (Telemetry Loops) |
| **Scaling** | Bespoke / Per-site | Standardized / Pattern-based |