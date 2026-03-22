---
title: "UIAO Seven-Layer Model"
version: "1.0"
classification: "CUI/FOUO"
---

# The UIAO Seven-Layer Model

This model defines the architectural stack for the modernization efforts at Unified Identity-Addressing-Overlay Architecture. Each layer represents a functional domain, and the three UIAO pillars (Identity, Addressing, Overlay) are highlighted to show where vendor-specific integration occurs.

```mermaid
graph TD
    %% Define CSS-like classes for the UIAO Pillars
    classDef identity fill:#f9f,stroke:#333,stroke-width:2px;
    classDef addressing fill:#bbf,stroke:#333,stroke-width:2px;
    classDef overlay fill:#dfd,stroke:#333,stroke-width:2px;
    classDef default_layer fill:#fff,stroke:#333,stroke-width:1px;

    %% Generate Layer Nodes
    
    L7["7. Application"]:::default_layer
    
    L6["6. User Identity (Microsoft INR)"]:::identity
    
    L5["5. Security Policy"]:::default_layer
    
    L4["4. Addressing Overlay (Infoblox)"]:::addressing
    
    L3["3. Unified Fabric (Cisco Catalyst SD-WAN)"]:::overlay
    
    L2["2. Transport Underlay"]:::default_layer
    
    L1["1. Physical/Cloud"]:::default_layer
    

    %% Generate Sequential Connections (7 -> 6 -> ... -> 1)
    L7 --> L6
    L6 --> L5
    L5 --> L4
    L4 --> L3
    L3 --> L2
    L2 --> L1
```

---

## Layer Descriptions


### Layer 7: Application


Business logic and user interface



### Layer 6: User Identity

**Vendor:** Microsoft INR | **Pillar:** Identity




### Layer 5: Security Policy


Policy enforcement and trust boundaries



### Layer 4: Addressing Overlay

**Vendor:** Infoblox | **Pillar:** Addressing




### Layer 3: Unified Fabric

**Vendor:** Cisco Catalyst SD-WAN | **Pillar:** Overlay




### Layer 2: Transport Underlay


Physical and Cloud ISP transport



### Layer 1: Physical/Cloud


Hardware and Hyperscale substrates




---

*End of Seven-Layer Model v1.0*