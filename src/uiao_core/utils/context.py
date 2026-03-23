"""Shared context-loading utilities for UIAO-Core generators.

Extracted from individual generator modules (oscal.py, poam.py, charts.py,
ssp.py, docs.py) to eliminate DRY violations (ADR-0004).
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


def load_context(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load canon YAML and data/*.yml files into a merged context dict.

    Loads data directory files first (sorted alphabetically), then overlays
    the canon YAML on top so canon values take precedence.

    Args:
        canon_path: Path to the canon YAML file. Defaults to
            ``settings.canon_dir / 'uiao_leadership_briefing_v1.0.yaml'``.
        data_dir: Path to the data directory containing .yml overlays.
            Defaults to ``settings.data_dir``.

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

    # Load data/*.yml files first
    if data_dir.exists():
        for yml_file in sorted(data_dir.glob("*.yml")):
            key = yml_file.stem.replace("-", "_")
            with yml_file.open("r", encoding="utf-8") as f:
                context[key] = yaml.safe_load(f) or {}

    # Overlay canon YAML on top
    if canon_path.exists():
        with canon_path.open("r", encoding="utf-8") as f:
            canon_data = yaml.safe_load(f) or {}
        context.update(canon_data)

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
