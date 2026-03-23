"""Legacy shim - delegates to uiao_core.generators.rich_docx.

This script is kept for backward compatibility. New code should
import ``build_rich_docx`` from ``uiao_core.generators.rich_docx``.
"""
import logging

from uiao_core.generators.rich_docx import build_rich_docx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    out = build_rich_docx()
    print(f"Rich DOCX exported -> {out}")
