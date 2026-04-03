#!/usr/bin/env python3
"""Quarto Pre-Render Script for UIAO Document Pipeline.

Bridges the Jinja2 template pipeline to Quarto by injecting YAML frontmatter
into generated Markdown files. Reads document metadata from
data/quarto-frontmatter.yml and prepends it to each matching .md file in docs/.

This script runs AFTER generate_docs.py and BEFORE quarto render.
"""

import re

import yaml
from pathlib import Path

DOCS_DIR = Path("docs")
FRONTMATTER_FILE = Path("data/quarto-frontmatter.yml")
DEFAULT_AUTHOR = "UIAO Modernization Program"


def load_frontmatter_config() -> dict:
    """Load the frontmatter mapping configuration."""
    if not FRONTMATTER_FILE.exists():
        print(f"[quarto-pre-render] WARNING: {FRONTMATTER_FILE} not found. Using defaults.")
        return {"documents": {}}
    with open(FRONTMATTER_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"documents": {}}


def build_frontmatter(doc_key: str, config: dict, filename: str) -> str:
    """Build YAML frontmatter string for a document."""
    doc_config = config.get("documents", {}).get(doc_key, {})
    title = doc_config.get("title", filename.replace("_", " ").replace(".md", "").title())
    subtitle = doc_config.get("subtitle", "")
    author = doc_config.get("author", DEFAULT_AUTHOR)
    classification = doc_config.get("classification", "")
    formats = doc_config.get("formats", ["html", "docx", "pdf", "gfm"])

    lines = ["---"]
    lines.append(f'title: "{title}"')
    if subtitle:
        lines.append(f'subtitle: "{subtitle}"')
    lines.append(f'author: "{author}"')
    lines.append("date: today")
    lines.append('date-format: "MMMM D, YYYY"')
    if classification:
        lines.append(f'classification: "{classification}"')

    # Format-specific overrides
    if "pptx" in formats:
        slide_level = doc_config.get("slide-level", 2)
        lines.append("format:")
        for fmt in formats:
            if fmt == "pptx":
                lines.append("  pptx:")
                lines.append(f"    slide-level: {slide_level}")
            else:
                lines.append(f"  {fmt}: default")
    else:
        lines.append("format:")
        for fmt in formats:
            lines.append(f"  {fmt}: default")

    lines.append("---")
    return "\n".join(lines) + "\n\n"


def has_frontmatter(content: str) -> bool:
    """Check if file already has YAML frontmatter."""
    stripped = content.lstrip()
    return stripped.startswith("---")


def derive_doc_key(filename: str) -> str:
    """Derive document key from filename for frontmatter lookup."""
    key = filename.replace(".md", "")
    # Remove version suffixes like _v1.0, _v2.1
    key = re.sub(r"_v\d+\.\d+$", "", key)
    # Convert to kebab-case for lookup
    key = key.replace("_", "-").lower()
    return key


def inject_frontmatter():
    """Scan docs/ and inject YAML frontmatter into generated Markdown files."""
    config = load_frontmatter_config()
    md_files = sorted(DOCS_DIR.rglob("*.md"))

    if not md_files:
        print("[quarto-pre-render] No .md/.qmd files found in docs/. Nothing to process.")
        return

    injected = 0
    skipped = 0

    for md_file in md_files:
        # Skip index/navigation files that MkDocs uses
        if md_file.name in ("index.md", "nav.md", "README.md"):
            skipped += 1
            continue

        content = md_file.read_text(encoding="utf-8")

        if has_frontmatter(content):
            print(f"[quarto-pre-render] SKIP (has frontmatter): {md_file}")
            skipped += 1
            continue

        doc_key = derive_doc_key(md_file.stem)
        frontmatter = build_frontmatter(doc_key, config, md_file.name)
        md_file.write_text(frontmatter + content, encoding="utf-8")
        print(f"[quarto-pre-render] INJECT: {md_file} (key={doc_key})")
        injected += 1

    print(f"\n[quarto-pre-render] Complete: {injected} injected, {skipped} skipped, {injected + skipped} total")


if __name__ == "__main__":
    inject_frontmatter()
