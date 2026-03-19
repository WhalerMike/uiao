# UIAO Architecture Diagram Review (Temporary File)

---

## Diagram 1: UIAO Logic Flow (Data-Driven Architecture)

**Purpose:** Visualize the transition from static docs to the single source of truth.

```mermaid
graph TD
  subgraph Data_Layer [Single Source of Truth - YAML]
    A[data/program.yml] --> D{Jinja2 Engine}
    B[data/roadmap.yml] --> D
    C[data/appendices.yml] --> D
  end
  subgraph Logic_Overlay [UIAO Core Framework]
    D --> E((Identity))
    D --> F((Addressing))
    D --> G((Overlay))
  end
  subgraph Artifact_Generation [Auto-Generated site/]
    E & F & G --> H[Leadership Briefing.md]
    E & F & G --> I[Technical Roadmap.md]
    E & F & G --> J[C1 IPAM Plan.md]
  end
  style Data_Layer fill:#f9f,stroke:#333,stroke-width:2px
  style Logic_Overlay fill:#bbf,stroke:#333,stroke-width:2px,color:#fff
  style Artifact_Generation fill:#dfd,stroke:#333,stroke-width:1px
```

---

## Diagram 2: High-Level Core Stack Integration

**Purpose:** Maps specific vendors (Catalyst, INR, Infoblox) to the UIAO pillars.

```mermaid
graph LR
    subgraph Identity_Layer [Identity Layer]
        INR[Microsoft INR]
    end

    subgraph Addressing_Layer [Addressing Layer]
        IB[Infoblox IPAM/DNS]
    end

    subgraph Overlay_Layer [Overlay Layer]
        CAT[Cisco Catalyst SD-WAN]
    end

    INR -- "Policy Attribution" --> CAT
    IB -- "C1 IPAM Sync" --> CAT
    CAT -- "D1 Telemetry" --> IB

    style Identity_Layer fill:#f0f7ff,stroke:#0078d4
    style Addressing_Layer fill:#f0fff4,stroke:#008762
    style Overlay_Layer fill:#fff5f0,stroke:#e34326
```

---

## Diagram 3: Identity-to-Packet Lifecycle (Sequence)

**Purpose:** Tracks how an identity-authenticated user is assigned an IP and routed via the SD-WAN overlay.

```mermaid
sequenceDiagram
  autonumber
  participant User as Endpoint (INR Authenticated)
  participant IB as Infoblox (C1 IPAM)
  participant SDWAN as Cisco Catalyst SD-WAN
  participant DC as Data Center Resource

  Note over User, IB: Identity-Driven Addressing
  User->>IB: DHCP Request (Identity Metadata Attached)
  IB-->>User: Assign IP via C1 IPAM (Reserved Segment)

  Note over User, SDWAN: Policy Enforcement
  User->>SDWAN: Packet Ingress (Encapsulated)
  SDWAN->>SDWAN: Inspect Identity Tag + Source IP
  SDWAN->>DC: Route via Secure Fabric Overlay

  Note over SDWAN, IB: D1 Telemetry Loop
  SDWAN-->>IB: Export Flow Logs (D1 Telemetry)
```

---

## Diagram 4: Modernization Workstream Roadmap (2026)

**Purpose:** GANTT visualization based on the `project-plans.yml` updates.

```mermaid
gantt
  title UIAO Modernization Timeline (2026)
  dateFormat  YYYY-MM-DD

  section Phase 1: Foundation
  TIC 3.0 Alignment           :done, a1, 2026-01-01, 30d
  Identity Fabric Setup        :active, a2, 2026-02-01, 45d

  section Phase 2: Core Services
  C1 IPAM Integration (Infoblox) :a3, after a2, 60d
  D1 Telemetry (Catalyst)        :a4, after a3, 45d

  section Phase 3: Overlay
  SD-WAN Fabric Expansion        :a5, after a4, 90d
```

---

## Diagram 5: UIAO Conceptual Seven-Layer Model

**Purpose:** Defining the relationship between user identity and the underlay network.

```mermaid
graph TD
    L7["7. Application"]
    L6["6. User Identity (Microsoft INR)"]
    L5["5. Security Policy"]
    L4["4. Addressing Overlay (Infoblox)"]
    L3["3. Unified Fabric (Catalyst SD-WAN)"]
    L2["2. Transport (SD-WAN Underlay)"]
    L1["1. Physical/Cloud"]

    L7 --> L6
    L6 -.-> L5
    L5 ==> L4
    L4 ==> L3
    L3 --> L2
    L2 --> L1

    linkStyle 2,3 stroke-width:4px,fill:none,stroke:blue
```

---

## Diagram 6: State Diagram — Frozen Domain Transition

**Purpose:** Modeling how a legacy, unmanaged network segment is transitioned into a managed UIAO segment.

```mermaid
stateDiagram-v2
  [*] --> Legacy: Discovery
  state Legacy {
    [*] --> Unmanaged
    Unmanaged --> StaticAddressing
  }
  Legacy --> Freezing: Begin C1 IPAM Import
  state Freezing {
    [*] --> DHCP_Migration
    DHCP_Migration --> Policy_Audit
  }
  Freezing --> UIAO_Managed: Fabric Overlay Applied
  state UIAO_Managed {
    [*] --> IdentityEnforced
    IdentityEnforced --> TelemetryActive
  }
  UIAO_Managed --> [*]
```

---

## Diagram 7: YAML Data Schema Relationship (data/)

**Purpose:** ER Diagram showing how the three core YAML files are structured and interlinked.

```mermaid
erDiagram
  PROGRAM_YML {
    string program_vision
    string architecture_philosophy
    list frozen_domains
  }
  ROADMAP_YML {
    list tic3_phases
    list workstreams
  }
  APPENDICES_YML {
    map canon_a_z
    map canon_aa_az
    map canon_ca_cz
  }

  PROGRAM_YML ||--o{ APPENDICES_YML : reference
  ROADMAP_YML ||--o{ APPENDICES_YML : reference
  ROADMAP_YML ||--|{ PROGRAM_YML : supports
```

---

## Diagram 8: C1 IPAM (Infoblox) Deployment Pattern

**Purpose:** Technical architecture for integrating the Addressing layer.

```mermaid
graph LR
    subgraph SD_WAN_Fabric [SD-WAN Fabric]
        EDGE1[Catalyst Edge 1000V]
        EDGE2[Catalyst Edge 8300]
    end

    subgraph Core_Services [Core Services VPC]
        IB_GRID[Infoblox Grid Master]
        IB_CP[Infoblox Cloud Platform]
    end

    subgraph Data_Center [Data Center]
        DC_DHCP[Legacy DHCP]
    end

    EDGE1 -- "DHCP Relay" --> IB_CP
    EDGE2 -- "DHCP Relay" --> IB_CP
    IB_CP <--> IB_GRID
    IB_GRID -. "C1 Migration" .-> DC_DHCP
```

---

## Diagram 9: Component Diagram — scripts/generate.py

**Purpose:** Showing how the Python script interacts with YAML and Jinja2 templates.

```mermaid
graph TD
  subgraph Core_Data ["Core Data"]
    P_YML[program.yml]
    R_YML[roadmap.yml]
    A_YML[appendices.yml]
  end

  GEN[scripts/generate.py]

  subgraph Templates ["Templates folder"]
    PV_J2[program-vision.md.j2]
    TR_J2[tic3-roadmap.md.j2]
  end

  subgraph Generated ["Generated Docs"]
    PV_MD[site/program-vision.md]
    TR_MD[site/tic3-roadmap.md]
  end

  P_YML --> GEN
  R_YML --> GEN
  A_YML --> GEN
  GEN --> PV_J2
  GEN --> TR_J2
  PV_J2 --> PV_MD
  TR_J2 --> TR_MD
```

---

## Diagram 10: Appendix Canon Family Mapping (Class Diagram)

**Purpose:** Categorizing the 104-appendix canon defined in `appendices.yml`.

```mermaid
classDiagram
  class Appendix_Canon {
    +104 Total Appendices
    +Single Source of Truth
  }
  class Family_A_Z {
    +Primary Strategy
    +Example: A (Vision)
  }
  class Family_AA_AZ {
    +Technical Standards
    +Example: AB (Addressing)
  }
  class Family_BA_BZ {
    +Operational Procedures
  }
  class Family_CA_CZ {
    +Vendor Specifics
    +Example: C1 (Infoblox IPAM)
  }

  Appendix_Canon <|-- Family_A_Z
  Appendix_Canon <|-- Family_AA_AZ
  Appendix_Canon <|-- Family_BA_BZ
  Appendix_Canon <|-- Family_CA_CZ
```

---

## Diagram 11: D1 Telemetry Flow (Catalyst to Infoblox)

**Purpose:** Detailed flow of the operational telemetry loop.

```mermaid
graph TD
  subgraph Fabric_Overlay
    A[Catalyst Edge] -->|IPFIX/Flow| B(SD-WAN Manager)
  end
  subgraph Operations
    B -->|API Export| C[D1 Telemetry Collector]
    C -->|Context Enrichment| D[Infoblox Grid]
    D -->|IPAM Alert| E((SOC/NOC))
  end
  style A fill:#f96
  style D fill:#6f9
```

---

## Diagram 12: GitHub Actions Workflow (Doc-as-Code)

**Purpose:** Visualizing the CI/CD pipeline that builds the documentation.

```mermaid
sequenceDiagram
  participant User
  participant Git as GitHub Repo (main)
  participant GA as GitHub Actions
  participant Py as scripts/generate.py

  User->>Git: Push changes (data/program.yml)
  Git->>GA: Trigger 'generate-docs' workflow
  GA->>GA: Checkout code & setup Python
  GA->>Py: Run generation script
  Py->>GA: Documentation generated (site/*.md)
  GA->>Git: Commit updated documents
  Git-->>User: Deployment successful
```
