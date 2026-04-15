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

## Signed Commits (GPG)

This project follows FedRAMP Moderate supply-chain requirements. Commit signatures are checked on every PR via `.github/workflows/verify-signatures.yml`. While advisory today, repository admins may promote the rule to a hard branch-protection gate at any time.

### One-time GPG setup

```bash
# 1. Generate a new RSA-4096 key (or reuse an existing one)
gpg --full-generate-key
# Choose: (1) RSA and RSA, keysize 4096, no expiry (or set an expiry date)

# 2. List your keys to find the key ID
gpg --list-secret-keys --keyid-format=long
# Example output:
#   sec   rsa4096/ABCDEF1234567890 2024-01-01 [SC]

# 3. Export your public key and add it to GitHub
gpg --armor --export ABCDEF1234567890
# Copy the output, then go to:
# GitHub → Settings → SSH and GPG keys → New GPG key → Paste

# 4. Tell Git to use your key
git config --global user.signingkey ABCDEF1234567890
git config --global commit.gpgsign true

# (macOS only) point Git at the system gpg binary
git config --global gpg.program gpg
```

### Verifying locally

```bash
# Verify the last commit
git log --show-signature -1

# Check all unsigned commits on your branch vs main
git log --format="%H %G?" origin/main..HEAD
```

A status of `G` means a good signature; `N` means unsigned.
