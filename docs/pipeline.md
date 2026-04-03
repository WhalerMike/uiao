---
title: "Pipeline"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Generation Pipeline

> **ADR-0005 Rationale:** Add a dedicated pipeline documentation page with live
> Mermaid rendering to give agency reviewers an interactive, visual overview of
> the UIAO document-compilation workflow. Material for MkDocs + `pymdownx.superfences`
> handles client-side Mermaid rendering with zero extra plugins.

## Pipeline Overview

The UIAO Document Compiler transforms canon YAML data through a multi-stage
pipeline, producing compliance-ready artifacts in Markdown, DOCX, PDF, PPTX,
and OSCAL JSON formats.

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

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
    A["Canon YAML\ndata/"] -->|validate| B["Schema\nValidation"]
    B -->|normalize| C["Artifact\nNormalization"]
    C -->|compile| D{"Generator\nRouter"}
    D -->|docs| E["Markdown\ndocs/"]
    D -->|rich_docx| F["DOCX\nexports/docx/"]
    D -->|oscal| G["OSCAL JSON\nexports/oscal/"]
    D -->|ssp| H["SSP JSON\nexports/oscal/"]
    D -->|charts| I["PNG Charts\nassets/images/"]
    D -->|pptx| J["PPTX\nexports/pptx/"]
    E -->|mkdocs build| K["Live Site\nGitHub Pages"]

    style A fill:#1a237e,color:#fff
    style B fill:#283593,color:#fff
    style C fill:#283593,color:#fff
    style D fill:#0d47a1,color:#fff
    style E fill:#1b5e20,color:#fff
    style F fill:#1b5e20,color:#fff
    style G fill:#1b5e20,color:#fff
    style H fill:#1b5e20,color:#fff
    style I fill:#1b5e20,color:#fff
    style J fill:#1b5e20,color:#fff
    style K fill:#b71c1c,color:#fff
```

</details>

</details>

</details>

</details>

</details>

</details>

</details>

</details>

</details>

## Stage Details

### 1. Schema Validation

All canon YAML files in `data/` are validated against JSON schemas in
`schemas/`. This ensures structural correctness before any generation begins.

### 2. Artifact Normalization

Data is merged, cross-referenced, and ordered into canonical form. Control
plane mappings, compliance matrices, and KSI categories are resolved.

### 3. Generator Router

The Typer CLI (`uiao generate`) dispatches to the appropriate generator based
on the requested output format:

| Generator | Output | Location |
|-----------|--------|----------|
| `docs` | Jinja2 Markdown | `docs/` |
| `rich_docx` | Styled DOCX | `exports/docx/` |
| `oscal` | Component Definition JSON | `exports/oscal/` |
| `ssp` | SSP Skeleton JSON | `exports/oscal/` |
| `charts` | Compliance PNG charts | `assets/images/` |
| `pptx` | Leadership briefing PPTX | `exports/pptx/` |

### 4. MkDocs Publish

Generated Markdown and exported artifacts are served via MkDocs Material on
GitHub Pages, providing an always-current agency-facing dashboard.

## Zero-Trust Architecture Flow

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

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TD
    subgraph Identity["Identity Plane"]
        AZ["Azure AD\nEntra ID"] --> COND["Conditional\nAccess"]
        COND --> MFA["MFA +\nDevice Trust"]
    end

    subgraph Addressing["Addressing Plane"]
        DNS["Infoblox\nDDI"] --> IPAM["IP Address\nManagement"]
    end

    subgraph Overlay["Overlay Plane"]
        SD["SD-WAN /\nZTNA"] --> SEG["Micro-\nSegmentation"]
    end

    subgraph Telemetry["Telemetry Plane"]
        SPL["Splunk /\nAzure Monitor"] --> KSI["KSI\nDashboard"]
    end

    MFA --> SD
    IPAM --> SD
    SEG --> SPL
    KSI -->|evidence| OSCAL["OSCAL\nArtifacts"]

    style Identity fill:#1565c0,color:#fff
    style Addressing fill:#2e7d32,color:#fff
    style Overlay fill:#6a1b9a,color:#fff
    style Telemetry fill:#e65100,color:#fff
    style OSCAL fill:#b71c1c,color:#fff
```

</details>

</details>

</details>

</details>

</details>

</details>

</details>

</details>

</details>

---

*This page is auto-generated as part of the UIAO Document Compiler pipeline.*
