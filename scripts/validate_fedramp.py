#!/usr/bin/env python3
"""FedRAMP Rev 5 OSCAL validation using trestle + fedramp plugin.
Run after generation to enforce compliance in CI/local.
"""

import subprocess
import sys
from pathlib import Path

# Paths relative to repo root
EXPORTS_DIR = Path(__file__).parent.parent / "exports" / "oscal"

ARTIFACTS = {
    "component-definition": EXPORTS_DIR / "uiao-component-definition.json",
    "ssp": EXPORTS_DIR / "uiao-ssp-skeleton.json",
    "poam": EXPORTS_DIR / "uiao-poam-template.json",
}


def run_trestle(cmd: list) -> None:
    """Run trestle command, raise on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {' '.join(cmd)} failed (code {result.returncode})")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    else:
        print(f"Success: {' '.join(cmd)}")


def main():
    print("Starting FedRAMP Rev 5 OSCAL validation...")

    for name, path in ARTIFACTS.items():
        if not path.exists():
            print(f"Skipping {name}: file not found at {path}")
            continue

        print(f"\nValidating {name} ({path.name})")

        # 1. Core OSCAL schema + constraint validation (strict mode)
        run_trestle(["trestle", "validate", "-f", str(path), "--mode", "strict"])

        # 2. FedRAMP-specific validation via plugin (if installed)
        if name == "ssp":
            run_trestle([
                "trestle", "fedramp", "validate",
                "--artifact", str(path),
                "--profile", "fedramp-rev5-moderate"
            ])

    print("\nAll FedRAMP validations passed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
