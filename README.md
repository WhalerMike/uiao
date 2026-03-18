# UIAO-Core

Unified Identity-Addressing-Overlay Architecture - Machine-readable data layer for federal modernization.

## Overview

This repo replaces repetitive static documents with a structured YAML data layer + Jinja2 templates. Documents are generated on demand via GitHub Actions.

## Repository Structure

```
uiao-core/
  data/              # YAML Single Source of Truth
    program.yml      # Core program data (vision, architecture, canon)
    roadmap.yml      # TIC 3.0 roadmap and modernization timeline
    appendices.yml   # 104-appendix canon map (A-CZ)
  templates/         # Jinja2 templates for document generation
    leadership-briefing.md.j2
    program-vision.md.j2
    unified-architecture.md.j2
    tic3-roadmap.md.j2
    modernization-timeline.md.j2
  site/              # Auto-generated documents (do not edit)
  scripts/           # Generation scripts (generate.py)
  schemas/           # YAML validation schemas
  .github/workflows/ # GitHub Actions for auto-generation
```

## How It Works

1. **Data Layer** (`data/*.yml`): All program facts stored once in YAML
2. **Templates** (`templates/*.md.j2`): Jinja2 templates reference data fields
3. **Generation**: On push, GitHub Actions runs `scripts/generate.py`
4. **Output** (`site/*.md`): Generated Markdown documents

## Data Files

| File | Contents | Lines |
|------|----------|-------|
| `program.yml` | Program vision, architecture, 17-point canon, frozen domains | ~180 |
| `roadmap.yml` | TIC 3.0 phases, milestones, workstreams, timeline | ~150 |
| `appendices.yml` | 104 appendix definitions across 4 families (A-Z, AA-AZ, BA-BZ, CA-CZ) | ~430 |

## Generated Documents

| Template | Description |
|----------|-------------|
| Leadership Briefing | Executive summary for CIO/CISO audience |
| Program Vision | Full architectural vision and core thesis |
| Unified Architecture | Seven-concept model and layer details |
| TIC 3.0 Roadmap | Phase-by-phase implementation plan |
| Modernization Timeline | Workstream milestones and dependencies |

## Adding New Documents

1. Add a new `.md.j2` template in `templates/`
2. Reference data fields from `data/*.yml` using `{{ variable }}` syntax
3. Push to `main` - GitHub Actions auto-generates the document

## Design Principles

- **Write data once**: No duplication across documents
- **Machine-readable**: YAML structure for AI/LLM consumption
- **On-demand generation**: Any document format from the same data
- **Vendor-agnostic**: Templates can target any vendor or audience
- **Version-controlled**: Full change history via Git

## Classification

CUI/FOUO or as appropriate
