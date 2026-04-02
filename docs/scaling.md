---
title: "Scaling"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Regional Scaling Model

A primary goal of the **uiao-core** project is to eliminate "Configuration Drift." We achieve this by using immutable patterns defined in the **Appendix Canon Library**.

## One Pattern, Every Scale
Whether we are deploying a small regional office or a massive agency datacenter, the core logic (Identity, Addressing, Overlay, Telemetry) remains the same.

![Scaling Model](./images/regional_scale.png)

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
graph TD
  Library[(Appendix Canon<br/>Single Source of Truth)]
  subgraph Core[Pattern A: Standard Naming & Identity]
      direction LR
      A1[Appendix A-01]
      A2[Appendix BA-01]
  end
  Library --> Core
  subgraph Scale
      direction LR
      subgraph SmallBranch[1. Regional Office<br/>(Small Scale)]
          S1[2 Edge Nodes]
          S2[1 ISE Policy]
      end
      subgraph RegionalHub[2. Regional Hub<br/>(Medium Scale)]
          RM1[10 Edge Nodes]
          RM2[4 Fabric Nodes]
          RM3[2 ISE Policies]
      end
      subgraph Datacenter[3. Agency DC<br/>(Large Scale)]
          L1[50 Edge Nodes]
          L2[12 Fabric Nodes]
          L3[8 ISE Policies]
          L4[Full Telemetry Stack]
      end
  end
  Core ==>|Apply Same Pattern| SmallBranch
  Core ==>|Apply Same Pattern| RegionalHub
  Core ==>|Apply Same Pattern| Datacenter
  classDef pattern fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
  class Core pattern;
  classDef scale fill:#f1f8e9,stroke:#558b2f;
  class SmallBranch,RegionalHub,Datacenter scale;
```

</details>

</details>

</details>

</details>

</details>

</details>

</details>

### The Blueprint Approach
By referencing **Pattern A (Appendix A-01 / BA-01)**, we ensure that a security policy defined in the head-end is perfectly replicated at the edge switch, eliminating configuration drift across all deployment scales.