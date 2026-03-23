"""UIAO Build Readiness Validator

Pre-flight check to ensure all critical architectural assets exist
before running generate_docs.py. This prevents broken builds when
visuals or data files are still being committed.
"""
import os
import sys
import warnings

warnings.warn(
    "scripts/validate_build_readiness.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)

REQUIRED_FILES = [
    "data/nist_crosswalk.yml",
    "data/roadmap.yml",
    "visuals/README.md",
]

REQUIRED_DIRS = [
    "visuals",
]


def check_readiness():
    missing = []

    # Check Directories
    for d in REQUIRED_DIRS:
        if not os.path.exists(d):
            missing.append(f"Directory Missing: {d}")

    # Check Files
    for f in REQUIRED_FILES:
        if not os.path.exists(f):
            missing.append(f"File Missing: {f}")

    if missing:
        print("BUILD BLOCKED: The following architectural assets are missing:")
        for m in missing:
            print(f"  - {m}")
        print("\nACTION: Wait for Comet/Perplexity to finish the Visuals/Data sync.")
        sys.exit(1)
    else:
        print("BUILD READY: All UIAO Pillars and Visuals are present.")
        sys.exit(0)


if __name__ == "__main__":
    check_readiness()
