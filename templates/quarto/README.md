# UIAO Quarto Reference Templates

This directory contains Quarto reference templates for branded document output.

## Setup Instructions

### DOCX Reference Template (uiao-reference.docx)

1. Generate the default Pandoc reference template:

```bash
quarto pandoc -o templates/quarto/uiao-reference.docx --print-default-data-file reference.docx
```

2. Open `uiao-reference.docx` in Microsoft Word.
3. Modify these styles in the Styles pane:
   - **Heading 1**: Segoe UI, 18pt, Bold, Color #1a365d, Space After 12pt
   - **Heading 2**: Segoe UI, 14pt, Bold, Color #2c5282, Space After 10pt
   - **Heading 3**: Segoe UI, 12pt, Bold, Color #2c5282, Space After 8pt
   - **Body Text / Normal**: Calibri, 11pt, Color #2d3748, Line Spacing 1.15
   - **Table Grid**: Alternating row shading (light blue #f7fafc), Header row #1a365d with white text
   - **Header**: UIAO logo left, document title center, classification right
   - **Footer**: Page X of Y center, "UIAO Modernization Program" right
4. Save the file. This is now the master DOCX template.

### PPTX Reference Template (uiao-reference.pptx)

1. Generate the default Pandoc reference template:

```bash
quarto pandoc -o templates/quarto/uiao-reference.pptx --print-default-data-file reference.pptx
```

2. Open `uiao-reference.pptx` in PowerPoint.
3. Edit the Slide Master (View > Slide Master):
   - **Title Slide**: UIAO branding, dark blue (#1a365d) background, white text
   - **Section Header**: Subtitle layout with accent bar
   - **Title and Content**: Standard body slide
   - **Two Content**: Side-by-side comparison layout
   - **Blank**: Clean layout for diagrams
4. Apply UIAO color palette:
   - Primary: #1a365d
   - Secondary: #2c5282
   - Accent: #3182ce
   - Background: #ffffff
   - Text: #2d3748
5. Set fonts: Segoe UI for headings, Calibri for body.
6. Save the file. This is now the master PPTX template.

## Notes

- The `.docx` and `.pptx` reference template files are BINARY files.
  They must be created manually per the instructions above.
- After creating them, commit them to this directory.
- Quarto uses these as style references -- your content fills the template.
- To update branding, edit the template files and re-commit.
