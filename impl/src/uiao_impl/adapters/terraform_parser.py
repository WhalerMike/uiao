"""
terraform_parser.py — Real Terraform/OpenTofu data parsing.

Internal module consumed by TerraformAdapter. Handles:
- Terraform state file (v4 JSON) → flat resource list
- Terraform plan JSON (`terraform plan -json`) → resource change list
- HCL2 configuration → desired-state resource list
- Three-way diff (live vs state vs config)

This module does NOT invoke the `terraform` CLI. It parses the output
files that the CLI produces.
"""

from __future__ import annotations

import re
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# State file parsing (v4 JSON format)
# ---------------------------------------------------------------------------

def parse_tfstate(state: dict) -> List[dict]:
    """Extract resources from a Terraform v4 state file.

    Args:
        state: Parsed JSON from a .tfstate file.

    Returns:
        Flat list of resource dicts, one per instance. Each dict has:
        - type: resource type (e.g., "aws_instance")
        - name: resource name (e.g., "web")
        - provider: provider string
        - mode: "managed" or "data"
        - attributes: flattened attribute dict from the instance
    """
    version = state.get("version", 0)
    if version != 4:
        raise ValueError(
            f"Unsupported state file version {version}; expected 4. "
            f"Terraform >=0.12 produces v4 state."
        )

    resources: List[dict] = []
    for resource in state.get("resources", []):
        rtype = resource.get("type", "unknown")
        rname = resource.get("name", "unknown")
        provider_raw = resource.get("provider", "")
        mode = resource.get("mode", "managed")

        # Normalize provider string: extract short name from
        # 'provider["registry.terraform.io/hashicorp/aws"]'
        provider = _extract_provider_short_name(provider_raw)

        for instance in resource.get("instances", []):
            attrs = instance.get("attributes", {})
            resources.append({
                "type": rtype,
                "name": rname,
                "provider": provider,
                "mode": mode,
                "attributes": attrs,
                "id": attrs.get("id", ""),
            })

    return resources


def _extract_provider_short_name(provider_raw: str) -> str:
    """Extract 'aws' from 'provider["registry.terraform.io/hashicorp/aws"]'."""
    match = re.search(r'/([^/"\]]+)["\]]?\s*$', provider_raw)
    if match:
        return match.group(1)
    # Fallback: strip 'provider["...]' wrapper
    return provider_raw.strip().strip('"').strip("'").split("/")[-1]


# ---------------------------------------------------------------------------
# Plan JSON parsing (`terraform plan -json` output)
# ---------------------------------------------------------------------------

# Map Terraform plan actions to severity levels
_ACTION_SEVERITY: Dict[str, str] = {
    "create": "info",
    "update": "warning",
    "delete": "high",
    "no-op": "none",
    "read": "none",
}


def parse_plan_json(plan: dict) -> List[dict]:
    """Extract resource changes from Terraform plan JSON.

    Args:
        plan: Parsed JSON from `terraform plan -json` output.

    Returns:
        List of change dicts. Each has:
        - address: full resource address
        - type: resource type
        - name: resource name
        - provider: provider short name
        - actions: list of action strings (e.g., ["create"])
        - severity: mapped severity (info/warning/high/none)
        - before: dict of pre-change attributes (None for create)
        - after: dict of post-change attributes (None for delete)
        - diff: dict of fields that changed (empty for create/delete)
    """
    changes: List[dict] = []
    for rc in plan.get("resource_changes", []):
        change = rc.get("change", {})
        actions = change.get("actions", [])

        # Skip no-ops and reads — they're not actionable drift
        if actions == ["no-op"] or actions == ["read"]:
            continue

        action_str = actions[0] if actions else "unknown"
        severity = _ACTION_SEVERITY.get(action_str, "info")

        before = change.get("before")
        after = change.get("after")

        # Compute field-level diff for updates
        diff: Dict[str, Any] = {}
        if before and after and action_str == "update":
            for key in set(list(before.keys()) + list(after.keys())):
                bval = before.get(key)
                aval = after.get(key)
                if bval != aval:
                    diff[key] = {"before": bval, "after": aval}

        provider_raw = rc.get("provider_name", "")
        provider = provider_raw.split("/")[-1] if "/" in provider_raw else provider_raw

        changes.append({
            "address": rc.get("address", ""),
            "type": rc.get("type", ""),
            "name": rc.get("name", ""),
            "provider": provider,
            "actions": actions,
            "severity": severity,
            "before": before,
            "after": after,
            "diff": diff,
        })

    return changes


# ---------------------------------------------------------------------------
# HCL2 configuration parsing
# ---------------------------------------------------------------------------

def parse_hcl(
    hcl_content: str,
    variables: Optional[Dict[str, Any]] = None,
) -> List[dict]:
    """Parse HCL2 configuration and extract resource blocks.

    Args:
        hcl_content: Raw HCL2 string (contents of a .tf file).
        variables: Optional variable overrides for interpolation.

    Returns:
        List of resource dicts (same shape as parse_tfstate output):
        - type, name, provider, mode="config", attributes
    """
    try:
        import hcl2
    except ImportError as exc:
        raise ImportError(
            "python-hcl2 is required for HCL parsing. "
            "Install with: pip install python-hcl2"
        ) from exc

    parsed = hcl2.load(StringIO(hcl_content))
    vars_dict = variables or {}

    resources: List[dict] = []
    for resource_block in parsed.get("resource", []):
        for rtype_raw, instances in resource_block.items():
            # python-hcl2 returns keys with embedded quotes; strip them
            rtype = rtype_raw.strip('"')
            for rname_raw, config in instances.items():
                rname = rname_raw.strip('"')
                # Resolve simple variable references
                resolved_attrs = _resolve_variables(config, vars_dict)
                resources.append({
                    "type": rtype,
                    "name": rname,
                    "provider": _infer_provider_from_type(rtype),
                    "mode": "config",
                    "attributes": resolved_attrs,
                    "id": "",  # config doesn't have IDs
                })

    return resources


def _resolve_variables(
    config: Any, variables: Dict[str, Any]
) -> Any:
    """Recursively resolve var.X references in HCL config values."""
    if isinstance(config, str):
        # Match ${var.name} or bare var.name references
        def replacer(m: re.Match) -> str:
            var_name = m.group(1)
            return str(variables.get(var_name, m.group(0)))

        result = re.sub(r'\$\{var\.(\w+)\}', replacer, config)
        result = re.sub(r'\bvar\.(\w+)\b', replacer, result)
        return result
    elif isinstance(config, dict):
        return {k: _resolve_variables(v, variables) for k, v in config.items()}
    elif isinstance(config, list):
        return [_resolve_variables(item, variables) for item in config]
    return config


def _infer_provider_from_type(resource_type: str) -> str:
    """Infer provider from resource type prefix (aws_instance → aws)."""
    parts = resource_type.split("_", 1)
    return parts[0] if len(parts) > 1 else "unknown"


# ---------------------------------------------------------------------------
# Three-way diff
# ---------------------------------------------------------------------------

def three_way_diff(
    live: List[dict],
    state: List[dict],
    config: List[dict],
) -> dict:
    """Three-way comparison: live system vs Terraform state vs HCL config.

    Each input is a list of resource dicts (from parse_tfstate or similar).
    Resources are keyed by (type, name) tuple.

    Returns:
        Dict with:
        - live_vs_state: {added: [], removed: [], changed: [], consistent: []}
        - state_vs_config: {added: [], removed: [], changed: [], consistent: []}
        - summary: {total_resources: int, drift_count: int, aligned: int}
    """
    live_map = _key_resources(live)
    state_map = _key_resources(state)
    config_map = _key_resources(config)

    live_vs_state = _compare_maps(live_map, state_map, "live", "state")
    state_vs_config = _compare_maps(state_map, config_map, "state", "config")

    all_keys = set(live_map) | set(state_map) | set(config_map)
    drift_keys = (
        set(live_vs_state["added"] + live_vs_state["removed"] + live_vs_state["changed"])
        | set(state_vs_config["added"] + state_vs_config["removed"] + state_vs_config["changed"])
    )

    return {
        "live_vs_state": live_vs_state,
        "state_vs_config": state_vs_config,
        "summary": {
            "total_resources": len(all_keys),
            "drift_count": len(drift_keys),
            "aligned": len(all_keys) - len(drift_keys),
        },
    }


def _key_resources(resources: List[dict]) -> Dict[Tuple[str, str], dict]:
    """Key a list of resources by (type, name)."""
    result: Dict[Tuple[str, str], dict] = {}
    for r in resources:
        key = (r.get("type", ""), r.get("name", ""))
        result[key] = r
    return result


def _compare_maps(
    left: Dict[Tuple[str, str], dict],
    right: Dict[Tuple[str, str], dict],
    left_label: str,
    right_label: str,
) -> dict:
    """Compare two resource maps and produce a diff summary."""
    left_keys = set(left.keys())
    right_keys = set(right.keys())

    added = sorted(f"{t}.{n}" for t, n in (right_keys - left_keys))
    removed = sorted(f"{t}.{n}" for t, n in (left_keys - right_keys))

    changed: List[str] = []
    consistent: List[str] = []
    for key in sorted(left_keys & right_keys):
        left_attrs = left[key].get("attributes", {})
        right_attrs = right[key].get("attributes", {})
        addr = f"{key[0]}.{key[1]}"
        if left_attrs != right_attrs:
            changed.append(addr)
        else:
            consistent.append(addr)

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "consistent": consistent,
    }
