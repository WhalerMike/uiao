"""SSP (System Security Plan) generator.

Builds OSCAL-compliant SSP JSON from canon YAML sources.
Wraps the existing scripts/generate_ssp.py logic into
a clean, importable module.
"""
from __future__ import annotations

from pathlib import Path


def build_ssp(
    canon_path: str | Path,
    output_path: str | Path = "exports/ssp.json",
) -> Path:
    """Generate an OSCAL SSP from canon YAML files.

    Args:
        canon_path: Directory containing canon YAML sources.
        output_path: Destination for the generated SSP JSON.

    Returns:
        Path to the written SSP file.

    Raises:
        FileNotFoundError: If canon_path does not exist.
        NotImplementedError: Placeholder until migration from scripts/.
    """
    canon = Path(canon_path)
    output = Path(output_path)

    if not canon.exists():
        msg = f"Canon directory not found: {canon}"
        raise FileNotFoundError(msg)

    # TODO(Week 2): Migrate logic from scripts/generate_ssp.py
    # This stub ensures the CLI and import paths work now.
    raise NotImplementedError(
        "SSP generation not yet migrated to uiao_core.generators.ssp. "
        "Use scripts/generate_ssp.py directly for now."
    )
