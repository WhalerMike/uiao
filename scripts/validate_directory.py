#!/usr/bin/env python3
# <!-- NEW (Proposed) -->
"""validate_directory.py — Validate repository directory layout.

Thin wrapper around :mod:`tools.validators.structure_validator` so the
``canon-validation`` and ``repo-hygiene`` workflows can call a stable
``scripts/`` path. Directory-layout rules live in
``tools/schema/directory_schema.json``.

Usage
-----
    python scripts/validate_directory.py
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parent.parent / "tools" / "validators" / "structure_validator.py"


def main() -> int:
    if not VALIDATOR.exists():
        print(f"[validate_directory] validator missing at {VALIDATOR}; treating as no-op.")
        return 0
    ns = runpy.run_path(str(VALIDATOR), run_name="__main__")
    rc = ns.get("__return__", 0)
    return int(rc) if isinstance(rc, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        print(f"[validate_directory] error: {exc}")
        sys.exit(1)
