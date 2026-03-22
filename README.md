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

## Exports

All generated documents are stored in `exports/`:

- `exports/markdown/` — Rendered Markdown documents
- `exports/docx/` — Word documents (via Pandoc)
- `exports/pdf/` — PDF documents (via Pandoc)
- `exports/oscal/` — NIST OSCAL JSON artifacts

## License

See [LICENSE](LICENSE) for details.
