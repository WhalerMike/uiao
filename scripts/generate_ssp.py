"""Legacy shim - delegates to uiao_core.generators.ssp.

This script is kept for backward compatibility. New code should
import ``build_ssp`` from ``uiao_core.generators.ssp``.

Deprecated: Use `uiao generate-ssp` CLI command instead.
"""
import logging
import warnings

from uiao_core.generators.ssp import build_ssp

warnings.warn(
    "scripts/generate_ssp.py is deprecated. Use `uiao generate-ssp` instead.",
    DeprecationWarning,
    stacklevel=1,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    build_ssp()
