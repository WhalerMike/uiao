# UIAO Document Compiler (UDC) - Usage Guide

This guide covers how to use the UDC pipeline to author, validate, and compile UIAO canon artifacts into publication-ready documents.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Repository Layout](#repository-layout)
3. [Authoring YAML Data Files](#authoring-yaml-data-files)
4. [Creating Templates](#creating-templates)
5. [UDC Schemas](#udc-schemas)
6. [Running Locally](#running-locally)
7. [GitHub Actions Pipeline](#github-actions-pipeline)
8. [Retrieving Compiled Documents](#retrieving-compiled-documents)
9. [Adding a New Document](#adding-a-new-document)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

**Automatic (CI/CD):** Push changes to `data/`, `templates/`, `schemas/`, or `scripts/` on the `main` branch. GitHub Actions will automatically validate, normalize, compile, and commit outputs.

**Manual trigger:** Go to **Actions > Generate UIAO Documents > Run workflow** in GitHub.

**Local development:**
```bash
git clone https://github.com/WhalerMike/uiao-core.git
cd uiao-core
pip install -r requirements.txt
python scripts/validate_schemas.py
python scripts/normalize_artifacts.py
python scripts/compile_documents.py
```

---

## Repository Layout

```
uiao-core/
  data/                  # YAML canon artifacts (single source of truth)
  templates/             # Jinja2 templates (.md.j2 files)
  schemas/udc/           # UDC validation schemas (YAML + JSON pairs)
  scripts/
    generate.py          # Original Jinja2 renderer (YAML -> Markdown)
    validate_schemas.py  # Validates YAML against JSON schemas
    normalize_artifacts.py # Canonical ordering and metadata expansion
    compile_documents.py # Multi-format compilation (MD, DOCX, PDF, HTML)
  site/                  # Auto-generated Markdown output (do not edit)
  exports/               # Compiled publication documents (DOCX, PDF, HTML)
  .github/workflows/     # CI/CD pipeline definition
  requirements.txt       # Python dependencies
```

---

## Authoring YAML Data Files

All program data lives in `data/` as YAML files. Each file is loaded by its filename (hyphens become underscores).

**Example:** `data/program.yml` is available in templates as `{{ program }}`.

### UDC Metadata Fields

For files that should be schema-validated, include these metadata fields:

```yaml
id: UIAO-SPEC-001
title: UIAO Canon Specification
version: 1.0.0
status: draft          # draft | review | approved | published | deprecated
authors:
  - name: Your Name
    role: Author
    organization: Your Org
canonical_path: data/canon-spec.yml
classification: unclassified   # unclassified | cui | confidential
tags:
  - architecture
  - canon
```

---

## Creating Templates

Templates use Jinja2 syntax and live in `templates/` with the `.md.j2` extension.

**Example template** (`templates/my-document.md.j2`):
```jinja2
# {{ program.title }}

**Version:** {{ program.version }}
**Status:** {{ program.status }}

## Architecture Overview

{% for concept in program.architecture.concepts %}
### {{ concept.name }}
{{ concept.description }}
{% endfor %}
```

All data files are available as template variables using their filename (with hyphens converted to underscores).

---

## UDC Schemas

Four schema pairs live in `schemas/udc/` (YAML definition + JSON Schema for validation):

| Schema | Purpose |
|--------|--------|
| `udc_metadata` | Document identity: id, title, version, status, authors |
| `udc_templates` | Template bindings: format type, file path, field mappings |
| `udc_pipeline` | Pipeline stages: validate, normalize, compile, hash |
| `udc_export` | Export config: formats, naming, hashing, immutability |

The validator auto-detects which schema applies based on the content of each YAML file.

---

## Running Locally

### Prerequisites

- Python 3.12+
- pandoc (for DOCX/PDF/HTML export)
- LaTeX (optional, for PDF export via xelatex)

### Install Dependencies

```bash
pip install -r requirements.txt

# For DOCX/HTML export:
sudo apt-get install pandoc     # Linux
brew install pandoc             # macOS

# For PDF export (optional):
sudo apt-get install texlive-xetex  # Linux
brew install --cask mactex          # macOS
```

### Step 1: Validate

```bash
python scripts/validate_schemas.py
```

Validates all YAML files in `data/` against matching UDC JSON schemas. Files without matching schemas are skipped. Exit code 1 on validation failure.

### Step 2: Normalize

```bash
python scripts/normalize_artifacts.py
```

Reads `data/` files and writes normalized versions to `normalized/` with:
- Canonical key ordering (id, title, version, status first)
- Default metadata expansion (modified_date, classification, status)
- Consistent YAML formatting

### Step 3: Compile

```bash
python scripts/compile_documents.py
```

Runs the full compilation pipeline:
1. Loads all YAML data from `data/`
2. Renders Jinja2 templates to Markdown in `site/`
3. Converts Markdown to DOCX in `exports/` (requires pandoc)
4. Converts Markdown to PDF in `exports/` (requires pandoc + LaTeX)
5. Converts Markdown to HTML in `exports/`
6. Generates `exports/manifest.json` with SHA-256 hashes

### Legacy Generate (Markdown only)

```bash
python scripts/generate.py
```

The original renderer. Generates Markdown files in `site/` only.

---

## GitHub Actions Pipeline

The workflow (`.github/workflows/generate-docs.yml`) triggers on:
- Push to `main` branch affecting `data/`, `templates/`, `schemas/`, or `scripts/`
- Manual dispatch via GitHub Actions UI

### Pipeline Stages

| Stage | Script | Description |
|-------|--------|-------------|
| Install | `pip install -r requirements.txt` | Install Python deps + pandoc |
| Validate | `validate_schemas.py` | Check YAML against JSON schemas |
| Normalize | `normalize_artifacts.py` | Canonical ordering + metadata defaults |
| Compile | `compile_documents.py` | Generate MD, DOCX, PDF, HTML |
| Upload | `actions/upload-artifact@v4` | Upload exports as downloadable artifacts (90-day retention) |
| Commit | `git push` | Commit generated files to `site/` and `exports/` |

---

## Retrieving Compiled Documents

### From GitHub Actions

1. Go to **Actions** tab in the repository
2. Click the latest successful workflow run
3. Scroll to **Artifacts** section
4. Download **udc-exports** zip file
5. Extract to get DOCX, PDF, HTML files + manifest.json

### From the Repository

Compiled documents are also committed to:
- `site/` - Markdown versions
- `exports/` - DOCX, PDF, HTML versions

### Integrity Verification

Each compilation generates `exports/manifest.json` containing SHA-256 hashes for every exported file. To verify:

```bash
# Linux/macOS
sha256sum exports/my-document.docx
# Compare against manifest.json entry
```

---

## Adding a New Document

1. **Add data** (if needed): Create or update a YAML file in `data/`
2. **Create template**: Add a `.md.j2` file in `templates/`
3. **Push to main**: GitHub Actions auto-generates all output formats
4. **Download**: Get compiled DOCX/PDF/HTML from Actions artifacts or `exports/`

### Example: Adding a FedRAMP Boundary Document

```bash
# 1. Add data
vi data/fedramp-boundary.yml

# 2. Create template
vi templates/fedramp-boundary.md.j2

# 3. Push
git add .
git commit -m "Add FedRAMP boundary document"
git push origin main

# 4. Wait for Actions to complete, then check exports/
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Validation fails | Check YAML syntax and ensure required fields match the UDC metadata schema |
| DOCX not generated | Ensure `pandoc` is installed (`pandoc --version`) |
| PDF not generated | Install LaTeX: `sudo apt-get install texlive-xetex` |
| Template render error | Check Jinja2 syntax; ensure data file keys match template variables |
| Workflow not triggering | Verify changes are in watched paths: `data/`, `templates/`, `schemas/`, `scripts/` |
| Empty exports/ | Run `python scripts/compile_documents.py` locally to see error output |

---

## Script Reference

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `generate.py` | Jinja2 render (legacy) | `data/` + `templates/` | `site/*.md` |
| `validate_schemas.py` | Schema validation | `data/` + `schemas/udc/` | Pass/fail report |
| `normalize_artifacts.py` | Canonical normalization | `data/` | `normalized/` |
| `compile_documents.py` | Multi-format compilation | `data/` + `templates/` | `site/` + `exports/` |
