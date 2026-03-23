"""Legacy shim - delegates to uiao_core.generators.trestle.

This script is kept for backward compatibility. New code should
import ``validate_oscal_artifacts`` from ``uiao_core.generators.trestle``.

Deprecated: Use `uiao validate-ssp` CLI command instead.
"""
import logging
import sys
import warnings

from uiao_core.generators.trestle import validate_oscal_artifacts

warnings.warn(
    "scripts/validate_with_trestle.py is deprecated. Use `uiao validate-ssp` instead.",
    DeprecationWarning,
    stacklevel=1,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    failures = validate_oscal_artifacts()
    sys.exit(1 if failures else 0)
