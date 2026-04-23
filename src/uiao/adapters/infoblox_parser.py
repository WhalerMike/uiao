"""
infoblox_parser.py — Real Infoblox WAPI JSON parsing.

Internal module consumed by InfobloxAdapter. Handles:
- WAPI A-record JSON → flat record list
- WAPI CNAME-record JSON → flat record list
- WAPI network / DHCP-range / fixed-address JSON → flat object lists
- Record-set comparison for three-way drift detection
"""

from __future__ import annotations

from typing import Any, Iterable, List


def _results(payload: Any) -> Iterable[dict]:
    """Normalize WAPI response envelopes.

    WAPI returns either a bare list or an object with a `result` key
    (depends on client options). Accept both; anything else yields empty.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, list):
            return result
    return []


def parse_a_records(payload: Any) -> List[dict]:
    """Parse Infoblox A-records from WAPI JSON.

    Args:
        payload: Raw JSON from GET /wapi/vX.Y/record:a

    Returns:
        List of A-record dicts with normalized fields.
    """
    records: List[dict] = []
    for entry in _results(payload):
        records.append(
            {
                "type": "record-a",
                "name": entry.get("name", ""),
                "ipv4addr": entry.get("ipv4addr", ""),
                "view": entry.get("view", "default"),
                "zone": entry.get("zone", ""),
                "ttl": entry.get("ttl"),
                "ref": entry.get("_ref", ""),
                "comment": entry.get("comment", ""),
            }
        )
    return records


def parse_cname_records(payload: Any) -> List[dict]:
    """Parse Infoblox CNAME-records from WAPI JSON."""
    records: List[dict] = []
    for entry in _results(payload):
        records.append(
            {
                "type": "record-cname",
                "name": entry.get("name", ""),
                "canonical": entry.get("canonical", ""),
                "view": entry.get("view", "default"),
                "zone": entry.get("zone", ""),
                "ttl": entry.get("ttl"),
                "ref": entry.get("_ref", ""),
                "comment": entry.get("comment", ""),
            }
        )
    return records


def parse_networks(payload: Any) -> List[dict]:
    """Parse Infoblox network objects from WAPI JSON (network / networkcontainer)."""
    networks: List[dict] = []
    for entry in _results(payload):
        networks.append(
            {
                "type": "network",
                "cidr": entry.get("network", entry.get("address", "")),
                "view": entry.get("network_view", entry.get("view", "default")),
                "name": entry.get("name", ""),
                "tags": dict(entry.get("tags", {}) or {}),
                "ref": entry.get("_ref", ""),
                "comment": entry.get("comment", ""),
            }
        )
    return networks


def parse_dhcp_ranges(payload: Any) -> List[dict]:
    """Parse Infoblox DHCP ranges from WAPI JSON (range)."""
    ranges: List[dict] = []
    for entry in _results(payload):
        ranges.append(
            {
                "type": "dhcp-range",
                "start": entry.get("start_addr", ""),
                "end": entry.get("end_addr", ""),
                "network": entry.get("network", ""),
                "view": entry.get("network_view", "default"),
                "ref": entry.get("_ref", ""),
                "comment": entry.get("comment", ""),
            }
        )
    return ranges


def parse_fixed_addresses(payload: Any) -> List[dict]:
    """Parse Infoblox fixed-address reservations from WAPI JSON (fixedaddress)."""
    reservations: List[dict] = []
    for entry in _results(payload):
        reservations.append(
            {
                "type": "fixed-address",
                "ipv4addr": entry.get("ipv4addr", ""),
                "mac": entry.get("mac", ""),
                "name": entry.get("name", ""),
                "view": entry.get("network_view", "default"),
                "ref": entry.get("_ref", ""),
                "comment": entry.get("comment", ""),
            }
        )
    return reservations


def _record_key(record: dict) -> str:
    """Stable identity key for a parsed Infoblox record.

    Uses the WAPI `_ref` when present (globally unique inside a grid);
    falls back to `<type>:<view>:<name-or-cidr-or-ip>` so comparisons
    still work on hand-crafted baselines that lack refs.
    """
    ref = record.get("ref") or ""
    if ref:
        return ref
    rtype = record.get("type", "unknown")
    view = record.get("view", "default")
    ident = record.get("name") or record.get("cidr") or record.get("ipv4addr") or record.get("start", "")
    return f"{rtype}:{view}:{ident}"


def diff_record_sets(
    baseline: List[dict],
    live: List[dict],
) -> dict:
    """Compare a canon baseline record set against live WAPI output.

    Args:
        baseline: Expected records (from canon / prior snapshot).
        live: Current records pulled from WAPI.

    Returns:
        Dict with added/removed/modified/consistent keys + summary counts.
    """
    baseline_map = {_record_key(r): r for r in baseline}
    live_map = {_record_key(r): r for r in live}

    baseline_keys = set(baseline_map.keys())
    live_keys = set(live_map.keys())

    added = sorted(live_keys - baseline_keys)
    removed = sorted(baseline_keys - live_keys)

    modified: List[str] = []
    consistent: List[str] = []
    for key in sorted(baseline_keys & live_keys):
        if baseline_map[key] != live_map[key]:
            modified.append(key)
        else:
            consistent.append(key)

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "consistent": consistent,
        "summary": {
            "total": len(baseline_keys | live_keys),
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "consistent_count": len(consistent),
            "drift_count": len(added) + len(removed) + len(modified),
        },
    }
