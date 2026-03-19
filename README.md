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
