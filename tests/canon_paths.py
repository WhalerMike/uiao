"""Canon path resolution for uiao tests.

Canon (the single source of truth YAMLs, schemas, and generation inputs)
ships inside the ``uiao`` package at ``src/uiao/canon/``. Tests resolve the
canon root in this order:

1. ``UIAO_CANON_PATH`` environment variable (explicit override).
2. Packaged canon at ``<repo-root>/src/uiao/canon/``.

Usage::

    from canon_paths import CONTROL_LIBRARY_DIR, DIAGRAMS_CANON
"""

from __future__ import annotations

import os
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TESTS_DIR.parent


def _resolve_canon_root() -> Path:
    env = os.environ.get("UIAO_CANON_PATH")
    if env:
        candidate = Path(env).expanduser().resolve()
        if candidate.exists():
            return candidate
    return (_PROJECT_ROOT / "src" / "uiao" / "canon").resolve()


CANON_ROOT: Path = _resolve_canon_root()
DATA_DIR: Path = CANON_ROOT / "data"
CONTROL_LIBRARY_DIR: Path = DATA_DIR / "control-library"
VENDOR_OVERLAYS_DIR: Path = DATA_DIR / "vendor-overlays"
PLANTUML_CONFIG: Path = DATA_DIR / "plantuml-config.json"
CONTROL_PLANES_YML: Path = DATA_DIR / "control-planes.yml"
FEDRAMP_SSP_TEMPLATE: Path = DATA_DIR / "fedramp_ssp_template_structure.yaml"
GENERATION_INPUTS_DIR: Path = CANON_ROOT / "generation-inputs"
DIAGRAMS_CANON: Path = GENERATION_INPUTS_DIR / "diagrams.yaml"
JML_LOGIC_CANON: Path = GENERATION_INPUTS_DIR / "uiao_jml_logic_v1.0.yaml"
LEADERSHIP_BRIEFING: Path = GENERATION_INPUTS_DIR / "uiao_leadership_briefing_v1.0.yaml"
