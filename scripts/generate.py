#!/usr/bin/env python3
"""Legacy shim - delegates to uiao.generators.docs.

This script is kept for backward compatibility. New code should
import ``build_docs`` from ``uiao.generators.docs``.

Deprecated: Use `uiao generate-docs` CLI command instead.
"""

import logging
import warnings

from uiao.generators.docs import build_docs

warnings.warn(
    "scripts/generate.py is deprecated. Use `uiao generate-docs` instead.",
    DeprecationWarning,
    stacklevel=1,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    build_docs()

