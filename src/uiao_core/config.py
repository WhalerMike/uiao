"""UIAO Core configuration via Pydantic Settings.

All paths are configurable via UIAO_ prefixed environment variables
or .env file. Defaults assume running from repo root.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    exports_dir: Path = Path("exports")
    visuals_dir: Path = Path("visuals")
    schemas_dir: Path = Path("schemas")
    compliance_dir: Path = Path("compliance")

    # PlantUML JAR path for local rendering (no network required).
    # Set UIAO_PLANTUML_JAR=/path/to/plantuml.jar to override.
    # Falls back to plantweb (public plantuml.com) if not set or not found.
    plantuml_jar: Optional[Path] = None
