"""Shared context-loading utilities for UIAO-Core generators.

Extracted from individual generator modules (oscal.py, poam.py, charts.py,
ssp.py, docs.py) to eliminate DRY violations (ADR-0004).

Vendor Overlay support
----------------------
Agencies can drop YAML files into ``data/vendor-overlays/`` to replace
vendor-specific component names without touching the canonical data.
Overlays are deep-merged on top of the fully-loaded context so they have
the final word on any key they define.  See ``data/vendor-overlays/example.yaml``
for a worked example.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from uiao_core.config import Settings


def get_settings() -> Settings:
    """Get or create a Settings instance.

    Falls back to a Settings object with no .env file if the default
    initialization fails (e.g., missing .env in CI).
    """
    try:
        return Settings()
    except Exception:
        return Settings(_env_file=None)


def _deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge *b* into *a* in-place and return *a*.

    - Dicts: recurse.
    - Lists: append then deduplicate while preserving order (keyed by ``id``
      for dicts, or by value for scalars).
    - Scalars: *b* overwrites *a*.
    """
    for key, value in b.items():
        if key in a:
            if isinstance(a[key], dict) and isinstance(value, dict):
                a[key] = _deep_merge(a[key], value)
            elif isinstance(a[key], list) and isinstance(value, list):
                a[key] = _dedupe_list(a[key] + value)
            else:
                a[key] = value
        else:
            a[key] = value
    return a


def _dedupe_list(items: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    deduped: list[Any] = []
    for item in items:
        identifier = item.get("id") if isinstance(item, dict) else item
        if identifier not in seen:
            seen.add(identifier)
            deduped.append(item)
    return deduped


def load_context(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    overlay_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load canon YAML and data/*.yml files into a merged context dict.

    Loading order (later steps override earlier ones):

    1. ``data/*.yml`` files (sorted alphabetically)
    2. Canon YAML (``generation-inputs/uiao_leadership_briefing_v1.0.yaml`` by default)
    3. Vendor overlays from *overlay_dir* (``data/vendor-overlays/*.yaml``,
       sorted alphabetically) – applied last so they win over everything.

    Args:
        canon_path: Path to the canon YAML file. Defaults to
            ``settings.canon_dir / 'uiao_leadership_briefing_v1.0.yaml'``.
        data_dir: Path to the data directory containing .yml data files.
            Defaults to ``settings.data_dir``.
        overlay_dir: Path to the vendor-overlays directory.  Defaults to
            ``data_dir / 'vendor-overlays'``.  Pass ``False`` to disable
            overlay loading entirely.

    Returns:
        Merged context dictionary.
    """
    settings = get_settings()
    if canon_path is None:
        canon_path = settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml"
    if data_dir is None:
        data_dir = settings.data_dir
    canon_path = Path(canon_path)
    data_dir = Path(data_dir)

    context: dict[str, Any] = {}

    # 1. Load data/*.yml files
    if data_dir.exists():
        for yml_file in sorted(data_dir.glob("*.yml")):
            key = yml_file.stem.replace("-", "_")
            with yml_file.open("r", encoding="utf-8") as f:
                context[key] = yaml.safe_load(f) or {}

    # 2. Overlay canon YAML on top
    if canon_path.exists():
        with canon_path.open("r", encoding="utf-8") as f:
            canon_data = yaml.safe_load(f) or {}
        context.update(canon_data)

    # 3. Apply vendor overlays (deep-merge so they win over base + canon)
    if overlay_dir is not False:
        if overlay_dir is None:
            overlay_dir = data_dir / "vendor-overlays"
        overlay_dir = Path(overlay_dir)
        if overlay_dir.exists():
            for ov_file in sorted(overlay_dir.glob("*.yaml")):
                with ov_file.open("r", encoding="utf-8") as f:
                    ov_data = yaml.safe_load(f) or {}
                context = _deep_merge(context, ov_data)

    return context


def load_canon(
    canon_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load a canon YAML file and return its contents as a dict.

    Args:
        canon_path: Path to the canon YAML file. Defaults to
            ``settings.canon_dir / 'uiao_leadership_briefing_v1.0.yaml'``.

    Returns:
        Canon data dictionary.
    """
    settings = get_settings()
    if canon_path is None:
        canon_path = settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml"
    canon_path = Path(canon_path)
    with canon_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
