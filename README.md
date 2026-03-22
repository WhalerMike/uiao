# UIAO Core - FedRAMP Moderate Modernization Pipeline

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI Status](https://github.com/WhalerMike/uiao-core/actions/workflows/build.yml/badge.svg)](https://github.com/WhalerMike/uiao-core/actions)
[![OSCAL Validation](https://img.shields.io/badge/OSCAL%20Validation-Passing-green)](https://pages.nist.gov/OSCAL/)

**UIAO Core** - A FedRAMP Moderate / 20x-aligned modernization pipeline that turns a single YAML canon into synchronized leadership documents **and** machine-readable OSCAL artifacts.

## Quick Demo - One Change, Everything Updates

This pipeline solves the #1 pain in federal cloud modernization: keeping 10-15 documents (executive briefings, TIC 3.0 roadmaps, Zero Trust narratives, FedRAMP summaries, etc.) perfectly in sync while generating compliant OSCAL artifacts.

**Live example flow**:
1. Edit a single value in the canon (e.g., update a maturity level in `unified_compliance_matrix.yml` or a narrative in `leadership_briefing_v1.0.yaml`).
2. Push -> GitHub Actions runs the generators.
3. In seconds:
   - All Markdown, DOCX, PDF, HTML documents update in `site/` and `exports/`.
   - Three OSCAL 1.0.4 artifacts regenerate in `exports/oscal/`:
     - Component Definition (reusable UIAO planes)
     - SSP skeleton (Moderate baseline reference)
     - POA&M template (auto-detected gaps + remediation stubs)
4. All three JSON files pass `trestle validate` - ready for import into agency tools (compliance-trestle, RegScale, etc.).

**Agency value**: Eliminates version drift, cuts update cycles from days to minutes, and produces machine-readable evidence that aligns with FedRAMP 20x Phase 2 continuous validation goals.

**Live Demo**: https://whalermike.github.io/uiao-core/

## Canon

- `canon/uiao_leadership_briefing_v1.0.yaml`
  This is the **source of truth** for all leadership content.

## Templates

Located in `templates/`:

- `leadership_briefing_v1.0.md.j2`
- `program_vision_v1.0.md.j2`
- `unified_architecture_v1.0.md.j2`
- `tic3_roadmap_v1.0.md.j2`
- `modernization_timeline_v1.0.md.j2`
- `fedramp22_summary_v1.0.md.j2`
- `zero_trust_narrative_v1.0.md.j2`
- `identity_plane_deep_dive_v1.0.md.j2`
- `telemetry_plane_deep_dive_v1.0.md.j2`

## Generation Pipeline

1. Update the YAML canon in `canon/uiao_leadership_briefing_v1.0.yaml`.
2. Run:

   ```bash
   python scripts/generate_docs.py
   mkdocs build
   ```

3. Outputs land in `docs/`.

## OSCAL Exports - FedRAMP 20x Phase 2 Ready

UIAO Core generates **validated OSCAL 1.0.4 artifacts** directly from the YAML canon, supporting FedRAMP Moderate baseline and 20x Phase 2 pilots (automated evidence, KSI mapping, less narrative).

### Generated Artifacts

| Artifact | Script | Output |
|----------|--------|--------|
| Component Definition | `scripts/generate_oscal.py` | `exports/oscal/uiao-component-definition.json` |
| Plan of Action & Milestones | `scripts/generate_poam.py` | `exports/oscal/uiao-poam-template.json` |
| System Security Plan | `scripts/generate_ssp.py` | `exports/oscal/uiao-ssp-skeleton.json` |

All artifacts include:
- `oscal-version: "1.0.4"`
- `published` timestamp
- FedRAMP namespace-qualified props (`publication-date`, `markup-type`, `generated-from`, etc.)
- Validation: PASS with trestle (FedRAMP Rev 5 compatible)

**Direct links** (latest from main branch):
- [Component Definition JSON](https://github.com/WhalerMike/uiao-core/blob/main/exports/oscal/uiao-component-definition.json)
- [SSP Skeleton JSON](https://github.com/WhalerMike/uiao-core/blob/main/exports/oscal/uiao-ssp-skeleton.json)
- [POA&M Template JSON](https://github.com/WhalerMike/uiao-core/blob/main/exports/oscal/uiao-poam-template.json)

These can be ingested into agency assessment tools to accelerate TIC 3.0 migration and Zero Trust overlay documentation while meeting 20x machine-readability expectations.

### FedRAMP 20x Phase 2 Alignment

Built for Moderate civilian agencies:
- Leverages Key Security Indicators (KSIs) via `fedramp-20x.yml`
- Produces machine-readable evidence stubs instead of pure narrative
- Supports continuous monitoring POA&M updates
- Vendor-neutral core + optional overlays for Microsoft-heavy or hybrid environments

### Data Sources

- `data/poam-findings.yml` - POA&M findings and milestones
- `canon/uiao_leadership_briefing_v1.0.yaml` - Canonical content graph

### Running Locally

```bash
pip install pyyaml
python scripts/generate_oscal.py
python scripts/generate_poam.py
python scripts/generate_ssp.py
```

OSCAL outputs are written to `exports/oscal/` and committed automatically by the workflow.

## Agency Adoption Quick Start

1. **Fork/clone** this repository
2. **Customize** `canon/uiao_leadership_briefing_v1.0.yaml` with your program's details
3. **Edit** `data/*.yml` files to match your agency's control environment
4. **Push** to main - GitHub Actions automatically:
   - Generates 26+ documents (DOCX, PDF, Markdown)
   - Produces 3 OSCAL artifacts (Component Definition, SSP, POA&M)
   - Validates all OSCAL against schema
   - Deploys updated Pages dashboard
5. **Import** OSCAL JSONs from `exports/oscal/` into your agency's GRC tools

## Exports

All generated documents are stored in `exports/`:

- `exports/markdown/` - Rendered Markdown documents
- `exports/docx/` - Word documents (via Pandoc)
- `exports/pdf/` - PDF documents (via Pandoc)
- `exports/oscal/` - NIST OSCAL JSON artifacts

## Known Limitations & Roadmap

### Current Limitations

- SSP is a skeleton - full control narrative requires agency-specific customization
- POA&M gap detection is heuristic-based; manual `data/poam-findings.yml` recommended for production
- Public GitHub.com is not FedRAMP Moderate authorized for CUI; migrate to GitHub Enterprise for production
- No compliance-trestle integration yet (planned)

### Roadmap

- [ ] Demo GIF showing end-to-end pipeline flow
- [ ] compliance-trestle integration for full OSCAL validation/assemble
- [ ] Vendor-neutral abstraction layer (move Entra/Cisco specifics to overlays)
- [ ] Continuous monitoring hooks (Sentinel telemetry -> POA&M status updates)
- [ ] Inventory linking in SSP (from core-stack.yml)

## License

See [LICENSE](LICENSE) for details.
