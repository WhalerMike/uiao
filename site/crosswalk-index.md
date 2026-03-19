# UIAO Crosswalk Index

*Unified Cross-Reference Matrix -- Version 1.0 (2026-03)*

Single authoritative cross-reference matrix linking all UIAO components

---

## Capabilities

- Traceability

- Dependency mapping

- Impact analysis

- Canonical navigation

- Future expansion


---

## Plane Crosswalk Matrix

| Plane | Control Plane Spec | Architecture Diagram | Project Plans | Canon Volumes | Modernization Appendix |
|-------|-------------------|---------------------|---------------|---------------|----------------------|

| **Identity** | `IdentityControlPlane.md` | Identity Control Plane Architecture.png | A1_Identity_ProjectPlan.md | A-M, AA-AM | Appendix A |

| **Network** | `NetworkControlPlane.md` | Network Control Plane.png | B1_Network_ProjectPlan.md, B1_SD-WAN_ProjectPlan.md | A-M, AN-AZ | Appendix B |

| **Addressing / IPAM** | `AddressingControlPlane.md` | (covered within Network and Identity diagrams) | C1_Addressing_ProjectPlan.md, C1_IPAM_ProjectPlan.md | CA-CM, CN-CZ | Appendix C |

| **Telemetry** | `TelemetryControlPlane.md` | Telemetry Signal Flow.png | D1_Telemetry_ProjectPlan.md | DA-DM, DN-DZ | Appendix D |

| **Endpoint** | `EndpointControlPlane.md` | (covered within Five-Plane Architecture) |  | EA-EM, EN-EZ | (future) |

| **Security** | `SecurityControlPlane.md` | (implicit across all diagrams) |  | N-Z | (future) |

| **Unified Architecture** | `03_Unified_Architecture.md` | UIAO Five-Plane Architecture.png |  | All | Appendix E (TIC3) |


---

## Plane-to-Diagram Mapping


### Identity

- Identity Control Plane Architecture.png

- Monitoring Domains Map.png

- UIAO Five-Plane Architecture.png



### Network

- Network Control Plane.png

- Server Operations Stack.png

- UIAO Five-Plane Architecture.png



### Addressing / IPAM

- Network Control Plane.png

- Identity Control Plane Architecture.png

- UIAO Five-Plane Architecture.png



### Telemetry

- Telemetry Signal Flow.png

- Monitoring Domains Map.png

- UIAO Five-Plane Architecture.png



### Endpoint

- UIAO Five-Plane Architecture.png



### Security

- Network Control Plane.png

- Identity Control Plane Architecture.png

- Telemetry Signal Flow.png

- UIAO Five-Plane Architecture.png



### Unified Architecture

- UIAO Five-Plane Architecture.png



---

## Cross-Plane Dependencies


### identity <-> network
Identity depends on network reachability; Network depends on identity for segmentation and policy


### network <-> addressing
Addressing is a sub-domain of network; IPAM drives routing, segmentation, and telemetry


### telemetry <-> identity <-> network <-> addressing <-> endpoint <-> security
Telemetry consumes signals from all planes; Telemetry informs modernization sequencing


### security <-> identity <-> network <-> addressing <-> telemetry <-> endpoint
Security overlays every plane; Security is a cross-cutting concern


### endpoint <-> identity <-> network
Endpoints authenticate via identity; Endpoints connect via network


---

## Canon Expansion Rules

1. Every new plane must include a control plane spec, diagram, project plan, canon volume coverage, and appendix mapping

2. Every new diagram must be added to 02_ArchitectureDiagrams (PNG) and 03_Diagrams (DRAWIO)

3. Every new appendix must map to a plane, modernization track, and canon volume


---

## Directory Structure (v4.0)

### Principles

- Deterministic

- Plane-aligned

- Canon-aligned

- Future-proof

- Fully modular and infinitely expandable


### Directories

| Directory | Purpose |
|-----------|--------|

| `00_Core` | Authoritative architectural specifications and control plane definitions |

| `01_Canon` | Publication-ready doctrine and executive-level artifacts |

| `01_ProjectPlans` | Modernization workstreams and plane-specific project plans |

| `02_Appendices` | Canonical appendices (00_Canon_Volumes) and individual expansions |

| `03_Appendices` | Modernization-specific appendices (A-E) |

| `02_ArchitectureDiagrams` | Rendered architecture diagrams (PNG) and markdown placeholders |

| `03_Diagrams` | Editable drawio source files |

| `04_Indexes` | Directory indexes, crosswalks, and repository metadata |

| `04_Templates` | Reusable templates for future volumes and documents |

| `05_Assets` | Images, diagrams, and placeholders for publication |

| `05_Reference` | External reference documents |

| `06_Drafts` | Sandbox for early drafts and experimental content |

| `OldDocs` | Full provenance archive of pre-canonical files |

| `Fix` | Reserved for repair operations and temporary staging |


### Placement Rules

1. No files in root; all files must live in a subdirectory

2. Plane specs always live in 00_Core

3. Canon volumes always live in 01_Canon

4. PNG diagrams go to 02_ArchitectureDiagrams; drawio to 03_Diagrams

5. Canon volumes go to 02_Appendices/00_Canon_Volumes; modernization appendices to 03_Appendices

6. All legacy files remain in OldDocs until explicitly retired


---

*Generated from UIAO data layer*