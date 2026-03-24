# UIAO-MEMORY.md
**Persistent memory for uiao-core Copilot agents**
Update after EVERY run (success or failure).

## Correction Log (reverse chronological)

| Date | Task | Outcome | Issue / Error Summary | Correction Rule |
|------|------|---------|----------------------|----------------|
| 2026-03-24 | OSCAL evidence linking review + fixes (PR #47) | SUCCESS | RE-PLAN applied: added missing linker.py + bundler.py, added prop:id on every back-matter prop, added 34 tests (all pass), updated SSP back-matter | linker.py and bundler.py are REQUIRED companions to collector.py; never ship __init__.py that imports modules not in the PR |
| 2026-03-23 | Security CI/CD hardening | SUCCESS (#44) | +382/-23, passed all checks | Keep strict security/ dir structure and fedramp-rev5 baseline checks |
| 2026-03-23 | Inventory linking | SUCCESS (#42) | +260/-3, diagrams rendered | Always generate both JSON manifest + Mermaid/PNG diagrams in same PR |
| 2026-03-23 | SSP templating | FAILED | Rate limit + unresolved variables | ALWAYS resolve all {{var}} placeholders from inventory.json first |
| 2026-03-23 | OSCAL evidence linking | FAILED | Rate limit + schema validation errors | ALWAYS add prop:id on every link, generate fresh UUIDv4, validate against OSCAL 1.0.4 schema (repo baseline) |
| 2026-03-23 | POA&M generation | FAILED | Rate limit + incomplete risk fields | ALWAYS use exact FedRAMP POA&M enum values (Open, In-Progress, Closed), generate unique POAM-ID with prefix POAM-UIAO- |
| 2026-03-23 | Continuous monitoring | FAILED | Rate limit + missing control mappings | ALWAYS cross-reference every monitored control to an OSCAL evidence record |
| 2026-03-23 | FedRAMP Rev 5 SSP | FAILED | Rate limit before code generation | ALWAYS start from templates/fedramp-rev5-ssp.yaml |
| 2026-03-23 | Visual manifest | FAILED | Rate limit + out-of-sync with Git tree | ALWAYS regenerate manifest from git ls-tree + inventory.json |

## Quick Reference Rules
- Never ship without running make validate-oscal locally
- Every PR must reference this memory file in the commit message
- If error matches any row above, auto-apply correction rule before retry
- ALWAYS ship linker.py + bundler.py together with collector.py (they are a triad)
- ALWAYS add prop:id (uuid field) on every prop in OSCAL back-matter resources
- OSCAL schema validation runs via `make validate-oscal` (compliance-trestle); linker.py generates conformant structures but does not call the validator inline
- ALWAYS populate back-matter resources in SSP before marking PR as review-ready
- pip-audit currently shows CVEs in environment system packages (urllib3, setuptools, pip, pyopenssl); these are transitive/system-level — not direct project deps — but monitor for resolution in compliance-trestle upgrades
