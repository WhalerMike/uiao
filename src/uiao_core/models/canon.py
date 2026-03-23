"""Pydantic v2 models for the UIAO canon YAML source-of-truth.

Uses extra='allow' for Week 1 flexibility; will be tightened
with strict nested models and field validators in Week 2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel, ConfigDict

from ..config import Settings

settings = Settings()


class LeadershipBriefing(BaseModel):
    """Top-level leadership briefing from canon YAML."""
    executive_summary: str = ""
    program_overview: str = ""
    modernization_need: str = ""
    program_vision: str = ""
    control_planes: List[Dict[str, Any]] = []
    core_concepts: List[Dict[str, Any]] = []
    model_config = ConfigDict(extra="allow")


class CanonModel(BaseModel):
    """Root model for the canon YAML document."""
    version: str = "1.0"
    document: str = ""
    classification: str = "UNCLASSIFIED"
    audience: List[str] = []
    leadership_briefing: LeadershipBriefing = LeadershipBriefing()
    model_config = ConfigDict(extra="allow")


def load_canon(canon_path: Path | None = None) -> CanonModel:
    """Load and validate the canon YAML file.

    Args:
        canon_path: Override path to canon YAML. Defaults to
                    canon/uiao_leadership_briefing_v1.0.yaml.

    Returns:
        Validated CanonModel instance.
    """
    path = canon_path or (
        settings.root_dir / settings.canon_dir
        / "uiao_leadership_briefing_v1.0.yaml"
    )
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return CanonModel.model_validate(data)
