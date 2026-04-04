# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub issue.

Instead, please report it via GitHub's private vulnerability reporting feature:
[Report a Vulnerability](../../security/advisories/new)

You can expect an initial response within **72 hours** and a resolution timeline within **14 days** for critical issues.

## AI Agent Governance

This section defines the governance policy for AI coding agents (e.g., GitHub Copilot Coding Agent) operating in this repository.

### Scope

These rules apply to all automated agents that read, generate, or modify files in this repository, including but not limited to GitHub Copilot, Dependabot, and any custom workflow bots.

### Permitted Actions

- Reading source files, templates, and canonical YAML data to generate documentation.
- Creating or updating files in `docs/`, `exports/`, and `site/` as part of the defined CI/CD pipeline.
- Opening pull requests that include only auto-generated artifacts or dependency updates.
- Running approved scripts listed in `scripts/` with inputs validated against `schemas/`.

### Prohibited Actions

- Committing secrets, credentials, API keys, or PII directly into any file.
- Modifying canonical source files (`generation-inputs/`, `data/`, `schemas/`) without a human-reviewed pull request.
- Disabling or bypassing branch protection rules, required status checks, or secret-scanning alerts.
- Exfiltrating repository contents to unapproved external endpoints.
- Self-modifying workflow files (`.github/workflows/`) without explicit human approval.

### Secret Scanning

Secret scanning is enforced on all branches via the GitHub MCP Server `secret_scanning` tool (see `.github/workflows/ai-security-audit.yml`). Any detected secret triggers an automatic alert and blocks the affected pull request until the secret is rotated and the alert is resolved.

### Audit Trail

Every action taken by an AI agent must be traceable via:
1. A commit message following [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `chore: auto-generate OSCAL artifacts [skip ci]`).
2. A linked pull request or workflow run in GitHub Actions.
3. Retention of security audit artifacts for a minimum of **90 days** (enforced in `ai-security-audit.yml`).

### Human-in-the-Loop Requirements

The following changes **always** require a human reviewer to approve before merging:

- Changes to `generation-inputs/` or `data/` (source-of-truth files).
- Changes to `schemas/` (validation schemas).
- Changes to `.github/workflows/` (CI/CD pipeline configuration).
- Changes to `SECURITY.md`, `AGENTS.md`, or `CONTRIBUTING.md`.
- Any change that modifies GitHub Actions permissions or secrets.

### Compliance

This governance policy aligns with:
- **NIST SP 800-53 Rev 5** — SI-7 (Software, Firmware, and Information Integrity), AU-2 (Event Logging)
- **NIST SP 800-218** — Secure Software Development Framework (SSDF)
- **CISA Secure-by-Design Principles**
