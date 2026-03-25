"""Legacy shim - delegates to uiao_core.generators.docs.

This script is kept for backward compatibility. New code should
import ``build_docs`` from ``uiao_core.generators.docs``.

Deprecated: Use `uiao generate-docs` CLI command instead.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any

from uiao_core.generators.docs import (
    DATA_DIR,
    OVERLAYS_DIR,
    _merge_by_key,
    apply_overlay,
    build_docs,
    load_overlays as _load_overlays_impl,
)

warnings.warn(
    "scripts/generate_docs.py is deprecated. Use `uiao generate-docs` instead.",
    DeprecationWarning,
    stacklevel=1,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_overlays(
    context: dict[str, Any],
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load vendor overlays and apply them to the context.

    This shim uses the module-level ``DATA_DIR`` constant so that tests can
    monkeypatch ``generate_docs.DATA_DIR`` to redirect overlay loading to a
    temporary directory without touching the real data files.
    """
    return _load_overlays_impl(context, data_dir=data_dir if data_dir is not None else DATA_DIR)


if __name__ == "__main__":
    build_docs()
