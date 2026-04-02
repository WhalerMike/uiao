---
title: "Logic"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Pipeline Logic & Data Normalization

The **uiao-core** repository functions as a compiler for infrastructure. It translates high-level intent defined in YAML into vendor-specific configurations and documentation.

## The Data Pipeline
How `program.yml` becomes a deployed configuration:

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
  YAML[(program.yml)] --> Python[generate.py Logic]
  subgraph "Logic Processing"
    Python --> RegEx[Hyphen-to-Underscore Translation]
    RegEx --> Jinja[Jinja2 Templates]
  end
  Jinja -->|Output 1| Cisco[Cisco CLI / API Config]
  Jinja -->|Output 2| Blox[Infoblox WAPI Calls]
  Jinja -->|Output 3| Azure[Azure VNet/NSG Rules]
  style YAML fill:#dfd
  style Jinja fill:#ffd
```

</details>

</details>

## The Normalization Engine

The `generate.py` script performs a critical translation step. YAML keys in the canon use hyphens (e.g., `A-01`, `site-location`) for readability, but Jinja2 template variables cannot contain hyphens. The `normalize_key()` filter converts all hyphens to underscores at load time.

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TD
  A[(program.yml / appendices.yml)] -->|Key: 'site-location'| B[generate.py Load]
  B --> C{Normalization Filter}
  C -->|Regex: s/-/_/g| D[Key: 'site_location']
  subgraph "Jinja2 Context"
    D --> E{Render Template}
    F[template.j2] --> E
  end
  E -->|Success| G[site/config.txt]
  E -->|Failure: Hyphen detected| H[Jinja2 UndefinedError]
  style C fill:#fff3e0,stroke:#ef6c00
  style D fill:#e8f5e9,stroke:#2e7b32
```

</details>

</details>

### Key Pipeline Steps

1. **Load** — All YAML files from `data/` are read into a unified context dictionary.
2. **Normalize** — Hyphenated keys are converted to underscore format for Jinja2 safety.
3. **Render** — Each `.j2` template is rendered with the full context, producing Markdown files in `docs/`.
4. **Build** — MkDocs compiles the Markdown into a static site with Material theme.
5. **Deploy** — GitHub Actions pushes the built site to GitHub Pages.

### Schema Validation
Before any rendering occurs, the CI/CD pipeline validates `appendices.yml` against `schema.json`:

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

![UIAO Architecture Diagram](../assets/images/mermaid/unified_arch.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TD
  A[(appendices.yml)] --> B[Git Commit / PR]
  subgraph "CI/CD Pipeline (GitHub Actions)"
      B --> C[Fetch PR Data]
      D[[Load schema.json]] --> E{Validate Data<br/>against Schema}
      C --> E
      E -->|Pass| F[Pipeline Success]
      E -->|Fail| G[Pipeline Failure]
  end
  G -->|Alert| H[Developer Check<br/>Required Fields / Formats]
  F --> I[Execute generate.py]
  I --> J[Publish Modernization Atlas]
  style E fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
  style G fill:#ffcdd2,stroke:#c62828
  style F fill:#c8e6c9,stroke:#2e7b32
```

</details>

</details>