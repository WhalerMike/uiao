# Contributor Guide

This guide covers how to contribute documentation to the UIAO project.

## Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/WhalerMike/uiao-docs.git
   cd uiao-docs
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the local preview server:
   ```bash
   mkdocs serve
   ```
4. Open `http://127.0.0.1:8000` in your browser.

## Contribution Workflow

1. Create a feature branch from `main`
2. Add or edit Markdown files in `docs/`
3. Preview locally with `mkdocs serve`
4. Commit with a descriptive message
5. Open a Pull Request against `main`
6. Site auto-deploys on merge

## Content Standards

- Use UIAO-xxx identifiers for all documents
- Include a status header (Current, Needs Replacing, Needs Creating)
- Include Last Updated date
- Follow Markdown best practices

## Style Guide

- Use ATX-style headings (`#`, `##`, `###`)
- Use fenced code blocks with language identifiers
- Use admonitions for notes and warnings
- Reference PlantUML diagrams where applicable
