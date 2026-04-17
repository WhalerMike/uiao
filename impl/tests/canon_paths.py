"""Canon path resolution for uiao-impl tests.

Canon (the single source of truth YAMLs, schemas, and generation inputs)
now lives in the ``core/`` sibling module of the consolidated ``uiao``
monorepo. Tests resolve the canon root in this order:

1. ``UIAO_CANON_PATH`` environment variable (explicit override for
   non-default layouts or downstream consumers with custom checkouts).
2. Monorepo layout: ``<repo-root>/core/`` — the canonical location
   since the four-repo consolidation (PR #1). Primary expected path.
3. Pre-monorepo sibling checkout at ``../uiao-core`` (legacy local dev
   layout — kept for any stragglers still operating four-repo locally).
4. Legacy in-tree location at the project root (pre-split fallback —
   will fail at assertion time if canon files do not exist, which is
   the correct signal).

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
    # Monorepo layout: impl/ and core/ are siblings under the repo root.
    monorepo_core = (_PROJECT_ROOT.parent / "core").resolve()
    if (monorepo_core / "data" / "control-library").is_dir():
        return monorepo_core
    # Pre-monorepo sibling-checkout layout.
    sibling = (_PROJECT_ROOT.parent / "uiao-core").resolve()
    if sibling.exists():
        return sibling
    return _PROJECT_ROOT


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
