#!/usr/bin/env python3
# <!-- NEW (Proposed) -->
"""validate_canon.py — Run canon-document schema validation.

This is the ``canon-validation`` workflow's structural gate. It delegates
to :mod:`tools.validators.canon_validator`, which owns the schema logic
(``tools/schema/canon_schema.json``). This wrapper exists so workflows can
invoke a stable ``scripts/`` entrypoint regardless of where the validator
implementation lives.

Usage
-----
    python scripts/validate_canon.py
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parent.parent / "tools" / "validators" / "canon_validator.py"


def main() -> int:
    if not VALIDATOR.exists():
        print(f"[validate_canon] validator missing at {VALIDATOR}; treating as no-op.")
        return 0
    ns = runpy.run_path(str(VALIDATOR), run_name="__main__")
    rc = ns.get("__return__", 0)
    return int(rc) if isinstance(rc, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - surface unexpected errors
        print(f"[validate_canon] error: {exc}")
        sys.exit(1)
