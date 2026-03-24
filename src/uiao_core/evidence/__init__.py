"""Evidence collection, linking, and bundling sub-package for UIAO-Core.

Provides OSCAL-compliant evidence handling:
- ``collector`` — pluggable connectors for log/scan/policy data sources
- ``linker``    — maps collected artifacts to OSCAL controls and back-matter
- ``bundler``   — packages artifacts into FedRAMP 20x ZIP evidence bundles
"""

from __future__ import annotations

from uiao_core.evidence.bundler import EvidenceBundler
from uiao_core.evidence.collector import EvidenceCollector
from uiao_core.evidence.linker import EvidenceLinker

__all__ = ["EvidenceCollector", "EvidenceLinker", "EvidenceBundler"]
