"""Document generator.

Migrated from scripts/generate_docs.py into the uiao_core package.
Renders Jinja2 templates against canon YAML + data overlays to produce
Markdown documents for docs/ and site/ directories.
"""
from __future__ import annotations

import yaml
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from typing import Any

from uiao_core.config import Settings


# ---------------------------------------------------------------------------
# Template mapping: template -> (docs_name, site_name)
# ---------------------------------------------------------------------------
DEFAULT_TEMPLATE_MAPPING: dict[str, tuple[str, str]] = {
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


def _get_settings() -> Settings:
    """Get or create Settings instance."""
    try:
        return Settings()
    except Exception:
        return Settings(_env_file=None)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_canon(
    canon_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load the canon YAML file."""
    if canon_path is None:
        settings = _get_settings()
        canon_path = settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml"
    canon_path = Path(canon_path)
    if not canon_path.exists():
        return {}
    with canon_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_data_files(
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load all YAML files from data/ directory and merge into context."""
    if data_dir is None:
        settings = _get_settings()
        data_dir = settings.data_dir
    data_dir = Path(data_dir)
    data: dict[str, Any] = {}
    if not data_dir.exists():
        return data
    for yml_file in sorted(data_dir.glob("*.yml")):
        key = yml_file.stem.replace("-", "_")
        with yml_file.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        if content:
            if isinstance(content, dict):
                data.update(content)
            data[key] = content
    return data


def _merge_by_key(
    base_list: list[dict[str, Any]],
    overlay_list: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    """Merge overlay items into base list by matching on key field."""
    result = [dict(item) for item in base_list]
    index = {item[key]: i for i, item in enumerate(result) if key in item}
    for ov_item in overlay_list:
        item_key = ov_item.get(key)
        if item_key is not None and item_key in index:
            result[index[item_key]].update(ov_item)
        else:
            result.append(dict(ov_item))
    return result


def apply_overlay(
    context: dict[str, Any],
    overlay_data: dict[str, Any],
) -> None:
    """Merge a single overlay file's data into the context."""
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
        if isinstance(context.get("fedramp_20x_control_plane_alignment"), list):
            context["fedramp_20x_control_plane_alignment"] = _merge_by_key(
                context["fedramp_20x_control_plane_alignment"],
                overlay_data["fedramp_alignment_overrides"],
                "plane_id",
            )


def load_overlays(
    context: dict[str, Any],
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load vendor overlays and apply them to the context."""
    if data_dir is None:
        settings = _get_settings()
        data_dir = settings.data_dir
    data_dir = Path(data_dir)
    overlays_dir = data_dir / "overlays"
    config_path = data_dir / "overlay-config.yml"
    if not config_path.exists():
        return context
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    active_overlays = (config or {}).get("active_overlays", [])
    if not overlays_dir.exists():
        return context
    for vendor in active_overlays:
        vendor_dir = overlays_dir / vendor
        if not vendor_dir.is_dir():
            continue
        for yml_file in sorted(vendor_dir.glob("*.yml")):
            with yml_file.open("r", encoding="utf-8") as f:
                overlay_data = yaml.safe_load(f)
            if overlay_data:
                apply_overlay(context, overlay_data)
    return context


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_template(
    env: Environment,
    template_name: str,
    context: dict[str, Any],
    output_path: Path,
) -> str:
    """Render a single Jinja2 template and write to output_path."""
    template = env.get_template(template_name)
    output = template.render(**context)
    output_path.write_text(output, encoding="utf-8")
    return output


def build_docs(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    docs_dir: str | Path | None = None,
    site_dir: str | Path | None = None,
    template_mapping: dict[str, tuple[str, str]] | None = None,
) -> list[str]:
    """Build all documentation from templates.

    Returns list of generated file paths.
    """
    settings = _get_settings()
    if templates_dir is None:
        templates_dir = settings.project_root / "templates"
    if docs_dir is None:
        docs_dir = settings.project_root / "docs"
    if site_dir is None:
        site_dir = settings.project_root / "site"
    if template_mapping is None:
        template_mapping = DEFAULT_TEMPLATE_MAPPING

    templates_dir = Path(templates_dir)
    docs_dir = Path(docs_dir)
    site_dir = Path(site_dir)

    # Load context: data files first, then overlays, then canon overwrites
    context = load_data_files(data_dir)
    context = load_overlays(context, data_dir)
    canon_context = load_canon(canon_path)
    context.update(canon_context)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )

    docs_dir.mkdir(exist_ok=True)
    site_dir.mkdir(exist_ok=True)

    generated: list[str] = []
    for tpl_name, (docs_name, site_name) in template_mapping.items():
        out_path = docs_dir / docs_name
        output = render_template(env, tpl_name, context, out_path)
        # Also write to site/ with hyphenated name
        (site_dir / site_name).write_text(output, encoding="utf-8")
        # Also write versioned copy to site/
        (site_dir / docs_name).write_text(output, encoding="utf-8")
        generated.append(str(out_path))

    return generated
