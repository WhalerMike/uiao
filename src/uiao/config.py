"""UIAO configuration via Pydantic Settings.

All paths are configurable via ``UIAO_`` prefixed environment variables or a
``.env`` file. Defaults assume running from the repo root (or any directory
where the installed ``uiao`` package is importable).

Canonical artifacts (``canon/``, ``rules/``, ``schemas/``, ``compliance/``)
ship inside the package at ``src/uiao/``. :meth:`Settings.model_post_init`
auto-discovers those directories so modules consuming ``settings.canon_dir``
/ ``settings.data_dir`` / etc. resolve to the packaged location regardless
of CWD.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_canon_root() -> Optional[Path]:
    """Resolve the canon root if discoverable.

    Order of precedence:

    1. ``UIAO_CANON_PATH`` environment variable.
    2. Packaged canon: the directory containing this module
       (``src/uiao/``) — the primary path in the consolidated repo.
    3. ``None`` — caller falls back to CWD-relative defaults.
    """
    env = os.environ.get("UIAO_CANON_PATH")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p
    pkg_root = Path(__file__).resolve().parent
    if (pkg_root / "canon" / "data").is_dir() or (pkg_root / "rules").is_dir():
        return pkg_root
    return None


# Fields that are rerouted to the packaged canon root when their
# CWD-relative default does not exist locally but does exist under
# the canon root.
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
        """Reroute canon-backed paths to the packaged canon when present.

        A field is rerouted only when ALL of the following hold:

        * the current value is a relative ``Path`` (so an explicit absolute
          override via env var or .env is always honoured);
        * the default location does not exist under CWD;
        * the packaged canon root contains a directory with the same name.
        """
        canon_root = _resolve_canon_root()
        if canon_root is None:
            return

        for name in _CANON_BACKED_FIELDS:
            current: Path = getattr(self, name)
            if current.is_absolute():
                continue  # explicit override — respect it
            if current.exists():
                continue  # local copy wins
            candidate = canon_root / current
            if candidate.exists():
                object.__setattr__(self, name, candidate)
