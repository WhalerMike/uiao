import warnings
warnings.warn(
    "scripts/validate_with_trestle.py is deprecated. Use `uiao validate-ssp` instead.",
    DeprecationWarning,
    stacklevel=1,
)

"""Full OSCAL schema validation using compliance-trestle.

Validates OSCAL JSON artifacts in exports/oscal/ against NIST's
compliance-trestle Pydantic models for strict OSCAL 1.0 compliance.
Exits with a non-zero code if any artifact fails validation.

See also: scripts/validate_oscal.py for lightweight structural pre-checks.
"""
import json
import sys
from pathlib import Path

from trestle.oscal.component import ComponentDefinition
from trestle.oscal.ssp import SystemSecurityPlan
from trestle.oscal.poam import PlanOfActionAndMilestones

ROOT = Path(__file__).resolve().parent.parent
OSCAL_DIR = ROOT / "exports" / "oscal"

# Map each root key to its trestle model class
ARTIFACT_MODELS = {
    "component-definition": ComponentDefinition,
    "system-security-plan": SystemSecurityPlan,
    "plan-of-action-and-milestones": PlanOfActionAndMilestones,
}


def main():
    print("Validating OSCAL artifacts with compliance-trestle...")
    json_files = list(OSCAL_DIR.glob("*.json"))

    if not json_files:
        print("  No JSON files found in exports/oscal/")
        print("  Skipping validation (artifacts may not be generated yet)")
        return 0

    failures = 0
    for json_path in sorted(json_files):
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  FAIL: {json_path.name} — invalid JSON: {e}")
            failures += 1
            continue

        if not isinstance(data, dict) or not data:
            print(f"  FAIL: {json_path.name} — not a JSON object or empty")
            failures += 1
            continue

        root_key = next(iter(data))
        model_class = ARTIFACT_MODELS.get(root_key)

        if model_class is None:
            print(f"  SKIP: {json_path.name} — unknown OSCAL type '{root_key}'")
            continue

        try:
            model_class.parse_obj(data[root_key])
            print(f"  PASS: {json_path.name}")
        except Exception as e:
            print(f"  FAIL: {json_path.name}")
            print(f"    {e}")
            failures += 1

    total = len(json_files)
    print(f"\nTrestle validation complete: {total} file(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
