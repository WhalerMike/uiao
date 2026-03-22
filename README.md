# UIAO Document Compiler v1.0

The UIAO Document Compiler v1.0 is a YAML‑driven system that generates leadership‑grade modernization documents from a single canonical content graph.

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

## OSCAL & GRC Compliance

The CI/CD pipeline automatically generates NIST OSCAL artifacts on every push to `main`:

### Generated Artifacts

| Artifact | Script | Output |
|----------|--------|--------|
| Component Definition | `scripts/generate_component_def.py` | `exports/oscal/component-definition.json` |
| Plan of Action & Milestones | `scripts/generate_poam.py` | `exports/oscal/poam.json` |
| System Security Plan | `scripts/generate_ssp.py` | `exports/oscal/ssp.json` |

### Data Sources

- `data/poam-findings.yml` — POA&M findings and milestones
- `canon/uiao_leadership_briefing_v1.0.yaml` — Canonical content graph

### Running Locally

```bash
pip install pyyaml
python scripts/generate_component_def.py
python scripts/generate_poam.py
python scripts/generate_ssp.py
```

OSCAL outputs are written to `exports/oscal/` and committed automatically by the workflow.

## Agency Adoption Quick Start

1. **Fork/clone** this repository
2. **Customize** `canon/uiao_leadership_briefing_v1.0.yaml` with your program's details
3. **Edit** `data/*.yml` files to match your agency's control environment
4. **Push** to main — GitHub Actions automatically:
   - Generates 26+ documents (DOCX, PDF, Markdown)
   - Produces 3 OSCAL artifacts (Component Definition, SSP, POA&M)
   - Validates all OSCAL against schema
   - Deploys updated Pages dashboard
5. **Import** OSCAL JSONs from `exports/oscal/` into your agency's GRC tools

**Live Demo**: https://whalermike.github.io/uiao-core/

## Exports

All generated documents are stored in `exports/`:

- `exports/markdown/` — Rendered Markdown documents
- `exports/docx/` — Word documents (via Pandoc)
- `exports/pdf/` — PDF documents (via Pandoc)
- `exports/oscal/` — NIST OSCAL JSON artifacts

## Known Limitations & Roadmap

### Current Limitations
- SSP is a skeleton — full control narrative requires agency-specific customization
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
