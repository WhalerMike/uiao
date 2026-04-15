"""Canon path resolution for uiao-impl tests.

Canon (the single source of truth YAMLs, schemas, and generation inputs)
lives in the sibling ``uiao-core`` repository post four-repo-split. Tests
that depend on canon resolve the canon root in this order:

1. ``UIAO_CANON_PATH`` environment variable (set in CI to the uiao-core
   checkout path).
2. Sibling checkout at ``../uiao-core`` (common local dev layout).
3. Legacy in-tree location at the project root (pre-split fallback — will
   fail at assertion time if canon files do not exist, which is the
   correct signal).

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
    sibling = (_PROJECT_ROOT.parent / "uiao-core").resolve()
    if sibling.exists():
        return sibling
    return _PROJECT_ROOT


CANON_ROOT: Path = _resolve_canon_root()
DATA_DIR: Path = CANON_ROOT / "data"
CONTROL_LIBRARY_DIR: Path = DATA_DIR / "control-library"
VENDOR_OVERLAYS_DIR: Path = DATA_DIR / "vendor-overlays"
PLANTUML_CONFIG: Path = DATA_DIR / "plantuml-config.json"
GENERATION_INPUTS_DIR: Path = CANON_ROOT / "generation-inputs"
DIAGRAMS_CANON: Path = GENERATION_INPUTS_DIR / "diagrams.yaml"
JML_LOGIC_CANON: Path = GENERATION_INPUTS_DIR / "uiao_jml_logic_v1.0.yaml"
