"""
m365_parser.py — Real Microsoft 365 Graph API response parsing.

Internal module consumed by M365Adapter. Handles:
- Graph API entity responses → flat resource list
- Security policy responses → policy claim list
- Multi-workload tenant config → unified claim list
- Baseline comparison (current config vs desired baseline)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Graph entity parsing
# ---------------------------------------------------------------------------

def parse_graph_entities(
    response: dict,
    workload: str = "unknown",
) -> List[dict]:
    """Extract entities from a Graph API response.

    Handles both single-entity and collection responses (with @odata value array).

    Args:
        response: Parsed JSON from a Graph API call.
        workload: The M365 workload this response belongs to.

    Returns:
        Flat list of entity dicts, each with:
        - id, displayName, @odata.type, _workload, and all original fields
    """
    entities: List[dict] = []

    # Collection response
    if "value" in response and isinstance(response["value"], list):
        for item in response["value"]:
            entity = dict(item)
            entity.setdefault("_workload", workload)
            entities.append(entity)
    # Single entity response
    elif "id" in response:
        entity = dict(response)
        entity.setdefault("_workload", workload)
        entities.append(entity)

    return entities


# ---------------------------------------------------------------------------
# Security policy parsing
# ---------------------------------------------------------------------------

_POLICY_STATE_SEVERITY: Dict[str, str] = {
    "enabled": "info",
    "disabled": "warning",
    "enabledForReportingButNotEnforced": "warning",
}


def parse_security_policies(response: dict) -> List[dict]:
    """Extract security policies from a Graph conditional access response.

    Args:
        response: Parsed JSON from /identity/conditionalAccessPolicies.

    Returns:
        List of policy dicts with severity rating based on state.
    """
    policies: List[dict] = []
    for item in response.get("value", []):
        state = item.get("state", "unknown")
        policies.append({
            "id": item.get("id", ""),
            "displayName": item.get("displayName", ""),
            "state": state,
            "severity": _POLICY_STATE_SEVERITY.get(state, "info"),
            "conditions": item.get("conditions", {}),
            "grantControls": item.get("grantControls", {}),
            "createdDateTime": item.get("createdDateTime", ""),
            "modifiedDateTime": item.get("modifiedDateTime", ""),
            "_workload": item.get("_workload", "defender-o365"),
            "@odata.type": item.get("@odata.type", "#microsoft.graph.conditionalAccessPolicy"),
        })
    return policies


# ---------------------------------------------------------------------------
# Multi-workload tenant config parsing
# ---------------------------------------------------------------------------

def parse_tenant_config(config: dict) -> List[dict]:
    """Parse a multi-workload tenant configuration bundle.

    Expects a dict with a "workloads" key mapping workload names to
    their entity collections.

    Args:
        config: {"workloads": {"exchange-online": {"mailboxSettings": [...], ...}, ...}}

    Returns:
        Flat list of all entities across all workloads, each tagged with _workload.
    """
    entities: List[dict] = []
    workloads = config.get("workloads", {})

    for workload_name, collections in workloads.items():
        if not isinstance(collections, dict):
            continue
        for collection_name, items in collections.items():
            if not isinstance(items, list):
                continue
            for item in items:
                entity = dict(item)
                entity.setdefault("_workload", workload_name)
                entity.setdefault("_collection", collection_name)
                entities.append(entity)

    return entities


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------

def compare_against_baseline(
    current: List[dict],
    baseline: Dict[str, Any],
) -> dict:
    """Compare current tenant configuration against a desired baseline.

    Args:
        current: List of entity dicts from parse_tenant_config or similar.
        baseline: Dict of {setting_key: expected_value} pairs.

    Returns:
        Dict with:
        - compliant: list of setting keys that match baseline
        - non_compliant: list of {key, expected, actual} dicts
        - missing: list of baseline keys not found in current config
        - summary: {total, compliant_count, non_compliant_count, missing_count}
    """
    # Build a flat key→value map from current config
    current_flat: Dict[str, Any] = {}
    for entity in current:
        for key, value in entity.items():
            if key.startswith("_") or key.startswith("@"):
                continue
            # Use displayName or id as prefix for disambiguation
            prefix = entity.get("displayName", entity.get("id", ""))
            flat_key = f"{prefix}.{key}" if prefix else key
            current_flat[flat_key] = value

    compliant: List[str] = []
    non_compliant: List[dict] = []
    missing: List[str] = []

    for key, expected in baseline.items():
        if key in current_flat:
            if current_flat[key] == expected:
                compliant.append(key)
            else:
                non_compliant.append({
                    "key": key,
                    "expected": expected,
                    "actual": current_flat[key],
                })
        else:
            missing.append(key)

    total = len(baseline)
    return {
        "compliant": compliant,
        "non_compliant": non_compliant,
        "missing": missing,
        "summary": {
            "total": total,
            "compliant_count": len(compliant),
            "non_compliant_count": len(non_compliant),
            "missing_count": len(missing),
        },
    }
