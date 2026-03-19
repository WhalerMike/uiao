import yaml
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "canon" / "uiao_leadership_briefing_v1.0.yaml"
TEMPLATES_DIR = ROOT / "templates"
DOCS_DIR = ROOT / "docs"

def load_canon():
    with CANON.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def render_template(env, template_name, context, output_name):
    template = env.get_template(template_name)
    output = template.render(**context)
    out_path = DOCS_DIR / output_name
    out_path.write_text(output, encoding="utf-8")

def main():
    context = load_canon()
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)

    mapping = {
        "leadership_briefing_v1.0.md.j2": "leadership_briefing_v1.0.md",
        "program_vision_v1.0.md.j2": "program_vision_v1.0.md",
        "unified_architecture_v1.0.md.j2": "unified_architecture_v1.0.md",
        "tic3_roadmap_v1.0.md.j2": "tic3_roadmap_v1.0.md",
        "modernization_timeline_v1.0.md.j2": "modernization_timeline_v1.0.md",
        "fedramp22_summary_v1.0.md.j2": "fedramp22_summary_v1.0.md",
        "zero_trust_narrative_v1.0.md.j2": "zero_trust_narrative_v1.0.md",
        "identity_plane_deep_dive_v1.0.md.j2": "identity_plane_deep_dive_v1.0.md",
        "telemetry_plane_deep_dive_v1.0.md.j2": "telemetry_plane_deep_dive_v1.0.md",
    }

    DOCS_DIR.mkdir(exist_ok=True)

    for template_name, output_name in mapping.items():
        render_template(env, template_name, context, output_name)

if __name__ == "__main__":
    main()
