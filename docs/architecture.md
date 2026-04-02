---
title: "Architecture"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Modernization Atlas: Unified Architecture

This document outlines the four-plane model driving the agency's IT transformation. By decoupling identity from physical location, we create a system that is both more secure and more agile.

## Architectural Convergence
The following diagram visualizes the intersection of user identity and network location.

![Unified Architecture](./images/unified_arch.png)

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

```mermaid
graph TD
  subgraph "Identity Plane (The 'Who')"
    A[Azure AD / Cisco ISE] -->|SGT / Identity Tags| D{Policy Engine}
  end
  subgraph "Addressing Plane (The 'Where')"
    B[Infoblox IPAM] -->|IP Scopes / VLANs| D
  end
  subgraph "Overlay Plane (The 'How')"
    D -->|Fabric Assignment| E[Cisco Catalyst Center]
    E -->|VXLAN Encapsulation| F[Edge Switch Port]
  end
  subgraph "Telemetry Control Plane (Observation)"
    G[Splunk / Azure Monitor] -.->|Real-time Feedback| D
    G -.->|Audit Logs| E
  end
  style D fill:#f96,stroke:#333,stroke-width:2px
  style F fill:#bbf,stroke:#333,stroke-width:2px
```

</details>

</details>

</details>

### Core Pillars

* **Identity Plane (The "Who"):** Azure AD and Cisco ISE provide unified identity through Security Group Tags and Conditional Access policies, feeding into the central Policy Engine.
* **Addressing Plane (The "Where"):** Infoblox IPAM delivers automated IP scope and VLAN assignment, eliminating manual spreadsheet tracking.
* **Overlay Plane (The "How"):** Cisco Catalyst Center orchestrates VXLAN fabric assignments, translating policy decisions into edge switch port configurations.
* **Telemetry Control Plane (Observation):** Splunk and Azure Monitor provide real-time feedback loops and audit logging, enabling proactive threat detection and performance optimization.

### Architectural Principles
- Identity-driven routing
- Telemetry-informed decisions
- Cloud-first path selection
- Zero Trust segmentation
- Modular, incremental modernization