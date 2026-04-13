
# UIAO Vendor Technology Stack and Compliance Registry

**Classification:** CUI/FOUO  
**Version:** 1.0  
**Generated:** Auto-compiled from `data/vendor-stack.yml`  

---

## 1. Purpose

This document provides a comprehensive registry of the core technology vendors that comprise the UIAO architecture. It serves three critical functions within the Documentation-as-Code pipeline: it tracks each vendor's FedRAMP authorization status, maps vendor capabilities to NIST 800-53 Rev 5 controls, and monitors compliance with active CISA directives including Binding Operational Directives and Emergency Directives.

Unlike traditional vendor documentation maintained in static Word files or spreadsheets, this registry is machine-generated from structured YAML data stored in the repository. When a vendor releases a critical patch, updates its FedRAMP certification, or when CISA issues a new directive, a single update to `data/vendor-stack.yml` automatically regenerates this document, the FedRAMP Crosswalk, and all downstream compliance artifacts.

---

## 2. How This Document Works

The vendor stack document is produced through the UIAO Document Compiler pipeline, which operates as follows:

1. **Data Layer:** The structured vendor data resides in `data/vendor-stack.yml`. Each vendor entry includes its product name, UIAO pillar mapping, FedRAMP certification class, required software versions, applicable NIST controls, KSI category mapping, and any active CISA directive compliance notes.

2. **Template Layer:** This Jinja2 template (`templates/vendor_stack_v1.0.md.j2`) defines the narrative structure and formatting. It uses Jinja2 loops and conditionals to iterate over the vendor entries and render them into readable Markdown.

3. **Generation Engine:** The `scripts/generate_docs.py` Python script loads the canon YAML and all `data/*.yml` files, merges them into a unified context dictionary, and passes that context to each Jinja2 template. The template engine replaces variable placeholders with actual data values.

4. **CI/CD Pipeline:** On every push to the `main` branch, a GitHub Actions workflow (`.github/workflows/docs.yml`) triggers the generation script. The output is written to both `docs/` and `site/` directories, then committed back to the repository automatically.

5. **Website Delivery:** The GitHub Pages site at `https://whalermike.github.io/uiao-core/` reads the generated Markdown from the `site/` directory and renders it through the USWDS-styled Document Compiler interface, where it can be viewed inline or downloaded in Markdown, Word, PDF, or HTML formats.

---

## 3. Core Vendor Registry

The UIAO architecture integrates five primary technology vendors, each mapped to a specific architectural pillar. Under FedRAMP 20x (2026 Consolidated Rules), all vendors are classified using the new Class-based system, where Class C corresponds to the legacy Moderate baseline.

| Provider | Product | UIAO Pillar | FedRAMP Class | Status |
| :--- | :--- | :--- | :--- | :--- |




---

## 4. External Security Baselines

The UIAO architecture integrates with CISA's Secure Cloud Business Applications (SCuBA) project to provide automated compliance validation and continuous reporting as required by BOD 25-01.



---

## 5. Active CISA Directives

The following Binding Operational Directives (BODs) and Emergency Directives (EDs) are actively tracked in this repository. Compliance status is updated in `data/vendor-stack.yml` and reflected automatically in all generated documents.

| Directive | Name | Status | Affected Vendor |
| :--- | :--- | :--- | :--- |




---

## 6. Maintaining This Document

This document is automatically regenerated whenever changes are pushed to the `main` branch. To update vendor information:

1. Edit `data/vendor-stack.yml` with the new vendor version, directive status, or certification update.
2. Commit and push to `main`.
3. The GitHub Actions workflow will regenerate all documents, including this one.
4. The updated document will appear on the UIAO-Core website within minutes.

This approach ensures that the vendor compliance registry is never stale, always version-controlled, and permanently auditable through Git history.