#!/usr/bin/env python3
"""
UIAO-Core Gemini Diagram Generator
===================================
Scans src/templates/**/*.md and any files tagged diagram-owner: gemini
for plantuml/diagram code blocks, generates AI images via Imagen 4.0,
and writes processed output to build/templates/ for Pandoc compilation.

ROUTING: Only processes files in src/templates/ or files with
diagram-owner: gemini in YAML frontmatter.

Ref: generation-inputs/DIAGRAM-STANDARDS.md
"""

import os
import re
import uuid
import glob
import json
import time
import base64
import requests
from pathlib import Path

# API Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "imagen-4.0-generate-001"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:predict?key={API_KEY}"

if not API_KEY:
    print("Error: GEMINI_API_KEY environment variable is not set. Please add it to GitHub Secrets.")
    exit(1)

# Professional Style Guide for UIAO-Core Architectural Diagrams
STYLE_GUIDE = (
    "A professional, high-resolution architectural diagram. "
    "MANDATORY: Strictly white background, no shadows, no gradients, no 3D effects. "
    "Style: Clean, sharp black lines, professional technical blueprint aesthetic, sans-serif labeling. "
    "Composition: Centered, balanced, clear whitespace. "
    "Quality: Vector-style illustration suitable for a FedRAMP technical specification. "
    "Avoid: Artistic flourishes, dark backgrounds, or blurry lines."
)


def is_gemini_owned(filepath):
    """Check if a file is owned by the Gemini pipeline.

    Returns True if:
    - File is in src/templates/ (folder-based routing)
    - File has diagram-owner: gemini in YAML frontmatter (tag-based routing)
    """
    # Folder-based: src/templates/ is always Gemini territory
    if str(filepath).startswith("src/templates/"):
        return True
    # Tag-based: check YAML frontmatter
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                import yaml

                fm = yaml.safe_load(content[3:end])
                if isinstance(fm, dict) and fm.get("diagram-owner") == "gemini":
                    return True
    except Exception:
        pass
    return False


def call_image_api(prompt):
    """Calls the Imagen API with exponential backoff for reliability."""
    payload = {
        "instances": [{"prompt": f"{STYLE_GUIDE}\n\nSubject: {prompt}"}],
        "parameters": {"sampleCount": 1, "aspectRatio": "1:1", "outputOptions": {"mimeType": "image/png"}},
    }
    headers = {"Content-Type": "application/json"}
    max_retries = 5
    delay = 1
    for _attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                result = response.json()
                if "predictions" in result and len(result["predictions"]) > 0:
                    return result["predictions"][0]["bytesBase64Encoded"]
            if response.status_code == 429:  # Rate limited
                print(f"Rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue
            print(f"API Error ({response.status_code}): {response.text}")
            break
        except Exception as e:
            print(f"Connection error: {e}")
            time.sleep(delay)
            delay *= 2
    return None


def collect_gemini_files():
    """Collect all Markdown files owned by the Gemini pipeline."""
    files = []
    # Primary: src/templates/**/*.md (always Gemini-owned)
    for f in glob.glob("src/templates/**/*.md", recursive=True):
        files.append(f)
    # Secondary: scan other dirs for files tagged diagram-owner: gemini
    for pattern in ["docs/**/*.md", "docs/**/*.qmd", "generation-inputs/**/*.md", "templates/**/*.md"]:
        for f in glob.glob(pattern, recursive=True):
            if is_gemini_owned(f):
                files.append(f)
    return list(set(files))  # deduplicate


def process_templates():
    """Scans Gemini-owned files, generates diagrams, and prepares build files."""
    template_files = collect_gemini_files()

    # We store images in a central assets folder that Pandoc can reach
    assets_dir = Path("assets/generated_diagrams")
    assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(template_files)} Gemini-owned file(s) to process.")
    if not template_files:
        print("No files to process. Create src/templates/*.md or tag files with diagram-owner: gemini.")
        # Ensure build dir exists for compile.sh
        Path("build/templates").mkdir(parents=True, exist_ok=True)
        return

    for template_path in template_files:
        with open(template_path, encoding="utf-8") as f:
            content = f.read()

        # Regex to match ```plantuml or ```diagram blocks
        pattern = r"```(?:plantuml|diagram)\s*\n(.*?)\n```"
        matches = list(re.finditer(pattern, content, re.DOTALL))
        if not matches:
            continue

        print(f"  Processing {template_path}: {len(matches)} diagram(s) found.")

        # Replace blocks in reverse order to preserve string positions
        for match in reversed(matches):
            diagram_text = match.group(1).strip()
            image_id = str(uuid.uuid4())[:8]
            image_filename = f"diagram_{image_id}.png"
            image_path = assets_dir / image_filename

            print(f"    Generating: {image_filename}...")
            image_data = call_image_api(diagram_text)

            if image_data:
                with open(image_path, "wb") as img_file:
                    img_file.write(base64.b64decode(image_data))
                # Replace the code block with a Markdown image link
                # Path is relative from build/templates/ to assets/
                relative_path = f"../../assets/generated_diagrams/{image_filename}"
                replacement = f"![UIAO Architecture Diagram]({relative_path})"
                content = content[: match.start()] + replacement + content[match.end() :]
                print(f"    Success: {image_filename}")
            else:
                print(f"    FAILED: Could not generate image for block in {template_path}")

        # Determine build output path
        tp = Path(template_path)
        if str(tp).startswith("src/templates/"):
            build_path = Path("build/templates") / tp.relative_to("src/templates")
        else:
            # For tagged files outside src/templates/, mirror the path under build/
            build_path = Path("build") / tp
        build_path.parent.mkdir(parents=True, exist_ok=True)
        with open(build_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"    Saved processed template: {build_path}")


if __name__ == "__main__":
    print("UIAO-Core Gemini Diagram Generator")
    print("===================================")
    print("Routing: src/templates/ + diagram-owner: gemini tagged files")
    print("Ref: generation-inputs/DIAGRAM-STANDARDS.md")
    print()
    process_templates()
    print("\nDiagram generation complete.")
