import yaml
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "canon" / "uiao_leadership_briefing_v1.0.yaml"
DATA_DIR = ROOT / "data"
OVERLAYS_DIR = DATA_DIR / "overlays"
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
                                        # Merge dict keys into top-level context first
                    if isinstance(content, dict):
                        data.update(content)
                    # Then set stem key (overwrites any collision with full dict)
                    data[key] = content
    return data

def _merge_by_key(base_list, overlay_list, key):
    """Merge overlay items into base list by matching on key field.

    For each overlay item, if a matching base item is found (by key value), the
    base item is shallow-updated with the overlay item's fields.  Overlay items
    with no matching base entry are appended as new entries.
    """
    result = [dict(item) for item in base_list]
    index = {item[key]: i for i, item in enumerate(result) if key in item}
    for ov_item in overlay_list:
        item_key = ov_item.get(key)
        if item_key is not None and item_key in index:
            result[index[item_key]].update(ov_item)
        else:
            result.append(dict(ov_item))
    return result

def apply_overlay(context, overlay_data):
    """Merge a single overlay file's data into the context.

    Recognised special keys:
    - ``control_plane_overrides``: merged into the ``control_planes`` list.
      When ``context["control_planes"]`` is a dict with a nested
      ``control_planes`` list (generate_atlas.py style), items are matched
      and updated by ``id``.  When it is a bare list, this key is a no-op
      (those templates render control planes from other context keys).
    - ``fedramp_alignment_overrides``: merged into any
      ``fedramp_20x_control_plane_alignment`` list found either nested inside
      ``context["control_planes"]`` or at the top level of the context,
      matched by ``plane_id``.
    - ``overlay_meta``: skipped (metadata only).
    """
    if "control_plane_overrides" in overlay_data:
        cp = context.get("control_planes")
        if isinstance(cp, dict) and "control_planes" in cp:
            cp["control_planes"] = _merge_by_key(
                cp["control_planes"],
                overlay_data["control_plane_overrides"],
                "id",
            )

    if "fedramp_alignment_overrides" in overlay_data:
        cp = context.get("control_planes")
        if isinstance(cp, dict) and "fedramp_20x_control_plane_alignment" in cp:
            cp["fedramp_20x_control_plane_alignment"] = _merge_by_key(
                cp["fedramp_20x_control_plane_alignment"],
                overlay_data["fedramp_alignment_overrides"],
                "plane_id",
            )
        # Also update the top-level key spread by data.update() in load_data_files()
        if isinstance(context.get("fedramp_20x_control_plane_alignment"), list):
            context["fedramp_20x_control_plane_alignment"] = _merge_by_key(
                context["fedramp_20x_control_plane_alignment"],
                overlay_data["fedramp_alignment_overrides"],
                "plane_id",
            )

def load_overlays(context):
    """Load vendor overlays and apply them to the context.

    Reads ``data/overlay-config.yml`` for the list of active vendors, then
    loads every ``*.yml`` file found under ``data/overlays/<vendor>/`` and
    merges each one into *context* via :func:`apply_overlay`.

    If ``data/overlay-config.yml`` is absent or ``active_overlays`` is empty,
    the function returns *context* unchanged (backward-compatible default).
    """
    config_path = DATA_DIR / "overlay-config.yml"
    if not config_path.exists():
        return context
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    active_overlays = (config or {}).get("active_overlays", [])

    if not OVERLAYS_DIR.exists():
        return context

    for vendor in active_overlays:
        vendor_dir = OVERLAYS_DIR / vendor
        if not vendor_dir.is_dir():
            continue
        for yml_file in sorted(vendor_dir.glob("*.yml")):
            with yml_file.open("r", encoding="utf-8") as f:
                overlay_data = yaml.safe_load(f)
            if overlay_data:
                apply_overlay(context, overlay_data)

    return context

def render_template(env, template_name, context, output_name):
    template = env.get_template(template_name)
    output = template.render(**context)
    out_path = DOCS_DIR / output_name
    out_path.write_text(output, encoding="utf-8")
    return output

def main():
    # Load all data/*.yml files first
    context = load_data_files()

    # Apply vendor overlays (merges vendor-specific content on top of core data)
    context = load_overlays(context)

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
