"""Legacy shim - delegates to uiao.generators.oscal.

This script is kept for backward compatibility. New code should
import ``build_oscal`` from ``uiao.generators.oscal``.

Deprecated: Use `uiao generate-oscal` CLI command instead.
"""

import logging
import warnings

from uiao.generators.oscal import build_oscal

warnings.warn(
    "scripts/generate_oscal.py is deprecated. Use `uiao generate-oscal` instead.",
    DeprecationWarning,
    stacklevel=1,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    build_oscal()

