---
title: "Repo-Structure"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Repository Structure: User vs Machine Documents

```text
uiao-core/
├── canon/                    # Canonical definitions, principles, invariants
├── docs/                     # Human-facing documentation
│   ├── appendix/
│   ├── architecture/
│   ├── governance/
│   ├── onboarding/
│   ├── patterns/
│   ├── user-guides/
│   └── visuals/
├── machine/                  # Machine-facing artifacts
│   ├── adapters/
│   ├── configs/
│   ├── generators/
│   ├── pipelines/
│   └── schemas/
├── templates/                # Reusable templates
│   ├── user-docs/
│   └── machine-docs/
├── scripts/                  # Utility scripts
├── src/                      # Runtime code
├── tests/                    # Automated tests
└── tools/                    # Developer tools
```

## Zone Summary

| Zone | Audience | Allowed Formats | Prohibited |
|------|----------|----------------|------------|
| `docs/` | Humans | `.md`, `.png`, `.svg`, `.drawio` | `.json`, `.yaml`, `.oscal` |
| `machine/` | Automation | `.json`, `.yaml`, `.xml`, `.oscal` | `.md`, `.txt`, `.docx` |
| `canon/` | Both | `.md`, versioned definitions | Generated artifacts |
| `scripts/` | Tools | `.ps1`, `.py`, `.sh` | Documentation, schemas |
