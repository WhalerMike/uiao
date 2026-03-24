# UIAO-MEMORY.md
**Persistent memory for uiao-core Copilot agents**
Update after EVERY run (success or failure).

## Correction Log (reverse chronological)

| Date | Task | Outcome | Issue / Error Summary | Correction Rule |
|------|------|---------|----------------------|----------------|
| 2026-03-24 | Continuous monitoring review + fixes | SUCCESS (#48 review PR) | Missing dashboard/ksi.py, dashboard/export.py, monitoring/ongoing_auth.py; POA&M lacked POAM-UIAO- prefix + Open/In-Progress/Closed status enum; no OSCAL evidence cross-links; no tests | ALWAYS create all modules referenced in __init__.py; ALWAYS add POAM-UIAO- prefix + FedRAMP status enum; ALWAYS generate OA evidence cross-links; ALWAYS write tests |
| 2026-03-23 | Security CI/CD hardening | SUCCESS (#44) | +382/-23, passed all checks | Keep strict security/ dir structure and fedramp-rev5 baseline checks |
| 2026-03-23 | Inventory linking | SUCCESS (#42) | +260/-3, diagrams rendered | Always generate both JSON manifest + Mermaid/PNG diagrams in same PR |
| 2026-03-23 | SSP templating | FAILED | Rate limit + unresolved variables | ALWAYS resolve all {{var}} placeholders from inventory.json first |
| 2026-03-23 | OSCAL evidence linking | FAILED | Rate limit + schema validation errors | ALWAYS add prop:id on every link, generate fresh UUIDv4, validate against OSCAL 1.3.0 schema |
| 2026-03-23 | POA&M generation | FAILED | Rate limit + incomplete risk fields | ALWAYS use exact FedRAMP POA&M enum values (Open, In-Progress, Closed), generate unique POAM-ID with prefix POAM-UIAO- |
| 2026-03-23 | Continuous monitoring | FAILED | Rate limit + missing control mappings | ALWAYS cross-reference every monitored control to an OSCAL evidence record |
| 2026-03-23 | FedRAMP Rev 5 SSP | FAILED | Rate limit before code generation | ALWAYS start from templates/fedramp-rev5-ssp.yaml |
| 2026-03-23 | Visual manifest | FAILED | Rate limit + out-of-sync with Git tree | ALWAYS regenerate manifest from git ls-tree + inventory.json |

## Quick Reference Rules
- Never ship without running make validate-oscal locally
- Every PR must reference this memory file in the commit message
- If error matches any row above, auto-apply correction rule before retry
- ALWAYS create ALL modules that are imported in `__init__.py` in the same PR
- ALWAYS add `prop:id` on every relevant-evidence link (fresh UUIDv4)
- ALWAYS generate `POAM-UIAO-<hex>` IDs and include `status: Open` (or In-Progress/Closed) in every POA&M entry
- ALWAYS include `OngoingAuthGenerator` output to cross-link every monitored control to an OSCAL observation
- ALWAYS write pytest tests for every new module in `tests/test_<module>.py`
- pip-audit vulnerabilities in certifi, configobj, idna, pip, pyasn1, pyjwt, pyopenssl, setuptools, twisted, urllib3, wheel are pre-existing in this environment (not introduced by feature PRs)
