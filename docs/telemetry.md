---
title: "Telemetry"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Visibility & Telemetry Control Plane

Modernization requires more than just connectivity; it requires a continuous feedback loop between infrastructure, security, and operations.

## Closed-Loop Integration
This visualization shows how real-time signals inform policy and security decisions.

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

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
graph TB
  subgraph "Telemetry Control Plane (Visibility)"
    direction TB
    S[Splunk / Azure Monitor]
    IB[Infoblox Ecosystem]
  end
  subgraph "Identity Plane"
    ID[Azure AD / Cisco ISE]
  end
  subgraph "Network & Addressing Plane"
    IP[IPAM Scopes]
    SD[Cisco Catalyst Center]
  end
  ID -- "Auth Events" --> S
  IP -- "Lease Data" --> S
  SD -- "Flow Logs / SNMP" --> S
  S -- "Threat Alerts" --> ID
  S -- "Performance Signals" --> SD
  IB -- "DNS Analytics" --> S
  classDef telemetry fill:#f1f8e9,stroke:#558b2f,stroke-width:2px;
  classDef feedback stroke-dasharray: 5 5;
  class S,IB telemetry;
```

</details>

</details>

</details>

</details>

</details>

</details>

</details>

</details>

### Telemetry Sources
The agency utilizes the following telemetry anchors to maintain the "Modernization Atlas" accuracy:
- **Splunk:** Primary SIEM for security events and performance analytics.
- **Azure Monitor:** Cloud-native metrics for Azure AD and hybrid workloads.
- **Infoblox Ecosystem:** DNS analytics and IPAM change tracking.

All telemetry keys are normalized in `generate.py` to ensure consistent data ingestion.