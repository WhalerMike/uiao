from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_TOP_LEVEL = {"assessment_metadata", "tenant", "ksi_results"}
REQUIRED_METADATA = {"run_id", "assessment_date", "tool_version"}
REQUIRED_KSI_FIELDS = {"ksi_id", "status", "severity"}
VALID_STATUSES = {"PASS", "FAIL", "WARN"}
VALID_SEVERITIES = {"Critical", "High", "Medium", "Low"}


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_normalized_json(path: str) -> ValidationResult:
    """Validate a normalized SCuBA JSON file for IR pipeline conformance."""
    errors: List[str] = []
    warnings: List[str] = []

    p = Path(path)
    if not p.exists():
        return ValidationResult(valid=False, errors=[f"File not found: {path}"])

    try:
        data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidationResult(valid=False, errors=[f"JSON parse error: {exc}"])

    if not isinstance(data, dict):
        return ValidationResult(valid=False, errors=["Root must be a JSON object"])

    for key in sorted(REQUIRED_TOP_LEVEL - set(data.keys())):
        errors.append(f"Missing required top-level key: '{key}'")

    meta = data.get("assessment_metadata", {})
    if isinstance(meta, dict):
        for key in sorted(REQUIRED_METADATA - set(meta.keys())):
            errors.append(f"assessment_metadata missing required key: '{key}'")
    else:
        errors.append("'assessment_metadata' must be an object")

    tenant = data.get("tenant", {})
    if isinstance(tenant, str):
        errors.append("'tenant' must be an object with 'tenant_id', not a bare string")
    elif isinstance(tenant, dict):
        if "tenant_id" not in tenant:
            warnings.append("'tenant.tenant_id' not set — will default to 'unknown-tenant'")
    else:
        errors.append("'tenant' must be an object")

    ksi_results = data.get("ksi_results", [])
    if not isinstance(ksi_results, list):
        errors.append("'ksi_results' must be an array")
    else:
        if not ksi_results:
            warnings.append("'ksi_results' is empty — no evidence will be produced")
        for i, entry in enumerate(ksi_results):
            if not isinstance(entry, dict):
                errors.append(f"ksi_results[{i}] must be an object")
                continue
            for key in sorted(REQUIRED_KSI_FIELDS - set(entry.keys())):
                errors.append(f"ksi_results[{i}] missing required field: '{key}'")
            status = entry.get("status", "")
            if status and status not in VALID_STATUSES:
                errors.append(f"ksi_results[{i}] invalid status '{status}' — expected one of {sorted(VALID_STATUSES)}")
            severity = entry.get("severity", "")
            if severity and severity not in VALID_SEVERITIES:
                warnings.append(f"ksi_results[{i}] unrecognised severity '{severity}'")

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
