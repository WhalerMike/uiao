"""Pydantic v2 models for the UIAO canon YAML source-of-truth.

Uses extra='allow' for Week 1 flexibility; will be tightened with strict
nested models and field validators in Week 2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from ..config import Settings

settings = Settings()


class CanonEntry(BaseModel):
    """Generic canon entry with flexible extra fields."""

    id: str
    name: str
    description: str = ""
    category: str = ""
    model_config = ConfigDict(extra="allow")


class DiagramDefinition(BaseModel):
    """Definition of a single PlantUML diagram in the canon ``diagrams:`` section."""

    title: str = ""
    type: str = ""
    description: str = ""
    include_in: list[str] = []
    content: str = ""
    model_config = ConfigDict(extra="allow")


class LeadershipBriefing(BaseModel):
    """Top-level leadership briefing from canon YAML."""

    executive_summary: str = ""
    program_overview: str = ""
    modernization_need: str = ""
    program_vision: str = ""
    control_planes: list[dict[str, Any]] = []
    core_concepts: list[dict[str, Any]] = []
    model_config = ConfigDict(extra="allow")


class CanonModel(BaseModel):
    """Full canon document model."""

    version: str = ""
    document: str = ""
    classification: str = ""
    audience: list[str] = []
    leadership_briefing: LeadershipBriefing = LeadershipBriefing()
    diagrams: dict[str, DiagramDefinition] = {}
    model_config = ConfigDict(extra="allow")


def load_canon(canon_path: Path | None = None) -> CanonModel:
    """Load and validate a canon YAML file."""
    path = canon_path or (settings.root_dir / settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return CanonModel.model_validate(data)
