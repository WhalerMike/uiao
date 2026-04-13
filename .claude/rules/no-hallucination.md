# Rule: No-Hallucination Protocol
## Scope
Activated when the user invokes "No-Hallucination Mode" or "NHP", or when operating on documentation derived from canonical governance artifacts.
## Protocol Steps
1. **Enter No-Hallucination Mode.** Acknowledge activation explicitly.
2. **Use only the text the user provides as the source of truth.** Do not draw from training data for factual claims about UIAO artifacts or documentation.
3. **Do not invent new content unless explicitly allowed.** If invention is permitted, label all invented items as `NEW (Proposed)`.
4. **If something is missing, write `MISSING`.** Never fill gaps with assumptions.
5. **If unsure, write `UNSURE`.** Never present uncertain information as fact.
6. **Restate understanding before generating.** Confirm interpretation of the source material.
7. **List all assumptions before generating.** Make implicit reasoning explicit.
8. **Ask clarifying questions if anything is ambiguous.** Do not proceed through ambiguity.
9. **Work in micro-steps:** list → group → identify gaps → propose → generate.
10. **End with a validation step** comparing output to the source of truth.
11. **Highlight any uncertainties or assumptions** in a dedicated section at the end of output.
## Documentation-Specific Additions
- When generating articles, verify every technical claim traces to a canonical source in `uiao-core`
- When creating guides, ensure every procedure step has been validated against the operational playbook
- Article narrative sections (story, comic) are clearly labeled as creative content, not factual claims
- Technical sections are held to full NHP rigor
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
