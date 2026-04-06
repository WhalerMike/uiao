"""UIAO-Core generators package.

Contains OSCAL document generators (SSP, OSCAL CD, POA&M), documentation
generators, chart/visualization builders, PlantUML-to-PNG rendering, Gemini AI
image generation, and canon-driven diagram automation.

Mermaid has been fully removed; all diagram rendering now uses PlantUML (.puml)
via the ``plantuml`` module.
"""

from uiao_core.generators.diagrams import build_diagrams
from uiao_core.generators.docs import build_docs
from uiao_core.generators.gemini_visuals import build_gemini_visuals
from uiao_core.generators.oscal import build_oscal
from uiao_core.generators.plantuml import render_plantuml_dir, render_plantuml_file
from uiao_core.generators.poam import build_poam_export
from uiao_core.generators.pptx import build_pptx
from uiao_core.generators.rich_docx import build_rich_docx
from uiao_core.generators.ssp import build_ssp

__all__ = [
    "build_diagrams",
    "build_docs",
    "build_gemini_visuals",
    "render_plantuml_dir",
    "render_plantuml_file",
    "build_oscal",
    "build_poam_export",
    "build_pptx",
    "build_rich_docx",
    "build_ssp",
]
