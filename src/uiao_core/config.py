"""UIAO Core configuration via Pydantic Settings.

All paths are configurable via UIAO_ prefixed environment variables
or .env file. Defaults assume running from repo root.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="UIAO_",
        env_file=".env",
        extra="ignore",
    )

    root_dir: Path = Path.cwd()
    canon_dir: Path = Path("canon")
    templates_dir: Path = Path("templates")
    data_dir: Path = Path("data")
    exports_dir: Path = Path("exports")
    schemas_dir: Path = Path("schemas")
    compliance_dir: Path = Path("compliance")
