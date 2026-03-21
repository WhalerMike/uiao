# Contributor's Guide: The Appendix Canon

Welcome to the **uiao-core** project. To maintain a "Single Source of Truth," we use a strict **Docs-as-Code** workflow. This guide explains how to add or update technical standards in the Appendix Canon.

## The Rule of One
Every technical standard in the agency must exist as a single entry in `data/atlas-appendices.yml`. If a standard changes, you update it there, and the entire Modernization Atlas updates automatically on the next pipeline run.

## How to Add a New Appendix Entry

### 1. Identify the Category
Choose the correct ID based on the library structure:
* **A-Z:** Core Standards (Naming, Global Settings)
* **AA-AZ:** Network Patterns (Routing, SD-WAN)
* **BA-BZ:** Security Protocols (ISE, Firewall, Zero-Trust)
* **CA-CZ:** Operational Procedures (Decommissioning, Backups)

### 2. Update `data/atlas-appendices.yml`
Add your entry following the established schema.

**Crucial:** Keys must use a hyphen (e.g., `BA-05`). The system's `normalize_key` function will automatically handle the conversion for the templates.

```yaml
  BA-05:
    title: "Example Security Standard"
    status: "Draft"
    owner: "Security Engineering"
    description: "Brief narrative of the standard's purpose."
    source_file: "path/to/authoritative/doc.pdf"
    config_snippet: |
      setting_name: "standard_value"
```

## 3. Validate Your Changes

Before committing, run the schema validation to ensure you haven't missed any required fields:

```bash
# This mirrors the check run by our GitHub Action
python -c "import jsonschema, yaml, json; \
schema = json.load(open('data/schema.json')); \
data = yaml.safe_load(open('data/atlas-appendices.yml')); \
jsonschema.validate(instance=data, schema=schema)"
```

## The "Hyphen-to-Underscore" Logic

When writing Jinja2 templates (`.j2`), remember that the pipeline normalizes YAML keys for variable safety.

- YAML Key: `BA-05`
- Jinja2 Variable: `{{ data.appendices.BA_05 }}`

## Workflow

1. Create a feature branch: `git checkout -b feat/appendix-BA-05`
2. Update `data/atlas-appendices.yml`
3. Verify the local build: `python scripts/generate_atlas.py`
4. Submit a Pull Request. The CI/CD pipeline will fail if your entry does not match the `schema.json`.
