"""Basic OSCAL artifact validation for CI.

Validates that generated OSCAL JSON files in exports/oscal/ are
well-formed JSON with expected root keys and required fields.
No external dependencies required (pure stdlib).

Note: This script performs lightweight structural pre-checks only.
For full OSCAL 1.0 schema compliance, see scripts/validate_with_trestle.py
which uses compliance-trestle Pydantic models.
"""

import json
import sys
import warnings
from pathlib import Path

warnings.warn(
    "scripts/validate_oscal.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)

ROOT = Path(__file__).resolve().parent.parent
OSCAL_DIR = ROOT / "exports" / "oscal"

# Expected root keys and their required sub-fields
EXPECTED_ARTIFACTS = {
    "component-definition": ["uuid", "metadata", "components"],
    "plan-of-action-and-milestones": ["uuid", "metadata", "poam-items"],
    "system-security-plan": ["uuid", "metadata"],
}


def validate_file(file_path):
    """Validate a single OSCAL JSON file."""
    errors = []
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    if not isinstance(data, dict):
        return ["Root element is not a JSON object"]

    root_keys = list(data.keys())
    if not root_keys:
        return ["Empty JSON object"]

    root_key = root_keys[0]
    print(f"  {file_path.name}: root key = '{root_key}'")

    # Check if root key is a known OSCAL type
    if root_key in EXPECTED_ARTIFACTS:
        required = EXPECTED_ARTIFACTS[root_key]
        inner = data[root_key]
        if not isinstance(inner, dict):
            errors.append(f"'{root_key}' value is not an object")
        else:
            for field in required:
                if field not in inner:
                    errors.append(f"Missing required field: {root_key}.{field}")
            # Validate metadata has required sub-fields
            meta = inner.get("metadata", {})
            if isinstance(meta, dict):
                for mf in ["title", "version", "oscal-version"]:
                    if mf not in meta:
                        errors.append(f"Missing metadata field: {mf}")
            else:
                errors.append("metadata is not an object")
    else:
        print(f"  WARNING: Unknown OSCAL root key '{root_key}'")

    return errors


def main():
    print("Validating OSCAL artifacts in exports/oscal/...")
    json_files = list(OSCAL_DIR.glob("*.json"))

    if not json_files:
        print("  No JSON files found in exports/oscal/")
        print("  Skipping validation (artifacts may not be generated yet)")
        return 0

    total_errors = 0
    for jf in sorted(json_files):
        errors = validate_file(jf)
        if errors:
            print(f"  FAIL: {jf.name}")
            for e in errors:
                print(f"    - {e}")
            total_errors += len(errors)
        else:
            print(f"  PASS: {jf.name}")

    print(f"\nValidation complete: {len(json_files)} files, {total_errors} errors")

    if total_errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
