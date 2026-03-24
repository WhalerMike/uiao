"""Legacy shim - delegates to uiao_core.generators.charts.

This script is kept for backward compatibility. New code should
import ``build_charts`` from ``uiao_core.generators.charts``.

Deprecated: Use `uiao generate-charts` CLI command instead.
"""

import logging
import warnings

from uiao_core.generators.charts import build_charts

warnings.warn(
    "scripts/generate_charts.py is deprecated. Use `uiao generate-charts` instead.",
    DeprecationWarning,
    stacklevel=1,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    build_charts()
