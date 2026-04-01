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
# Ensure this matches your project's region/endpoint if necessary
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


def call_image_api(prompt):
    """Calls the Imagen API with exponential backoff for reliability."""
    payload = {
        "instances": [{"prompt": f"{STYLE_GUIDE}\n\nSubject: {prompt}"}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "1:1",
            "outputOptions": {"mimeType": "image/png"}
        }
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


def process_templates():
    """Scans src/templates, generates diagrams via Gemini, and prepares build files."""
    template_files = glob.glob("src/templates/**/*.md", recursive=True)

    # We store images in a central assets folder that Pandoc can reach
    assets_dir = Path("assets/generated_diagrams")
    assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(template_files)} templates to process.")

    for template_path in template_files:
        with open(template_path, encoding='utf-8') as f:
            content = f.read()

        # Regex to match ```mermaid or ```diagram blocks
        # This captures the content within the block regardless of minor whitespace
        pattern = r'```(?:mermaid|diagram)\s*\n(.*?)\n```'
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
                with open(image_path, 'wb') as img_file:
                    img_file.write(base64.b64decode(image_data))

                # Replace the code block with a Markdown image link
                # Path is relative from build/templates/ to assets/
                relative_path = f"../../assets/generated_diagrams/{image_filename}"
                replacement = f"![UIAO Architecture Diagram]({relative_path})"
                content = content[:match.start()] + replacement + content[match.end():]
                print(f"    Success: {image_filename}")
            else:
                print(f"    FAILED: Could not generate image for block in {template_path}")

        # Save the processed template to the build directory
        build_path = Path("build/templates") / Path(template_path).relative_to("src/templates")
        build_path.parent.mkdir(parents=True, exist_ok=True)
        with open(build_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Saved processed template: {build_path}")


if __name__ == "__main__":
    print("UIAO-Core Gemini Diagram Generator")
    print("===================================")
    process_templates()
    print("\nDiagram generation complete.")
