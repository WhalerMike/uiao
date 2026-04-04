"""Document generator.

Migrated from scripts/generate_docs.py into the uiao_core package.
Renders Jinja2 templates against canon YAML + data overlays to produce
Markdown documents for docs/ and site/ directories.

After template rendering, diagram generation is triggered automatically via
:func:`generate_diagrams_from_canon`. A post-processing step then replaces
``mermaid`` fenced code blocks in rendered Markdown with ``<img>`` references
to the pre-rendered PNGs, enabling DOCX/PPTX/PDF compatibility where live JS
is unavailable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from uiao_core.utils.context import get_settings, load_canon

# ---------------------------------------------------------------------------
# Module-level path constants (overridable for testing via monkeypatch)
# ---------------------------------------------------------------------------
_settings = get_settings()
DATA_DIR: Path = _settings.data_dir
OVERLAYS_DIR: Path = DATA_DIR / "overlays"

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
    "executive_summary_v1.0.md.j2": ("executive_summary_v1.0.md", "executive-summary.md"),
    "fedramp_ssp_narrative_full_v1.0.md.j2": (
        "fedramp_ssp_narrative_full_v1.0.md",
        "fedramp-ssp-narrative.md",
    ),
    "authorization_boundary_v1.0.md.j2": (
        "authorization_boundary_v1.0.md",
        "authorization-boundary.md",
    ),
    "system_inventory_and_components_v1.0.md.j2": (
        "system_inventory_and_components_v1.0.md",
        "system-inventory.md",
    ),
    "crosswalk_index_v1.0.md.j2": ("crosswalk_index_v1.0.md", "crosswalk-index.md"),
    "fedramp_crosswalk_v1.0.md.j2": ("fedramp_crosswalk_v1.0.md", "fedramp-crosswalk.md"),
    "management_stack_v1.0.md.j2": ("management_stack_v1.0.md", "management-stack.md"),
}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------
def load_data_files(
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load all YAML files from data/ directory and merge into context."""
    if data_dir is None:
        settings = get_settings()
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
        data_dir = DATA_DIR
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


# ---------------------------------------------------------------------------
# Mermaid block post-processing
# ---------------------------------------------------------------------------
_MERMAID_FENCE_RE = re.compile(
    r"```mermaid\n(.*?)```",
    re.DOTALL,
)


def replace_mermaid_blocks_with_images(
    markdown_text: str,
    images_dir: str = "assets/images/mermaid",
    alt_prefix: str = "diagram",
) -> str:
    """Replace fenced ``mermaid`` code blocks with ``<img>`` references.

    This post-processing step enables DOCX/PPTX/PDF renderers (which cannot
    execute JavaScript) to embed pre-rendered PNG images in place of raw
    Mermaid source blocks.

    The replacement uses an HTML ``<img>`` tag rather than a Markdown
    ``![]()`` shorthand so that the ``alt`` attribute is preserved verbatim
    and works across both MkDocs HTML and python-docx pipelines.

    Args:
        markdown_text: The Markdown content to process.
        images_dir: Relative path prefix for PNG image URLs.
        alt_prefix: Fallback prefix for ``alt`` text when no title can be
            inferred from the diagram source.

    Returns:
        Markdown text with each ``mermaid`` fence replaced by an ``<img>``
        referencing ``<images_dir>/<alt_prefix>_<n>.png`` where *n* is the
        1-based occurrence index.
    """
    counter = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        src = match.group(1).strip()
        # Try to infer a slug from the first non-empty line of the source
        first_line = next((ln.strip() for ln in src.splitlines() if ln.strip()), "")
        slug = re.sub(r"[^a-z0-9_-]", "_", first_line.lower())[:40].strip("_") or f"{alt_prefix}_{counter}"
        img_url = f"{images_dir}/{slug}.png"
        return f'<img src="{img_url}" alt="{slug}" />'

    return _MERMAID_FENCE_RE.sub(_replace, markdown_text)


def build_docs(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    docs_dir: str | Path | None = None,
    site_dir: str | Path | None = None,
    template_mapping: dict[str, tuple[str, str]] | None = None,
    generate_diagrams: bool = True,
    force_visuals: bool = False,
) -> list[str]:
    """Build all documentation from templates.

    After rendering templates, optionally auto-generates Mermaid diagrams
    from ``generation-inputs/diagrams.yaml`` and replaces fenced ``mermaid`` blocks in
    the rendered Markdown with ``<img>`` references to pre-rendered PNGs.

    Args:
        canon_path: Path to the canon YAML file.
        data_dir: Path to the data YAML directory.
        templates_dir: Path to Jinja2 templates directory.
        docs_dir: Output directory for Markdown documents.
        site_dir: Output directory for site copies.
        template_mapping: Override the default template→output mapping.
        generate_diagrams: When ``True`` (default), call
            :func:`generate_diagrams_from_canon` before template rendering.
        force_visuals: Passed through to the diagram renderer; forces
            re-render even when a cached PNG already exists.

    Returns:
        List of generated file paths (docs/*.md).
    """
    settings = get_settings()
    if templates_dir is None:
        templates_dir = settings.root_dir / "templates"
    if docs_dir is None:
        docs_dir = settings.root_dir / "docs"
    if site_dir is None:
        site_dir = settings.root_dir / "site"
    if template_mapping is None:
        template_mapping = DEFAULT_TEMPLATE_MAPPING

    templates_dir = Path(templates_dir)
    docs_dir = Path(docs_dir)
    site_dir = Path(site_dir)

    # Auto-generate diagrams from canon before rendering templates
    if generate_diagrams:
        from uiao_core.generators.diagrams import generate_diagrams_from_canon

        generate_diagrams_from_canon(canon_path=canon_path, force=force_visuals)

    # Load context: data files first, then overlays, then canon overwrites
    context = load_data_files(data_dir)
    context = load_overlays(context, data_dir)
    canon_context = load_canon(canon_path)
    context.update(canon_context)

    # Safe default for perimeter_collapse (legacy stub for tic3_roadmap template)
    context.setdefault(
        "perimeter_collapse",
        {
            "transitions": [],
            "description": "Perimeter collapse model (legacy stub)",
            "current_state": "hub-spoke private endpoints",
            "target_state": "full zero-trust segmentation",
        },
    )

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
        # Post-process: replace mermaid fences with <img> tags for PDF/DOCX
        processed = replace_mermaid_blocks_with_images(output)
        out_path.write_text(processed, encoding="utf-8")
        # Also write to site/ with hyphenated name
        (site_dir / site_name).write_text(processed, encoding="utf-8")
        # Also write versioned copy to site/
        (site_dir / docs_name).write_text(processed, encoding="utf-8")
        generated.append(str(out_path))

    return generated
