# FedRAMP Rev 5 OSCAL Reference Materials

This folder contains reference copies and links to official FedRAMP OSCAL Rev 5 artifacts used for alignment in uiao-core generation/validation.

## Source
All content is derived from the official (now archived) FedRAMP OSCAL repository:

- **Repository**: https://github.com/GSA/fedramp-automation
- **Last used release/tag**: `fedramp-2.0.0-oscal-1.0.4` (September 2024)
- **Status**: Archived July 1, 2025 - read-only. No active successor repo identified; contact oscal@fedramp.gov for latest guidance.
- **Key paths**:
  - Baselines: `/dist/content/rev5/baselines/json/` (e.g., FedRAMP_rev5_MODERATE-baseline_profile.json)
  - Templates: `/documents/` (SSP, POA&M in JSON/XML/YAML)
  - Registry/Resources: `/dist/content/rev5/resources/`

## Attribution
See root-level [NOTICE](../../../NOTICE) file for full attribution to GSA/FedRAMP PMO and NIST.

## Usage in this repo
- Baselines are referenced via `import-profile` href in generated SSP/POA&M.
- Templates serve as schema/structure alignment targets for `generate_ssp.py`, `generate_poam.py`, etc.
- Validation uses `compliance-trestle-fedramp` plugin against Rev 5 profiles.

## Recommendations
- Periodically check https://www.fedramp.gov/developers/ or https://www.fedramp.gov/rev5/documents-templates for updates.
- If new canonical OSCAL repo emerges, update hrefs and copies here.

Do not modify files in this folder directly - treat as vendor/reference.
