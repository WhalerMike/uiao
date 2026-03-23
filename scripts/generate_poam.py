"""Legacy shim - delegates to uiao_core.generators.poam.

This script is kept for backward compatibility. New code should
import ``build_poam_export`` from ``uiao_core.generators.poam``.

Deprecated: Use `uiao generate-poam` CLI command instead.
"""
import warnings
import logging

warnings.warn(
    "scripts/generate_poam.py is deprecated. Use `uiao generate-poam` instead.",
    DeprecationWarning,
    stacklevel=1,
)

from uiao_core.generators.poam import build_poam_export

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    build_poam_export()
