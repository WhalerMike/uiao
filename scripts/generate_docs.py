import yaml
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "canon" / "uiao_leadership_briefing_v1.0.yaml"
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
DOCS_DIR = ROOT / "docs"
SITE_DIR = ROOT / "site"

def load_canon():
    with CANON.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_data_files():
    """Load all YAML files from data/ directory and merge into context."""
    data = {}
    if DATA_DIR.exists():
        for yml_file in sorted(DATA_DIR.glob("*.yml")):
            key = yml_file.stem.replace("-", "_")
            with yml_file.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                if content:
                    data[key] = content
    return data

def render_template(env, template_name, context, output_name):
    template = env.get_template(template_name)
    output = template.render(**context)
    out_path = DOCS_DIR / output_name
    out_path.write_text(output, encoding="utf-8")
    return output

def main():
    # Load all data/*.yml files first
    context = load_data_files()

    # Load canon YAML (primary context - overwrites data keys)
    canon_context = load_canon()
    context.update(canon_context)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)

    # Mapping: template -> docs output name -> site output name (hyphenated)
    mapping = {
        "leadership_briefing_v1.0.md.j2": ("leadership_briefing_v1.0.md", "leadership-briefing.md"),
        "program_vision_v1.0.md.j2": ("program_vision_v1.0.md", "program-vision.md"),
        "unified_architecture_v1.0.md.j2": ("unified_architecture_v1.0.md", "unified-architecture.md"),
        "tic3_roadmap_v1.0.md.j2": ("tic3_roadmap_v1.0.md", "tic3-roadmap.md"),
        "modernization_timeline_v1.0.md.j2": ("modernization_timeline_v1.0.md", "modernization-timeline.md"),
        "fedramp22_summary_v1.0.md.j2": ("fedramp22_summary_v1.0.md", "fedramp22_summary_v1.0.md"),
        "zero_trust_narrative_v1.0.md.j2": ("zero_trust_narrative_v1.0.md", "zero_trust_narrative_v1.0.md"),
        "identity_plane_deep_dive_v1.0.md.j2": ("identity_plane_deep_dive_v1.0.md", "identity_plane_deep_dive_v1.0.md"),
        "telemetry_plane_deep_dive_v1.0.md.j2": ("telemetry_plane_deep_dive_v1.0.md", "telemetry_plane_deep_dive_v1.0.md"),
        "vendor_stack_v1.0.md.j2": ("vendor_stack_v1.0.md", "vendor-stack.md"),
                "seven_layer_model_v1.0.md.j2": ("seven_layer_model_v1.0.md", "seven-layer-model.md"),
    }

    DOCS_DIR.mkdir(exist_ok=True)
    SITE_DIR.mkdir(exist_ok=True)

    for template_name, (docs_name, site_name) in mapping.items():
        output = render_template(env, template_name, context, docs_name)
        # Also write to site/ with hyphenated name for the custom index.html
        site_path = SITE_DIR / site_name
        site_path.write_text(output, encoding="utf-8")
        # Also write versioned copy to site/
        site_v_path = SITE_DIR / docs_name
        site_v_path.write_text(output, encoding="utf-8")

if __name__ == "__main__":
    main()
