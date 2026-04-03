---
title: "Proposal-One-Pager"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO-Core: FedRAMP 20x-Aligned Modernization Pipeline

**Overview**

UIAO-Core is a YAML-driven document compiler and OSCAL generator for federal IT modernization programs (TIC 3.0, Zero Trust, FedRAMP Moderate). Single source of truth (canon YAML) auto-produces:
- Leadership briefings, roadmaps, FedRAMP summaries
- Machine-readable OSCAL artifacts (Component Definition, SSP skeleton, POA&M with KSI mappings)

**Key Benefits for Moderate Civilian Agencies**
- **20x Alignment**: Leverages FedRAMP 20x Phase 2 KSIs (e.g., MFA, Telemetry Visibility) with automated evidence injection.
- **Time Savings**: Change one YAML -> 26+ docs + 3 OSCAL files update in ~4 min via CI/CD.
- **Reusability**: Import UIAO components into agency SSPs; inherit controls.
- **Compliance**: Schema-validated, auto-committed artifacts; Apache 2.0 licensed.

**Pipeline Highlights**
- Inputs: data/*.yml + canon/*.yaml
- Outputs: DOCX/PDF/Markdown + exports/oscal/*.json
- Automation: GitHub Actions (generate + validate + commit)
- Live Demo: https://whalermike.github.io/uiao-core/
- Demo GIF: [Insert GIF link]

**Next Steps for Adoption**
1. Fork/clone repo.
2. Customize canon YAML for your program.
3. Push -> watch artifacts regenerate.
4. Import OSCAL JSONs into agency tools (e.g., compliance-trestle).
5. Contact: Michael Whaler for pilot support.

**Status**: Proof-of-concept ready for agency evaluation (Moderate baseline compatible).
