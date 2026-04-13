# Rule: Documentation Governance
## Scope
Always active. Applies to all operations within uiao-docs.
## Rules
1. **Derived Repository:** This repository contains DERIVED and OPERATIONAL artifacts only. No CANONICAL artifacts may be created here — canon lives exclusively in `uiao-core`.
2. **Provenance Mandatory:** Every document must include a `provenance` block in its frontmatter tracing to a canonical source in `uiao-core`. Documents without provenance are classified as ORPHAN and are CI-blocking.
3. **Metadata Schema Compliance:** Every document with YAML frontmatter must validate against the documentation metadata schema defined in `schemas/docs-metadata-schema.json`.
4. **Article Series Standards:** All articles in the M365 modernization series must follow the canonical structure:
- Story/narrative section (lightly humorous, dry-humor tone)
- Comic section
- Technical section
- Disclaimer
- Author bio (pseudonym: Michal Doroszewski)
- Title, byline, all section headers, and 'About the Author' header use muted-blue header style
- Only narrative body text is black
- Article 1 is the canonical formatting template
5. **Version Isolation:** No document may reference a previous version of itself or any artifact from a prior version epoch.
6. **GCC-Moderate Boundary:** All cloud service references must be scoped to GCC-Moderate (M365 SaaS). Azure services, GCC-High, and DoD references are CI-blocking unless tagged with `boundary-exception: true`.
7. **Appendix Integrity:** Every appendix must have a unique ID, be registered in the appendix index, and include a Copy section. No exceptions.
8. **Owner Accountability:** Every document must have an `owner` field. Ownerless documents are flagged for immediate assignment.
9. **Placeholder Standards:** Every placeholder includes a unique ID and a fully detailed description. Prose references use "Table X", "Diagram Y", or "Image Z" format.
10. **Image Standards:** All images must include a title, dimensions (width × height), and alt text.
11. **Diagram Rendering:** PlantUML is the canonical diagram renderer. Mermaid is prohibited.
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
