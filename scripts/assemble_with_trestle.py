"""Legacy shim - delegates to uiao_core.generators.trestle.

This script is kept for backward compatibility. New code should
import ``assemble_ssp`` from ``uiao_core.generators.trestle``.
"""
import logging

from uiao_core.generators.trestle import assemble_ssp

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    out = assemble_ssp()
    print(f"Assembled SSP written to {out}")
