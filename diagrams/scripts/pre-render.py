#!/usr/bin/env python3
"""
UIAO Diagram Pre-Render Script
================================
Quarto pre-render hook that ensures all diagram SVGs are current before
the Quarto site builds. Runs as part of the Quarto render pipeline.

This script:
  1. Validates all .mmd sources (frontmatter, registry, category alignment)
  2. Renders any .mmd sources that are newer than their rendered SVGs
  3. Runs inject.py on the docs/ tree to update markdown image references
  4. Exits non-zero if any blocking error occurs (halts Quarto render)

Registration in docs/_quarto.yml:
    project:
      pre-render:
        - python ../diagrams/scripts/pre-render.py

Boundary: GCC-Moderate · Classification: Controlled
"""

import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent  # diagrams/scripts/ -> repo root
DIAGRAMS_DIR = REPO_ROOT / "diagrams"
SOURCES_DIR = DIAGRAMS_DIR / "sources"
RENDERED_FULL = DIAGRAMS_DIR / "rendered" / "full"
RENDERED_NANO = DIAGRAMS_DIR / "rendered" / "nano"
VALIDATE_SCRIPT = SCRIPT_DIR / "validate.py"
RENDER_SCRIPT = SCRIPT_DIR / "render.py"
INJECT_SCRIPT = SCRIPT_DIR / "inject.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(cmd: list[str], label: str) -> int:
    """Run a subprocess and return exit code."""
    print(f"\n── {label} ──")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return result.returncode


def needs_render(mmd_path: Path) -> bool:
    """Check if an .mmd source is newer than its rendered SVGs."""
    stem = mmd_path.stem  # e.g., DIAG_010_UIAO_Platform_Overview
    # Extract DIAG_NNN from the filename
    diag_id = "_".join(stem.split("_")[:2])  # DIAG_010

    full_svg = RENDERED_FULL / f"{diag_id}.svg"
    nano_svg = RENDERED_NANO / f"{diag_id}.svg"

    if not full_svg.exists() or not nano_svg.exists():
        return True

    mmd_mtime = mmd_path.stat().st_mtime
    full_mtime = full_svg.stat().st_mtime
    nano_mtime = nano_svg.stat().st_mtime

    return mmd_mtime > min(full_mtime, nano_mtime)


def find_sources() -> list[Path]:
    """Find all .mmd source files."""
    sources = []
    for root, dirs, files in os.walk(SOURCES_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".mmd") and not f.startswith("_"):
                sources.append(Path(root) / f)
    return sorted(sources)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("UIAO Diagram Pre-Render Pipeline")
    print("=" * 60)

    errors = 0

    # Step 1: Validate
    if VALIDATE_SCRIPT.exists():
        rc = run([sys.executable, str(VALIDATE_SCRIPT)], "Step 1/3: Validate diagram sources")
        if rc != 0:
            print("\n  ⛔ Validation failed — halting pre-render.")
            sys.exit(1)
    else:
        print(f"\n  WARNING: validate.py not found at {VALIDATE_SCRIPT}")

    # Step 2: Render stale diagrams
    print("\n── Step 2/3: Render stale diagrams ──")
    sources = find_sources()
    stale = [s for s in sources if needs_render(s)]

    if not stale:
        print("  All SVGs are current — nothing to render.")
    else:
        print(f"  {len(stale)} diagram(s) need rendering:")
        for s in stale:
            print(f"    → {s.name}")

        if RENDER_SCRIPT.exists():
            rc = run([sys.executable, str(RENDER_SCRIPT)], "Rendering diagrams")
            if rc != 0:
                print("\n  WARNING: render.py exited with errors.")
                print("  Continuing with available SVGs...")
                # Non-blocking: missing SVGs will show as placeholders
        else:
            print(f"\n  WARNING: render.py not found at {RENDER_SCRIPT}")
            print("  SVGs will be placeholders until CI renders them.")

    # Step 3: Inject into docs
    if INJECT_SCRIPT.exists():
        rc = run(
            [sys.executable, str(INJECT_SCRIPT), "--scope", "docs/"], "Step 3/3: Inject diagram references into docs"
        )
        if rc != 0:
            print("\n  WARNING: inject.py reported errors.")
            errors += 1
    else:
        print(f"\n  WARNING: inject.py not found at {INJECT_SCRIPT}")

    # Summary
    print(f"\n{'=' * 60}")
    if errors > 0:
        print(f"  Pre-render completed with {errors} warning(s).")
        print("  Quarto render will proceed — placeholders shown for missing SVGs.")
    else:
        print("  Pre-render completed successfully.")
    print(f"{'=' * 60}\n")

    # Always exit 0 so Quarto render proceeds even if renders are missing.
    # Validation errors (Step 1) are the only hard stop.
    sys.exit(0)


if __name__ == "__main__":
    main()
