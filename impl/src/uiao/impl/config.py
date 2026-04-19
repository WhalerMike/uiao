"""UIAO Core configuration via Pydantic Settings.

All paths are configurable via UIAO_ prefixed environment variables
or .env file. Defaults assume running from repo root.

Canonical artifacts are split across two locations in the consolidated
monorepo (per ADR-028):

* Reference data (``data/``, ``compliance/``, ``generation-inputs/``)
  lives in the ``core/`` module.
* Governance SSOT (``rules/``, ``schemas/``, KSI library) lives in
  ``src/uiao/`` per the Core Canon invariant in AGENTS.md.

:meth:`Settings.model_post_init` auto-discovers these directories so
source modules that consume ``settings.rules_dir`` /
``settings.data_dir`` / etc. resolve the correct canon location
regardless of whether the caller ran from ``<repo>/impl/`` (monorepo),
``uiao-impl/`` (pre-consolidation sibling checkout), or the old
pre-split monorepo root.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_canon_roots() -> List[Path]:
    """Resolve candidate canon roots in precedence order.

    Each canon-backed field is resolved against the first root in the
    returned list where ``<root>/<field>`` exists. Order of precedence:

    1. ``UIAO_CANON_PATH`` environment variable (single explicit root).
    2. Monorepo layout: ``../core`` and ``../src/uiao`` siblings of CWD
       (post-consolidation; primary expected path since the four-repo
       merge). ``core/`` holds reference data, ``src/uiao/`` holds the
       governance SSOT (rules, schemas, KSI).
    3. Pre-monorepo sibling checkout at ``../uiao-core`` (legacy).

    Returns:
        List of existing roots. May be empty if nothing resolves; callers
        then fall back to CWD-relative defaults.
    """
    env = os.environ.get("UIAO_CANON_PATH")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return [p]

    roots: List[Path] = []
    monorepo_core = (Path.cwd().parent / "core").resolve()
    if (monorepo_core / "data").is_dir():
        roots.append(monorepo_core)
    monorepo_src = (Path.cwd().parent / "src" / "uiao").resolve()
    if (monorepo_src / "rules").is_dir() or (monorepo_src / "schemas").is_dir():
        roots.append(monorepo_src)
    if roots:
        return roots

    sibling = (Path.cwd().parent / "uiao-core").resolve()
    if sibling.exists():
        return [sibling]
    return []


# Backwards-compatible single-root accessor (first element of the list).
def _resolve_canon_root() -> Optional[Path]:
    roots = _resolve_canon_roots()
    return roots[0] if roots else None


# Fields that should be rerouted to a canon root when their CWD-relative
# default does not exist locally but does exist under one of the roots.
_CANON_BACKED_FIELDS: tuple[str, ...] = (
    "canon_dir",
    "data_dir",
    "rules_dir",
    "schemas_dir",
    "compliance_dir",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="UIAO_",
        env_file=".env",
        extra="ignore",
    )

    project_root: Path = Path.cwd()
    root_dir: Path = Path.cwd()
    canon_dir: Path = Path("generation-inputs")
    templates_dir: Path = Path("templates")
    data_dir: Path = Path("data")
    rules_dir: Path = Path("rules")
    exports_dir: Path = Path("exports")
    visuals_dir: Path = Path("visuals")
    schemas_dir: Path = Path("schemas")
    compliance_dir: Path = Path("compliance")

    # PlantUML JAR path for local rendering (no network required).
    # Set UIAO_PLANTUML_JAR=/path/to/plantuml.jar to override.
    # Falls back to plantweb (public plantuml.com) if not set or not found.
    plantuml_jar: Optional[Path] = None

    def model_post_init(self, __context: object) -> None:  # noqa: D401
        """Reroute canon-backed paths to discovered canon roots.

        A field is rerouted only when ALL of the following hold:

        * the current value is a relative ``Path`` (so an explicit absolute
          override via env var or .env is always honoured);
        * the default location does not exist under CWD;
        * at least one candidate canon root contains a directory matching
          the field's default name — the first such root wins.

        This keeps single-repo / pre-split workflows working unchanged
        while letting post-split callers transparently reach canon
        content that is split between ``core/`` (data, compliance) and
        ``src/uiao/`` (rules, schemas, ksi) in the monorepo.
        """
        canon_roots = _resolve_canon_roots()
        if not canon_roots:
            return

        for name in _CANON_BACKED_FIELDS:
            current: Path = getattr(self, name)
            if current.is_absolute():
                continue  # explicit override — respect it
            if current.exists():
                continue  # local copy wins
            for root in canon_roots:
                candidate = root / current
                if candidate.exists():
                    object.__setattr__(self, name, candidate)
                    break
