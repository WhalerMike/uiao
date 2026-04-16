---
uiao_id: UIAO_ACCESS_01
title: Access and Downloads
status: Current
owner: Governance Board
date: 2026-04-07
---

# Access & Downloads

This page is the canonical entry point for accessing UIAO documentation in different formats
and understanding export workflows.

## Online Canon

- **Primary site:** <https://whalermike.github.io/uiao-docs/>
- **Canon Overview:** [/canon/](canon/index.md)
- **Corpus Status Dashboard:** [/canon/corpus-status-dashboard/](canon/corpus-status-dashboard.md)
- **ADR Index:** [/adr/](adr/index.md)

## Downloads

### Canon and Appendices

- **Full Canon (HTML export)** -- _TBD: link to zipped site export_
- **Appendix A -- Adapter Plane (PDF)** -- _TBD: link_
- **Appendix B -- Truth Fabric (PDF)** -- _TBD: link_
- **Appendix C -- Drift Fabric (PDF)** -- _TBD: link_
- **Appendix D -- Evidence Fabric (PDF)** -- _TBD: link_
- **Appendix E -- Governance Plane (PDF)** -- _TBD: link_

### Diagrams

- **Cross-Fabric Governance Map (SVG)** -- `docs/images/cross-fabric-map.svg`

> For PDFs, use the browser Print function on any page. The SVG remains the canonical,
> clickable source on the live site.

## Export Workflows

### Site Export (HTML)

1. Run MkDocs build:

   ```bash
   mkdocs build
   ```

2. Package site:

   ```bash
   cd site
   zip -r ../uiao-docs-site.zip .
   ```

3. Publish `uiao-docs-site.zip` to your chosen distribution channel and update links above.

### PDF Bundles

Use the automated export workflow at
[Actions > document-export](https://github.com/WhalerMike/uiao-docs/actions/workflows/document-export.yml)
or your preferred tool (Pandoc, browser Print to PDF).

Ensure:

- Status badges are visible
- Provenance footer is included
- Cross-Fabric Map is embedded with caption

Store PDFs and update links in the Downloads section above when available.

## Contributor Workflows

- **Contributing Guide:** [contributing.md](contributing.md)
- **PR Template:** [.github/PULL_REQUEST_TEMPLATE.md](https://github.com/WhalerMike/uiao-docs/blob/main/.github/PULL_REQUEST_TEMPLATE.md)

All changes must pass:

- Frontmatter validation CI (`validate-uiao-frontmatter.yml`)
- Corpus index update on merge (`update-corpus-index.yml`)
- ADR metadata contract for ADR files (see [ADR Metadata Contract](meta/adr-metadata-contract.md))

## Governance

Metadata contracts:

- **ADR metadata:** [ADR Metadata Contract](meta/adr-metadata-contract.md)
- **ADR process:** [ADR-000 ADR Process and Lifecycle](adr/adr-000-adr-process.md)

Contact the Governance Board for questions about access, exports, or governance.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
