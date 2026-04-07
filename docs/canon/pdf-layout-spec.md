---
title: "UIAO PDF Layout Specification"
status: ACTIVE
version: "1.0"
last_updated: "2026-04-07"
---

# UIAO PDF Layout Specification

This document specifies the layout, structure, and formatting requirements for the UIAO Governance Canon PDF export. The PDF export is produced from the MkDocs site using `mkdocs-with-pdf` or equivalent plugin and serves as the printable/archival form of the Canon.

---

## 1. Document Identity

| Field | Value |
|---|---|
| Document Title | UIAO Governance Canon |
| Subtitle | Universal Integration Adapter Orchestration — Governance Reference |
| Version | Sourced from `mkdocs.yml site_description` |
| Date | Build date (auto-populated) |
| Author | UIAO Governance Board |
| Classification | Internal Governance |

---

## 2. Page Layout

| Property | Value |
|---|---|
| Page size | A4 (210mm × 297mm) |
| Top margin | 25mm |
| Bottom margin | 25mm |
| Left margin | 30mm (binding side) |
| Right margin | 20mm |
| Header height | 10mm |
| Footer height | 10mm |

---

## 3. Typography

| Element | Font | Size | Style |
|---|---|---|---|
| Document title | Inter or system sans-serif | 28pt | Bold |
| Chapter heading (H1) | Inter | 20pt | Bold |
| Section heading (H2) | Inter | 16pt | Bold |
| Subsection heading (H3) | Inter | 13pt | Bold |
| Body text | Inter | 11pt | Regular |
| Code blocks | JetBrains Mono or monospace | 9pt | Regular |
| Table header | Inter | 10pt | Bold |
| Table body | Inter | 10pt | Regular |
| Footer text | Inter | 8pt | Regular, gray |
| Header text | Inter | 8pt | Regular, gray |

---

## 4. Page Structure

### Cover Page
- Document title (centered, large)
- Subtitle (centered)
- UIAO logo (if available)
- Version and build date (bottom center)
- Classification label (bottom right)

### Table of Contents
- Auto-generated from H1/H2/H3 headings
- Maximum 3 levels deep
- Page numbers right-aligned
- TOC begins on page ii (roman numerals for front matter)

### Main Content
- Page numbering begins at 1 on first content page
- Chapter breaks force a new page
- Appendix sections are prefixed: "Appendix A — Adapter Plane", etc.
- ADR sections are prefixed: "ADR-005:", etc.

### Header (all pages except cover)
- Left: "UIAO Governance Canon"
- Right: Current chapter title

### Footer (all pages except cover)
- Left: "Internal Governance — Not for External Distribution"
- Center: Page number (e.g., "Page 42 of 180")
- Right: Build date

---

## 5. Code Block Formatting

- Background: light gray (#f5f5f5)
- Border: 1px solid #e0e0e0
- Border-radius: 4px
- Padding: 8px
- Line wrapping: enabled (no horizontal overflow)
- Syntax highlighting: enabled where supported by PDF renderer

---

## 6. Table Formatting

- Header row: dark background (#2d3748), white text
- Alternating row shading: white / very light gray (#f9f9f9)
- Border: 1px solid #e2e8f0 on all cells
- Column widths: auto-fit to content, respect page margins
- Tables that exceed page width MUST be rotated to landscape orientation or split across pages

---

## 7. Diagram Inclusion

- PlantUML diagrams are rendered to SVG/PNG during MkDocs build
- All 6 architecture diagrams MUST be included in the PDF
- Diagrams are placed inline at their reference point in the document
- Minimum diagram width: 120mm
- Maximum diagram width: 150mm (fits within page margins)
- Caption format: "Figure N: [Diagram Title]"
- Diagrams that exceed 150mm width are placed on their own landscape page

---

## 8. Appendix Numbering

Appendices use a letter-number scheme matching the canonical directory structure:

- Appendix A: Adapter Plane (A-01 through A-04)
- Appendix B: Truth Fabric (B-01 through B-04)
- Appendix C: Drift Fabric (C-01 through C-03)
- Appendix D: Evidence Fabric (D-01 through D-04)
- Appendix E: Governance Plane (E-01 through E-03)

Appendix numbering is separate from main body page numbering. Appendix pages use the format "A-1", "A-2", "B-1", etc. in the footer.

---

## 9. ADR Numbering

ADRs are included in the PDF as a dedicated chapter: "Architectural Decision Records (ADR-005 through ADR-027)".

Each ADR entry includes:
- ADR number and title (H2 heading)
- Status badge (PROPOSED / ACCEPTED / DEPRECATED / SUPERSEDED)
- Date
- Context, Decision, Consequences sections

---

## 10. Accessibility Requirements

- All headings must use proper heading tags (H1–H6) — no bold paragraphs masquerading as headings
- All images must include alt text
- All tables must include a header row with `scope="col"`
- Color MUST NOT be the sole indicator of meaning — all color-coded elements must also use text labels
- PDF must be tagged for screen reader accessibility (PDF/UA compliance where renderer supports it)

---

## 11. Build Command

```bash
mkdocs build
# PDF output: site/pdf/uiao-governance-canon.pdf
```

The MkDocs PDF plugin is configured in `mkdocs.yml` under `plugins:`. The output file name and path are set in the plugin configuration. The PDF is NOT committed to the repository — it is produced as a CI artifact on each tagged release.
