---
title: "Appendices"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Appendix Canon Library

This library contains the 104 standardized technical and operational patterns (A-CZ) used across the agency's infrastructure.

## Library Overview
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
graph LR
  subgraph "Data Source: appendices.yml"
    A[Group A-Z: Core Standards]
    B[Group AA-AZ: Network Patterns]
    C[Group BA-BZ: Security Protocols]
    D[Group CA-CZ: Operational Procedures]
  end
  subgraph "Processing: generate.py"
    Logic{Jinja2 Renderer}
    Logic -->|Lookup ID| A
    Logic -->|Lookup ID| B
    Logic -->|Lookup ID| C
    Logic -->|Lookup ID| D
  end
  subgraph "Output: site/ Documentation"
    Doc1[Appendix A: Global Naming]
    Doc2[Appendix AZ: SD-WAN Edge]
    Doc3[Appendix CZ: Decommissioning]
  end
  Logic --> Doc1
  Logic --> Doc2
  Logic --> Doc3
  style Logic fill:#f9f,stroke:#333,stroke-width:2px
  style A,B,C,D fill:#e1f5fe,stroke:#01579b
```

</details>

</details>

</details>

## Table of Contents




### Core Standards (A-Z)

| ID | Title | Status |
| :--- | :--- | :--- |



| A_01 | Global Naming Convention | Approved |



| A_02 | Global IP Addressing Standard | Approved |



| A_03 | Global VLAN Assignment Standard | Approved |





### Network Patterns (AA-AZ)

| ID | Title | Status |
| :--- | :--- | :--- |



| A_01 | Global Naming Convention | Approved |



| A_02 | Global IP Addressing Standard | Approved |



| A_03 | Global VLAN Assignment Standard | Approved |





### Security Protocols (BA-BZ)

| ID | Title | Status |
| :--- | :--- | :--- |











### Operational Procedures (CA-CZ)

| ID | Title | Status |
| :--- | :--- | :--- |












---



## <a name="a_01"></a> [A_01] Global Naming Convention

**Status:** Approved
**Owner:** Infrastructure Architecture Board
**Last Updated:** 2026-03-21

### Description
Establishes a deterministic, function-first nomenclature for all physical and logical assets. This standard ensures that every device hostname, interface label, and VLAN name contains enough context for rapid identification and troubleshooting without requiring a CMDB lookup.

### Configuration Standard
```yaml
naming_logic:
    format: "{region}-{site}-{function}-{index}"
    patterns:
      hostname: "^[a-z]{3}-[a-z0-9]{4}-(sw|rtr|srv|fw)-[0-9]{2}$"
      interface: "{media}{slot}/{port}.{subinterface}"
      vlan_name: "VL-{id}-{description}"
    site_codes:
      hq: "BALT"
      regional_hub: "RDC1"
      branch: "BR01"
    role_codes:
      core_switch: "csw"
      dist_switch: "dsw"
      access_switch: "asw"
      border_router: "brt"
      firewall: "fwa"

```

**Source Document:** `standards/IA-Naming-v4.2.pdf`

[Back to Top](#)

---

## <a name="a_02"></a> [A_02] Global IP Addressing Standard

**Status:** Approved
**Owner:** Network Operations (NetOps)
**Last Updated:** 2026-03-21

### Description
Defines the hierarchical IPAM allocation strategy for RFC 1918 space. This standard ensures maximum route summarization efficiency and provides a deterministic subnetting model that can be automated via Infoblox.

### Configuration Standard
```yaml
ipam_hierarchy:
    global_prefix: "10.0.0.0/8"
    site_allocation: "/16"
    subnet_masks:
      management: "/24"
      vmotion: "/24"
      vtep_overlay: "/22"
      user_data: "/23"
      voice_voip: "/24"
    reserved_offsets:
      gateway: ".1"
      hsrp_vip: ".254"
      static_range: ".10-.50"
      dhcp_pool: ".51-.250"

```

**Source Document:** `standards/IA-IPAM-Strategy-v2.1.pdf`

[Back to Top](#)

---

## <a name="a_03"></a> [A_03] Global VLAN Assignment Standard

**Status:** Approved
**Owner:** Infrastructure Architecture Board
**Last Updated:** 2026-03-21

### Description
Establishes deterministic VLAN ID ranges to maintain configuration consistency across the agency's entire switching fabric. Prevents VLAN ID collision between sites and simplifies trunk policy management.

### Configuration Standard
```yaml
vlan_matrix:
    system_reserved: "1, 1002-1005"
    ranges:
      infrastructure_mgmt: "10-99"
      server_farm_dmz: "100-499"
      user_access: "500-899"
      voice_video: "900-999"
      guest_wifi: "1000-1099"
      sd_access_fabric: "2000-2999"
    default_assignments:
      native_vlan: 999
      dead_vlan: 666
      mgmt_vlan: 10

```

**Source Document:** `standards/IA-VLAN-Matrix-v3.0.pdf`

[Back to Top](#)

---

